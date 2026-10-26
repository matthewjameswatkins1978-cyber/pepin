import json
import os
import pathlib
import subprocess
import time
import unittest

from tests.test_a11 import JsonLineClient, typed, typed_record, typed_list

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEXER = ROOT / "examples" / "pep_lexer.pep"
PARSER = ROOT / "examples" / "pep_parser.pep"
BUILD = ROOT / "_build" / "a12"


def fields(value):
    return {item["name"]: item["value"] for item in value["fields"]}


def scalar(value):
    if value["type"] == "Int":
        return int(value["value"])
    if value["type"] == "Bool":
        return value["value"]
    if value["type"] == "Str":
        return value["value"]
    raise AssertionError(f"unexpected typed scalar {value['type']}")


def span(value):
    return (value["start"]["offset"], value["endOffset"],
            value["start"]["line"], value["start"]["column"])


def parser_cursor_value(document, revision, done=False, next_node_id=0, lex_done=False, lex_stage="validate", top_level_child_index=0):
    lex_cursor = typed_record("LexCursor", [
        ("document", typed("Str", document)), ("revision", typed("Str", revision)),
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
        ("document", typed("Str", document)), ("revision", typed("Str", revision)),
        ("stream", stream), ("nextNodeId", typed("Int", str(next_node_id))),
        ("done", typed("Bool", done)),
        ("functionActive", typed("Bool", False)), ("functionName", typed("Str", "")),
        ("functionStartByte", typed("Int", "0")), ("functionLine", typed("Int", "1")),
        ("functionColumn", typed("Int", "1")), ("functionRootId", typed("Int", "0")),
        ("functionChildIndex", typed("Int", "0")),
        ("topLevelChildIndex", typed("Int", str(top_level_child_index))),
        ("frames", typed_list("ParserFrame", [])),
    ])


def parser_chunk_value(document, revision, cursor, status="complete", nodes=None, done=True,
                       error_code="", message="", start=0, ending=0, line=0, column=0):
    return typed_record("ParserChunk", [
        ("document", typed("Str", document)), ("revision", typed("Str", revision)),
        ("status", typed("Str", status)), ("nodes", typed_list("FlatAstNode", nodes or [])),
        ("cursor", cursor), ("done", typed("Bool", done)),
        ("errorCode", typed("Str", error_code)), ("message", typed("Str", message)),
        ("errorStart", typed("Int", str(start))), ("errorEnd", typed("Int", str(ending))),
        ("errorLine", typed("Int", str(line))), ("errorColumn", typed("Int", str(column))),
    ])


def pep_flat_nodes(result):
    values = fields(result)
    nodes = values["nodes"]["value"]
    normalized = []
    for node in nodes:
        item = fields(node)
        kind = scalar(item["kind"])
        text = scalar(item["text"])
        integer_value = int(scalar(item["integerValue"]))
        boolean_value = scalar(item["booleanValue"])
        string_parts = [scalar(part) for part in item["stringParts"]["value"]]
        if kind in {"type_scalar", "type_named", "type_list"}:
            node_span = None
        else:
            node_span = (int(scalar(item["startByte"])), int(scalar(item["endByte"])),
                         int(scalar(item["line"])), int(scalar(item["column"])))
        if kind == "integer":
            value = integer_value
        elif kind == "boolean":
            value = boolean_value
        elif kind == "string":
            value = "".join(string_parts)
        else:
            value = text
        normalized.append((kind, value, node_span))
    return normalized


def ocaml_type_nodes(name):
    if name.startswith("List[") and name.endswith("]"):
        inner = name[5:-1]
        return [("type_list", "", None), *ocaml_type_nodes(inner)]
    scalar_types = {"Int", "Bool", "Str", "SourceBytes", "Unit"}
    return [("type_scalar" if name in scalar_types else "type_named", name, None)]


def ocaml_flat_nodes(tops):
    output = []

    def add(kind, value, node_span):
        output.append((kind, value, span(node_span) if node_span is not None else None))

    def expression(node):
        kind = node["kind"]
        node_span = node["span"]
        if kind == "int":
            add("integer", node["value"], node_span)
        elif kind == "bool":
            add("boolean", node["value"], node_span)
        elif kind == "string":
            add("string", node["value"], node_span)
        elif kind == "name":
            add("name", node["name"], node_span)
        elif kind == "hole":
            add("hole", node["name"] or "", node_span)
        elif kind == "call":
            add("call", node["name"], node_span)
            for child in node["arguments"]:
                expression(child)
        elif kind == "binary":
            add("binary", node["operator"], node_span)
            expression(node["left"])
            expression(node["right"])
        elif kind == "unary":
            add("unary", node["operator"], node_span)
            expression(node["operand"])
        elif kind == "list":
            add("list", "", node_span)
            for child in node["elements"]:
                expression(child)
        elif kind == "if":
            add("if_expression", "", node_span)
            expression(node["condition"])
            expression(node["then"])
            expression(node["else"])
        elif kind == "record":
            add("record", node["typeName"], node_span)
            for field in node["fields"]:
                add("record_field", field["name"], field["span"])
                expression(field["value"])
        elif kind == "field_access":
            add("field_access", node["field"], node_span)
            expression(node["value"])
        elif kind == "match":
            add("match", "", node_span)
            expression(node["value"])
            for arm in node["arms"]:
                add("match_arm", "", arm["span"])
                pattern(arm["pattern"])
                expression(arm["result"])
        else:
            raise AssertionError(f"unhandled OCaml expression kind {kind}")

    def pattern(node):
        kind = node["kind"]
        if kind == "wildcard_pattern":
            add(kind, "", node["span"])
        elif kind == "binding_pattern":
            add(kind, node["name"], node["span"])
        elif kind == "constructor_pattern":
            add(kind, node["name"], node["span"])
            for child in node["arguments"]:
                pattern(child)
        else:
            raise AssertionError(f"unhandled OCaml pattern kind {kind}")

    def statement(node):
        kind = node["kind"]
        if kind == "expression":
            add("expression_statement", "", node["span"])
            expression(node["value"])
        elif kind in {"let", "var"}:
            add(kind, node["name"], node["span"])
            if node["annotation"] is not None:
                for type_node in ocaml_type_nodes(node["annotation"]):
                    output.append(type_node)
            expression(node["value"])
        elif kind == "assignment":
            add(kind, node["name"], node["span"])
            expression(node["value"])
        elif kind == "return":
            add(kind, "", node["span"])
            expression(node["value"])
        elif kind == "block":
            add(kind, "", node["span"])
            for child in node["statements"]:
                statement(child)
        elif kind == "if_statement":
            add(kind, "", node["span"])
            expression(node["condition"])
            for child in node["then"]:
                statement(child)
            for child in node["else"]:
                statement(child)
        elif kind == "for_in":
            add(kind, node["name"], node["span"])
            expression(node["iterable"])
            for child in node["body"]:
                statement(child)
        elif kind == "while":
            add(kind, "", node["span"])
            expression(node["condition"])
            for child in node["body"]:
                statement(child)
        else:
            raise AssertionError(f"unhandled OCaml statement kind {kind}")

    for node in tops:
        kind = node["kind"]
        if kind == "function":
            add("function", node["name"], node["span"])
            for parameter in node["parameters"]:
                add("parameter", parameter["name"], parameter["span"])
                output.extend(ocaml_type_nodes(parameter["type"]))
            output.extend(ocaml_type_nodes(node["returnType"]))
            for child in node["body"]:
                statement(child)
        elif kind == "record_declaration":
            add(kind, node["name"], node["span"])
            for field in node["fields"]:
                add("field_declaration", field["name"], field["span"])
                output.extend(ocaml_type_nodes(field["type"]))
        elif kind == "union_declaration":
            add(kind, node["name"], node["span"])
            for variant in node["variants"]:
                add("variant_declaration", variant["name"], variant["span"])
                for argument in variant["arguments"]:
                    output.extend(ocaml_type_nodes(argument))
        else:
            statement(node)
    return output


def pep_topology_nodes(result):
    normalized = []
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
        node_span = None if kind.startswith("type_") else (
            int(scalar(item["startByte"])), int(scalar(item["endByte"])),
            int(scalar(item["line"])), int(scalar(item["column"])),
        )
        normalized.append((
            int(scalar(item["id"])), int(scalar(item["parentId"])),
            int(scalar(item["childIndex"])), scalar(item["role"]), kind,
            value, node_span,
        ))
    return normalized


def ocaml_tree_nodes(tops):
    """Derive wire topology independently from the OCaml parser's nested AST."""
    output = []

    def add(kind, value, node_span, parent_id, child_index, role):
        node_id = len(output)
        output.append((node_id, parent_id, child_index, role, kind, value,
                       span(node_span) if node_span is not None else None))
        return node_id

    def type_node(name, parent_id, child_index, role):
        if name.startswith("List[") and name.endswith("]"):
            node_id = add("type_list", "", None, parent_id, child_index, role)
            type_node(name[5:-1], node_id, 0, "element_type")
        else:
            scalar_types = {"Int", "Bool", "Str", "SourceBytes", "Unit"}
            kind = "type_scalar" if name in scalar_types else "type_named"
            add(kind, name, None, parent_id, child_index, role)

    def expressions(node, parent_id, child_index, role):
        kind = node["kind"]
        node_span = node["span"]
        if kind == "int":
            add("integer", node["value"], node_span, parent_id, child_index, role)
        elif kind == "bool":
            add("boolean", node["value"], node_span, parent_id, child_index, role)
        elif kind == "string":
            add("string", node["value"], node_span, parent_id, child_index, role)
        elif kind == "name":
            add("name", node["name"], node_span, parent_id, child_index, role)
        elif kind == "hole":
            add("hole", node["name"] or "", node_span, parent_id, child_index, role)
        elif kind in {"call", "list", "record", "field_access", "unary"}:
            value = node.get("name", node.get("typeName", node.get("field", node.get("operator", ""))))
            flat_kind = {"field_access": "field_access"}.get(kind, kind)
            if kind == "call":
                children = [(child, "argument") for child in node["arguments"]]
            elif kind == "list":
                children = [(child, "element") for child in node["elements"]]
            elif kind == "record":
                children = [(field, "field") for field in node["fields"]]
            elif kind == "field_access":
                children = [(node["value"], "value")]
            else:
                children = [(node["operand"], "operand")]
            node_id = add(flat_kind, value, node_span, parent_id, child_index, role)
            for index, (child, child_role) in enumerate(children):
                if kind == "record":
                    record_id = add("record_field", child["name"], child["span"], node_id, index, child_role)
                    expressions(child["value"], record_id, 0, "value")
                else:
                    expressions(child, node_id, index, child_role)
        elif kind == "binary":
            node_id = add("binary", node["operator"], node_span, parent_id, child_index, role)
            expressions(node["left"], node_id, 0, "left")
            expressions(node["right"], node_id, 1, "right")
        elif kind == "if":
            node_id = add("if_expression", "", node_span, parent_id, child_index, role)
            expressions(node["condition"], node_id, 0, "condition")
            expressions(node["then"], node_id, 1, "then")
            expressions(node["else"], node_id, 2, "else")
        elif kind == "match":
            node_id = add("match", "", node_span, parent_id, child_index, role)
            expressions(node["value"], node_id, 0, "value")
            for index, arm in enumerate(node["arms"]):
                arm_id = add("match_arm", "", arm["span"], node_id, index, "arm")
                patterns(arm["pattern"], arm_id, 0, "pattern")
                expressions(arm["result"], arm_id, 1, "result")
        else:
            raise AssertionError(f"unhandled OCaml expression kind {kind}")

    def patterns(node, parent_id, child_index, role):
        kind = node["kind"]
        if kind == "wildcard_pattern":
            add(kind, "", node["span"], parent_id, child_index, role)
        elif kind == "binding_pattern":
            add(kind, node["name"], node["span"], parent_id, child_index, role)
        elif kind == "constructor_pattern":
            node_id = add(kind, node["name"], node["span"], parent_id, child_index, role)
            for index, child in enumerate(node["arguments"]):
                patterns(child, node_id, index, "argument")
        else:
            raise AssertionError(f"unhandled OCaml pattern kind {kind}")

    def statements(node, parent_id, child_index, role):
        kind = node["kind"]
        node_id = add({"expression": "expression_statement"}.get(kind, kind),
                      node.get("name", ""), node["span"], parent_id, child_index, role)
        if kind == "expression":
            expressions(node["value"], node_id, 0, "value")
        elif kind in {"let", "var"}:
            if node["annotation"] is not None:
                type_node(node["annotation"], node_id, 0, "annotation")
            expressions(node["value"], node_id, 0, "value")
        elif kind == "assignment":
            expressions(node["value"], node_id, 0, "value")
        elif kind == "return":
            expressions(node["value"], node_id, 0, "value")
        elif kind == "block":
            for index, child in enumerate(node["statements"]):
                statements(child, node_id, index, "statement")
        elif kind == "if_statement":
            expressions(node["condition"], node_id, 0, "condition")
            for index, child in enumerate(node["then"]):
                statements(child, node_id, index, "then")
            for index, child in enumerate(node["else"]):
                statements(child, node_id, index, "else")
        elif kind == "for_in":
            expressions(node["iterable"], node_id, 0, "iterable")
            for index, child in enumerate(node["body"]):
                statements(child, node_id, index, "body")
        elif kind == "while":
            expressions(node["condition"], node_id, 0, "condition")
            for index, child in enumerate(node["body"]):
                statements(child, node_id, index, "body")
        else:
            raise AssertionError(f"unhandled OCaml statement kind {kind}")

    for top_index, node in enumerate(tops):
        kind = node["kind"]
        if kind == "function":
            node_id = add("function", node["name"], node["span"], -1, top_index, "top_level")
            for index, parameter in enumerate(node["parameters"]):
                parameter_id = add("parameter", parameter["name"], parameter["span"],
                                   node_id, index, "parameter")
                type_node(parameter["type"], parameter_id, 0, "type")
            type_node(node["returnType"], node_id, 0, "return_type")
            for index, child in enumerate(node["body"]):
                statements(child, node_id, index, "statement")
        elif kind == "record_declaration":
            node_id = add(kind, node["name"], node["span"], -1, top_index, "top_level")
            for index, field in enumerate(node["fields"]):
                field_id = add("field_declaration", field["name"], field["span"],
                               node_id, index, "field")
                type_node(field["type"], field_id, 0, "type")
        elif kind == "union_declaration":
            node_id = add(kind, node["name"], node["span"], -1, top_index, "top_level")
            for index, variant in enumerate(node["variants"]):
                variant_id = add("variant_declaration", variant["name"], variant["span"],
                                 node_id, index, "variant")
                for arg_index, argument in enumerate(variant["arguments"]):
                    type_node(argument, variant_id, arg_index, "field_type")
        else:
            statements(node, -1, top_index, "top_level")
    return output


def valid_tree_topology(nodes):
    if [node[0] for node in nodes] != list(range(len(nodes))):
        return False
    by_id = {node[0]: node for node in nodes}
    roots = []
    siblings = {}
    for node_id, parent_id, child_index, role, _kind, _value, _span in nodes:
        if parent_id == -1:
            if role != "top_level":
                return False
            roots.append(child_index)
        elif parent_id not in by_id or parent_id >= node_id:
            return False
        siblings.setdefault((parent_id, role), []).append(child_index)
    if roots != list(range(len(roots))):
        return False
    if any(index < 0 for indices in siblings.values() for index in indices):
        return False
    if any(len(indices) > 1 and sorted(indices) != list(range(len(indices)))
           for indices in siblings.values()):
        return False
    for node in nodes:
        seen = set()
        current = node[0]
        while current != -1:
            if current in seen:
                return False
            seen.add(current)
            current = by_id[current][1]
    return True


def topology_matches(actual, expected):
    return valid_tree_topology(actual) and valid_tree_topology(expected) and actual == expected


class A12ParserDifferentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BUILD.mkdir(parents=True, exist_ok=True)
        bundle = LEXER.read_text(encoding="utf-8") + "\n" + PARSER.read_text(encoding="utf-8")
        cls.bundle_path = BUILD / "parser_bundle.pep"
        cls.bundle_path.write_text(bundle, encoding="utf-8", newline="\n")

    def setUp(self):
        env = os.environ.copy()
        env.setdefault("PEPIN_OPAM_ROOT", os.environ.get("OPAMROOT", ""))
        self.session = JsonLineClient(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "session", "--jsonl"], ROOT, env,
        )
        opened = self.session.send({
            "schemaVersion": 3, "op": "open", "name": "a12-parser-bundle",
            "source": self.bundle_path.read_text(encoding="utf-8"), "metadataOnly": True,
        })
        self.assertEqual(opened.get("outcome"), "ok", opened)
        self.assertTrue(opened.get("analysisOmitted"), opened)
        self.assertEqual(opened.get("status"), "valid", opened)
        self.tool_document = opened["document"]
        self.tool_revision = opened["revision"]

        empty = self.session.send({"schemaVersion": 3, "op": "open_bytes", "name": "empty", "bytes": []})
        self.assertEqual(empty.get("outcome"), "ok", empty)
        self.target_document = empty["document"]
        self.target_revision = empty["revision"]
        self.initial_cursor = parser_cursor_value(self.target_document, self.target_revision)
        self.register_tool("pep-parser-start", "parser_start", [], self.initial_cursor)
        finished_cursor = parser_cursor_value(self.target_document, self.target_revision, done=True, lex_done=True, lex_stage="done")
        expected_chunk = parser_chunk_value(self.target_document, self.target_revision, finished_cursor)
        self.register_tool("pep-parser-step", "parser_step", [finished_cursor], expected_chunk)

    def register_tool(self, tool, function, arguments, expected):
        registered = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
            "tool": tool, "document": self.tool_document,
            "revision": self.tool_revision, "function": function,
        })
        self.assertEqual(registered.get("status"), "Registered", registered)
        validated = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
            "tool": tool, "document": self.tool_document, "revision": self.tool_revision,
            "testVectors": [{"arguments": arguments, "expect": expected, "semanticTarget": {
                "document": self.target_document, "revision": self.target_revision, "entryFunctions": [],
            }}],
        })
        self.assertEqual(validated.get("status"), "Validated", validated)
        activated = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
            "tool": tool, "document": self.tool_document, "revision": self.tool_revision,
        })
        self.assertEqual(activated.get("status"), "Active", activated)

    def tearDown(self):
        self.session.close()

    def test_metadata_only_open_preserves_defaults_and_rejects_bad_flag_without_mutation(self):
        normal = self.session.send({
            "schemaVersion": 3, "op": "open_bytes", "name": "normal", "bytes": [],
        })
        self.assertEqual(normal.get("outcome"), "ok", normal)
        self.assertEqual(normal.get("ast"), [])
        self.assertIsNotNone(normal.get("typedTree"))
        self.assertNotIn("analysisOmitted", normal)

        omitted = self.session.send({
            "schemaVersion": 3, "op": "open", "name": "metadata-only",
            "source": "", "metadataOnly": True,
        })
        self.assertEqual(omitted.get("outcome"), "ok", omitted)
        self.assertIsNone(omitted.get("ast"))
        self.assertIsNone(omitted.get("typedTree"))
        self.assertTrue(omitted.get("analysisOmitted"))
        self.assertEqual(omitted.get("status"), "valid")

        rejected = self.session.send({
            "schemaVersion": 3, "op": "open_bytes", "name": "bad-metadata-only",
            "bytes": [], "metadataOnly": "true",
        })
        self.assertEqual(rejected.get("outcome"), "error", rejected)
        self.assertEqual(rejected["error"]["code"], "PEP_SESSION_FIELD_TYPE")

        after_rejection = self.session.send({
            "schemaVersion": 3, "op": "open_bytes", "name": "after-rejection", "bytes": [],
        })
        self.assertEqual(after_rejection.get("document"), "doc-5", after_rejection)

    def parse(self, source, metadata_only=False):
        parse_started = time.perf_counter()
        raw = source if isinstance(source, bytes) else source.encode("utf-8")
        target = self.session.send({
            "schemaVersion": 3, "op": "open_bytes", "name": "parser-target",
            "bytes": list(raw), "metadataOnly": metadata_only,
        })
        self.assertEqual(target.get("outcome"), "ok", target)
        request_bytes = self.session.last_request_bytes
        response_bytes = self.session.last_response_bytes
        max_request_bytes = request_bytes
        max_response_bytes = response_bytes
        semantic_target = {
            "document": target["document"], "revision": target["revision"], "entryFunctions": [],
        }
        started = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "pep-parser-start", "arguments": [], "semanticTarget": semantic_target,
        })
        self.assertEqual(started.get("outcome"), "ok", started)
        self.assertEqual(started["revision"], self.tool_revision)
        request_bytes += self.session.last_request_bytes
        response_bytes += self.session.last_response_bytes
        cursor = started["result"]
        nodes = []
        final_fields = None
        step_count = 0
        while step_count <= len(raw) + 1:
            invoked = self.session.send({
                "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                "tool": "pep-parser-step", "arguments": [cursor], "semanticTarget": semantic_target,
            })
            source_offset = scalar(fields(fields(fields(cursor)["stream"])["lexCursor"])["offset"])
            self.assertEqual(invoked.get("outcome"), "ok", {"offset": source_offset, "response": invoked})
            self.assertEqual(invoked["revision"], self.tool_revision)
            request_bytes += self.session.last_request_bytes
            response_bytes += self.session.last_response_bytes
            max_request_bytes = max(max_request_bytes, self.session.last_request_bytes)
            max_response_bytes = max(max_response_bytes, self.session.last_response_bytes)
            result_fields = fields(invoked["result"])
            self.assertEqual(scalar(result_fields["document"]), target["document"])
            self.assertEqual(scalar(result_fields["revision"]), target["revision"])
            chunk_nodes = result_fields["nodes"]["value"]
            if not scalar(result_fields["done"]):
                self.assertNotEqual(result_fields["cursor"], cursor,
                                    "nonterminal parser continuation must advance its cursor")
            nodes.extend(chunk_nodes)
            cursor = result_fields["cursor"]
            final_fields = result_fields
            step_count += 1
            if scalar(result_fields["done"]):
                break
        nodes.sort(key=lambda node: int(scalar(fields(node)["id"])))
        self.assertIsNotNone(final_fields)
        self.assertTrue(scalar(final_fields["done"]), "parser continuation failed to complete")
        result = typed_record("ParserProgress", [
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
        self.last_parser_steps = step_count
        self.last_parser_request_bytes = request_bytes
        self.last_parser_response_bytes = response_bytes
        self.last_parser_max_request_bytes = max_request_bytes
        self.last_parser_max_response_bytes = max_response_bytes
        self.last_parser_elapsed_ms = (time.perf_counter() - parse_started) * 1000
        return target, result

    def assert_differential(self, source):
        target, result = self.parse(source)
        self.assertEqual(scalar(fields(result)["status"]), "complete")
        actual = pep_flat_nodes(result)
        expected = ocaml_flat_nodes(target["ast"])
        self.assertEqual(actual, expected, source)
        actual_tree = pep_topology_nodes(result)
        expected_tree = ocaml_tree_nodes(target["ast"])
        self.assertTrue(valid_tree_topology(actual_tree), source)
        self.assertTrue(valid_tree_topology(expected_tree), source)
        self.assertEqual(actual_tree, expected_tree, source)
        return actual

    def test_topology_oracle_rejects_corrupted_parent_role_and_order(self):
        source = "fn main() -> Int { if true { return 1 } else { return 2 } }"
        target, result = self.parse(source)
        actual = pep_topology_nodes(result)
        expected = ocaml_tree_nodes(target["ast"])
        self.assertTrue(topology_matches(actual, expected))

        changed_parent = list(actual)
        node = changed_parent[1]
        changed_parent[1] = (node[0], 999, *node[2:])
        self.assertFalse(topology_matches(changed_parent, expected))

        changed_role = list(actual)
        node = changed_role[1]
        changed_role[1] = (*node[:3], "wrong_role", *node[4:])
        self.assertFalse(topology_matches(changed_role, expected))

        changed_child_order = list(actual)
        node = changed_child_order[1]
        changed_child_order[1] = (*node[:2], node[2] + 1, *node[3:])
        self.assertFalse(topology_matches(changed_child_order, expected))

        changed_node_order = list(actual)
        changed_node_order[1], changed_node_order[2] = changed_node_order[2], changed_node_order[1]
        self.assertFalse(topology_matches(changed_node_order, expected))

    def test_flat_node_ids_are_unique_contiguous_and_deterministic(self):
        source = "fn f(x: List[Int]) -> List[Int] { return x }"
        _, first_result = self.parse(source)
        _, second_result = self.parse(source)
        first = pep_topology_nodes(first_result)
        second = pep_topology_nodes(second_result)
        self.assertEqual(first, second)
        self.assertEqual([node[0] for node in first], list(range(len(first))))
        self.assertTrue(valid_tree_topology(first))

    def test_expression_precedence_associativity_and_spans(self):
        actual = self.assert_differential("1 + 2 * 3 - 4")
        self.assertEqual([node[0] for node in actual], [
            "expression_statement", "binary", "binary", "integer", "binary", "integer", "integer", "integer",
        ])
    def test_boolean_comparison_grouping_and_unary_precedence(self):
        self.assert_differential("!true || false && 4 == 4 && 5 != 6 && 7 <= 8")
        self.assert_differential("-(1 + 2) * 3 / 4")

    def test_function_bindings_unary_and_typed_parameters(self):
        self.assert_differential("fn main(x: Int) -> Int { let y: Int = -x; return y }")

    def test_union_match_constructor_patterns_and_holes(self):
        self.assert_differential(
            "type Maybe = None() | Some(Int)\n"
            "fn pick(value: Maybe) -> Int { return match value { None() => 0 Some(number) => number } }"
        )
        self.assert_differential("fn unfinished() -> Int { return ?result }")

    def test_record_type_literal_and_field_access(self):
        self.assert_differential(
            "type Point { x: Int, y: Int }\n"
            "fn main() -> Int { let point = Point { x: 1, y: 2 }; return point.x }"
        )

    def test_conditional_statement_loops_and_assignment(self):
        self.assert_differential(
            "fn count(xs: List[Int]) -> Int { var total = 0; "
            "for item in xs { total = total + item } "
            "while total <= 10 { total = total + 1 } "
            "if total <= 10 { return 0 } else { return total } }"
        )

    def test_incomplete_and_invalid_sources_return_structured_errors(self):
        for raw in (b"fn main() -> Int { return (1 + 2", b"fn main() -> Int { return 1"):
            target, result = self.parse(raw)
            result_fields = fields(result)
            self.assertEqual(scalar(result_fields["status"]), "incomplete")
            self.assertTrue(scalar(result_fields["errorCode"]).startswith("PEP_PARSE_"))
            self.assertEqual(target.get("status"), "invalid")
        target, result = self.parse(b"fn main() -> Int { return @ }")
        self.assertEqual(scalar(fields(result)["status"]), "invalid")
        self.assertEqual(scalar(fields(result)["errorCode"]), "PEP_UNEXPECTED_CHARACTER")
        self.assertEqual(target.get("status"), "invalid")


    def test_calls_trailing_commas_strings_holes_and_if_expressions(self):
        self.assert_differential("fn main() -> Int { let values = [1, 2,]; return choose(values, 0) }")
        self.assert_differential(r'fn message(flag: Bool) -> Str { return if flag { "café\n" } else { ?label } }')
        self.assert_differential("[]")

    def test_nested_patterns_and_wildcards(self):
        self.assert_differential(
            "type Tree = Leaf(Int) | Node(Tree, Tree)\n"
            "fn total(tree: Tree) -> Int { return match tree { "
            "Leaf(number) => number Node(Leaf(_), right) => total(right) _ => 0 } }"
        )

    def test_if_statement_parenthesized_condition_and_unary_context(self):
        self.assert_differential(
            "fn f(limit: Int) -> Int { if !(limit <= 0) { return 1 } else { return limit } }"
        )

    def test_cursor_revision_mismatch_is_rejected_without_session_corruption(self):
        stale = parser_cursor_value("doc-stale", "sha256:stale")
        semantic_target = {
            "document": self.target_document, "revision": self.target_revision, "entryFunctions": [],
        }
        rejected = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "pep-parser-step", "arguments": [stale], "semanticTarget": semantic_target,
        })
        self.assertEqual(rejected.get("outcome"), "ok", rejected)
        result = fields(rejected["result"])
        self.assertEqual(scalar(result["status"]), "invalid")
        self.assertEqual(scalar(result["errorCode"]), "PEP_PARSER_CURSOR_REVISION")
        valid = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "pep-parser-start", "arguments": [], "semanticTarget": semantic_target,
        })
        self.assertEqual(valid.get("outcome"), "ok", valid)

    def test_parser_cursor_is_cooperative_and_host_target_remains_authoritative(self):
        raw = b"let value: Int = 7;"
        opened = self.session.send({
            "schemaVersion": 3, "op": "open_bytes", "name": "cursor-authority", "bytes": list(raw),
        })
        self.assertEqual(opened.get("outcome"), "ok", opened)
        semantic_target = {
            "document": opened["document"], "revision": opened["revision"], "entryFunctions": [],
        }
        started = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "pep-parser-start", "arguments": [], "semanticTarget": semantic_target,
        })
        self.assertEqual(started.get("outcome"), "ok", started)

        forged_terminal = parser_cursor_value(
            opened["document"], opened["revision"], done=True, lex_done=True, lex_stage="done",
        )
        skipped = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "pep-parser-step", "arguments": [forged_terminal],
            "semanticTarget": semantic_target,
        })
        self.assertEqual(skipped.get("outcome"), "ok", skipped)
        skipped_fields = fields(skipped["result"])
        self.assertEqual(scalar(skipped_fields["status"]), "complete")
        self.assertEqual(skipped_fields["nodes"]["value"], [])
        self.assertNotEqual(forged_terminal, started["result"],
                            "a complete status is trusted only after consuming the start/step chain")

        inconsistent = parser_cursor_value(
            opened["document"], opened["revision"], lex_stage="scan",
        )
        nested = fields(fields(fields(inconsistent)["stream"])["lexCursor"])
        nested["document"]["value"] = "doc-forged"
        nested["revision"]["value"] = "sha256:" + "f" * 64
        rejected = self.session.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "pep-parser-step", "arguments": [inconsistent],
            "semanticTarget": semantic_target,
        })
        self.assertEqual(rejected.get("outcome"), "ok", rejected)
        rejected_fields = fields(rejected["result"])
        self.assertEqual(scalar(rejected_fields["errorCode"]), "PEP_LEXER_CURSOR_REVISION")
        self.assertEqual(scalar(rejected_fields["document"]), opened["document"])
        self.assertEqual(scalar(rejected_fields["revision"]), opened["revision"])

        target, recovered = self.parse(raw)
        self.assertNotEqual(target["document"], opened["document"])
        self.assertEqual(scalar(fields(recovered)["status"]), "complete")

    def test_open_bytes_source_limit_is_explicit_and_does_not_allocate_a_document(self):
        self.assertGreater(PARSER.stat().st_size, 65536,
                           "standalone parser source exceeds the open_bytes limit")
        oversized = self.session.send({
            "schemaVersion": 3, "op": "open_bytes", "name": "oversized",
            "bytes": [0] * 65537,
        })
        self.assertEqual(oversized.get("outcome"), "error", oversized)
        self.assertEqual(oversized["error"]["code"], "PEP_SOURCE_BYTE_LIMIT")
        accepted = self.session.send({
            "schemaVersion": 3, "op": "open_bytes", "name": "after-oversized", "bytes": [],
        })
        self.assertEqual(accepted.get("outcome"), "ok", accepted)
        self.assertEqual(accepted["document"], "doc-3",
                         "rejected source must not consume a document identity")

    def test_malformed_utf8_has_original_span_and_session_recovers(self):
        raw = b"let text: Str = \xff"
        bad_offset = raw.index(b"\xff")
        target, result = self.parse(raw, metadata_only=True)
        self.assertEqual(target.get("outcome"), "ok", target)
        self.assertEqual(target.get("status"), "invalid")
        diagnostic = target["diagnostics"][0]
        self.assertEqual(diagnostic["code"], "PEP_INVALID_UTF8")
        self.assertEqual(diagnostic["span"]["start"]["offset"], bad_offset)
        self.assertEqual(diagnostic["span"]["endOffset"], bad_offset + 1)
        result_fields = fields(result)
        self.assertEqual(scalar(result_fields["status"]), "invalid")
        self.assertEqual(scalar(result_fields["errorCode"]), "PEP_INVALID_UTF8")
        self.assertEqual(scalar(result_fields["errorStart"]), bad_offset)
        self.assertEqual(scalar(result_fields["errorEnd"]), bad_offset + 1)

        recovered_target, recovered = self.parse(b"fn recovered() -> Int { return 1 }")
        self.assertEqual(recovered_target.get("status"), "valid")
        self.assertEqual(scalar(fields(recovered)["status"]), "complete")

    def test_incremental_parser_processes_actual_lexer_source(self):
        raw = LEXER.read_bytes()
        target, result = self.parse(raw, metadata_only=True)
        result_fields = fields(result)
        self.assertEqual(scalar(result_fields["status"]), "complete")
        oracle_run = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"),
             "check", str(LEXER), "--json"],
            cwd=ROOT, env={**os.environ, "PEPIN_OPAM_ROOT": os.environ.get("PEPIN_OPAM_ROOT", os.environ.get("OPAMROOT", ""))},
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(oracle_run.returncode, 0, oracle_run.stderr)
        oracle = json.loads(oracle_run.stdout)
        self.assertEqual(pep_flat_nodes(result), ocaml_flat_nodes(oracle["ast"]))
        self.assertGreater(len(result_fields["nodes"]["value"]), 100)
        self.assertGreater(self.last_parser_steps, 1)
        self.assertLess(self.last_parser_steps, len(raw))
        self.assertEqual(scalar(result_fields["document"]), target["document"])
        self.assertEqual(scalar(result_fields["revision"]), target["revision"])

    def test_malformed_delimiters_match_ocaml_diagnostics(self):
        corpus = [
            ("missing_else", "fn f() -> Int { if true { return 1 } }", "PEP_PARSE_ELSE", "invalid"),
            ("mismatched_group", "fn f() -> Int { return (1 }", "PEP_PARSE_EXPECTED", "invalid"),
            ("mismatched_list", "fn f() -> Int { return [1 }", "PEP_PARSE_EXPECTED", "invalid"),
            ("truncated_union", "type X = A(Int) |", "PEP_PARSE_NAME", "incomplete"),
            ("missing_function_brace", "fn f() -> Int { return 1", "PEP_PARSE_EXPECTED", "incomplete"),
        ]
        probe = BUILD / "malformed_parser_probe.pep"
        for name, source, expected_code, expected_status in corpus:
            with self.subTest(name=name):
                raw = source.encode("utf-8")
                _, result = self.parse(raw, metadata_only=True)
                parser_fields = fields(result)
                probe.write_bytes(raw)
                oracle_run = subprocess.run(
                    ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"),
                     "check", str(probe), "--json"],
                    cwd=ROOT, env={**os.environ, "PEPIN_OPAM_ROOT": os.environ.get("PEPIN_OPAM_ROOT", os.environ.get("OPAMROOT", ""))},
                    capture_output=True, text=True, encoding="utf-8", check=False,
                )
                oracle = json.loads(oracle_run.stdout)
                self.assertEqual(scalar(parser_fields["status"]), expected_status)
                self.assertEqual(scalar(parser_fields["errorCode"]), expected_code)
                self.assertEqual(oracle["status"], "invalid")
                diagnostic = oracle["diagnostics"][0]
                self.assertEqual(scalar(parser_fields["errorCode"]), diagnostic["code"])
                self.assertEqual(scalar(parser_fields["errorStart"]),
                                 diagnostic["span"]["start"]["offset"])
                self.assertEqual(scalar(parser_fields["errorEnd"]),
                                 diagnostic["span"]["endOffset"])

    def test_repository_examples_match_ocaml_parser_ast(self):
        matched = 0
        skipped_oversize = []
        for source_path in sorted((ROOT / "examples").glob("*.pep")):
            raw = source_path.read_bytes()
            if len(raw) > 65536:
                skipped_oversize.append(source_path.name)
                continue
            target, result = self.parse(raw, metadata_only=True)
            oracle_run = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"),
                 "check", str(source_path), "--json"],
                cwd=ROOT, env={**os.environ, "PEPIN_OPAM_ROOT": os.environ.get("PEPIN_OPAM_ROOT", os.environ.get("OPAMROOT", ""))},
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            oracle = json.loads(oracle_run.stdout)
            oracle_ast = oracle.get("ast")
            parser_fields = fields(result)
            if isinstance(oracle_ast, list):
                self.assertEqual(scalar(parser_fields["status"]), "complete", source_path.name)
                self.assertEqual(pep_flat_nodes(result), ocaml_flat_nodes(oracle_ast), source_path.name)
                matched += 1
            else:
                self.assertNotEqual(scalar(parser_fields["status"]), "complete", source_path.name)
                self.assertEqual(scalar(parser_fields["errorCode"]), oracle.get("errorCode"), source_path.name)
        self.assertGreaterEqual(matched, 8)
        self.assertIn("pep_parser.pep", skipped_oversize)

    def test_incremental_parser_transport_scaling(self):
        measurements = []
        for count in (8, 16, 32):
            statements = "".join(
                f"let item{index}: Int = {index}; " for index in range(count)
            )
            source = f"fn generated() -> Int {{ {statements} return item{count - 1} }}"
            target, result = self.parse(source)
            self.assertEqual(scalar(fields(result)["status"]), "complete")
            self.assertEqual(pep_flat_nodes(result), ocaml_flat_nodes(target["ast"]))
            self.assertLess(self.last_parser_max_request_bytes, 1_048_576)
            self.assertLess(self.last_parser_max_response_bytes, 1_048_576)
            measurements.append((
                len(source.encode("utf-8")), self.last_parser_steps,
                self.last_parser_request_bytes, self.last_parser_response_bytes,
                self.last_parser_max_request_bytes, self.last_parser_max_response_bytes,
            ))
        for before, after in zip(measurements, measurements[1:]):
            self.assertGreater(after[0], before[0])
            self.assertLessEqual(after[1], before[1] * 2 + 8)
            self.assertLessEqual(after[2], before[2] * 3)
            self.assertLessEqual(after[3], before[3] * 3)
        self.incremental_scaling_measurements = measurements

    def test_unicode_crlf_byte_positions(self):
        self.assert_differential(b'fn text() -> Str {\r\n  return "caf\xc3\xa9"\r\n}')

if __name__ == "__main__":
    unittest.main()
