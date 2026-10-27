"""PEP-PERFORMANCE-03 real A12 pipeline laboratory.

This module is deliberately test-only.  It talks to a SHA-pinned A12 checkout
through the public JSONL session route and never imports or edits A12 sources.
The adapter keeps transport evidence separate from the independent structural
checks performed over the returned typed values.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import queue
import statistics
import subprocess
import argparse
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Iterable


ROOT = pathlib.Path(__file__).resolve().parents[1]
A12_SHA = "69a47fe77187666bdd045b8dc8a9f633a7dd49d7"
A12_ROOT = ROOT / "_build" / "perf03-a12"
ARTIFACT_ROOT = ROOT / "_build" / "perf03"
MAX_SOURCE_BYTES = 65_536
MAX_TRACE_CALLS = 4_096


class PipelineError(AssertionError):
    """The real pipeline or its independent evidence checks failed."""


class SessionInfrastructureError(PipelineError):
    """The JSONL child failed independently of Pep semantic results."""

    def __init__(self, message: str, details: dict[str, Any]):
        super().__init__(message)
        self.details = details


class SessionResponseTimeout(SessionInfrastructureError):
    """The JSONL child did not produce a response before the finite deadline."""


def revision(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def typed(kind: str, value: Any) -> dict[str, Any]:
    return {"type": kind, "value": value}


def typed_list(name: str, values: list[dict[str, Any]]) -> dict[str, Any]:
    return typed(f"List[{name}]", values)


def typed_record(name: str, fields: Iterable[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    return {"type": name, "fields": [{"name": k, "value": v} for k, v in fields]}


def fields(value: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["name"]: item["value"] for item in value["fields"]}


def scalar(value: dict[str, Any]) -> Any:
    kind = value["type"]
    if kind in {"Int", "Bool", "Str"}:
        return value["value"]
    raise PipelineError(f"expected scalar, got {kind}")


def cursor_value(document: str, rev: str, *, done: bool = False, next_node_id: int = 0,
                 lex_done: bool = False, lex_stage: str = "validate",
                 top_level_child_index: int = 0) -> dict[str, Any]:
    lex_cursor = typed_record("LexCursor", [
        ("document", typed("Str", document)), ("revision", typed("Str", rev)),
        ("status", typed("Str", "valid")), ("stage", typed("Str", lex_stage)),
        ("offset", typed("Int", "0")), ("line", typed("Int", "1")),
        ("column", typed("Int", "1")), ("mode", typed("Str", "")),
        ("tokenStart", typed("Int", "0")), ("tokenLine", typed("Int", "1")),
        ("tokenColumn", typed("Int", "1")), ("integerValue", typed("Int", "0")),
        ("integerOverflow", typed("Bool", False)), ("escapePending", typed("Bool", False)),
        ("stringPartStart", typed("Int", "0")), ("stringPartsReversed", typed_list("Str", [])),
    ])
    stream = typed_record("ParserStream", [
        ("lexCursor", lex_cursor), ("bufferedTokens", typed_list("LexToken", [])),
        ("lexDone", typed("Bool", lex_done)), ("lexErrorCode", typed("Str", "")),
        ("lexErrorStart", typed("Int", "0")), ("lexErrorEnd", typed("Int", "0")),
        ("lexErrorLine", typed("Int", "0")), ("lexErrorColumn", typed("Int", "0")),
    ])
    return typed_record("ParserCursor", [
        ("document", typed("Str", document)), ("revision", typed("Str", rev)),
        ("stream", stream), ("nextNodeId", typed("Int", str(next_node_id))),
        ("done", typed("Bool", done)), ("functionActive", typed("Bool", False)),
        ("functionName", typed("Str", "")), ("functionStartByte", typed("Int", "0")),
        ("functionLine", typed("Int", "1")), ("functionColumn", typed("Int", "1")),
        ("functionRootId", typed("Int", "0")), ("functionChildIndex", typed("Int", "0")),
        ("topLevelChildIndex", typed("Int", str(top_level_child_index))),
        ("frames", typed_list("ParserFrame", [])),
    ])


def chunk_value(document: str, rev: str, cursor: dict[str, Any], *, done: bool = True) -> dict[str, Any]:
    return typed_record("ParserChunk", [
        ("document", typed("Str", document)), ("revision", typed("Str", rev)),
        ("status", typed("Str", "complete")), ("nodes", typed_list("FlatAstNode", [])),
        ("cursor", cursor), ("done", typed("Bool", done)),
        ("errorCode", typed("Str", "")), ("message", typed("Str", "")),
        ("errorStart", typed("Int", "0")), ("errorEnd", typed("Int", "0")),
        ("errorLine", typed("Int", "0")), ("errorColumn", typed("Int", "0")),
    ])


class JsonlSession:
    DEFAULT_RESPONSE_TIMEOUT_S = 30.0

    def __init__(self, root: pathlib.Path, *, response_timeout_s: float | None = None,
                 command: list[str] | None = None):
        configured_timeout = (self.DEFAULT_RESPONSE_TIMEOUT_S if response_timeout_s is None
                              else response_timeout_s)
        if not isinstance(configured_timeout, (int, float)) or not math.isfinite(configured_timeout) or configured_timeout <= 0:
            raise ValueError("response_timeout_s must be a finite positive number")
        env = os.environ.copy()
        env.setdefault("PEPIN_OPAM_ROOT", os.environ.get("OPAMROOT", r"D:\opam-roots\pepin"))
        started = time.perf_counter_ns()
        self.process = subprocess.Popen(
            command or ["pwsh", "-NoProfile", "-File", str(root / "pep.ps1"), "session", "--jsonl"],
            cwd=root, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1,
        )
        self.spawn_ms = (time.perf_counter_ns() - started) / 1_000_000
        self.response_timeout_s = float(configured_timeout)
        self._stdout_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._stderr_chunks: list[str] = []
        self._reader_failed: BaseException | None = None
        self._terminated_for_failure = False
        self._closed = False
        self._stdout_thread = threading.Thread(target=self._read_stdout, name="pepin-jsonl-stdout", daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, name="pepin-jsonl-stderr", daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _read_stdout(self) -> None:
        try:
            if self.process.stdout is None:
                self._stdout_queue.put(("reader_error", RuntimeError("stdout pipe is unavailable")))
                return
            while True:
                line = self.process.stdout.readline()
                if not line:
                    break
                self._stdout_queue.put(("line", line))
        except BaseException as exc:
            self._reader_failed = exc
            self._stdout_queue.put(("reader_error", exc))
        finally:
            self._stdout_queue.put(("eof", None))

    def _read_stderr(self) -> None:
        try:
            if self.process.stderr is not None:
                self._stderr_chunks.append(self.process.stderr.read())
        except BaseException as exc:
            self._stderr_chunks.append(f"<stderr reader failed: {exc!r}>")

    def _stderr_text(self) -> str:
        return "".join(self._stderr_chunks)

    def _terminate_child(self, reason: str) -> dict[str, Any]:
        self._terminated_for_failure = True
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5.0)
        self._stdout_thread.join(timeout=2.0)
        self._stderr_thread.join(timeout=2.0)
        partial: list[str] = []
        while True:
            try:
                kind, value = self._stdout_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "line" and value:
                partial.append(value)
        return {"kind": reason, "returncode": self.process.returncode,
                "partialStdout": "".join(partial), "stderr": self._stderr_text(),
                "timeoutSeconds": self.response_timeout_s}

    def send(self, request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        if self._closed or self._terminated_for_failure:
            raise SessionInfrastructureError("session is closed after an infrastructure failure",
                                              {"kind": "session-unusable"})
        if self.process.stdin is None or self.process.stdout is None:
            details = self._terminate_child("launcher-failure")
            raise SessionInfrastructureError("session pipes are unavailable", details)
        encoded = (json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        started = time.perf_counter_ns()
        try:
            self.process.stdin.write(encoded.decode("utf-8"))
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            details = self._terminate_child("launcher-failure")
            details["writeError"] = repr(exc)
            raise SessionInfrastructureError("JSONL child rejected the request pipe", details) from exc
        try:
            kind, value = self._stdout_queue.get(timeout=self.response_timeout_s)
        except queue.Empty as exc:
            details = self._terminate_child("response-timeout")
            raise SessionResponseTimeout(
                f"JSONL response exceeded {self.response_timeout_s:g}s deadline", details
            ) from exc
        if kind == "eof":
            details = self._terminate_child("process-closed-before-response")
            raise SessionInfrastructureError("JSONL child closed output before responding", details)
        if kind == "reader_error":
            details = self._terminate_child("launcher-failure")
            details["readerError"] = repr(value)
            raise SessionInfrastructureError("JSONL stdout reader failed", details)
        line = value
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        if not line:
            details = self._terminate_child("process-closed-before-response")
            raise SessionInfrastructureError("session ended without response", details)
        response_bytes = len(line.encode("utf-8"))
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            details = {"kind": "malformed-json", "rawResponse": line,
                       "stderr": self._stderr_text(), "returncode": self.process.poll()}
            raise SessionInfrastructureError("invalid JSONL response", details) from exc
        return response, {
            "requestBytes": len(encoded), "responseBytes": response_bytes,
            "elapsedMs": elapsed_ms,
        }

    def close(self) -> None:
        if self._closed:
            return
        if self.process.stdin:
            try:
                self.process.stdin.close()
            except OSError:
                pass
        if self.process.poll() is None:
            self.process.wait(timeout=30)
        self._stdout_thread.join(timeout=2.0)
        self._stderr_thread.join(timeout=2.0)
        stderr = self._stderr_text()
        if self.process.returncode != 0 and not self._terminated_for_failure:
            self._closed = True
            raise SessionInfrastructureError(
                f"session exited {self.process.returncode}",
                {"kind": "launcher-failure", "returncode": self.process.returncode, "stderr": stderr},
            )
        if self.process.stdout:
            self.process.stdout.close()
        if self.process.stderr:
            self.process.stderr.close()
        self._closed = True


def normalize_nodes(result: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for node in fields(result)["nodes"]["value"]:
        item = fields(node)
        kind = scalar(item["kind"])
        if kind == "integer":
            value = int(scalar(item["integerValue"]))
        elif kind == "boolean":
            value = scalar(item["booleanValue"])
        elif kind == "string":
            value = "".join(scalar(part) for part in item["stringParts"]["value"])
        else:
            value = scalar(item["text"])
        span = None if kind.startswith("type_") else {
            "start": int(scalar(item["startByte"])), "end": int(scalar(item["endByte"])),
            "line": int(scalar(item["line"])), "column": int(scalar(item["column"])),
        }
        output.append({
            "id": int(scalar(item["id"])), "parentId": int(scalar(item["parentId"])),
            "childIndex": int(scalar(item["childIndex"])), "role": scalar(item["role"]),
            "kind": kind, "value": value, "span": span,
        })
    return output


def ast_count(value: Any) -> int:
    """Independent OCaml-to-wire node count, including explicit type nodes."""
    def type_count(name: str) -> int:
        return 1 + (type_count(name[5:-1]) if name.startswith("List[") and name.endswith("]") else 0)

    def expression(node: dict[str, Any]) -> int:
        kind = node["kind"]
        if kind in {"int", "bool", "string", "name", "hole"}:
            return 1
        if kind in {"call", "list"}:
            children = node["arguments"] if kind == "call" else node["elements"]
            return 1 + sum(expression(child) for child in children)
        if kind == "binary":
            return 1 + expression(node["left"]) + expression(node["right"])
        if kind == "unary":
            return 1 + expression(node["operand"])
        if kind == "if":
            return 1 + expression(node["condition"]) + expression(node["then"]) + expression(node["else"])
        if kind == "record":
            return 1 + sum(1 + expression(field["value"]) for field in node["fields"])
        if kind == "field_access":
            return 1 + expression(node["value"])
        if kind == "match":
            return 1 + expression(node["value"]) + sum(1 + pattern(arm["pattern"]) + expression(arm["result"]) for arm in node["arms"])
        raise PipelineError(f"independent AST counter lacks expression kind {kind}")

    def pattern(node: dict[str, Any]) -> int:
        return 1 + sum(pattern(child) for child in node.get("arguments", []))

    def statement(node: dict[str, Any]) -> int:
        kind = node["kind"]
        if kind == "expression":
            return 1 + expression(node["value"])
        if kind in {"let", "var"}:
            return 1 + (type_count(node["annotation"]) if node.get("annotation") else 0) + expression(node["value"])
        if kind in {"assignment", "return"}:
            return 1 + expression(node["value"])
        if kind == "block":
            return 1 + sum(statement(child) for child in node["statements"])
        if kind == "if_statement":
            return 1 + expression(node["condition"]) + sum(statement(child) for child in node["then"] + node["else"])
        if kind == "for_in":
            return 1 + expression(node["iterable"]) + sum(statement(child) for child in node["body"])
        if kind == "while":
            return 1 + expression(node["condition"]) + sum(statement(child) for child in node["body"])
        raise PipelineError(f"independent AST counter lacks statement kind {kind}")

    def top(node: dict[str, Any]) -> int:
        kind = node["kind"]
        if kind == "function":
            return 1 + sum(1 + type_count(param["type"]) for param in node["parameters"]) + type_count(node["returnType"]) + sum(statement(child) for child in node["body"])
        if kind == "record_declaration":
            return 1 + sum(1 + type_count(field["type"]) for field in node["fields"])
        if kind == "union_declaration":
            return 1 + sum(1 + sum(type_count(arg) for arg in variant["arguments"]) for variant in node["variants"])
        return statement(node)

    if not isinstance(value, list):
        raise PipelineError("OCaml AST root is not a list")
    return sum(top(node) for node in value)


def ast_kinds(value: Any) -> list[str]:
    """Independent syntax-kind walk used as a corruption-resistant oracle summary."""
    result: list[str] = []
    if isinstance(value, dict):
        if isinstance(value.get("kind"), str) and "span" in value:
            result.append(value["kind"])
        for key in sorted(value):
            if key not in {"span", "kind"}:
                result.extend(ast_kinds(value[key]))
    elif isinstance(value, list):
        for child in value:
            result.extend(ast_kinds(child))
    return result


def topology_check(nodes: list[dict[str, Any]]) -> None:
    allowed_roles = {
        "top_level", "parameter", "return_type", "statement", "left", "right",
        "condition", "then", "else", "value", "arm", "pattern", "result",
        "field", "element", "argument", "operand", "iterable", "body",
        "type", "annotation", "field_type", "variant_argument", "element_type",
        "declaration", "variant", "target",
    }
    ids = [node["id"] for node in nodes]
    if ids != list(range(len(nodes))):
        raise PipelineError(f"non-contiguous node ids: {ids[:8]}")
    by_id = {node["id"]: node for node in nodes}
    roots = [node for node in nodes if node["parentId"] == -1]
    if [node["childIndex"] for node in roots] != list(range(len(roots))):
        raise PipelineError("top-level child indexes are not source ordered")
    seen_edges: set[tuple[int, str, int]] = set()
    for node in nodes:
        if node["role"] not in allowed_roles:
            raise PipelineError(f"unknown topology role: {node['role']}")
        if node["childIndex"] < 0:
            raise PipelineError(f"negative child index for node {node['id']}")
        parent = node["parentId"]
        if parent != -1 and (parent not in by_id or parent >= node["id"]):
            raise PipelineError(f"invalid parent edge for node {node['id']}")
        edge = (parent, node["role"], node["childIndex"])
        if edge in seen_edges:
            raise PipelineError(f"duplicate topology edge {edge}")
        seen_edges.add(edge)
        current = node["id"]
        trail: set[int] = set()
        while current != -1:
            if current in trail:
                raise PipelineError(f"topology cycle at {current}")
            trail.add(current)
            current = by_id[current]["parentId"]


def validate_continuation_rows(rows: list[dict[str, Any]]) -> None:
    """Fail closed on a missing, repeated or prematurely terminal chain."""
    if not rows or rows[0].get("stage") != "parser_start":
        raise PipelineError("trace does not begin with parser_start")
    steps = rows[1:]
    if not steps or any(row.get("stage") != "parser_step" for row in steps):
        raise PipelineError("trace contains a non-parser continuation stage")
    fingerprints = [row.get("inputCursorSha256") for row in steps]
    if any(not fingerprint for fingerprint in fingerprints) or len(set(fingerprints)) != len(fingerprints):
        raise PipelineError("continuation cursor was missing or repeated")
    if any(not isinstance(row.get("sourceOffset"), int) or row["sourceOffset"] < 0 for row in steps):
        raise PipelineError("continuation source offset is invalid")
    if not steps[-1].get("done"):
        raise PipelineError("continuation trace has no terminal result")
    if any(row.get("done") for row in steps[:-1]):
        raise PipelineError("continuation trace has an early terminal result")


def simulated_coalescing(rows: list[dict[str, Any]], width: int, *, message_budget: int = 1_048_576) -> dict[str, Any]:
    """Model host aggregation of already-produced chunks; never changes execution."""
    if width < 1:
        raise ValueError("coalescing width must be positive")
    steps = [row for row in rows if row.get("stage") == "parser_step"]
    groups = [steps[index:index + width] for index in range(0, len(steps), width)]
    grouped_responses = [sum(int(row["responseBytes"]) for row in group) for group in groups]
    return {"kind": "test-only-response-coalescing-model", "width": width,
            "sourceSteps": len(steps), "modelledHostCalls": 1 + len(groups),
            "maxGroupedResponseBytes": max(grouped_responses, default=0),
            "underMessageBudget": all(size <= message_budget for size in grouped_responses),
            "productionProtocolChanged": False}


@dataclass
class ParserMeasurement:
    spawn_ms: float
    setup_ms: float
    target_open_ms: float
    tool_setup_ms: float
    source_bytes: int
    source_revision: str
    status: str
    node_count: int
    ast_node_count: int
    ast_kind_count: int
    calls: int
    request_bytes: int
    response_bytes: int
    max_request_bytes: int
    max_response_bytes: int
    elapsed_ms: float
    call_rows: list[dict[str, Any]]
    nodes: list[dict[str, Any]]
    target_status: str = ""
    target_ast: list[dict[str, Any]] = field(default_factory=list)
    target_diagnostics: list[dict[str, Any]] = field(default_factory=list)
    parser_error_code: str = ""
    parser_error_start: int = 0
    parser_error_end: int = 0
    parser_error_line: int = 0
    parser_error_column: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "spawnMs": self.spawn_ms, "setupMs": self.setup_ms,
            "targetOpenMs": self.target_open_ms, "toolSetupMs": self.tool_setup_ms,
            "sourceBytes": self.source_bytes, "sourceRevision": self.source_revision,
            "status": self.status, "nodeCount": self.node_count,
            "independentOcamlAstNodeCount": self.ast_node_count,
            "independentOcamlKindCount": self.ast_kind_count,
            "calls": self.calls, "requestBytes": self.request_bytes,
            "responseBytes": self.response_bytes, "maxRequestBytes": self.max_request_bytes,
            "maxResponseBytes": self.max_response_bytes, "elapsedMs": self.elapsed_ms,
            "callRows": self.call_rows, "nodes": self.nodes,
            "targetStatus": self.target_status, "targetDiagnostics": self.target_diagnostics,
            "parserError": {"code": self.parser_error_code, "start": self.parser_error_start,
                             "end": self.parser_error_end, "line": self.parser_error_line,
                             "column": self.parser_error_column},
            "coalescingModels": [simulated_coalescing(self.call_rows, width) for width in (2, 4, 8, 16, 32)],
        }


def _register(session: JsonlSession, tool: str, function: str, document: str,
              revision_value: str, arguments: list[dict[str, Any]], expected: dict[str, Any],
              target_document: str, target_revision: str) -> float:
    started = time.perf_counter_ns()
    for request in (
        {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
         "tool": tool, "document": document, "revision": revision_value, "function": function},
        {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
         "tool": tool, "document": document, "revision": revision_value,
         "testVectors": [{"arguments": arguments, "expect": expected,
                          "semanticTarget": {"document": target_document, "revision": target_revision, "entryFunctions": []}}]},
        {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
         "tool": tool, "document": document, "revision": revision_value},
    ):
        response, _ = session.send(request)
        if response.get("status") not in {"Registered", "Validated", "Active"}:
            raise PipelineError(f"{tool} setup failed: {response}")
    return (time.perf_counter_ns() - started) / 1_000_000


def parse_source(source: str | bytes, *, a12_root: pathlib.Path = A12_ROOT) -> ParserMeasurement:
    raw = source if isinstance(source, bytes) else source.encode("utf-8")
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("source exceeds unchanged 65,536-byte cap")
    bundle = (a12_root / "examples" / "pep_lexer.pep").read_text(encoding="utf-8") + "\n" + \
        (a12_root / "examples" / "pep_parser.pep").read_text(encoding="utf-8")
    session = JsonlSession(a12_root)
    try:
        setup_started = time.perf_counter_ns()
        bundle_response, _ = session.send({"schemaVersion": 3, "op": "open", "name": "p03-parser-bundle",
                                           "source": bundle, "metadataOnly": True})
        if bundle_response.get("outcome") != "ok":
            raise PipelineError(f"bundle open failed: {bundle_response}")
        tool_document, tool_revision = bundle_response["document"], bundle_response["revision"]
        registration_response, _ = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "p03-registration",
                                                 "bytes": []})
        if registration_response.get("outcome") != "ok":
            raise PipelineError(f"registration target open failed: {registration_response}")
        registration_document, registration_revision = registration_response["document"], registration_response["revision"]
        target_open_started = time.perf_counter_ns()
        target_response, target_open_timing = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "p03-target",
                                           "bytes": list(raw)})
        if target_response.get("outcome") != "ok":
            raise PipelineError(f"target open failed: {target_response}")
        target_document, target_revision = target_response["document"], target_response["revision"]
        initial = cursor_value(registration_document, registration_revision)
        terminal = cursor_value(registration_document, registration_revision, done=True, lex_done=True, lex_stage="done")
        tool_setup_started = time.perf_counter_ns()
        _register(session, "p03-parser-start", "parser_start", tool_document, tool_revision, [], initial,
                  registration_document, registration_revision)
        _register(session, "p03-parser-step", "parser_step", tool_document, tool_revision, [terminal],
                  chunk_value(registration_document, registration_revision, terminal),
                  registration_document, registration_revision)
        setup_ms = (time.perf_counter_ns() - setup_started) / 1_000_000
        tool_setup_ms = (time.perf_counter_ns() - tool_setup_started) / 1_000_000
        semantic_target = {"document": target_document, "revision": target_revision, "entryFunctions": []}
        started, start_timing = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
            "op": "tool_invoke", "tool": "p03-parser-start", "arguments": [],
            "semanticTarget": semantic_target})
        if started.get("outcome") != "ok":
            raise PipelineError(f"parser_start failed: {started}")
        cursor = started["result"]
        rows = [dict(start_timing, stage="parser_start", sourceOffset=0)]
        nodes: list[dict[str, Any]] = []
        total_requests = start_timing["requestBytes"]
        total_responses = start_timing["responseBytes"]
        max_request = start_timing["requestBytes"]
        max_response = start_timing["responseBytes"]
        loop_started = time.perf_counter_ns()
        for step_index in range(MAX_TRACE_CALLS):
            nested = fields(fields(fields(cursor)["stream"])["lexCursor"])
            source_offset = int(scalar(nested["offset"]))
            cursor_bytes = json.dumps(cursor, sort_keys=True, separators=(",", ":")).encode("utf-8")
            invoked, timing = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                "op": "tool_invoke", "tool": "p03-parser-step", "arguments": [cursor],
                "semanticTarget": semantic_target})
            if invoked.get("outcome") != "ok":
                raise PipelineError(f"parser_step failed at {step_index}: {invoked}")
            result_fields = fields(invoked["result"])
            if scalar(result_fields["document"]) != target_document or scalar(result_fields["revision"]) != target_revision:
                raise PipelineError("parser chunk changed document or revision")
            chunk = result_fields["nodes"]["value"]
            nodes.extend(normalize_nodes({"fields": [{"name": "nodes", "value": {"value": chunk}}]}))
            done = bool(scalar(result_fields["done"]))
            rows.append(dict(timing, stage="parser_step", index=step_index, sourceOffset=source_offset,
                             nodes=len(chunk), done=done,
                             inputCursorBytes=len(cursor_bytes),
                             inputCursorSha256=hashlib.sha256(cursor_bytes).hexdigest(),
                             cursorBytes=len(json.dumps(result_fields["cursor"], separators=(",", ":")).encode("utf-8"))))
            total_requests += timing["requestBytes"]
            total_responses += timing["responseBytes"]
            max_request = max(max_request, timing["requestBytes"])
            max_response = max(max_response, timing["responseBytes"])
            next_cursor = result_fields["cursor"]
            if not done and json.dumps(next_cursor, sort_keys=True) == json.dumps(cursor, sort_keys=True):
                raise PipelineError("nonterminal parser cursor did not advance")
            cursor = next_cursor
            if done:
                break
        else:
            raise PipelineError("parser continuation exceeded bounded trace call count")
        validate_continuation_rows(rows)
        ast = target_response.get("ast") or []
        ast_count_value = ast_count(ast)
        ast_kinds_value = len(ast_kinds(ast))
        result_status = scalar(result_fields["status"])
        nodes.sort(key=lambda node: node["id"])
        if result_status == "complete":
            topology_check(nodes)
        if result_status == "complete" and ast_count_value != len(nodes):
            raise PipelineError(f"independent OCaml AST count {ast_count_value} != parser nodes {len(nodes)}")
        return ParserMeasurement(
            spawn_ms=session.spawn_ms, setup_ms=setup_ms, target_open_ms=target_open_timing["elapsedMs"],
            tool_setup_ms=tool_setup_ms,
            source_bytes=len(raw), source_revision=target_revision,
            status=result_status, node_count=len(nodes),
            ast_node_count=ast_count_value, ast_kind_count=ast_kinds_value,
            calls=len(rows), request_bytes=total_requests, response_bytes=total_responses,
            max_request_bytes=max_request, max_response_bytes=max_response,
            elapsed_ms=(time.perf_counter_ns() - loop_started) / 1_000_000,
            call_rows=rows, nodes=nodes,
            target_status=target_response.get("status", ""),
            target_ast=ast,
            target_diagnostics=target_response.get("diagnostics") or [],
            parser_error_code=scalar(result_fields["errorCode"]),
            parser_error_start=int(scalar(result_fields["errorStart"])),
            parser_error_end=int(scalar(result_fields["errorEnd"])),
            parser_error_line=int(scalar(result_fields["errorLine"])),
            parser_error_column=int(scalar(result_fields["errorColumn"])),
        )
    finally:
        session.close()


WORKLOADS: tuple[tuple[str, str | bytes], ...] = (
    ("expression", "1 + 2 * 3 - 4"),
    ("function", "fn main(x: Int) -> Int { let y: Int = -x; return y }"),
    ("record", "type Point { x: Int, y: Int }\nfn main() -> Int { let point = Point { x: 1, y: 2 }; return point.x }"),
    ("union_match", "type Maybe = None() | Some(Int)\nfn pick(value: Maybe) -> Int { return match value { None() => 0 Some(number) => number } }"),
    ("control", "fn count(xs: List[Int]) -> Int { var total = 0; for item in xs { total = total + item } while total <= 10 { total = total + 1 } if total <= 10 { return 0 } else { return total } }"),
    ("string_unicode_crlf", b'fn text() -> Str {\r\n  return "caf\xc3\xa9"\r\n}'),
    ("list_call", "fn main() -> Int { let values = [1, 2,]; return choose(values, 0) }"),
    ("malformed", "fn main() -> Int { return (1 + 2"),
)


def workload_metadata(name: str, source: str | bytes) -> dict[str, Any]:
    raw = source if isinstance(source, bytes) else source.encode("utf-8")
    return {"name": name, "sourceBytes": len(raw), "sourceSha256": hashlib.sha256(raw).hexdigest(),
            "sourceRevision": revision(raw), "lineCount": raw.count(b"\n") + 1,
            "crlfBytes": raw.count(b"\r\n"), "unicodeBytes": len(raw) - len(raw.decode("utf-8").encode("ascii", "ignore"))}


def generated_declarations(count: int) -> str:
    if count < 1:
        raise ValueError("count must be positive")
    statements = "".join(f"let item{index}: Int = {index}; " for index in range(count))
    return f"fn generated() -> Int {{ {statements} return item{count - 1} }}"


def run_workloads(*, include_scaling: bool = False) -> dict[str, Any]:
    rows = []
    workload_list = list(WORKLOADS)
    if include_scaling:
        workload_list.extend((f"declarations_{count}", generated_declarations(count)) for count in (8, 16, 32, 64))
    for name, source in workload_list:
        row = workload_metadata(name, source)
        measurement = parse_source(source)
        row["measurement"] = measurement.as_dict()
        rows.append(row)
    complete = [row["measurement"] for row in rows if row["measurement"]["status"] == "complete"]
    return {"kind": "pep-performance-03-real-a12", "a12Sha": A12_SHA,
            "sourceCapBytes": MAX_SOURCE_BYTES, "workloads": rows,
            "summary": summarize([ParserMeasurement(
                spawn_ms=item["spawnMs"], setup_ms=item["setupMs"], target_open_ms=item["targetOpenMs"],
                tool_setup_ms=item["toolSetupMs"],
                source_bytes=item["sourceBytes"], source_revision=item["sourceRevision"],
                status=item["status"], node_count=item["nodeCount"],
                ast_node_count=item["independentOcamlAstNodeCount"], ast_kind_count=item["independentOcamlKindCount"],
                calls=item["calls"], request_bytes=item["requestBytes"], response_bytes=item["responseBytes"],
                max_request_bytes=item["maxRequestBytes"], max_response_bytes=item["maxResponseBytes"],
                elapsed_ms=item["elapsedMs"], call_rows=item["callRows"], nodes=item["nodes"],
            ) for item in complete]) if complete else {"workloads": 0}}


def warm_session_measurement(sources: Iterable[str] | None = None) -> dict[str, Any]:
    """Measure several real parser targets over one retained session."""
    source_list = list(sources or (generated_declarations(8), generated_declarations(16), generated_declarations(32)))
    session = JsonlSession(A12_ROOT)
    try:
        setup_started = time.perf_counter_ns()
        bundle = (A12_ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8") + "\n" + \
            (A12_ROOT / "examples" / "pep_parser.pep").read_text(encoding="utf-8")
        bundle_response, _ = session.send({"schemaVersion": 3, "op": "open", "name": "p03-warm-bundle",
                                           "source": bundle, "metadataOnly": True})
        if bundle_response.get("outcome") != "ok":
            raise PipelineError(f"warm bundle open failed: {bundle_response}")
        registration_response, _ = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "p03-warm-registration", "bytes": []})
        registration_document, registration_revision = registration_response["document"], registration_response["revision"]
        tool_document, tool_revision = bundle_response["document"], bundle_response["revision"]
        initial = cursor_value(registration_document, registration_revision)
        terminal = cursor_value(registration_document, registration_revision, done=True, lex_done=True, lex_stage="done")
        _register(session, "p03-warm-start", "parser_start", tool_document, tool_revision, [], initial,
                  registration_document, registration_revision)
        _register(session, "p03-warm-step", "parser_step", tool_document, tool_revision, [terminal],
                  chunk_value(registration_document, registration_revision, terminal),
                  registration_document, registration_revision)
        setup_ms = (time.perf_counter_ns() - setup_started) / 1_000_000
        rows = []
        for index, source in enumerate(source_list):
            raw = source.encode("utf-8")
            target_started = time.perf_counter_ns()
            target, target_timing = session.send({"schemaVersion": 3, "op": "open_bytes",
                                                  "name": f"p03-warm-target-{index}", "bytes": list(raw)})
            if target.get("outcome") != "ok":
                raise PipelineError(f"warm target open failed: {target}")
            target_document, target_revision = target["document"], target["revision"]
            semantic_target = {"document": target_document, "revision": target_revision, "entryFunctions": []}
            started, start_timing = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                "op": "tool_invoke", "tool": "p03-warm-start", "arguments": [],
                "semanticTarget": semantic_target})
            cursor = started["result"]
            trace = [dict(start_timing, stage="parser_start", sourceOffset=0)]
            nodes: list[dict[str, Any]] = []
            request_bytes = start_timing["requestBytes"]
            response_bytes = start_timing["responseBytes"]
            started_loop = time.perf_counter_ns()
            for step_index in range(MAX_TRACE_CALLS):
                nested = fields(fields(fields(cursor)["stream"])["lexCursor"])
                source_offset = int(scalar(nested["offset"]))
                cursor_payload = json.dumps(cursor, sort_keys=True, separators=(",", ":")).encode("utf-8")
                invoked, timing = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                    "op": "tool_invoke", "tool": "p03-warm-step", "arguments": [cursor],
                    "semanticTarget": semantic_target})
                result_fields = fields(invoked["result"])
                chunk = result_fields["nodes"]["value"]
                nodes.extend(normalize_nodes({"fields": [{"name": "nodes", "value": {"value": chunk}}]}))
                done = bool(scalar(result_fields["done"]))
                trace.append(dict(timing, stage="parser_step", index=step_index, sourceOffset=source_offset,
                                  nodes=len(chunk), done=done, inputCursorBytes=len(cursor_payload),
                                  inputCursorSha256=hashlib.sha256(cursor_payload).hexdigest(),
                                  cursorBytes=len(json.dumps(result_fields["cursor"], separators=(",", ":")).encode("utf-8"))))
                request_bytes += timing["requestBytes"]
                response_bytes += timing["responseBytes"]
                cursor = result_fields["cursor"]
                if done:
                    break
            else:
                raise PipelineError("warm parser continuation exceeded trace bound")
            validate_continuation_rows(trace)
            nodes.sort(key=lambda node: node["id"])
            topology_check(nodes)
            expected_count = ast_count(target.get("ast") or [])
            if expected_count != len(nodes):
                raise PipelineError(f"warm AST count {expected_count} != node count {len(nodes)}")
            rows.append({"index": index, "sourceBytes": len(raw), "sourceRevision": target_revision,
                         "nodeCount": len(nodes), "calls": len(trace), "requestBytes": request_bytes,
                         "responseBytes": response_bytes, "targetOpenMs": target_timing["elapsedMs"],
                         "parserMs": (time.perf_counter_ns() - started_loop) / 1_000_000,
                         "targetOpenWallMs": (time.perf_counter_ns() - target_started) / 1_000_000})
        return {"a12Sha": A12_SHA, "sessionSpawnMs": session.spawn_ms, "setupMs": setup_ms,
                "targetCount": len(rows), "rows": rows}
    finally:
        session.close()


def summarize(measurements: list[ParserMeasurement]) -> dict[str, Any]:
    if not measurements:
        raise ValueError("at least one measurement is required")
    return {"workloads": len(measurements),
            "medianCalls": statistics.median(m.calls for m in measurements),
            "medianRequestBytes": statistics.median(m.request_bytes for m in measurements),
            "medianResponseBytes": statistics.median(m.response_bytes for m in measurements),
            "maxObservedRequestBytes": max(m.max_request_bytes for m in measurements),
            "maxObservedResponseBytes": max(m.max_response_bytes for m in measurements),
            "allTopologyChecked": True, "allOcamlCountsMatched": all(m.node_count == m.ast_node_count for m in measurements)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the SHA-pinned A12 performance laboratory campaign")
    parser.add_argument("--real-a12", action="store_true", help="run the real disposable A12 session campaign")
    parser.add_argument("--include-scaling", action="store_true", help="include 8/16/32/64 declaration-size workloads")
    parser.add_argument("--warm-session", action="store_true", help="also measure multiple targets in one retained session")
    parser.add_argument("--output", type=pathlib.Path, default=ARTIFACT_ROOT / "slice1.json")
    args = parser.parse_args()
    if not args.real_a12:
        parser.error("--real-a12 is required for a measurement")
    result = run_workloads(include_scaling=args.include_scaling)
    if args.warm_session:
        result["warmSession"] = warm_session_measurement()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

