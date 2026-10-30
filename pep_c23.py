import argparse
import hashlib
import json
import pathlib
import shutil
import statistics
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
MAX_SESSION_MESSAGE_BYTES = 1_048_576
MAX_TYPED_NODES = 10_000
MAX_PARSER_STEPS = 4_096
MAX_CHECKER_STEPS = 4_096
SOURCES = (
    ROOT / "examples" / "pep_lexer.pep",
    ROOT / "examples" / "pep_parser.pep",
    ROOT / "tests" / "pep_checker_a13.pep",
    ROOT / "tests" / "pep_c23_emitter.pep",
)


class Session:
    def __init__(self):
        started = time.perf_counter_ns()
        self.process = subprocess.Popen(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "session", "--jsonl"],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1,
        )
        self.process_spawn_ms = (time.perf_counter_ns() - started) / 1_000_000
        self.request_bytes_total = 0
        self.response_bytes_total = 0
        self.last_request_bytes = 0
        self.last_response_bytes = 0
        self.last_response = None

    def send(self, request):
        encoded = json.dumps(request, ensure_ascii=False, separators=(",", ":"))
        request_bytes = len(encoded.encode("utf-8")) + 1
        if request_bytes > MAX_SESSION_MESSAGE_BYTES:
            raise RuntimeError("Pep C23 session request exceeds the 1 MiB JSONL message limit")
        self.last_request_bytes = request_bytes
        self.request_bytes_total += request_bytes
        self.process.stdin.write(encoded + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            detail = self.process.stderr.read()
            raise RuntimeError("Pep session ended without a response" + (": " + detail.strip() if detail else ""))
        response_bytes = len(line.encode("utf-8"))
        if response_bytes > MAX_SESSION_MESSAGE_BYTES:
            raise RuntimeError("Pep C23 session response exceeds the 1 MiB JSONL message limit")
        self.last_response_bytes = response_bytes
        self.response_bytes_total += response_bytes
        try:
            self.last_response = json.loads(line)
            return self.last_response
        except json.JSONDecodeError as error:
            raise RuntimeError("Pep session returned invalid JSON: " + line[:400]) from error

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            self.process.wait(timeout=30)
        detail = self.process.stderr.read()
        self.process.stdout.close()
        self.process.stderr.close()
        if self.process.returncode:
            raise RuntimeError(f"Pep session exited {self.process.returncode}: {detail.strip()}")


def require(response, key, expected, label):
    actual = response.get(key)
    if actual != expected:
        raise RuntimeError(f"{label}: expected {key}={expected!r}, received {response!r}")


def typed_record(status, parts=(), diagnostic=""):
    return {
        "type": "PepC23Emission",
        "fields": [
            {"name": "status", "value": {"type": "Str", "value": status}},
            {"name": "sourceParts", "value": {"type": "List[Str]", "value": [
                {"type": "Str", "value": part} for part in parts
            ]}},
            {"name": "diagnostic", "value": {"type": "Str", "value": diagnostic}},
        ],
    }


def typed(type_name, value):
    return {"type": type_name, "value": str(value) if type_name == "Int" else value}


def typed_list(item_type, values=()):
    return {"type": f"List[{item_type}]", "value": list(values)}


def typed_record_value(type_name, fields):
    return {"type": type_name, "fields": [
        {"name": name, "value": value} for name, value in fields
    ]}


def parser_cursor_value(document, revision, done=False, next_node_id=0,
                        lex_done=False, lex_stage="validate", top_level_child_index=0):
    lex_cursor = typed_record_value("LexCursor", [
        ("document", typed("Str", document)), ("revision", typed("Str", revision)),
        ("status", typed("Str", "valid")), ("stage", typed("Str", lex_stage)),
        ("offset", typed("Int", 0)), ("line", typed("Int", 1)),
        ("column", typed("Int", 1)), ("mode", typed("Str", "")),
        ("tokenStart", typed("Int", 0)), ("tokenLine", typed("Int", 1)),
        ("tokenColumn", typed("Int", 1)), ("integerValue", typed("Int", 0)),
        ("integerOverflow", typed("Bool", False)), ("escapePending", typed("Bool", False)),
        ("stringPartStart", typed("Int", 0)), ("stringPartsReversed", typed_list("Str")),
    ])
    stream = typed_record_value("ParserStream", [
        ("lexCursor", lex_cursor), ("bufferedTokens", typed_list("LexToken")),
        ("lexDone", typed("Bool", lex_done)), ("lexErrorCode", typed("Str", "")),
        ("lexErrorStart", typed("Int", 0)), ("lexErrorEnd", typed("Int", 0)),
        ("lexErrorLine", typed("Int", 0)), ("lexErrorColumn", typed("Int", 0)),
    ])
    return typed_record_value("ParserCursor", [
        ("document", typed("Str", document)), ("revision", typed("Str", revision)),
        ("stream", stream), ("nextNodeId", typed("Int", next_node_id)),
        ("done", typed("Bool", done)), ("functionActive", typed("Bool", False)),
        ("functionName", typed("Str", "")), ("functionStartByte", typed("Int", 0)),
        ("functionLine", typed("Int", 1)), ("functionColumn", typed("Int", 1)),
        ("functionRootId", typed("Int", 0)), ("functionChildIndex", typed("Int", 0)),
        ("topLevelChildIndex", typed("Int", top_level_child_index)),
        ("frames", typed_list("ParserFrame")),
    ])


def parser_chunk_value(document, revision, cursor, status="complete", nodes=(), done=True,
                       error_code="", message="", start=0, ending=0, line=0, column=0):
    return typed_record_value("ParserChunk", [
        ("document", typed("Str", document)), ("revision", typed("Str", revision)),
        ("status", typed("Str", status)), ("nodes", typed_list("FlatAstNode", nodes)),
        ("cursor", cursor), ("done", typed("Bool", done)),
        ("errorCode", typed("Str", error_code)), ("message", typed("Str", message)),
        ("errorStart", typed("Int", start)), ("errorEnd", typed("Int", ending)),
        ("errorLine", typed("Int", line)), ("errorColumn", typed("Int", column)),
    ])


def typed_fields(value, expected_type, label):
    if not isinstance(value, dict) or value.get("type") != expected_type:
        raise RuntimeError(f"{label}: expected typed {expected_type}")
    fields = value.get("fields")
    if not isinstance(fields, list):
        raise RuntimeError(f"{label}: missing typed fields")
    result = {}
    for item in fields:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or "value" not in item:
            raise RuntimeError(f"{label}: malformed typed field")
        if item["name"] in result:
            raise RuntimeError(f"{label}: duplicate typed field {item['name']}")
        result[item["name"]] = item["value"]
    return result


def typed_field_value(fields, name, type_name, label):
    value = fields.get(name)
    if not isinstance(value, dict) or value.get("type") != type_name:
        raise RuntimeError(f"{label}: field {name} must have type {type_name}")
    return value.get("value")


class PepCompilerToolBudgetError(RuntimeError):
    def __init__(self, stage, tool, target_document, target_revision, tool_revision,
                 tool_source_location):
        self.analysis_status = "INCONCLUSIVE"
        self.stage = stage
        self.code = "PEP_RUNTIME_STEP_LIMIT"
        self.tool = tool
        self.target_document = target_document
        self.target_revision = target_revision
        self.target_span = None
        self.tool_revision = tool_revision
        self.tool_source_location = tool_source_location
        location = tool_source_location or "unavailable"
        super().__init__(
            f"analysis_status={self.analysis_status}; stage={stage}; code={self.code}; "
            f"target_document={target_document}; target_revision={target_revision}; "
            f"target_source_span=unavailable; compiler_tool={tool}; "
            f"compiler_bundle_revision={tool_revision}; "
            f"compiler_bundle_location={location}"
        )


def invoke_tool(session, tool, arguments, semantic_target, tool_revision, label, stage=None):
    response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                             "op": "tool_invoke", "tool": tool,
                             "arguments": arguments, "semanticTarget": semantic_target})
    if response.get("outcome") != "ok":
        error = response.get("error", {})
        if stage and error.get("code") == "PEP_RUNTIME_STEP_LIMIT":
            message = error.get("message", "")
            marker = " at "
            location = None
            if marker in message:
                candidate = message.rsplit(marker, 1)[-1]
                line, separator, column = candidate.partition(":")
                if separator and line.isdigit() and column.isdigit():
                    location = f"compiler-bundle:{line}:{column}"
            raise PepCompilerToolBudgetError(
                stage, tool, semantic_target.get("document", "unavailable"),
                semantic_target.get("revision", "unavailable"), tool_revision, location
            )
    require(response, "outcome", "ok", label)
    require(response, "tool", tool, label)
    require(response, "revision", tool_revision, label)
    return response["result"]


def parser_node_identity(node, source_length):
    fields = typed_fields(node, "FlatAstNode", "parser node")
    values = {}
    for name in ("id", "parentId", "childIndex", "integerValue", "startByte", "endByte", "line", "column"):
        raw = typed_field_value(fields, name, "Int", "parser node")
        try:
            values[name] = int(raw)
        except (TypeError, ValueError) as error:
            raise RuntimeError(f"Pep C23 parser returned a malformed AST node {name}") from error
    for name in ("role", "kind", "text"):
        typed_field_value(fields, name, "Str", "parser node")
    typed_field_value(fields, "booleanValue", "Bool", "parser node")
    string_parts = typed_field_value(fields, "stringParts", "List[Str]", "parser node")
    if not isinstance(string_parts, list) or any(
        not isinstance(part, dict) or part.get("type") != "Str" for part in string_parts
    ):
        raise RuntimeError("Pep C23 parser returned malformed string parts on an AST node")
    node_id = values["id"]
    if node_id < 0 or values["childIndex"] < 0:
        raise RuntimeError("Pep C23 parser returned a negative AST node id or child index")
    if values["startByte"] < 0 or values["endByte"] < values["startByte"] or values["endByte"] > source_length:
        raise RuntimeError("Pep C23 parser returned an AST span outside the source bytes")
    return node_id, values["parentId"]


def validate_parser_node_sequence(node_ids):
    ordered_ids = sorted(node_ids)
    if ordered_ids != list(range(len(ordered_ids))):
        raise RuntimeError("Pep C23 parser AST node ids are not exactly 0..n-1")


def validate_parser_parent_links(node_ids, parent_ids):
    for node_id, parent_id in parent_ids:
        if parent_id != -1 and parent_id not in node_ids:
            raise RuntimeError("Pep C23 parser returned an AST node with a missing parent")
        if parent_id >= node_id:
            raise RuntimeError("Pep C23 parser parent IDs do not match its preorder tree contract")


def validate_parser_final_outcome(status, error_code):
    if status == "complete":
        if error_code:
            raise RuntimeError("Pep C23 parser marked an errored result complete")
        return
    if status in {"incomplete", "invalid"}:
        if not error_code:
            raise RuntimeError("Pep C23 parser returned a failed status without an error code")
        return
    raise RuntimeError(f"Pep C23 parser returned unknown final status {status!r}")


def parse_target(session, source_bytes, target, tool_revision):
    parse_started = time.perf_counter_ns()
    request_bytes_before = session.request_bytes_total
    response_bytes_before = session.response_bytes_total
    max_request_bytes = 0
    max_response_bytes = 0
    semantic_target = {"document": target["document"], "revision": target["revision"],
                       "entryFunctions": []}
    start_started = time.perf_counter_ns()
    cursor = invoke_tool(session, "pep-c23-parser-start", [], semantic_target,
                         tool_revision, "start parser", stage="parser")
    parser_start_ms = (time.perf_counter_ns() - start_started) / 1_000_000
    parser_start_request_bytes = session.last_request_bytes
    parser_start_response_bytes = session.last_response_bytes
    max_request_bytes = parser_start_request_bytes
    max_response_bytes = parser_start_response_bytes
    cursor_fields = typed_fields(cursor, "ParserCursor", "start parser")
    if typed_field_value(cursor_fields, "document", "Str", "start cursor") != target["document"] or \
       typed_field_value(cursor_fields, "revision", "Str", "start cursor") != target["revision"]:
        raise RuntimeError("Pep C23 parser start returned a cursor for another source revision")

    nodes = []
    node_ids = set()
    parent_ids = []
    final_fields = None
    step_elapsed_ms = []
    maximum_steps = min(len(source_bytes) + 2, MAX_PARSER_STEPS)
    for _ in range(maximum_steps):
        previous_cursor = cursor
        step_started = time.perf_counter_ns()
        chunk = invoke_tool(session, "pep-c23-parser-step", [cursor], semantic_target,
                            tool_revision, "advance parser", stage="parser")
        step_elapsed_ms.append((time.perf_counter_ns() - step_started) / 1_000_000)
        max_request_bytes = max(max_request_bytes, session.last_request_bytes)
        max_response_bytes = max(max_response_bytes, session.last_response_bytes)
        chunk_fields = typed_fields(chunk, "ParserChunk", "parser step")
        if typed_field_value(chunk_fields, "document", "Str", "parser chunk") != target["document"] or \
           typed_field_value(chunk_fields, "revision", "Str", "parser chunk") != target["revision"]:
            raise RuntimeError("Pep C23 parser chunk belongs to another source revision")
        status = typed_field_value(chunk_fields, "status", "Str", "parser chunk")
        chunk_nodes = typed_field_value(chunk_fields, "nodes", "List[FlatAstNode]", "parser chunk")
        next_cursor = chunk_fields.get("cursor")
        typed_fields(next_cursor, "ParserCursor", "parser chunk cursor")
        next_fields = typed_fields(next_cursor, "ParserCursor", "parser chunk cursor")
        if typed_field_value(next_fields, "document", "Str", "parser chunk cursor") != target["document"] or \
           typed_field_value(next_fields, "revision", "Str", "parser chunk cursor") != target["revision"]:
            raise RuntimeError("Pep C23 parser cursor belongs to another source revision")
        done = typed_field_value(chunk_fields, "done", "Bool", "parser chunk")
        for name in ("errorCode", "message"):
            typed_field_value(chunk_fields, name, "Str", "parser chunk")
        for name in ("errorStart", "errorEnd", "errorLine", "errorColumn"):
            typed_field_value(chunk_fields, name, "Int", "parser chunk")
        if not isinstance(chunk_nodes, list):
            raise RuntimeError("Pep C23 parser chunk nodes are not a list")
        for node in chunk_nodes:
            node_id, parent_id = parser_node_identity(node, len(source_bytes))
            if node_id < 0 or node_id in node_ids:
                raise RuntimeError("Pep C23 parser returned a negative or duplicate AST node id")
            node_ids.add(node_id)
            parent_ids.append((node_id, parent_id))
            nodes.append(node)
            if len(nodes) > MAX_TYPED_NODES:
                raise RuntimeError("Pep C23 parser AST exceeds the 10,000-node typed transport limit")
        if not done and (status != "continuing" or next_cursor == previous_cursor):
            raise RuntimeError("Pep C23 parser continuation did not make valid forward progress")
        if done and status not in {"complete", "incomplete", "invalid"}:
            raise RuntimeError(f"Pep C23 parser finished with unknown status {status!r}")
        cursor = next_cursor
        final_fields = chunk_fields
        if done:
            break
    else:
        raise RuntimeError(f"Pep C23 parser exceeded its bounded {maximum_steps}-step host limit")

    if final_fields is None:
        raise RuntimeError("Pep C23 parser produced no final chunk")
    final_status = typed_field_value(final_fields, "status", "Str", "final parser chunk")
    validate_parser_node_sequence(node_ids)
    if final_status == "complete":
        validate_parser_parent_links(node_ids, parent_ids)
    nodes.sort(key=lambda node: int(typed_field_value(
        typed_fields(node, "FlatAstNode", "parser node"), "id", "Int", "parser node")))
    error_code = typed_field_value(final_fields, "errorCode", "Str", "final parser chunk")
    validate_parser_final_outcome(final_status, error_code)
    error_start = int(typed_field_value(final_fields, "errorStart", "Int", "final parser chunk"))
    error_end = int(typed_field_value(final_fields, "errorEnd", "Int", "final parser chunk"))
    error_line = int(typed_field_value(final_fields, "errorLine", "Int", "final parser chunk"))
    error_column = int(typed_field_value(final_fields, "errorColumn", "Int", "final parser chunk"))
    if error_code and (error_start < 0 or error_end < error_start or error_end > len(source_bytes) or
                       error_line < 1 or error_column < 1):
        raise RuntimeError("Pep C23 parser returned an error span outside the source")
    parsed = typed_record_value("ParserProgress", [
        ("document", typed("Str", target["document"])),
        ("revision", typed("Str", target["revision"])),
        ("status", final_fields["status"]),
        ("nodes", typed_list("FlatAstNode", nodes)),
        ("done", final_fields["done"]),
        ("errorCode", final_fields["errorCode"]),
        ("message", final_fields["message"]),
        ("errorStart", final_fields["errorStart"]),
        ("errorEnd", final_fields["errorEnd"]),
        ("errorLine", final_fields["errorLine"]),
        ("errorColumn", final_fields["errorColumn"]),
    ])

    session.parser_measurements = {
        "parser_status": typed_field_value(final_fields, "status", "Str", "final parser chunk"),
        "parser_error_code": typed_field_value(final_fields, "errorCode", "Str", "final parser chunk"),
        "parser_error_start": typed_field_value(final_fields, "errorStart", "Int", "final parser chunk"),
        "parser_error_end": typed_field_value(final_fields, "errorEnd", "Int", "final parser chunk"),
        "parser_error_line": typed_field_value(final_fields, "errorLine", "Int", "final parser chunk"),
        "parser_error_column": typed_field_value(final_fields, "errorColumn", "Int", "final parser chunk"),
        "parser_start_ms": parser_start_ms,
        "parser_step_count": len(step_elapsed_ms),
        "parser_step_elapsed_ms": step_elapsed_ms,
        "parser_step_median_ms": statistics.median(step_elapsed_ms) if step_elapsed_ms else 0.0,
        "parser_elapsed_ms": (time.perf_counter_ns() - parse_started) / 1_000_000,
        "parser_request_bytes": session.request_bytes_total - request_bytes_before,
        "parser_response_bytes": session.response_bytes_total - response_bytes_before,
        "parser_max_request_bytes": max_request_bytes,
        "parser_max_response_bytes": max_response_bytes,
        "parser_node_count": len(nodes),
        "parser_host_step_limit": maximum_steps,
    }
    return parsed


def parser_progress(document, revision):
    return typed_record_value("ParserProgress", [
        ("document", typed("Str", document)), ("revision", typed("Str", revision)),
        ("status", typed("Str", "complete")), ("nodes", typed_list("FlatAstNode")),
        ("done", typed("Bool", True)), ("errorCode", typed("Str", "")),
        ("message", typed("Str", "")), ("errorStart", typed("Int", 0)),
        ("errorEnd", typed("Int", 0)), ("errorLine", typed("Int", 0)),
        ("errorColumn", typed("Int", 0)),
    ])


def checker_report(document, revision):
    fields = [("document", typed("Str", document)), ("revision", typed("Str", revision)),
              ("status", typed("Str", "valid")), ("syntaxNodeCount", typed("Int", 0))]
    for name, item_type in (("functions", "CheckedFunction"), ("bindings", "BindingFact"),
                            ("references", "ResolvedName"), ("calls", "ResolvedCall"),
                            ("expressionTypes", "ExpressionTypeFact"), ("holes", "HoleFact"),
                            ("diagnostics", "CheckDiagnostic")):
        fields.append((name, typed_list(item_type)))
    return typed_record_value("CheckerReport", fields)


def checker_cursor_value(document, revision, parsed, phase, done=False):
    empty_node = typed_record_value("FlatAstNode", [
        ("id", typed("Int", -1)), ("parentId", typed("Int", -1)),
        ("childIndex", typed("Int", -1)), ("role", typed("Str", "")),
        ("kind", typed("Str", "")), ("text", typed("Str", "")),
        ("integerValue", typed("Int", 0)), ("booleanValue", typed("Bool", False)),
        ("stringParts", typed_list("Str")), ("startByte", typed("Int", 0)),
        ("endByte", typed("Int", 0)), ("line", typed("Int", 1)),
        ("column", typed("Int", 1)),
    ])
    empty_bindings = typed_record_value("BindingCollection", [
        ("bindings", typed_list("BindingFact")), ("diagnostics", typed_list("CheckDiagnostic")),
    ])
    empty_names = typed_record_value("NameResolution", [
        ("references", typed_list("ResolvedName")), ("diagnostics", typed_list("CheckDiagnostic")),
    ])
    empty_types = typed_record_value("TypeAnalysis", [
        ("expressionTypes", typed_list("ExpressionTypeFact")),
        ("diagnostics", typed_list("CheckDiagnostic")),
        ("unreachable", typed_record_value("UnreachableLookup", [
            ("found", typed("Bool", False)), ("node", empty_node),
        ])),
    ])
    return typed_record_value("CheckerCursor", [
        ("document", typed("Str", document)), ("revision", typed("Str", revision)),
        ("phase", typed("Str", phase)), ("done", typed("Bool", done)),
        ("parsed", parsed), ("nodes", typed_list("FlatAstNode")),
        ("functions", typed_list("CheckedFunction")), ("bindingResult", empty_bindings),
        ("nameResult", empty_names), ("typedBindings", typed_list("BindingFact")),
        ("typeResult", empty_types), ("typeOffset", typed("Int", 0)),
        ("holes", typed_list("HoleFact")), ("report", checker_report(document, revision)),
        ("validation", typed_record_value("TreeValidation", [
            ("sourceLength", typed("Int", 0)), ("nextNode", typed("Int", 0)),
            ("nextRoot", typed("Int", 0)), ("valid", typed("Bool", True)),
            ("stack", typed_list("ValidationFrame")), ("totalCount", typed("Int", 0)),
        ])),
    ])


def check_target(session, parsed, target, tool_revision):
    started = time.perf_counter_ns()
    request_bytes_before = session.request_bytes_total
    response_bytes_before = session.response_bytes_total
    cursor = invoke_tool(session, "pep-c23-checker-start", [parsed], target,
                         tool_revision, "start checker", stage="checker")
    start_ms = (time.perf_counter_ns() - started) / 1_000_000
    max_request_bytes = session.last_request_bytes
    max_response_bytes = session.last_response_bytes
    parser_nodes = typed_field_value(typed_fields(parsed, "ParserProgress", "parser result"),
                                     "nodes", "List[FlatAstNode]", "parser result")
    node_count = len(parser_nodes)
    binding_kinds = {"parameter", "let", "var", "for_in", "binding_pattern"}
    binding_count = sum(
        typed_field_value(typed_fields(node, "FlatAstNode", "parser node"), "kind", "Str", "parser node")
        in binding_kinds
        for node in parser_nodes
    )
    maximum_steps = min(MAX_CHECKER_STEPS,
                        8 + 3 * ((node_count + 31) // 32) + (node_count + 7) // 8 + (binding_count + 7) // 8)
    step_elapsed_ms = []
    cursor_fields = typed_fields(cursor, "CheckerCursor", "checker start cursor")
    for _ in range(maximum_steps):
        if typed_field_value(cursor_fields, "document", "Str", "checker cursor") != target["document"] or \
           typed_field_value(cursor_fields, "revision", "Str", "checker cursor") != target["revision"]:
            raise RuntimeError("Pep checker cursor changed the authorised source revision")
        if typed_field_value(cursor_fields, "done", "Bool", "checker cursor"):
            break
        previous_cursor = cursor
        step_started = time.perf_counter_ns()
        cursor = invoke_tool(session, "pep-c23-checker-step", [cursor, typed_list("FlatAstNode", parser_nodes)], target,
                             tool_revision, "advance checker", stage="checker")
        step_elapsed_ms.append((time.perf_counter_ns() - step_started) / 1_000_000)
        max_request_bytes = max(max_request_bytes, session.last_request_bytes)
        max_response_bytes = max(max_response_bytes, session.last_response_bytes)
        if cursor == previous_cursor:
            raise RuntimeError("Pep checker continuation did not make progress")
        cursor_fields = typed_fields(cursor, "CheckerCursor", "checker step cursor")
    if not typed_field_value(cursor_fields, "done", "Bool", "final checker cursor"):
        raise RuntimeError(f"Pep checker exceeded the host continuation limit of {maximum_steps} steps")
    report = cursor_fields.get("report")
    report_fields = typed_fields(report, "CheckerReport", "checker report")
    if typed_field_value(report_fields, "document", "Str", "checker report") != target["document"] or \
       typed_field_value(report_fields, "revision", "Str", "checker report") != target["revision"]:
        raise RuntimeError("Pep checker report changed the authorised source revision")
    measurements = {}
    measurements.update({
        "checker_start_ms": start_ms,
        "checker_step_count": len(step_elapsed_ms),
        "checker_step_elapsed_ms": step_elapsed_ms,
        "checker_step_median_ms": statistics.median(step_elapsed_ms) if step_elapsed_ms else 0.0,
        "checker_elapsed_ms": (time.perf_counter_ns() - started) / 1_000_000,
        "checker_request_bytes": session.request_bytes_total - request_bytes_before,
        "checker_response_bytes": session.response_bytes_total - response_bytes_before,
        "checker_max_request_bytes": max_request_bytes,
        "checker_max_response_bytes": max_response_bytes,
        "checker_node_count": node_count,
        "checker_host_step_limit": maximum_steps,
    })
    return report, measurements


def emit(source_bytes, measurements=None):
    measurements = measurements if measurements is not None else {}
    emit_started = time.perf_counter_ns()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in SOURCES)
    except OSError as error:
        raise RuntimeError(f"cannot read Pep C23 compiler source: {error}") from error
    session = Session()
    measurements["process_spawn_ms"] = session.process_spawn_ms
    measurements["source_sha256"] = hashlib.sha256(source_bytes).hexdigest()
    try:
        measurements["compiler_bundle_sha256"] = hashlib.sha256(bundle.encode("utf-8")).hexdigest()
        bundle_started = time.perf_counter_ns()
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                              "name": "pep-c23-emitter", "metadataOnly": True})
        measurements["compiler_bundle_open_ms"] = (time.perf_counter_ns() - bundle_started) / 1_000_000
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        tool_document, tool_revision = opened["document"], opened["revision"]
        validation_started = time.perf_counter_ns()
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "stage-validation", "bytes": []})
        require(sample, "outcome", "ok", "open stage validation source")
        empty_parsed = parser_progress(sample["document"], sample["revision"])
        empty_checked = checker_report(sample["document"], sample["revision"])
        target_spec = {"document": sample["document"], "revision": sample["revision"], "entryFunctions": []}
        start_cursor = parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = parser_cursor_value(sample["document"], sample["revision"],
                                              done=True, lex_done=True, lex_stage="done")
        parser_tools = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             parser_chunk_value(sample["document"], sample["revision"], finished_cursor)),
        ]
        for tool, function, arguments, expected in parser_tools:
            registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_register", "tool": tool,
                                      "document": tool_document, "revision": tool_revision,
                                      "function": function})
            require(registered, "status", "Registered", f"register {tool}")
            validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": tool_document, "revision": tool_revision,
                                      "testVectors": [{"arguments": arguments, "expect": expected,
                                          "semanticTarget": target_spec}]})
            require(validated, "status", "Validated", f"validate {tool}")
            active = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_activate", "tool": tool,
                                   "document": tool_document, "revision": tool_revision})
            require(active, "status", "Active", f"activate {tool}")

        empty_expected = [
            ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
            ("pep-c23-checker-start", "checker_start", [empty_parsed],
             checker_cursor_value(sample["document"], sample["revision"], empty_parsed, "validation")),
            ("pep-c23-checker-step", "checker_step",
             [checker_cursor_value(sample["document"], sample["revision"], empty_parsed, "validation"), typed_list("FlatAstNode")],
             checker_cursor_value(sample["document"], sample["revision"], empty_parsed, "functions")),
        ]
        for tool, function, arguments, expected in empty_expected:
            registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_register", "tool": tool,
                                      "document": tool_document, "revision": tool_revision,
                                      "function": function})
            require(registered, "status", "Registered", f"register {tool}")
            validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": tool_document, "revision": tool_revision,
                                      "testVectors": [{"arguments": arguments, "expect": expected,
                                          "semanticTarget": target_spec}]})
            require(validated, "status", "Validated", f"validate {tool}")
            active = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_activate", "tool": tool,
                                   "document": tool_document, "revision": tool_revision})
            require(active, "status", "Active", f"activate {tool}")
        registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_register", "tool": "pep-c23-emitter",
                                  "document": tool_document, "revision": tool_revision,
                                  "function": "emit_c23_checked"})
        require(registered, "status", "Registered", "register emitter")
        expected_emission = typed_record("unsupported", (),
                                         "Pep C23 emission requires a top-level function named main")
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_validate", "tool": "pep-c23-emitter",
                                  "document": tool_document, "revision": tool_revision,
                                  "testVectors": [{"arguments": [empty_parsed, empty_checked],
                                      "expect": expected_emission, "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", "validate emitter")
        activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_activate", "tool": "pep-c23-emitter",
                                  "document": tool_document, "revision": tool_revision})
        require(activated, "status", "Active", "activate emitter")
        measurements["stage_registration_validation_ms"] = (time.perf_counter_ns() - validation_started) / 1_000_000

        target_open_started = time.perf_counter_ns()
        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "native-target",
                               "bytes": list(source_bytes)})
        measurements["target_open_parse_check_ms"] = (time.perf_counter_ns() - target_open_started) / 1_000_000
        require(target, "outcome", "ok", "open source")
        measurements["source_document"] = target["document"]
        measurements["source_revision"] = target["revision"]
        semantic_target = {"document": target["document"], "revision": target["revision"], "entryFunctions": []}
        parsed_value = parse_target(session, source_bytes, target, tool_revision)
        measurements.update(session.parser_measurements)
        checker_started = time.perf_counter_ns()
        checked_report, checker_measurements = check_target(
            session, parsed_value, semantic_target, tool_revision)
        measurements.update(checker_measurements)
        measurements["checker_stage_ms"] = (time.perf_counter_ns() - checker_started) / 1_000_000
        report_fields = typed_fields(checked_report, "CheckerReport", "checker report")
        measurements["checker_status"] = typed_field_value(report_fields, "status", "Str", "checker report")
        emitter_started = time.perf_counter_ns()
        emitter_request_bytes_before = session.request_bytes_total
        emitter_response_bytes_before = session.response_bytes_total
        emitted = invoke_tool(session, "pep-c23-emitter", [parsed_value, checked_report], semantic_target,
                              tool_revision, "emit checked source", stage="emitter")
        measurements["emitter_stage_ms"] = (time.perf_counter_ns() - emitter_started) / 1_000_000
        measurements["emitter_request_bytes"] = session.request_bytes_total - emitter_request_bytes_before
        measurements["emitter_response_bytes"] = session.response_bytes_total - emitter_response_bytes_before
        fields = {item["name"]: item["value"] for item in emitted["fields"]}
        if fields["status"]["value"] != "emitted":
            measurements["emitter_status"] = fields["status"]["value"]
            measurements["emitter_diagnostic"] = fields["diagnostic"]["value"]
            raise ValueError(fields["diagnostic"]["value"] or "Pep C23 emitter rejected the program")
        measurements["emitter_status"] = fields["status"]["value"]
        measured = session.send({"schemaVersion": 3, "op": "metrics"})
        require(measured, "outcome", "ok", "read compiler stage metrics")
        measurements["session_metrics"] = measured["metrics"]
        return "".join(part["value"] for part in fields["sourceParts"]["value"])
    finally:
        measurements["c23_pipeline_elapsed_ms"] = (time.perf_counter_ns() - emit_started) / 1_000_000
        if session.last_response and isinstance(session.last_response.get("metrics"), dict):
            measurements.setdefault("session_metrics", session.last_response["metrics"])
        session.close()


def compiler_path(requested):
    candidates = ([requested] if requested else ["clang", "clang.exe",
        str(pathlib.Path.home() / "scoop" / "apps" / "llvm" / "current" / "bin" / "clang.exe")])
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return pathlib.Path(resolved)
        path = pathlib.Path(candidate)
        if path.is_file():
            return path.resolve()
    wanted = requested or "Clang"
    raise RuntimeError(f"C23 compiler not found: {wanted}; install Clang or pass --compiler PATH")


def parser():
    result = argparse.ArgumentParser(prog="pep.ps1 build-c23/run-c23",
        description="Build or run the supported Pep subset through the Pep-written strict C23 emitter.")
    result.add_argument("command", choices=("build-c23", "run-c23"))
    result.add_argument("source", type=pathlib.Path)
    result.add_argument("-o", "--output", type=pathlib.Path,
                        help="native executable path (required for build-c23)")
    result.add_argument("--compiler", help="Clang executable path (defaults to Clang on PATH)")
    result.add_argument("--emit-c", type=pathlib.Path,
                        help="generated C23 source path (defaults beside the executable)")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    source_path = args.source.resolve()
    if not source_path.is_file():
        print(f"Pep source file not found: {source_path}", file=sys.stderr)
        return 2
    if args.command == "build-c23" and args.output is None:
        print("build-c23 requires -o/--output", file=sys.stderr)
        return 2
    try:
        source_bytes = source_path.read_bytes()
        source_identity = hashlib.sha256(source_bytes).hexdigest()[:12]
        default_name = f"{source_path.stem}-{source_identity}.exe"
        output = (args.output or (ROOT / "_build" / "native" / default_name)).resolve()
        c_path = (args.emit_c or output.with_suffix(".c")).resolve()
        if source_path == output or source_path == c_path or output == c_path:
            raise ValueError("Pep source, generated C, and executable paths must be distinct")
        compiler = compiler_path(args.compiler)
        source = emit(source_bytes)
        c_path.parent.mkdir(parents=True, exist_ok=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        c_path.write_text(source, encoding="utf-8", newline="\n")
        built = subprocess.run([str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic",
                                "-Werror", "-O2", str(c_path), "-o", str(output)],
                               text=True, capture_output=True, check=False)
        if built.stdout:
            print(built.stdout, end="")
        if built.stderr:
            print(built.stderr, end="", file=sys.stderr)
        if built.returncode:
            return built.returncode
        stream = sys.stderr if args.command == "run-c23" else sys.stdout
        print(f"C23: {c_path}", file=stream)
        print(f"Executable: {output}", file=stream)
        if args.command == "run-c23":
            ran = subprocess.run([str(output)], text=True, check=False)
            return ran.returncode
        return 0
    except ValueError as error:
        print(f"Pep C23 unsupported: {error}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Pep C23 error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
