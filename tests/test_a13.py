import copy
import hashlib
import json
import os
import pathlib
import subprocess
import unittest

from tests.test_a11 import JsonLineClient, revision, typed, typed_list, typed_record
from pep_c23 import (checker_binding_context_nodes, checker_binding_type_context_nodes,
                      checker_node_context_index, checker_node_value, checker_scope_context_nodes,
                      checker_type_context_nodes, checker_active_subtree_ids,
                      checker_bindings_for_references, checker_binding_type_names,
                      checker_hole_context_nodes,
                      checker_duplicate_context_nodes, checker_report_context_nodes,
                      checker_report_diagnostic_codes, checker_complete_report,
                      checker_cursor_without_typed_bindings,
                      checker_name_result, checker_empty_type_result,
                      checker_type_result, checker_cursor_with_results,
                      checker_cursor_with_functions, checker_functions_for_context,
                      parser_cursor_value, parser_chunk_value)

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEXER = ROOT / "examples" / "pep_lexer.pep"
PARSER = ROOT / "examples" / "pep_parser.pep"
CHECKER = ROOT / "tests" / "pep_checker_a13.pep"
BUILD = ROOT / "_build" / "a13"
NL = chr(10)
CRLF = chr(13) + chr(10)


def fields(value):
    return {item["name"]: item["value"] for item in value["fields"]}


def scalar(value):
    return int(value["value"]) if value["type"] == "Int" else value["value"]


def checker_report(document, source, *, status="valid", nodes=0, functions=(), calls=(), diagnostics=()):
    funcs = [typed_record("CheckedFunction", [
        ("semanticId", typed("Int", str(item[0]))), ("syntaxId", typed("Int", str(item[1]))),
        ("name", typed("Str", item[2])), ("arity", typed("Int", str(item[3]))),
        ("returnType", typed("Str", item[6])), ("startByte", typed("Int", str(item[4]))),
        ("endByte", typed("Int", str(item[5]))),
    ]) for item in functions]
    edges = [typed_record("ResolvedCall", [
        ("callerId", typed("Int", str(item[0]))), ("calleeId", typed("Int", str(item[1]))),
        ("syntaxId", typed("Int", str(item[2]))), ("startByte", typed("Int", str(item[3]))),
        ("endByte", typed("Int", str(item[4]))),
    ]) for item in calls]
    errors = [typed_record("CheckDiagnostic", [
        ("code", typed("Str", item[0])), ("message", typed("Str", item[1])),
        ("syntaxId", typed("Int", str(item[2]))), ("startByte", typed("Int", str(item[3]))),
        ("endByte", typed("Int", str(item[4]))),
    ]) for item in diagnostics]
    return typed_record("CheckerReport", [
        ("document", typed("Str", document)), ("revision", typed("Str", revision(source.encode("utf-8")))),
        ("status", typed("Str", status)), ("syntaxNodeCount", typed("Int", str(nodes))),
        ("functions", typed_list("CheckedFunction", funcs)),
        ("bindings", typed_list("BindingFact", [])), ("references", typed_list("ResolvedName", [])),
        ("calls", typed_list("ResolvedCall", edges)),
        ("expressionTypes", typed_list("ExpressionTypeFact", [])),
        ("holes", typed_list("HoleFact", [])),
        ("diagnostics", typed_list("CheckDiagnostic", errors)),
    ])


def empty_checker_node():
    return typed_record("CheckerNode", [
        ("id", typed("Int", "-1")), ("parentId", typed("Int", "-1")),
        ("childIndex", typed("Int", "-1")), ("role", typed("Str", "")),
        ("kind", typed("Str", "")), ("text", typed("Str", "")),
        ("startByte", typed("Int", "0")), ("endByte", typed("Int", "0")),
    ])


def checker_progress_header(parsed):
    parsed_fields = fields(parsed)
    names = ("document", "revision", "status", "done", "errorCode", "message",
             "errorStart", "errorEnd", "errorLine", "errorColumn")
    values = {name: parsed_fields[name] for name in names}
    return typed_record("ParserProgress", [
        ("document", values["document"]), ("revision", values["revision"]),
        ("status", values["status"]), ("nodes", typed_list("FlatAstNode", [])),
        *[(name, values[name]) for name in names[3:]],
    ])


def empty_parser_progress(document, source=""):
    return typed_record("ParserProgress", [
        ("document", typed("Str", document)),
        ("revision", typed("Str", revision(source.encode("utf-8")))),
        ("status", typed("Str", "complete")),
        ("nodes", typed_list("FlatAstNode", [])),
        ("done", typed("Bool", True)),
        ("errorCode", typed("Str", "")),
        ("message", typed("Str", "")),
        ("errorStart", typed("Int", "0")),
        ("errorEnd", typed("Int", "0")),
        ("errorLine", typed("Int", "0")),
        ("errorColumn", typed("Int", "0")),
    ])


def checker_cursor(document, source, parsed, phase, *, done=False):
    empty_bindings = typed_record("BindingCollection", [
        ("bindings", typed_list("BindingFact", [])),
        ("diagnostics", typed_list("CheckDiagnostic", [])),
        ("nextOrdinal", typed("Int", "0")),
    ])
    empty_names = typed_record("NameResolution", [
        ("references", typed_list("ResolvedName", [])),
        ("diagnostics", typed_list("CheckDiagnostic", [])),
    ])
    empty_types = typed_record("TypeAnalysis", [
        ("expressionTypes", typed_list("ExpressionTypeFact", [])),
        ("diagnostics", typed_list("CheckDiagnostic", [])),
        ("unreachable", typed_record("UnreachableLookup", [
            ("found", typed("Bool", False)),
            ("node", empty_checker_node()),
        ])),
    ])
    return typed_record("CheckerCursor", [
        ("document", typed("Str", document)),
        ("revision", typed("Str", revision(source.encode("utf-8")))),
        ("phase", typed("Str", phase)),
        ("done", typed("Bool", done)),
        ("parsed", parsed),
        ("nodes", typed_list("CheckerNode", [])),
        ("functions", typed_list("CheckedFunction", [])),
        ("bindingResult", empty_bindings),
        ("nameResult", empty_names),
        ("typedBindings", typed_list("BindingFact", [])),
        ("typeResult", empty_types),
        ("typeOffset", typed("Int", "0")),
        ("holes", typed_list("HoleFact", [])),
        ("report", checker_report(document, source)),
        ("validation", typed_record("TreeValidation", [
            ("sourceLength", typed("Int", "0")),
            ("nextNode", typed("Int", "0")),
            ("nextRoot", typed("Int", "0")),
            ("valid", typed("Bool", True)),
            ("stack", typed_list("ValidationFrame", [])),
            ("totalCount", typed("Int", "0")),
        ])),
        ("functionState", typed_record("FunctionAssembly", [
            ("active", typed("Bool", False)),
            ("node", empty_checker_node()),
            ("arity", typed("Int", "0")),
            ("resultShape", typed_record("PepTypeShape", [
                ("kind", typed("Str", "")),
                ("name", typed("Str", "")),
                ("listDepth", typed("Int", "0")),
            ])),
            ("typeListNode", typed("Int", "-1")),
            ("typeListDepth", typed("Int", "0")),
            ("ordinal", typed("Int", "0")),
            ("nominalTypes", typed_list("Str", [])),
        ])),
    ])


class A13FunctionResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BUILD.mkdir(parents=True, exist_ok=True)
        cls.bundle = NL.join(path.read_text(encoding="utf-8") for path in (LEXER, PARSER, CHECKER))
        (BUILD / "checker_bundle.pep").write_text(cls.bundle, encoding="utf-8", newline=NL)

    def setUp(self):
        self.client = JsonLineClient(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "session", "--jsonl"], ROOT, os.environ.copy(),
        )
        opened = self.client.send({"schemaVersion": 3, "op": "open", "source": self.bundle,
                                   "name": "a13-checker", "metadataOnly": True})
        self.assertEqual(opened.get("outcome"), "ok", opened)
        self.assertEqual(opened.get("status"), "valid", opened)
        self.tool_document = opened["document"]
        self.tool_revision = revision(self.bundle.encode("utf-8"))
        empty = self._open("")
        registered = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                                       "tool": "pep-a13-checker", "document": self.tool_document,
                                       "revision": self.tool_revision, "function": "analyze"})
        self.assertEqual(registered.get("status"), "Registered", registered)
        validated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                                      "tool": "pep-a13-checker", "document": self.tool_document,
                                      "revision": self.tool_revision,
                                      "testVectors": [{"arguments": [], "expect": checker_report(empty["document"], ""),
                                                       "semanticTarget": {"document": empty["document"], "revision": empty["revision"], "entryFunctions": []}}]})
        self.assertEqual(validated.get("status"), "Validated", validated)
        active = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                                   "tool": "pep-a13-checker", "document": self.tool_document,
                                   "revision": self.tool_revision})
        self.assertEqual(active.get("status"), "Active", active)

    def tearDown(self):
        self.client.close()

    def _open(self, source):
        opened = self.client.send({"schemaVersion": 3, "op": "open_bytes", "name": "a13-target",
                                   "bytes": list(source.encode("utf-8"))})
        self.assertEqual(opened.get("outcome"), "ok", opened)
        return opened

    def _register_checker_continuations(self):
        if getattr(self, "checker_continuations_registered", False):
            return
        empty = self._open("")
        target = {"document": empty["document"], "revision": empty["revision"], "entryFunctions": []}
        parsed = empty_parser_progress(empty["document"])
        initial = checker_cursor(empty["document"], "", parsed, "validation")
        bindings = checker_cursor(empty["document"], "", parsed, "functions")
        tools = [
            ("pep-a13-parser", "parser_parse_program", [], parsed),
            ("pep-a13-checker-start", "checker_start", [parsed, typed("Int", "0")], initial),
            ("pep-a13-checker-step", "checker_step", [initial, typed_list("CheckerNode", []), typed_list("BindingFact", [])], bindings),
        ]
        for tool, function, arguments, expected in tools:
            registered = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_register", "tool": tool,
                                           "document": self.tool_document, "revision": self.tool_revision,
                                           "function": function})
            self.assertEqual(registered.get("status"), "Registered", registered)
            validated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_validate", "tool": tool,
                                          "document": self.tool_document, "revision": self.tool_revision,
                                          "testVectors": [{"arguments": arguments, "expect": expected,
                                                           "semanticTarget": target}]})
            self.assertEqual(validated.get("status"), "Validated", validated)
            active = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_activate", "tool": tool,
                                       "document": self.tool_document, "revision": self.tool_revision})
            self.assertEqual(active.get("status"), "Active", active)
        self.checker_continuations_registered = True

    def _parse_staged(self, source):
        if not getattr(self, "parser_continuations_registered", False):
            empty = self._open("")
            empty_target = {"document": empty["document"], "revision": empty["revision"], "entryFunctions": []}
            initial = parser_cursor_value(empty["document"], empty["revision"])
            done = parser_cursor_value(empty["document"], empty["revision"], done=True, lex_done=True,
                                       lex_stage="done")
            for tool, function, arguments, expected in [
                ("pep-a13-parser-start", "parser_start", [], initial),
                ("pep-a13-parser-step", "parser_step", [done],
                 parser_chunk_value(empty["document"], empty["revision"], done)),
            ]:
                registered = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                               "op": "tool_register", "tool": tool,
                                               "document": self.tool_document, "revision": self.tool_revision,
                                               "function": function})
                self.assertEqual(registered.get("status"), "Registered", registered)
                validated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                              "op": "tool_validate", "tool": tool,
                                              "document": self.tool_document, "revision": self.tool_revision,
                                              "testVectors": [{"arguments": arguments, "expect": expected,
                                                               "semanticTarget": empty_target}]})
                self.assertEqual(validated.get("status"), "Validated", validated)
                active = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_activate", "tool": tool,
                                           "document": self.tool_document, "revision": self.tool_revision})
                self.assertEqual(active.get("status"), "Active", active)
            self.parser_continuations_registered = True

        opened = self._open(source)
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        started = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-a13-parser-start", "arguments": [],
                                    "semanticTarget": target})
        self.assertEqual(started.get("outcome"), "ok", started)
        cursor = started["result"]
        nodes = []
        chunk = None
        for _ in range(min(len(source.encode("utf-8")) + 2, 4096)):
            previous = cursor
            stepped = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                        "op": "tool_invoke", "tool": "pep-a13-parser-step",
                                        "arguments": [cursor], "semanticTarget": target})
            self.assertEqual(stepped.get("outcome"), "ok", stepped)
            self.assertEqual(stepped.get("revision"), self.tool_revision)
            chunk = fields(stepped["result"])
            self.assertEqual(scalar(chunk["document"]), opened["document"])
            self.assertEqual(scalar(chunk["revision"]), opened["revision"])
            nodes.extend(chunk["nodes"]["value"])
            cursor = chunk["cursor"]
            if scalar(chunk["done"]):
                break
            self.assertEqual(scalar(chunk["status"]), "continuing", chunk)
            self.assertNotEqual(cursor, previous)
        self.assertIsNotNone(chunk)
        self.assertTrue(scalar(chunk["done"]), chunk)
        self.assertEqual(scalar(chunk["status"]), "complete", chunk)
        nodes.sort(key=lambda node: scalar(fields(node)["id"]))
        parsed = typed_record("ParserProgress", [
            ("document", typed("Str", opened["document"])),
            ("revision", typed("Str", opened["revision"])),
            ("status", chunk["status"]),
            ("nodes", typed_list("FlatAstNode", nodes)),
            ("done", chunk["done"]),
            ("errorCode", chunk["errorCode"]),
            ("message", chunk["message"]),
            ("errorStart", chunk["errorStart"]),
            ("errorEnd", chunk["errorEnd"]),
            ("errorLine", chunk["errorLine"]),
            ("errorColumn", chunk["errorColumn"]),
        ])
        return opened, parsed

    def _analyze_staged(self, source, parser_result=None):
        self._register_checker_continuations()
        if parser_result is None:
            opened = self._open(source)
            target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
            parsed = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_invoke", "tool": "pep-a13-parser", "arguments": [],
                                       "semanticTarget": target})
            self.assertEqual(parsed.get("outcome"), "ok", parsed)
            self.assertTrue(scalar(fields(parsed["result"])["done"]), parsed)
            parsed = parsed["result"]
        else:
            opened, parsed = parser_result
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        parser_nodes = fields(parsed)["nodes"]["value"]
        checker_nodes = [checker_node_value(node, len(source.encode("utf-8"))) for node in parser_nodes]
        try:
            checker_context_index = checker_node_context_index(checker_nodes)
        except RuntimeError:
            checker_context_index = ({}, {}, {})
        cursor = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_invoke", "tool": "pep-a13-checker-start",
                                   "arguments": [checker_progress_header(parsed), typed("Int", str(len(parser_nodes)))], "semanticTarget": target})
        self.assertEqual(cursor.get("outcome"), "ok", cursor)
        value = cursor["result"]
        external_typed_bindings = typed_list("BindingFact", [])
        external_name_references = []
        external_name_diagnostics = []
        external_functions = []
        external_type_facts = []
        external_type_diagnostics = []
        external_type_unreachable = None
        report_source_fields = None
        node_count = len(parser_nodes)
        binding_kinds = {"parameter", "let", "var", "for_in", "binding_pattern"}
        binding_count = sum(
            scalar(fields(node)["kind"]) in binding_kinds
            for node in fields(parsed)["nodes"]["value"]
        )
        maximum_steps = min(4096, 9 + 2 * ((node_count + 31) // 32) +
                            ((node_count + 15) // 16) + ((node_count + 7) // 8) +
                            ((node_count + 7) // 8) + ((node_count + 7) // 8) +
                            (binding_count + 31) // 32)
        for _ in range(maximum_steps):
            current = fields(value)
            if scalar(current["done"]):
                break
            previous = value
            step_nodes = checker_nodes
            step_bindings = external_typed_bindings
            step_value = value
            if scalar(current["phase"]) == "validation":
                next_node = scalar(fields(current["validation"])["nextNode"])
                step_nodes = checker_nodes[next_node:min(next_node + 32, node_count)]
            elif scalar(current["phase"]) == "functions":
                offset = scalar(current["typeOffset"])
                step_nodes = checker_nodes[offset:min(offset + 32, node_count)]
            elif scalar(current["phase"]) == "bindings":
                offset = scalar(current["typeOffset"])
                step_nodes = checker_binding_context_nodes(
                    checker_context_index, offset, min(offset + 8, node_count))
                step_value = checker_cursor_with_functions(
                    value, checker_functions_for_context(external_functions, step_nodes))
            elif scalar(current["phase"]) == "names":
                offset = scalar(current["typeOffset"])
                step_nodes = checker_scope_context_nodes(
                    checker_context_index, offset, min(offset + 16, node_count))
                step_value = checker_cursor_with_functions(
                    value, checker_functions_for_context(external_functions, step_nodes))
            elif scalar(current["phase"]) == "binding_types":
                pending_bindings = fields(current["bindingResult"])["bindings"]["value"]
                syntax_ids = [scalar(fields(binding)["syntaxId"])
                              for binding in pending_bindings[:32]]
                step_nodes = checker_binding_type_context_nodes(checker_context_index, syntax_ids)
                context_ids = {
                    scalar(fields(node)["id"]) for node in step_nodes
                }
                context_references = [
                    reference for reference in external_name_references
                    if scalar(fields(reference)["syntaxId"]) in context_ids
                ]
                step_value = checker_cursor_with_results(
                    value, checker_name_result(context_references), fields(value)["typeResult"])
            elif scalar(current["phase"]) == "type_analysis":
                offset = scalar(current["typeOffset"])
                end_node = min(offset + 8, node_count)
                step_nodes = checker_type_context_nodes(
                    checker_context_index, offset, end_node)
                active_ids = {
                    scalar(fields(node)["id"]) for node in step_nodes
                }
                context_references = [
                    reference for reference in external_name_references
                    if scalar(fields(reference)["syntaxId"]) in active_ids
                ]
                step_bindings = checker_bindings_for_references(
                    external_typed_bindings, context_references)
                extra_type_names = checker_binding_type_names(step_bindings)
                if extra_type_names:
                    step_nodes = checker_type_context_nodes(
                        checker_context_index, offset, end_node, extra_type_names)
                    active_ids = {
                        scalar(fields(node)["id"]) for node in step_nodes
                    }
                    context_references = [
                        reference for reference in external_name_references
                        if scalar(fields(reference)["syntaxId"]) in active_ids
                    ]
                    step_bindings = checker_bindings_for_references(
                        external_typed_bindings, context_references)
                step_types = checker_type_result(
                    (), reversed(external_type_diagnostics), external_type_unreachable
                ) if end_node == node_count else checker_empty_type_result()
                step_value = checker_cursor_with_results(
                    value, checker_name_result(context_references), step_types)
                step_value = checker_cursor_with_functions(
                    step_value, checker_functions_for_context(external_functions, step_nodes))
            elif scalar(current["phase"]) == "holes":
                step_nodes = checker_hole_context_nodes(checker_context_index)
                hole_context_ids = {
                    scalar(fields(node)["id"]) for node in step_nodes
                }
                hole_references = [
                    reference for reference in external_name_references
                    if scalar(fields(reference)["syntaxId"]) in hole_context_ids
                ]
                step_value = checker_cursor_with_results(
                    value, checker_name_result(hole_references), checker_empty_type_result())
            elif scalar(current["phase"]) == "duplicate_functions":
                step_nodes = checker_duplicate_context_nodes(checker_context_index)
                step_value = checker_cursor_with_results(
                    value, checker_name_result(),
                    checker_type_result((), external_type_diagnostics, external_type_unreachable))
            elif scalar(current["phase"]) == "report":
                step_value = checker_cursor_with_results(
                    value, checker_name_result(external_name_references, external_name_diagnostics),
                    fields(value)["typeResult"])
                step_nodes = checker_report_context_nodes(
                    checker_context_index, checker_report_diagnostic_codes(fields(step_value)))
            stepped = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                        "op": "tool_invoke", "tool": "pep-a13-checker-step",
                                        "arguments": [step_value, typed_list("CheckerNode", step_nodes), step_bindings],
                                        "semanticTarget": target})
            self.assertEqual(stepped.get("outcome"), "ok", {
                "phase": scalar(current["phase"]),
                "typeOffset": scalar(current["typeOffset"]),
                "response": stepped,
            })
            self.assertEqual(stepped.get("revision"), self.tool_revision)
            if scalar(current["phase"]) == "report":
                report_source_fields = fields(step_value)
            value = stepped["result"]
            if (scalar(current["phase"]) == "functions"
                    and scalar(fields(value)["phase"]) != "functions"):
                external_functions = fields(value)["functions"]["value"]
            if scalar(current["phase"]) in ("bindings", "names", "type_analysis"):
                value = checker_cursor_with_functions(
                    value, typed_list("CheckedFunction", external_functions))
            if scalar(current["phase"]) == "names":
                name_fields = fields(value)["nameResult"]
                external_name_references.extend(
                    reversed(name_fields["fields"][0]["value"]["value"]))
                external_name_diagnostics.extend(
                    reversed(name_fields["fields"][1]["value"]["value"]))
                next_phase = scalar(fields(value)["phase"])
                name_result = checker_name_result(
                    external_name_references if next_phase != "names" else (),
                    external_name_diagnostics if next_phase != "names" else ())
                value = checker_cursor_with_results(
                    value, name_result, fields(value)["typeResult"])
            if scalar(current["phase"]) == "binding_types":
                delta = fields(value)["typedBindings"]["value"]
                external_typed_bindings = typed_list("BindingFact", delta + external_typed_bindings["value"])
                if scalar(fields(value)["phase"]) != "binding_types":
                    external_typed_bindings["value"].reverse()
            if scalar(current["phase"]) == "type_analysis":
                type_fields = fields(value)["typeResult"]
                next_phase = scalar(fields(value)["phase"])
                if next_phase == "type_analysis":
                    external_type_facts.extend(reversed(type_fields["fields"][0]["value"]["value"]))
                    external_type_diagnostics.extend(reversed(type_fields["fields"][1]["value"]["value"]))
                    unreachable = type_fields["fields"][2]["value"]
                    if external_type_unreachable is None and scalar(fields(unreachable)["found"]):
                        external_type_unreachable = unreachable
                elif next_phase == "holes":
                    external_type_facts.extend(type_fields["fields"][0]["value"]["value"])
                    external_type_diagnostics[:] = type_fields["fields"][1]["value"]["value"]
                    external_type_unreachable = type_fields["fields"][2]["value"]
                value = checker_cursor_with_results(
                    value, checker_name_result(), checker_empty_type_result())
            value = checker_cursor_without_typed_bindings(value)
            self.assertNotEqual(value, previous)
        cursor_fields = fields(value)
        self.assertTrue(scalar(cursor_fields["done"]), cursor_fields)
        report_value = cursor_fields["report"]
        if report_source_fields is not None:
            report_value = checker_complete_report(
                report_value, report_source_fields, external_typed_bindings,
                external_name_references, external_type_facts)
        report = fields(report_value)
        self.assertEqual(scalar(report["document"]), opened["document"])
        self.assertEqual(scalar(report["revision"]), opened["revision"])
        return opened, report

    def _analyze(self, source):
        opened = self._open(source)
        result = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                   "tool": "pep-a13-checker", "arguments": [],
                                   "semanticTarget": {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}})
        self.assertEqual(result.get("outcome"), "ok", result)
        self.assertEqual(result["revision"], self.tool_revision)
        report = fields(result["result"])
        self.assertEqual(scalar(report["document"]), opened["document"])
        self.assertEqual(scalar(report["revision"]), opened["revision"])
        return opened, report

    def test_checker_cursor_advances_each_phase_for_empty_program(self):
        source = ""
        opened = self._open(source)
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        parsed = empty_parser_progress(opened["document"], source)
        initial = checker_cursor(opened["document"], source, parsed, "validation")
        after_first_step = checker_cursor(opened["document"], source, parsed, "functions")
        for tool, function, arguments, expected in [
            ("pep-a13-checker-start", "checker_start", [parsed, typed("Int", "0")], initial),
            ("pep-a13-checker-step", "checker_step", [initial, typed_list("CheckerNode", []), typed_list("BindingFact", [])], after_first_step),
        ]:
            registered = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_register", "tool": tool,
                                           "document": self.tool_document, "revision": self.tool_revision,
                                           "function": function})
            self.assertEqual(registered.get("status"), "Registered", registered)
            validated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_validate", "tool": tool,
                                          "document": self.tool_document, "revision": self.tool_revision,
                                          "testVectors": [{"arguments": arguments, "expect": expected,
                                                           "semanticTarget": target}]})
            self.assertEqual(validated.get("status"), "Validated", validated)
            activated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_activate", "tool": tool,
                                          "document": self.tool_document, "revision": self.tool_revision})
            self.assertEqual(activated.get("status"), "Active", activated)

        started = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                    "tool": "pep-a13-checker-start", "arguments": [checker_progress_header(parsed), typed("Int", "0")],
                                    "semanticTarget": target})
        self.assertEqual(started.get("outcome"), "ok", started)
        self.assertEqual(started.get("revision"), self.tool_revision)
        cursor = started["result"]
        phases = ["validation", "functions", "bindings", "names", "binding_types", "type_analysis", "holes", "duplicate_functions", "report", "done"]
        seen = [scalar(fields(cursor)["phase"])]
        for _ in range(9):
            cursor_fields = fields(cursor)
            if scalar(cursor_fields["done"]):
                break
            stepped = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                        "op": "tool_invoke", "tool": "pep-a13-checker-step",
                                        "arguments": [cursor, typed_list("CheckerNode", []), typed_list("BindingFact", [])], "semanticTarget": target})
            self.assertEqual(stepped.get("outcome"), "ok", stepped)
            self.assertEqual(stepped.get("revision"), self.tool_revision)
            cursor = stepped["result"]
            seen.append(scalar(fields(cursor)["phase"]))
        self.assertEqual(seen, phases)
        result = fields(cursor)["report"]
        self.assertEqual(scalar(fields(result)["status"]), "valid")
        self.assertEqual(scalar(fields(result)["syntaxNodeCount"]), 0)

    def test_checker_cursor_checks_composed_gcd_with_fixed_budget(self):
        source = (
            "fn int_mod(a: Int, b: Int) -> Int { var x = a while !(x <= b - 1) { x = x - b } return x }" + NL +
            "fn int_gcd(a: Int, b: Int) -> Int { var x = a var y = b while !(y == 0) { let r = int_mod(x, y) x = y y = r } return x }" + NL +
            "fn main() -> Int { return int_gcd(48, 18) }" + NL +
            "say(int_text(int_gcd(48, 18)))"
        )
        empty = self._open("")
        empty_target = {"document": empty["document"], "revision": empty["revision"], "entryFunctions": []}
        empty_parsed = empty_parser_progress(empty["document"])
        parser_start_cursor = parser_cursor_value(empty["document"], empty["revision"])
        parser_done_cursor = parser_cursor_value(empty["document"], empty["revision"],
                                                 done=True, lex_done=True, lex_stage="done")
        for tool, function, arguments, expected in [
            ("pep-a13-parser-start", "parser_start", [], parser_start_cursor),
            ("pep-a13-parser-step", "parser_step", [parser_done_cursor],
             parser_chunk_value(empty["document"], empty["revision"], parser_done_cursor)),
            ("pep-a13-checker-start", "checker_start", [empty_parsed, typed("Int", "0")],
             checker_cursor(empty["document"], "", empty_parsed, "validation")),
            ("pep-a13-checker-step", "checker_step",
             [checker_cursor(empty["document"], "", empty_parsed, "validation"), typed_list("CheckerNode", []), typed_list("BindingFact", [])],
             checker_cursor(empty["document"], "", empty_parsed, "functions")),
        ]:
            registered = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_register", "tool": tool,
                                           "document": self.tool_document, "revision": self.tool_revision,
                                           "function": function})
            self.assertEqual(registered.get("status"), "Registered", registered)
            validated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_validate", "tool": tool,
                                          "document": self.tool_document, "revision": self.tool_revision,
                                          "testVectors": [{"arguments": arguments, "expect": expected,
                                                           "semanticTarget": empty_target}]})
            self.assertEqual(validated.get("status"), "Validated", validated)
            activated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_activate", "tool": tool,
                                          "document": self.tool_document, "revision": self.tool_revision})
            self.assertEqual(activated.get("status"), "Active", activated)

        opened = self._open(source)
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        parsed = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_invoke", "tool": "pep-a13-parser-start",
                                   "arguments": [], "semanticTarget": target})
        self.assertEqual(parsed.get("outcome"), "ok", parsed)
        parser_cursor = parsed["result"]
        parser_nodes = []
        final_parser_chunk = None
        for _ in range(min(len(source.encode("utf-8")) + 2, 4096)):
            previous_parser_cursor = parser_cursor
            stepped = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                        "op": "tool_invoke", "tool": "pep-a13-parser-step",
                                        "arguments": [parser_cursor], "semanticTarget": target})
            self.assertEqual(stepped.get("outcome"), "ok", stepped)
            final_parser_chunk = fields(stepped["result"])
            self.assertEqual(scalar(final_parser_chunk["document"]), opened["document"])
            self.assertEqual(scalar(final_parser_chunk["revision"]), opened["revision"])
            parser_nodes.extend(final_parser_chunk["nodes"]["value"])
            done = scalar(final_parser_chunk["done"])
            parser_cursor = final_parser_chunk["cursor"]
            if done:
                break
            self.assertEqual(scalar(final_parser_chunk["status"]), "continuing")
            self.assertNotEqual(parser_cursor, previous_parser_cursor)
        self.assertIsNotNone(final_parser_chunk)
        self.assertTrue(scalar(final_parser_chunk["done"]), final_parser_chunk)
        parser_nodes.sort(key=lambda node: scalar(fields(node)["id"]))
        parsed_value = typed_record("ParserProgress", [
            ("document", typed("Str", opened["document"])),
            ("revision", typed("Str", opened["revision"])),
            ("status", final_parser_chunk["status"]),
            ("nodes", typed_list("FlatAstNode", parser_nodes)),
            ("done", final_parser_chunk["done"]),
            ("errorCode", final_parser_chunk["errorCode"]),
            ("message", final_parser_chunk["message"]),
            ("errorStart", final_parser_chunk["errorStart"]),
            ("errorEnd", final_parser_chunk["errorEnd"]),
            ("errorLine", final_parser_chunk["errorLine"]),
            ("errorColumn", final_parser_chunk["errorColumn"]),
        ])
        self.assertEqual(scalar(final_parser_chunk["status"]), "complete")
        checker_nodes = [checker_node_value(node, len(source.encode("utf-8"))) for node in parser_nodes]
        cursor = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                   "tool": "pep-a13-checker-start",
                                   "arguments": [checker_progress_header(parsed_value), typed("Int", str(len(parser_nodes)))],
                                   "semanticTarget": target})
        self.assertEqual(cursor.get("outcome"), "ok", cursor)
        cursor_value = cursor["result"]
        external_typed_bindings = typed_list("BindingFact", [])
        external_name_references = []
        external_name_diagnostics = []
        step_count = 0
        type_analysis_steps = 0
        node_count = len(parser_nodes)
        binding_count = sum(
            scalar(fields(node)["kind"]) in {"parameter", "let", "var", "for_in", "binding_pattern"}
            for node in parser_nodes
        )
        maximum_steps = min(
            4096,
            9 + 2 * ((node_count + 31) // 32) +
            ((node_count + 15) // 16) + ((node_count + 7) // 8) +
            ((node_count + 7) // 8) + ((node_count + 7) // 8) + (binding_count + 31) // 32
        )
        while not scalar(fields(cursor_value)["done"]) and step_count < maximum_steps:
            previous = fields(cursor_value)
            phase = scalar(previous["phase"])
            step_nodes = checker_nodes
            if phase == "validation":
                validation = fields(previous["validation"])
                start_node = scalar(validation["nextNode"])
                step_nodes = checker_nodes[start_node:start_node + 32]
            elif phase == "functions":
                start_node = scalar(previous["typeOffset"])
                end_node = min(start_node + 32, scalar(fields(previous["validation"])["totalCount"]))
                step_nodes = checker_nodes[start_node:end_node]
            stepped = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                        "tool": "pep-a13-checker-step", "arguments": [cursor_value, typed_list("CheckerNode", step_nodes), external_typed_bindings],
                                        "semanticTarget": target})
            self.assertEqual(stepped.get("outcome"), "ok", stepped)
            self.assertEqual(stepped.get("revision"), self.tool_revision)
            cursor_value = stepped["result"]
            if phase == "names":
                name_fields = fields(cursor_value)["nameResult"]
                external_name_references.extend(
                    reversed(name_fields["fields"][0]["value"]["value"]))
                external_name_diagnostics.extend(
                    reversed(name_fields["fields"][1]["value"]["value"]))
                next_phase = scalar(fields(cursor_value)["phase"])
                name_result = checker_name_result(
                    external_name_references if next_phase != "names" else (),
                    external_name_diagnostics if next_phase != "names" else ())
                cursor_value = checker_cursor_with_results(
                    cursor_value, name_result, fields(cursor_value)["typeResult"])
            if phase == "binding_types":
                delta = fields(cursor_value)["typedBindings"]["value"]
                external_typed_bindings = typed_list("BindingFact", delta + external_typed_bindings["value"])
                if scalar(fields(cursor_value)["phase"]) != "binding_types":
                    external_typed_bindings["value"].reverse()
            cursor_value = checker_cursor_without_typed_bindings(cursor_value)
            current = fields(cursor_value)
            if scalar(previous["phase"]) == "type_analysis":
                type_analysis_steps += 1
                self.assertTrue(scalar(current["typeOffset"]) > scalar(previous["typeOffset"]) or scalar(current["phase"]) == "holes")
            step_count += 1
        self.assertTrue(scalar(fields(cursor_value)["done"]), fields(cursor_value))
        self.assertGreater(step_count, 0)
        self.assertGreaterEqual(type_analysis_steps, 2)
        report = fields(fields(cursor_value)["report"])
        reference = self._reference_check("cursor-composed-int-gcd", source)
        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), reference["status"], report)
        expected_diagnostics = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in reference["diagnostics"]
        ]
        actual_diagnostics = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in report["diagnostics"]["value"]
        ]
        self.assertEqual(actual_diagnostics, expected_diagnostics, report)

    def test_type_analysis_node_ranges_partition_flat_ast(self):
        source = ""
        opened = self._open(source)
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        empty_nodes = typed_list("CheckerNode", [])
        empty_result = typed_list("CheckerNode", [])
        registered = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_register", "tool": "pep-a13-node-range",
                                       "document": self.tool_document, "revision": self.tool_revision,
                                       "function": "type_analysis_nodes_in_range"})
        self.assertEqual(registered.get("status"), "Registered", registered)
        validated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": "pep-a13-node-range",
                                      "document": self.tool_document, "revision": self.tool_revision,
                                      "testVectors": [{"arguments": [empty_nodes, typed("Int", "0"), typed("Int", "0")],
                                                       "expect": empty_result, "semanticTarget": target}]})
        self.assertEqual(validated.get("status"), "Validated", validated)
        activated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_activate", "tool": "pep-a13-node-range",
                                      "document": self.tool_document, "revision": self.tool_revision})
        self.assertEqual(activated.get("status"), "Active", activated)

        nodes = []
        for node_id in range(3):
            nodes.append(typed_record("CheckerNode", [
                ("id", typed("Int", str(node_id))), ("parentId", typed("Int", "-1")),
                ("childIndex", typed("Int", "-1")), ("role", typed("Str", "")),
                ("kind", typed("Str", "synthetic")), ("text", typed("Str", "")),
                ("startByte", typed("Int", "0")), ("endByte", typed("Int", "0")),
            ]))
        def run_range(start, end):
            result = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                      "tool": "pep-a13-node-range",
                                      "arguments": [typed_list("CheckerNode", nodes), typed("Int", str(start)), typed("Int", str(end))],
                                      "semanticTarget": target})
            self.assertEqual(result.get("outcome"), "ok", result)
            return [scalar(fields(item)["id"]) for item in result["result"]["value"]]

        first = run_range(0, 2)
        second = run_range(2, 3)
        whole = run_range(0, 3)
        self.assertEqual(first, [0, 1])
        self.assertEqual(second, [2])
        self.assertEqual(first + second, whole)
        self.assertEqual(len(set(first + second)), 3)

    def test_staged_parser_checker_preserves_diagnostics_within_budget(self):
        empty = self._open("")
        empty_parsed = typed_record("ParserProgress", [
            ("document", typed("Str", empty["document"])),
            ("revision", typed("Str", empty["revision"])),
            ("status", typed("Str", "complete")),
            ("nodes", typed_list("FlatAstNode", [])),
            ("done", typed("Bool", True)),
            ("errorCode", typed("Str", "")),
            ("message", typed("Str", "")),
            ("errorStart", typed("Int", "0")),
            ("errorEnd", typed("Int", "0")),
            ("errorLine", typed("Int", "0")),
            ("errorColumn", typed("Int", "0")),
        ])
        empty_checked = checker_report(empty["document"], "")
        semantic_target = {"document": empty["document"], "revision": empty["revision"], "entryFunctions": []}
        for tool, function, arguments, expected in [
            ("pep-a13-parser", "parser_parse_program", [], empty_parsed),
            ("pep-a13-checker-staged", "analyze_parsed", [empty_parsed], empty_checked),
        ]:
            registered = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_register", "tool": tool,
                                           "document": self.tool_document, "revision": self.tool_revision,
                                           "function": function})
            self.assertEqual(registered.get("status"), "Registered", registered)
            validated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_validate", "tool": tool,
                                          "document": self.tool_document, "revision": self.tool_revision,
                                          "testVectors": [{"arguments": arguments, "expect": expected,
                                                           "semanticTarget": semantic_target}]})
            self.assertEqual(validated.get("status"), "Validated", validated)
            activated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_activate", "tool": tool,
                                          "document": self.tool_document, "revision": self.tool_revision})
            self.assertEqual(activated.get("status"), "Active", activated)

        source = (
            "type Maybe = None() | Some(Int)" + NL +
            "type Box { value: Int }" + NL +
            "fn box(maybe: Maybe) -> Box { return Box { value: match maybe { Some(value) => ?pending None() => 0 } } }"
        )
        opened = self._open(source)
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        parsed = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_invoke", "tool": "pep-a13-parser", "arguments": [],
                                   "semanticTarget": target})
        self.assertEqual(parsed.get("outcome"), "ok", parsed)
        self.assertEqual(parsed["result"]["fields"][0]["value"]["value"], opened["document"])
        self.assertEqual(parsed["result"]["fields"][1]["value"]["value"], opened["revision"])
        checked = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-a13-checker-staged",
                                    "arguments": [parsed["result"]], "semanticTarget": target})
        self.assertEqual(checked.get("outcome"), "ok", checked)
        self.assertEqual(checked["revision"], self.tool_revision)
        report = fields(checked["result"])
        reference = self._reference_check("record-match-hole-staged", source)
        self.assertEqual(reference["status"], "incomplete", reference)
        self.assertEqual(scalar(report["document"]), opened["document"])
        self.assertEqual(scalar(report["revision"]), opened["revision"])
        self.assertEqual(scalar(report["status"]), reference["status"], report)
        expected_diagnostics = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in reference["diagnostics"]
        ]
        actual_diagnostics = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in report["diagnostics"]["value"]
        ]
        self.assertEqual(actual_diagnostics, expected_diagnostics, report)
        holes = [fields(item) for item in report["holes"]["value"]]
        self.assertEqual([(scalar(item["name"]), scalar(item["expectedType"])) for item in holes], [("pending", "Int")])

        # Distinct nested constructors in a later payload remain partial coverage.
        later_payload_source = (
            "type Inner = I() | J()" + NL +
            "type Outer = O(Int, Inner) | N()" + NL +
            "fn f(x: Outer) -> Int { return match x { O(_, I()) => 0 O(_, J()) => 1 N() => 2 } }"
        )
        later_payload = self._open(later_payload_source)
        later_target = {"document": later_payload["document"], "revision": later_payload["revision"], "entryFunctions": []}
        later_parsed = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                         "op": "tool_invoke", "tool": "pep-a13-parser", "arguments": [],
                                         "semanticTarget": later_target})
        self.assertEqual(later_parsed.get("outcome"), "ok", later_parsed)
        later_checked = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_invoke", "tool": "pep-a13-checker-staged",
                                          "arguments": [later_parsed["result"]], "semanticTarget": later_target})
        self.assertEqual(later_checked.get("outcome"), "ok", later_checked)
        later_report = fields(later_checked["result"])
        later_reference = self._reference_check("nested-pattern-later-payload", later_payload_source)
        self.assertEqual(later_reference["status"], "invalid", later_reference)
        self.assertEqual(scalar(later_report["status"]), later_reference["status"], later_report)
        expected_later_diagnostics = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in later_reference["diagnostics"]
        ]
        actual_later_diagnostics = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in later_report["diagnostics"]["value"]
        ]
        self.assertEqual(actual_later_diagnostics, expected_later_diagnostics, later_report)
        self.assertEqual([item[0] for item in actual_later_diagnostics], ["PEP_NON_EXHAUSTIVE_MATCH"])

        duplicate_later_source = (
            "type Inner = I() | J()" + NL +
            "type Outer = O(Int, Inner) | N()" + NL +
            "fn f(x: Outer) -> Int { return match x { O(_, I()) => 0 O(_, I()) => 1 O(_, J()) => 2 N() => 3 } }"
        )
        duplicate_later = self._open(duplicate_later_source)
        duplicate_target = {"document": duplicate_later["document"], "revision": duplicate_later["revision"], "entryFunctions": []}
        duplicate_parsed = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                             "op": "tool_invoke", "tool": "pep-a13-parser", "arguments": [],
                                             "semanticTarget": duplicate_target})
        self.assertEqual(duplicate_parsed.get("outcome"), "ok", duplicate_parsed)
        duplicate_checked = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                              "op": "tool_invoke", "tool": "pep-a13-checker-staged",
                                              "arguments": [duplicate_parsed["result"]], "semanticTarget": duplicate_target})
        self.assertEqual(duplicate_checked.get("outcome"), "ok", duplicate_checked)
        duplicate_report = fields(duplicate_checked["result"])
        duplicate_reference = self._reference_check("nested-pattern-later-payload-duplicate", duplicate_later_source)
        self.assertEqual(duplicate_reference["status"], "invalid", duplicate_reference)
        self.assertEqual(scalar(duplicate_report["status"]), duplicate_reference["status"], duplicate_report)
        expected_duplicate_diagnostics = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in duplicate_reference["diagnostics"]
        ]
        actual_duplicate_diagnostics = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in duplicate_report["diagnostics"]["value"]
        ]
        self.assertEqual(actual_duplicate_diagnostics, expected_duplicate_diagnostics, duplicate_report)
        self.assertEqual([item[0] for item in actual_duplicate_diagnostics], ["PEP_DUPLICATE_MATCH_ARM"])

        later_payload_cases = [
            ("three-payload-late-duplicate",
             "type Inner = I() | J()" + NL +
             "type Outer = O(Int, Int, Inner) | N()" + NL +
             "fn f(x: Outer) -> Int { return match x { O(_, _, I()) => 0 O(_, _, I()) => 1 O(_, _, J()) => 2 N() => 3 } }",
             "PEP_DUPLICATE_MATCH_ARM"),
            ("three-payload-distinct-partials",
             "type Inner = I() | J()" + NL +
             "type Outer = O(Int, Int, Inner) | N()" + NL +
             "fn f(x: Outer) -> Int { return match x { O(_, _, I()) => 0 O(_, _, J()) => 1 N() => 2 } }",
             "PEP_NON_EXHAUSTIVE_MATCH"),
            ("binding-and-wildcard-equivalent",
             "type Inner = I() | J()" + NL +
             "type Outer = O(Int, Int, Inner) | N()" + NL +
             "fn f(x: Outer) -> Int { return match x { O(value, _, I()) => 0 O(_, _, I()) => 1 O(_, _, J()) => 2 N() => 3 } }",
             "PEP_DUPLICATE_MATCH_ARM"),
            ("utf8-crlf-duplicate-span",
             "type Inner = I() | J()" + CRLF +
             "type Outer = O(Int, Inner) | N()" + CRLF +
             'fn f(x: Outer) -> Int { let label: Str = "🐇"; return match x { O(_, I()) => 0 O(_, I()) => 1 O(_, J()) => 2 N() => 3 } }' + CRLF,
             "PEP_DUPLICATE_MATCH_ARM"),
        ]
        for case_name, case_source, expected_code in later_payload_cases:
            with self.subTest(case=case_name):
                case_opened = self._open(case_source)
                case_target = {"document": case_opened["document"], "revision": case_opened["revision"], "entryFunctions": []}
                case_parsed = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                                "op": "tool_invoke", "tool": "pep-a13-parser", "arguments": [],
                                                "semanticTarget": case_target})
                self.assertEqual(case_parsed.get("outcome"), "ok", case_parsed)
                case_checked = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                                 "op": "tool_invoke", "tool": "pep-a13-checker-staged",
                                                 "arguments": [case_parsed["result"]], "semanticTarget": case_target})
                self.assertEqual(case_checked.get("outcome"), "ok", case_checked)
                case_report = fields(case_checked["result"])
                case_reference = self._reference_check("nested-pattern-" + case_name, case_source)
                self.assertEqual(case_reference["status"], "invalid", case_reference)
                self.assertEqual(scalar(case_report["status"]), case_reference["status"], case_report)
                expected_case_diagnostics = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in case_reference["diagnostics"]
                ]
                actual_case_diagnostics = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in case_report["diagnostics"]["value"]
                ]
                self.assertEqual(actual_case_diagnostics, expected_case_diagnostics, case_report)
                self.assertEqual([item[0] for item in actual_case_diagnostics], [expected_code])
                if case_name == "utf8-crlf-duplicate-span":
                    source_bytes = case_source.encode("utf-8")
                    repeated_arm = "O(_, I()) => 1"
                    expected_start = len(case_source[:case_source.index(repeated_arm)].encode("utf-8"))
                    expected_end = expected_start + len(repeated_arm.encode("utf-8"))
                    self.assertIn("🐇".encode("utf-8"), source_bytes)
                    self.assertEqual(source_bytes.count(CRLF.encode("ascii")), 3)
                    self.assertEqual(actual_case_diagnostics, [(expected_code, expected_start, expected_end)])

        depth_two_source = (
            "type Leaf = L(Int) | OtherLeaf()" + CRLF +
            "type Mid = M(Leaf) | N()" + CRLF +
            "type Outer = O(Mid) | Empty()" + CRLF +
            'fn f(x: Outer) -> Int { let label: Str = "🐇"; return match x { O(M(L(value))) => value O(_) => 0 Empty() => 0 } }'
        )
        depth_two_opened = self._open(depth_two_source)
        depth_two_target = {"document": depth_two_opened["document"], "revision": depth_two_opened["revision"], "entryFunctions": []}
        depth_two_parsed = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                             "op": "tool_invoke", "tool": "pep-a13-parser", "arguments": [],
                                             "semanticTarget": depth_two_target})
        self.assertEqual(depth_two_parsed.get("outcome"), "ok", depth_two_parsed)
        depth_two_checked = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                              "op": "tool_invoke", "tool": "pep-a13-checker-staged",
                                              "arguments": [depth_two_parsed["result"]],
                                              "semanticTarget": depth_two_target})
        self.assertEqual(depth_two_checked.get("outcome"), "ok", depth_two_checked)
        depth_two_report = fields(depth_two_checked["result"])
        depth_two_reference = self._reference_check("nested-pattern-depth-two", depth_two_source)
        self.assertEqual(depth_two_reference["status"], "valid", depth_two_reference)
        self.assertEqual(scalar(depth_two_report["status"]), depth_two_reference["status"], depth_two_report)
        self.assertEqual(depth_two_report["document"]["value"], depth_two_opened["document"])
        self.assertEqual(depth_two_report["revision"]["value"], depth_two_opened["revision"])
        self.assertEqual(depth_two_report["diagnostics"]["value"], [])
        bound_value = next(fields(item) for item in depth_two_report["bindings"]["value"]
                           if scalar(fields(item)["name"]) == "value")
        self.assertEqual(scalar(bound_value["typeName"]), "Int")
        binding_start = depth_two_source.index("value")
        use_index = depth_two_source.index("value", binding_start + len("value"))
        use_start = len(depth_two_source[:use_index].encode("utf-8"))
        value_reference = next(fields(item) for item in depth_two_report["references"]["value"]
                               if scalar(fields(item)["name"]) == "value")
        self.assertEqual(scalar(value_reference["startByte"]), use_start)
        self.assertEqual(scalar(value_reference["bindingId"]), scalar(bound_value["semanticId"]))
        self.assertIn("🐇".encode("utf-8"), depth_two_source.encode("utf-8"))
        self.assertEqual(depth_two_source.count(CRLF), 3)

        nested_prefix = (
            "type Leaf = L(Int) | OtherLeaf()" + NL +
            "type Mid = M(Leaf) | N()" + NL +
            "type Outer = O(Mid) | Empty()" + NL
        )
        depth_two_cases = [
            ("singleton-depth-two-exhaustive",
             "type Leaf = L(Int)" + NL +
             "type Mid = M(Leaf)" + NL +
             "type Outer = O(Mid) | Empty()" + NL +
             "fn f(x: Outer) -> Int { return match x { O(M(L(value))) => value Empty() => 0 } }",
             "valid", None),
            ("distinct-nested", nested_prefix +
             "fn f(x: Outer) -> Int { return match x { O(M(L(_))) => 1 O(M(OtherLeaf())) => 2 O(_) => 0 Empty() => 0 } }",
             "valid", None),
            ("duplicate-nested", nested_prefix +
             "fn f(x: Outer) -> Int { return match x { O(M(L(_))) => 1 O(M(L(_))) => 2 O(_) => 0 Empty() => 0 } }",
             "invalid", "PEP_DUPLICATE_MATCH_ARM"),
            ("collective-depth-two-conservative-incomplete", nested_prefix +
             "fn f(x: Outer) -> Int { return match x { O(M(L(_))) => 1 O(M(OtherLeaf())) => 2 O(N()) => 3 Empty() => 0 } }",
             "invalid", "PEP_NON_EXHAUSTIVE_MATCH"),
            ("collective-depth-two-wildcard-fallback", nested_prefix +
             "fn f(x: Outer) -> Int { return match x { O(M(L(_))) => 1 O(M(OtherLeaf())) => 2 O(N()) => 3 O(_) => 4 Empty() => 0 } }",
             "valid", None),
            ("collective-depth-two-partial", nested_prefix +
             "fn f(x: Outer) -> Int { return match x { O(M(L(_))) => 1 O(N()) => 3 Empty() => 0 } }",
             "invalid", "PEP_NON_EXHAUSTIVE_MATCH"),
            ("wrong-nested-type", nested_prefix + "type Wrong = W()" + NL +
             "fn f(x: Outer) -> Int { return match x { O(M(W())) => 1 O(_) => 0 Empty() => 0 } }",
             "invalid", "PEP_PATTERN_TYPE_MISMATCH"),
            ("depth-three-valid", "type Seed = K(Int)" + NL + "type Leaf = L(Seed)" + NL + "type Mid = M(Leaf)" + NL + "type Outer = O(Mid)" + NL + "fn f(x: Outer) -> Int { return match x { O(M(L(K(value)))) => value } }", "valid", None),
            ("depth-three-distinct-partials", "type Seed = K(Int) | R(Int)" + NL + "type Leaf = L(Seed)" + NL + "type Mid = M(Leaf)" + NL + "type Outer = O(Mid)" + NL + "fn f(x: Outer) -> Int { return match x { O(M(L(K(_)))) => 1 O(M(L(R(_)))) => 2 _ => 0 } }", "valid", None),
            ("depth-three-duplicate", "type Seed = K(Int)" + NL + "type Leaf = L(Seed)" + NL + "type Mid = M(Leaf)" + NL + "type Outer = O(Mid)" + NL + "fn f(x: Outer) -> Int { return match x { O(M(L(K(_)))) => 1 O(M(L(K(_)))) => 2 _ => 0 } }", "invalid", "PEP_DUPLICATE_MATCH_ARM"),
            ("wrong-nested-arity", nested_prefix +
             "fn f(x: Outer) -> Int { return match x { O(M(L())) => 1 O(_) => 0 Empty() => 0 } }",
             "invalid", "PEP_PATTERN_ARITY"),
        ]
        for case_name, case_source, expected_status, expected_code in depth_two_cases:
            with self.subTest(depth_two_case=case_name):
                case_opened = self._open(case_source)
                case_target = {"document": case_opened["document"], "revision": case_opened["revision"], "entryFunctions": []}
                case_parsed = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                                "op": "tool_invoke", "tool": "pep-a13-parser", "arguments": [],
                                                "semanticTarget": case_target})
                self.assertEqual(case_parsed.get("outcome"), "ok", case_parsed)
                case_checked = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                                 "op": "tool_invoke", "tool": "pep-a13-checker-staged",
                                                 "arguments": [case_parsed["result"]], "semanticTarget": case_target})
                self.assertEqual(case_checked.get("outcome"), "ok", case_checked)
                case_report = fields(case_checked["result"])
                case_reference = self._reference_check("nested-pattern-depth-two-" + case_name, case_source)
                self.assertEqual(case_reference["status"], expected_status, case_reference)
                self.assertEqual(scalar(case_report["status"]), expected_status, case_report)
                expected_diagnostics = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in case_reference["diagnostics"]
                ]
                actual_diagnostics = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in case_report["diagnostics"]["value"]
                ]
                self.assertEqual(actual_diagnostics, expected_diagnostics, case_report)
                if expected_code is not None:
                    self.assertEqual([item[0] for item in actual_diagnostics], [expected_code])

        depth_three_source = (
            "type Seed = K(Int)" + NL +
            "type Leaf = L(Seed)" + NL +
            "type Mid = M(Leaf)" + NL +
            "type Outer = O(Mid)" + NL +
            "fn f(x: Outer) -> Int { return match x { O(M(L(K(value)))) => value } }"
        )
        depth_three_opened = self._open(depth_three_source)
        depth_three_target = {"document": depth_three_opened["document"], "revision": depth_three_opened["revision"], "entryFunctions": []}
        depth_three_parsed = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                               "op": "tool_invoke", "tool": "pep-a13-parser", "arguments": [],
                                               "semanticTarget": depth_three_target})
        self.assertEqual(depth_three_parsed.get("outcome"), "ok", depth_three_parsed)
        depth_three_checked = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                                "op": "tool_invoke", "tool": "pep-a13-checker-staged",
                                                "arguments": [depth_three_parsed["result"]],
                                                "semanticTarget": depth_three_target})
        self.assertEqual(depth_three_checked.get("outcome"), "ok", depth_three_checked)
        depth_three_report = fields(depth_three_checked["result"])
        depth_three_reference = self._reference_check("nested-pattern-depth-three", depth_three_source)
        self.assertEqual(depth_three_reference["status"], "valid", depth_three_reference)
        self.assertEqual(scalar(depth_three_report["status"]), "valid", depth_three_report)
        depth_three_diagnostics = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in depth_three_report["diagnostics"]["value"]
        ]
        self.assertEqual(depth_three_diagnostics, [])
        one_shot = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "pep-a13-checker", "arguments": [],
                                     "semanticTarget": target})
        if one_shot.get("outcome") == "error":
            self.assertEqual(one_shot["error"]["code"], "PEP_RUNTIME_STEP_LIMIT", one_shot)
        else:
            one_shot_report = fields(one_shot["result"])
            self.assertEqual(scalar(one_shot_report["status"]), reference["status"], one_shot_report)
            self.assertEqual(
                [(scalar(fields(item)["name"]), scalar(fields(item)["expectedType"])) for item in one_shot_report["holes"]["value"]],
                [("pending", "Int")],
            )

    def test_empty_program_is_consumed_through_the_owned_parser_chain(self):
        _, report = self._analyze("")
        self.assertEqual(scalar(report["status"]), "valid", report)
        self.assertEqual(scalar(report["syntaxNodeCount"]), 0)
        self.assertEqual(report["functions"]["value"], [])

    def test_forward_and_mutual_recursive_calls_use_checker_owned_ids(self):
        source = "fn first(x: Int) -> Int { return later(x) }" + NL + "fn later(x: Int) -> Int { return first(x) }" + NL
        opened, report = self._analyze(source)
        self.assertEqual(opened["status"], "valid")
        self.assertEqual(scalar(report["status"]), "valid", report)
        functions = [fields(item) for item in report["functions"]["value"]]
        by_name = {scalar(item["name"]): scalar(item["semanticId"]) for item in functions}
        self.assertEqual(by_name, {"first": 100000, "later": 100001})
        calls = [fields(item) for item in report["calls"]["value"]]
        self.assertEqual([(scalar(item["callerId"]), scalar(item["calleeId"])) for item in calls],
                         [(by_name["first"], by_name["later"]), (by_name["later"], by_name["first"])])
        bindings = [fields(item) for item in report["bindings"]["value"]]
        references = [fields(item) for item in report["references"]["value"]]
        self.assertEqual([scalar(item["name"]) for item in bindings], ["x", "x"])
        self.assertEqual([scalar(item["bindingId"]) for item in references], [scalar(item["semanticId"]) for item in bindings])
        typed_calls = []
        def visit(value):
            if isinstance(value, dict):
                if value.get("kind") == "call":
                    typed_calls.append((value.get("name"), value.get("functionId")))
                for nested in value.values():
                    visit(nested)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested)
        visit(opened["typedTree"])
        self.assertEqual(typed_calls, [("later", 1), ("first", 0)])

    def test_call_owner_collection_matches_reference(self):
        lines = ["fn accepts(x: Bool) -> Bool { return x }"]
        lines.extend(f"fn bad{i}() -> Bool {{ return accepts({i}) }}" for i in range(3))
        source = NL.join(lines)
        reference = self._reference_check("multiple-call-owners", source)
        _, report = self._analyze(source)
        expected = [(item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]]
        actual = [(scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                  for item in report["diagnostics"]["value"]]
        self.assertEqual(expected[0][0], "PEP_TYPE_MISMATCH", (expected, reference))
        self.assertEqual(actual, expected, (expected, actual, report))
        calls = [fields(item) for item in report["calls"]["value"]]
        self.assertEqual(len(calls), 3, report)
        self.assertEqual([scalar(item["callerId"]) for item in calls], [100001, 100002, 100003])
        self.assertEqual([scalar(item["calleeId"]) for item in calls], [100000] * 3)

    def test_unknown_function_and_wrong_arity_keep_call_byte_spans(self):
        source = "fn main() -> Int { return absent(1) }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "invalid", report)
        diagnostic = fields(report["diagnostics"]["value"][0])
        self.assertEqual(scalar(diagnostic["code"]), "PEP_UNKNOWN_FUNCTION")
        start = source.index("absent")
        self.assertEqual((scalar(diagnostic["startByte"]), scalar(diagnostic["endByte"])),
                         (len(source[:start].encode()), len(source[:start + len("absent(1)")].encode())))
        source = "fn id(x: Int) -> Int { return x }" + NL + "fn main() -> Int { return id() }"
        opened, report = self._analyze(source)
        self.assertEqual(opened["status"], "invalid")
        diagnostic = fields(report["diagnostics"]["value"][0])
        self.assertEqual(scalar(diagnostic["code"]), "PEP_ARGUMENT_COUNT")
        start = source.rindex("id()")
        self.assertEqual((scalar(diagnostic["startByte"]), scalar(diagnostic["endByte"])),
                         (len(source[:start].encode()), len(source[:start + len("id()")].encode())))

    def test_unknown_constructor_span_after_utf8_prefix_matches_reference(self):
        source = "// 🐇\n type M=A(Int)|B() fn f()->M{return C(1)}"
        reference = self._reference_check("unknown-constructor-unicode-prefix", source)
        _, report = self._analyze(source)
        self.assertEqual(reference["status"], "invalid", reference)
        diagnostic = fields(report["diagnostics"]["value"][0])
        self.assertEqual(scalar(diagnostic["code"]), "PEP_UNKNOWN_CONSTRUCTOR")
        start = source.index("C(1)")
        expected_span = (len(source[:start].encode("utf-8")),
                         len(source[:start + len("C(1)")].encode("utf-8")))
        expected = reference["diagnostics"][0]
        self.assertEqual((expected["span"]["start"]["offset"], expected["span"]["endOffset"]),
                         expected_span)
        self.assertEqual((scalar(diagnostic["startByte"]), scalar(diagnostic["endByte"])),
                         expected_span)

    def test_declared_uppercase_function_is_resolved_before_constructor_classification(self):
        source = "fn Missing(value: Int)->Int{return value} fn f()->Int{return Missing(7)}"
        reference = self._reference_check("declared-uppercase-function", source)
        _, report = self._analyze(source)
        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        self.assertEqual(report["diagnostics"]["value"], [], report)
        call = fields(report["calls"]["value"][0])
        self.assertEqual(scalar(call["callerId"]), 100001)
        self.assertEqual(scalar(call["calleeId"]), 100000)
        start = source.index("Missing(7)")
        self.assertEqual((scalar(call["startByte"]), scalar(call["endByte"])),
                         (len(source[:start].encode("utf-8")),
                          len(source[:start + len("Missing(7)")].encode("utf-8"))))

    def test_nested_block_shadowing_and_unknown_binding(self):
        source = "fn main(x: Int) -> Int { let y = x; { let x = y; return x } }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "valid", report)
        bindings = [fields(item) for item in report["bindings"]["value"]]
        references = [fields(item) for item in report["references"]["value"]]
        self.assertEqual([scalar(item["name"]) for item in bindings], ["x", "y", "x"])
        self.assertEqual([scalar(item["name"]) for item in references], ["x", "y", "x"])
        self.assertEqual([scalar(item["bindingId"]) for item in references],
                         [scalar(bindings[0]["semanticId"]), scalar(bindings[1]["semanticId"]), scalar(bindings[2]["semanticId"])])
        self.assertNotEqual(scalar(bindings[0]["scopeId"]), scalar(bindings[2]["scopeId"]))

        cases = [
            ("unknown-local", "fn main() -> Int { return missing }"),
            ("for-in-binding-does-not-escape", "fn main() -> Int { for item in [1] {} return item }"),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check("unknown-reference-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, report)
                self.assertEqual(len(actual), 1)
                self.assertEqual(actual[0][0], "PEP_UNKNOWN_VARIABLE")

    def test_primitive_synth_check_and_type_facts(self):
        source = "fn add(x: Int) -> Int { let y: Int = x + 1; return y }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "valid", report)
        function = fields(report["functions"]["value"][0])
        self.assertEqual(scalar(function["returnType"]), "Int")
        bindings = [fields(item) for item in report["bindings"]["value"]]
        self.assertEqual([scalar(item["typeName"]) for item in bindings], ["Int", "Int"])
        types = [fields(item) for item in report["expressionTypes"]["value"]]
        self.assertEqual([scalar(item["typeName"]) for item in types], ["Int", "Int", "Int", "Int"])
        shapes = [fields(item["typeShape"]) for item in types]
        self.assertEqual(
            [(scalar(shape["kind"]), scalar(shape["name"]), scalar(shape["listDepth"])) for shape in shapes],
            [("builtin", "Int", 0)] * 4,
        )
        binary = next(item for item in types if scalar(item["startByte"]) == source.index("x + 1"))
        self.assertEqual((scalar(binary["startByte"]), scalar(binary["endByte"])),
                         (source.index("x + 1"), source.index("x + 1") + len("x + 1")))

    def test_function_argument_diagnostics_match_ocaml(self):
        cases = [
            ("scalar", "fn g(a: Int) -> Int { return a }" + NL + "fn f() -> Int { return g(true) }"),
            ("multiple", "fn g(a: Int, b: Bool, c: Str) -> Int { return a }" + NL + "fn f() -> Int { return g(true, 1, false) }"),
            ("later-argument", "fn g(a: Int, b: Bool) -> Int { return a }" + NL + "fn f() -> Int { return g(1, 1) }"),
            ("list-leaf", "fn g(a: List[Int]) -> Int { return 0 }" + NL + "fn f() -> Int { return g([\"text\"]) }"),
            ("nested-list-leaf", "fn g(a: List[List[Int]]) -> Int { return 0 }" + NL + "fn f() -> Int { return g([[\"text\"]]) }"),
            ("record", "type Point { x: Int }" + NL + "fn g(a: Point) -> Int { return 0 }" + NL + "fn f() -> Int { return g(true) }"),
            ("nested-call-error", "fn g(a: Bool) -> Bool { return a }" + NL + "fn h(x: Int) -> Int { return x }" + NL + "fn f() -> Bool { return g(h(true)) }"),
            ("two-nested-call-errors", "fn g(a: Bool, b: Bool) -> Bool { return a }" + NL + "fn h(x: Int) -> Int { return x }" + NL + "fn f() -> Bool { return g(h(true), h(false)) }"),
            ("separate-call-errors", "fn g(a: Bool) -> Bool { return a }" + NL + "fn f() -> Int { let first = g(1); let second = g(2); return 0 }"),
            ("call-error-before-binary-sibling", "fn g(a: Int) -> Bool { return true }" + NL + "fn f() -> Int { return g(true) + true }"),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check("call-argument-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                expected = [(item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                            for item in reference["diagnostics"]]
                actual = [(scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                          for item in report["diagnostics"]["value"]]
                self.assertEqual(expected[0][0], "PEP_TYPE_MISMATCH", (name, expected))
                self.assertEqual(len(expected), 1, (name, expected))
                self.assertEqual(scalar(report["status"]), "invalid", report)
                self.assertEqual(actual, expected, (name, expected, actual))

    def test_return_argument_and_operator_type_errors_are_explicit(self):
        source = "fn wrong(x: Bool) -> Int { return x }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "invalid", report)
        codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
        self.assertIn("PEP_TYPE_MISMATCH", codes)

        source = "fn id(x: Int) -> Int { return x }" + NL + "fn main() -> Int { return id(true) }"
        _, report = self._analyze(source)
        codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
        self.assertIn("PEP_TYPE_MISMATCH", codes)

        source = "fn main() -> Int { return 1 + true }"
        _, report = self._analyze(source)
        codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
        self.assertIn("PEP_TYPE_MISMATCH", codes)

    def test_equality_left_operand_diagnostics_match_ocaml(self):
        cases = [
            ("hole", "fn f() -> Bool { return ?lhs == 1 }", "PEP_EQUALITY_UNTYPED"),
            ("hole-not-equal", "fn f() -> Bool { return ?lhs != 1 }", "PEP_EQUALITY_UNTYPED"),
            ("hole-before-unknown-right", "fn f() -> Bool { return ?lhs == missing }", "PEP_EQUALITY_UNTYPED"),
            ("all-hole-if", "fn f(flag: Bool) -> Bool { return (if flag { ?a } else { ?b }) == true }", "PEP_EQUALITY_UNTYPED"),
            ("unknown-if-condition", "fn f() -> Bool { return (if missing { ?a } else { ?b }) == true }", "PEP_UNKNOWN_VARIABLE"),
            ("unknown-name", "fn f() -> Bool { return missing == 1 }", "PEP_UNKNOWN_VARIABLE"),
            ("empty-list", "fn f() -> Bool { return [] == [1] }", "PEP_EMPTY_LIST_NEEDS_TYPE"),
        ]
        for name, source, expected_code in cases:
            with self.subTest(name=name):
                reference = self._reference_check("equality-left-" + name, source)
                _, report = self._analyze(source)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                self.assertEqual(actual, expected, (name, expected, actual, report))
                self.assertEqual([item[0] for item in actual], [expected_code])

    def test_return_mismatch_diagnostics_match_ocaml(self):
        cases = [
            ("scalar", "fn wrong(x: Bool) -> Int { return x }"),
            ("unit-result", "fn wrong() -> Unit { return 1 }"),
            ("conditional-branch", "fn wrong(flag: Bool) -> Int { return if flag { true } else { 0 } }"),
            ("conditional-list-leaf", "fn f(flag: Bool) -> List[Int] { return if flag { [1] } else { [true] } }"),
            ("conditional-nested-list-leaf", "fn f(flag: Bool) -> List[List[Int]] { return if flag { [[1]] } else { [[true]] } }"),
            ("conditional-nested-list-leaf-then", "fn f(flag: Bool) -> List[List[Int]] { return if flag { [[true]] } else { [[1]] } }"),
            ("list-leaf", "fn bad() -> List[Int] { return [\"text\"] }"),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check("return-mismatch-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, report)

    def test_nested_append_return_context_matches_ocaml(self):
        cases = [
            ("integer", "fn f(xs: List[List[Int]]) -> List[List[Int]] { return append(xs, [[1]]) }", "valid"),
            ("contextual-inner-bool", "fn f(xs: List[List[Int]]) -> List[List[Int]] { return append(xs, [[true]]) }", "valid"),
            ("exact-depth-mismatch", "fn f(xs: List[List[Int]]) -> List[List[Int]] { return append(xs, [true]) }", "invalid"),
        ]
        for name, source, expected_status in cases:
            with self.subTest(name=name):
                reference = self._reference_check("nested-append-return-context-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], expected_status, reference)
                self.assertEqual(scalar(report["status"]), reference["status"], report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, report)

    def test_primitive_builtin_signatures_are_checked(self):
        source = "fn main() -> Unit { say(int_text(7)); return say(\"done\") }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "valid", report)
        types_by_start = {scalar(fields(item)["startByte"]): scalar(fields(item)["typeName"]) for item in report["expressionTypes"]["value"]}
        for call, expected_type in [("say(int_text(7))", "Unit"), ("int_text(7)", "Str"), ("say(\"done\")", "Unit")]:
            self.assertEqual(types_by_start[source.index(call)], expected_type)

        cases = [
            ("say-wrong-arity", "fn main() -> Unit { return say() }", "PEP_ARGUMENT_COUNT"),
            ("say-wrong-type", "fn main() -> Unit { return say(1) }", "PEP_TYPE_MISMATCH"),
            ("int-text-wrong-arity", "fn main() -> Str { return int_text() }", "PEP_ARGUMENT_COUNT"),
            ("int-text-wrong-type", "fn main() -> Str { return int_text(true) }", "PEP_TYPE_MISMATCH"),
            ("byte-length-wrong-type", "fn main() -> Int { return byte_length(1) }", "PEP_TYPE_MISMATCH"),
            ("utf8-slice-wrong-type", "fn main() -> Str { return utf8_slice(source_bytes(), 0, true) }", "PEP_TYPE_MISMATCH"),
            ("multiple-wrong-builtin-types", "fn main() -> Int { let a = int_text(true); let b = byte_length(1); return 0 }", "PEP_TYPE_MISMATCH"),
        ]
        for name, source, expected_code in cases:
            reference = self._reference_check("builtin-argument-" + name, source)
            _, report = self._analyze(source)
            self.assertEqual(reference["status"], "invalid", reference)
            expected = [
                (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                for item in reference["diagnostics"]
            ]
            actual = [
                (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                for item in report["diagnostics"]["value"]
            ]
            self.assertEqual(actual, expected, (name, expected, actual, report))
            self.assertIn(expected_code, [item[0] for item in actual])

    def test_statement_conditions_are_typed_and_holes_keep_boolean_expectations(self):
        _, report = self._analyze("fn main() -> Unit { if true {} else {} while false {} }")
        self.assertEqual(scalar(report["status"]), "valid", report)

        for source in ["fn main() -> Unit { if 1 {} else {} }", "fn main() -> Unit { while \"no\" {} }"]:
            _, report = self._analyze(source)
            self.assertEqual(scalar(report["status"]), "invalid", report)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertIn("PEP_TYPE_MISMATCH", codes)

        for name, source in [("if", "fn main(flag: Bool) -> Unit { if ?condition {} else {} }"), ("while", "fn main(flag: Bool) -> Unit { while ?condition {} }")]:
            reference = self._reference_check("statement-condition-hole-" + name, source)
            _, report = self._analyze(source)
            self.assertEqual(reference["status"], "incomplete", reference)
            self.assertEqual(scalar(report["status"]), "incomplete", report)
            self.assertEqual(len(report["holes"]["value"]), 1)
            hole = fields(report["holes"]["value"][0])
            ref_hole = reference["holes"][0]
            self.assertEqual(scalar(hole["expectedType"]), ref_hole["expectedType"])
            self.assertEqual(ref_hole["expectedType"], "Bool")
            self.assertEqual((scalar(hole["startByte"]), scalar(hole["endByte"])), (ref_hole["span"]["start"]["offset"], ref_hole["span"]["endOffset"]))
            bindings = [fields(item) for item in report["bindings"]["value"]]
            binding_names = {scalar(item["semanticId"]): scalar(item["name"]) for item in bindings}
            visible_names = {binding_names[scalar(item)] for item in hole["visibleBindingIds"]["value"]}
            candidate_names = {binding_names[scalar(item)] for item in hole["candidateBindingIds"]["value"]}
            self.assertEqual(visible_names, {item["name"] for item in ref_hole["bindings"]})
            self.assertEqual(candidate_names, {item["name"] for item in ref_hole["actions"][0]["candidates"]})
            self.assertEqual(visible_names, {"flag"})
            self.assertEqual(candidate_names, {"flag"})
            flag = next(item for item in bindings if scalar(item["name"]) == "flag")
            self.assertEqual(scalar(hole["scopeId"]), scalar(flag["scopeId"]))
            self.assertIn(scalar(flag["semanticId"]), [scalar(item) for item in hole["visibleBindingIds"]["value"]])

    def test_unconstrained_empty_lists_match_reference_diagnostic(self):
        cases = [
            ("return-nonlist", "fn bad() -> Int { return [] }"),
            ("binding-no-context", "fn main() -> Int { let xs = []; return 0 }"),
            ("binding-nonlist-context", "fn main() -> Int { let xs: Int = []; return 0 }"),
            ("length-argument", "fn bad() -> Int { return length([]) }"),
            ("contains-argument", "fn bad() -> Bool { return contains([], true) }"),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check(name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                diagnostics = [fields(item) for item in report["diagnostics"]["value"]]
                self.assertEqual(
                    [scalar(item["code"]) for item in diagnostics],
                    ["PEP_EMPTY_LIST_NEEDS_TYPE"],
                    report,
                )
                self.assertEqual(len(reference["diagnostics"]), 1, reference)
                reference_diagnostic = reference["diagnostics"][0]
                start = source.index("[]")
                end = start + 2
                self.assertEqual(reference_diagnostic["code"], "PEP_EMPTY_LIST_NEEDS_TYPE")
                self.assertEqual(reference_diagnostic["span"]["start"]["offset"], start)
                self.assertEqual(reference_diagnostic["span"]["endOffset"], end)
                self.assertEqual(scalar(diagnostics[0]["startByte"]), start)
                self.assertEqual(scalar(diagnostics[0]["endByte"]), end)

    def test_list_literals_and_contextual_empty_list_typecheck(self):
        cases = [
            ("fn values() -> List[Int] { return [1, 2] }", "List[Int]"),
            ("fn empty() -> List[Int] { return [] }", "List[Int]"),
            ("fn main() -> Int { let values: List[Int] = []; return length(values) }", "Int"),
            ("fn main() -> Int { let values = [1, 2]; return length(values) }", "Int"),
        ]
        for source, result_type in cases:
            _, report = self._analyze(source)
            self.assertEqual(scalar(report["status"]), "valid", report)
            functions = [fields(item) for item in report["functions"]["value"]]
            self.assertEqual(scalar(functions[-1]["returnType"]), result_type)
            if "let values" in source:
                binding = fields(report["bindings"]["value"][0])
                self.assertEqual(scalar(binding["typeName"]), "List[Int]")
                self.assertGreater(len(report["expressionTypes"]["value"]), 0)
                if "let values =" in source:
                    shape = fields(binding["typeShape"])
                    self.assertEqual(scalar(shape["kind"]), "builtin")
                    self.assertEqual(scalar(shape["name"]), "Int")
                    self.assertEqual(scalar(shape["listDepth"]), 1)

        cases = [
            ("fn bad() -> List[Int] { return [1, true] }", "PEP_TYPE_MISMATCH"),
            ("fn bad() -> List[Int] { return [\"text\"] }", "PEP_TYPE_MISMATCH"),
        ]
        for source, expected_code in cases:
            _, report = self._analyze(source)
            self.assertEqual(scalar(report["status"]), "invalid", report)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertIn(expected_code, codes)

    def test_empty_list_uses_nominal_record_field_context_matches_ocaml(self):
        source = (
            "type Item { value: Int }" + NL +
            "type Bag { items: List[Item] }" + NL +
            "fn main() -> Int { let bag = Bag { items: [] }; return 0 }"
        )
        reference = self._reference_check("empty-nominal-record-list", source)
        _, report = self._analyze(source)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        self.assertEqual(report["diagnostics"]["value"], [], report)
        empty_offset = source.encode("utf-8").index(b"[]")
        empty_list = next(
            fields(item) for item in report["expressionTypes"]["value"]
            if scalar(fields(item)["startByte"]) == empty_offset
        )
        shape = fields(empty_list["typeShape"])
        self.assertEqual(scalar(shape["kind"]), "nominal")
        self.assertEqual(scalar(shape["name"]), "Item")
        self.assertEqual(scalar(shape["listDepth"]), 1)

    def test_nominal_call_result_field_access_matches_ocaml(self):
        source = (
            "type Utf8Check { width: Int, invalidOffset: Int }" + NL +
            "fn utf8_check() -> Utf8Check { return Utf8Check { width: 1, invalidOffset: -1 } }" + NL +
            "fn sample() -> Int { let check = utf8_check(); return check.invalidOffset }"
        )
        reference = self._reference_check("nominal-call-field-access", source)
        _, report = self._analyze_staged(source)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        self.assertEqual(report["diagnostics"]["value"], [], report)

    def test_semantic_snapshot_program_info_matches_ocaml(self):
        source = "fn main() -> Str { let info = semantic_snapshot(); return info.document }"
        reference = self._reference_check("semantic-snapshot-program-info", source)
        _, report = self._analyze(source)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        self.assertEqual(report["diagnostics"]["value"], [], report)
        expression_types = {
            scalar(fields(item)["typeName"])
            for item in report["expressionTypes"]["value"]
        }
        self.assertIn("ProgramInfo", expression_types, report)
        self.assertIn("Str", expression_types, report)

    def test_str_contains_checker_contract_matches_ocaml(self):
        cases = [
            ("valid", "fn has(haystack: Str, needle: Str) -> Bool { return str_contains(haystack, needle) }", "valid"),
            ("wrong-haystack", "fn bad() -> Bool { return str_contains(1, \"x\") }", "invalid"),
            ("wrong-needle", "fn bad() -> Bool { return str_contains(\"x\", 1) }", "invalid"),
            ("wrong-arity", "fn bad() -> Bool { return str_contains(\"x\") }", "invalid"),
            ("first-hole", "fn search() -> Bool { return str_contains(?haystack, \"x\") }", "incomplete"),
            ("second-hole", "fn search() -> Bool { return str_contains(\"x\", ?needle) }", "incomplete"),
        ]
        for name, source, status in cases:
            with self.subTest(name=name):
                reference = self._reference_check("str-contains-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], status, reference)
                self.assertEqual(scalar(report["status"]), status, report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, report)
                if name in {"first-hole", "second-hole"}:
                    self.assertEqual(len(report["holes"]["value"]), 1, report)
                    self.assertEqual(scalar(fields(report["holes"]["value"][0])["expectedType"]), "Str")

        source = (
            'fn has(haystack: Str, needle: Str) -> Bool { return str_contains(haystack, needle) }'
            + NL
            + 'fn flags(haystack: Str, needle: Str) -> List[Bool] { return [str_contains(haystack, needle)] }'
        )
        reference = self._reference_check("str-contains-declaration-signatures", source)
        _, report = self._analyze_staged(source)
        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        declarations = [fields(item) for item in report["functions"]["value"]]
        self.assertEqual(
            [(scalar(item["name"]), scalar(item["arity"]), scalar(item["returnType"])) for item in declarations],
            [("has", 2, "Bool"), ("flags", 2, "List[Bool]")],
        )

    def test_real_utf8_check_fragment_reaches_checker_with_ocaml_parity(self):
        lexer_source = LEXER.read_text(encoding="utf-8")
        type_start = lexer_source.index("type Utf8Check ")
        type_end = lexer_source.index(NL, type_start)
        function_start = lexer_source.index("fn utf8_check(")
        function_end = lexer_source.index(NL + "fn advance_position(", function_start)
        source = (
            lexer_source[type_start:type_end]
            + NL
            + lexer_source[function_start:function_end]
            + NL
            + "fn main() -> Int { return 0 }"
        )

        reference = self._reference_check("real-utf8-check-fragment", source)
        parser_result = self._parse_staged(source)
        _, report = self._analyze_staged(source, parser_result=parser_result)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        declarations = [fields(item) for item in report["functions"]["value"]]
        self.assertEqual(
            [(scalar(item["name"]), scalar(item["arity"]), scalar(item["returnType"])) for item in declarations],
            [("utf8_check", 3, "Utf8Check"), ("main", 0, "Int")],
        )

    def test_staged_checker_composes_thirty_two_sequential_local_bindings(self):
        count = 32
        lines = ["fn main() -> Int {"]
        lines.extend(
            f"  let x{index} = {index if index == 0 else f'x{index - 1} + 1'}"
            for index in range(count)
        )
        lines.extend([f"  return x{count - 1}", "}"])
        source = NL.join(lines)

        reference = self._reference_check("staged-32-sequential-bindings", source)
        parser_result = self._parse_staged(source)
        _, report = self._analyze_staged(source, parser_result=parser_result)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        self.assertEqual(len(report["bindings"]["value"]), count, report)
        names = [scalar(fields(item)["name"]) for item in report["bindings"]["value"]]
        self.assertEqual(names, [f"x{index}" for index in range(count)])

    def test_staged_checker_composes_sixty_four_sequential_local_bindings(self):
        count = 64
        lines = ["fn main() -> Int {"]
        lines.extend(
            f"  let x{index} = {index if index == 0 else f'x{index - 1} + 1'}"
            for index in range(count)
        )
        lines.extend([f"  return x{count - 1}", "}"])
        source = NL.join(lines)

        reference = self._reference_check("staged-64-sequential-bindings", source)
        parser_result = self._parse_staged(source)
        _, report = self._analyze_staged(source, parser_result=parser_result)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        self.assertEqual(len(report["bindings"]["value"]), count, report)
        names = [scalar(fields(item)["name"]) for item in report["bindings"]["value"]]
        self.assertEqual(names, [f"x{index}" for index in range(count)])

    def test_staged_checker_composes_ninety_six_sequential_local_bindings(self):
        count = 96
        lines = ["fn main() -> Int {"]
        lines.extend(
            f"  let x{index} = {index if index == 0 else f'x{index - 1} + 1'}"
            for index in range(count)
        )
        lines.extend([f"  return x{count - 1}", "}"])
        source = NL.join(lines)

        reference = self._reference_check("staged-96-sequential-bindings", source)
        parser_result = self._parse_staged(source)
        _, report = self._analyze_staged(source, parser_result=parser_result)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        self.assertEqual(len(report["bindings"]["value"]), count, report)
        self.assertEqual(len(report["references"]["value"]), count, report)
        names = [scalar(fields(item)["name"]) for item in report["bindings"]["value"]]
        self.assertEqual(names, [f"x{index}" for index in range(count)])

    def test_staged_checker_composes_one_hundred_twenty_eight_sequential_local_bindings(self):
        count = 128
        lines = ["fn main() -> Int {"]
        lines.extend(
            f"  let x{index} = {index}" if index == 0 else f"  let x{index} = x{index - 1} + 1"
            for index in range(count)
        )
        lines.extend([f"  return x{count - 1}", "}"])
        source = NL.join(lines)

        reference = self._reference_check("staged-128-sequential-bindings", source)
        parser_result = self._parse_staged(source)
        _, report = self._analyze_staged(source, parser_result=parser_result)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        self.assertEqual(len(report["bindings"]["value"]), count, report)
        self.assertEqual(len(report["references"]["value"]), count, report)

    def test_staged_checker_composes_two_hundred_fifty_six_sequential_local_bindings(self):
        count = 256
        lines = ["fn main() -> Int {"]
        lines.extend(
            f"  let x{index} = {index}" if index == 0 else f"  let x{index} = x{index - 1} + 1"
            for index in range(count)
        )
        lines.extend([f"  return x{count - 1}", "}"])
        source = NL.join(lines)

        reference = self._reference_check("staged-256-sequential-bindings", source)
        parser_result = self._parse_staged(source)
        _, report = self._analyze_staged(source, parser_result=parser_result)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        self.assertEqual(len(report["bindings"]["value"]), count, report)
        self.assertEqual(len(report["references"]["value"]), count, report)

    def test_staged_checker_composes_five_hundred_thirteen_sequential_local_bindings(self):
        count = 513
        lines = ["fn main() -> Int {"]
        lines.extend(
            f"  let x{index} = {index}" if index == 0 else f"  let x{index} = x{index - 1} + 1"
            for index in range(count)
        )
        lines.extend([f"  return x{count - 1}", "}"])
        source = NL.join(lines)

        reference = self._reference_check("staged-513-sequential-bindings", source)
        parser_result = self._parse_staged(source)
        _, report = self._analyze_staged(source, parser_result=parser_result)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        self.assertEqual(len(report["bindings"]["value"]), count, report)
        self.assertEqual(len(report["references"]["value"]), count, report)

    def test_full_compiler_bundle_typechecks_with_compact_checker_nodes(self):
        sources = (
            ROOT / "examples" / "pep_lexer.pep",
            ROOT / "examples" / "pep_parser.pep",
            ROOT / "tests" / "pep_checker_a13.pep",
            ROOT / "tests" / "pep_c23_emitter.pep",
        )
        bundle = NL.join(path.read_text(encoding="utf-8") for path in sources)
        opened = self.client.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                   "name": "a13-c23-compiler-bundle", "metadataOnly": True})
        self.assertEqual(opened.get("outcome"), "ok", opened)
        self.assertEqual(opened.get("status"), "valid", opened)

    def test_staged_checker_composes_two_hundred_twenty_four_function_roots(self):
        count = 224
        declarations = [
            f"fn f{index}(p{index}: Int) -> Int {{ let x{index} = p{index}; return x{index} }}"
            for index in range(count)
        ]
        declarations.extend([
            "fn enabled() -> Bool { return true }",
            "fn values() -> List[Int] { return [1] }",
            "fn main() -> Int { return 0 }",
        ])
        source = NL.join(declarations)

        reference = self._reference_check("staged-224-function-roots", source)
        parser_result = self._parse_staged(source)
        _, report = self._analyze_staged(source, parser_result=parser_result)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        actual = [
            (scalar(fields(item)["name"]), scalar(fields(item)["arity"]), scalar(fields(item)["returnType"]))
            for item in report["functions"]["value"]
        ]
        self.assertEqual(len(actual), count + 3)
        self.assertTrue(all(item[1] == 1 and item[2] == "Int" for item in actual[:count]))
        self.assertEqual(actual[0], ("f0", 1, "Int"))
        self.assertEqual(actual[-3:], [
            ("enabled", 0, "Bool"),
            ("values", 0, "List[Int]"),
            ("main", 0, "Int"),
        ])

    def test_staged_functions_resolve_forward_nominal_return_across_chunks(self):
        spacer_fields = ", ".join(f"slot{index}: Int" for index in range(16))
        source = NL.join([
            "fn make() -> Later { return Later { value: 7 } }",
            f"type Spacer {{ {spacer_fields} }}",
            "type Later { value: Int }",
        ])
        reference = self._reference_check("staged-forward-nominal-return", source)
        self.assertEqual(reference["status"], "valid", reference)
        opened, parsed = self._parse_staged(source)
        parser_nodes = fields(parsed)["nodes"]["value"]
        checker_nodes = [checker_node_value(node, len(source.encode("utf-8"))) for node in parser_nodes]
        later_id = next(
            scalar(fields(node)["id"])
            for node in parser_nodes
            if scalar(fields(node)["kind"]) == "record_declaration"
            and scalar(fields(node)["text"]) == "Later"
        )
        self.assertGreaterEqual(later_id, 32)

        self._register_checker_continuations()
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        cursor = self.client.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
            "tool": "pep-a13-checker-start",
            "arguments": [checker_progress_header(parsed), typed("Int", str(len(parser_nodes)))],
            "semanticTarget": target,
        })
        self.assertEqual(cursor.get("outcome"), "ok", cursor)
        cursor_value = cursor["result"]
        for _ in range(20):
            current = fields(cursor_value)
            phase = scalar(current["phase"])
            if phase == "bindings":
                break
            if phase == "validation":
                start = scalar(fields(current["validation"])["nextNode"])
                step_nodes = checker_nodes[start:min(start + 32, len(checker_nodes))]
            elif phase == "functions":
                start = scalar(current["typeOffset"])
                total = scalar(fields(current["validation"])["totalCount"])
                step_nodes = checker_nodes[start:min(start + 32, total)]
            else:
                self.fail(f"unexpected checker phase before function collection completed: {phase}")
            stepped = self.client.send({
                "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                "tool": "pep-a13-checker-step",
                "arguments": [cursor_value, typed_list("CheckerNode", step_nodes), typed_list("BindingFact", [])],
                "semanticTarget": target,
            })
            self.assertEqual(stepped.get("outcome"), "ok", stepped)
            cursor_value = stepped["result"]

        cursor_fields = fields(cursor_value)
        self.assertEqual(scalar(cursor_fields["phase"]), "bindings")
        functions = [fields(item) for item in cursor_fields["functions"]["value"]]
        make = next(item for item in functions if scalar(item["name"]) == "make")
        self.assertEqual(scalar(make["returnType"]), "Later")
        self.assertEqual(scalar(cursor_fields["revision"]), opened["revision"])

    def test_staged_checker_composes_thirty_two_function_signatures(self):
        declarations = []
        expected = []
        for index in range(32):
            if index % 3 == 0:
                declarations.append(f"fn f{index}() -> Int {{ return {index} }}")
                expected.append((f"f{index}", 0, "Int"))
            elif index % 3 == 1:
                declarations.append(f"fn f{index}(p{index}: Bool) -> Bool {{ return p{index} }}")
                expected.append((f"f{index}", 1, "Bool"))
            else:
                declarations.append(f"fn f{index}(p{index}: Int, q{index}: Bool) -> List[Bool] {{ return [] }}")
                expected.append((f"f{index}", 2, "List[Bool]"))
        declarations.append("fn main() -> Int { return 0 }")
        expected.append(("main", 0, "Int"))
        source = NL.join(declarations)

        reference = self._reference_check("staged-32-function-signatures", source)
        parser_result = self._parse_staged(source)
        _, report = self._analyze_staged(source, parser_result=parser_result)

        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        actual = [
            (scalar(fields(item)["name"]), scalar(fields(item)["arity"]), scalar(fields(item)["returnType"]))
            for item in report["functions"]["value"]
        ]
        self.assertEqual(actual, expected)

    def test_staged_checker_rejects_empty_validation_chunk_without_progress(self):
        source = "fn main() -> Int { return 1 }"
        opened, parsed = self._parse_staged(source)
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        self._register_checker_continuations()
        started = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-a13-checker-start",
                                    "arguments": [checker_progress_header(parsed), typed("Int", str(len(fields(parsed)["nodes"]["value"])))], "semanticTarget": target})
        self.assertEqual(started.get("outcome"), "ok", started)
        stepped = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-a13-checker-step",
                                    "arguments": [started["result"], typed_list("CheckerNode", []), typed_list("BindingFact", [])],
                                    "semanticTarget": target})
        self.assertEqual(stepped.get("outcome"), "ok", stepped)
        report = fields(fields(stepped["result"])["report"])
        self.assertEqual(scalar(report["status"]), "invalid", report)
        diagnostics = [fields(item) for item in report["diagnostics"]["value"]]
        self.assertEqual([scalar(item["code"]) for item in diagnostics], ["A13_INVALID_SYNTAX_TREE"])

    def test_staged_checker_rejects_noncontiguous_node_ids(self):
        source = "fn main() -> Int { return 0 }"
        opened, parsed = self._parse_staged(source)
        malformed = copy.deepcopy(parsed)
        nodes = next(field["value"]["value"] for field in malformed["fields"] if field["name"] == "nodes")
        first = nodes[0]
        id_field = next(field for field in first["fields"] if field["name"] == "id")
        id_field["value"] = typed("Int", "1")

        _, report = self._analyze_staged(source, parser_result=(opened, malformed))

        self.assertEqual(scalar(report["status"]), "invalid")
        diagnostics = [fields(item) for item in report["diagnostics"]["value"]]
        self.assertEqual(scalar(diagnostics[0]["code"]), "A13_INVALID_SYNTAX_TREE")

    def test_list_builtin_signatures_and_element_holes(self):
        cases = [
            ("fn size(values: List[Int]) -> Int { return length(values) }", "Int"),
            ("fn rev(values: List[Str]) -> List[Str] { return reverse(values) }", "List[Str]"),
            ("fn add(values: List[Int]) -> List[Int] { return append(values, 1) }", "List[Int]"),
            ("fn add(values: List[Int]) -> List[Int] { return prepend(values, 1) }", "List[Int]"),
            ("fn has(values: List[Bool]) -> Bool { return contains(values, true) }", "Bool"),
        ]
        for source, result_type in cases:
            _, report = self._analyze(source)
            self.assertEqual(scalar(report["status"]), "valid", report)
            function = fields(report["functions"]["value"][0])
            self.assertEqual(scalar(function["returnType"]), result_type)

        cases = [
            ("fn bad() -> List[Int] { return append([1], \"text\") }", "PEP_TYPE_MISMATCH"),
            ("fn bad() -> Int { return length(1) }", "PEP_LIST_EXPECTED"),
            ("fn bad() -> Int { return length([]) }", "PEP_EMPTY_LIST_NEEDS_TYPE"),
            ("fn bad() -> List[Int] { return reverse() }", "PEP_ARGUMENT_COUNT"),
            ("fn bad() -> Bool { return contains([source_bytes()], source_bytes()) }", "PEP_MEMBERSHIP_UNSUPPORTED"),
        ]
        for source, expected_code in cases:
            _, report = self._analyze(source)
            self.assertEqual(scalar(report["status"]), "invalid", report)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertIn(expected_code, codes)


    def test_list_type_mismatches_match_ocaml_codes_and_byte_spans(self):
        cases = [
            ("append-value", 'fn bad() -> List[Int] { return append([1], "text") }', '"text"'),
            ("contains-value", 'fn bad() -> Bool { return contains([1], "text") }', '"text"'),
            ("annotated-element", 'fn bad() -> Int { let values: List[Int] = ["x"]; return 0 }', '"x"'),
            ("returned-element", 'fn bad() -> List[Int] { return ["text"] }', '"text"'),
        ]
        for name, source, offending in cases:
            with self.subTest(name=name):
                _, report = self._analyze(source)
                reference = self._reference_check(name, source)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                self.assertEqual(reference["status"], "invalid", reference)
                pep_diagnostics = [fields(item) for item in report["diagnostics"]["value"]]
                canonical = [item for item in pep_diagnostics if scalar(item["code"]) == "PEP_TYPE_MISMATCH"]
                self.assertEqual(len(canonical), 1, report)
                expected_start = source.index(offending)
                expected_end = expected_start + len(offending)
                self.assertEqual(scalar(canonical[0]["startByte"]), expected_start)
                self.assertEqual(scalar(canonical[0]["endByte"]), expected_end)
                reference_diagnostic = reference["diagnostics"][0]
                self.assertEqual(reference_diagnostic["code"], "PEP_TYPE_MISMATCH")
                self.assertEqual(reference_diagnostic["span"]["start"]["offset"], expected_start)
                self.assertEqual(reference_diagnostic["span"]["endOffset"], expected_end)

    def test_list_holes_inherit_element_type_and_empty_context(self):
        source = "fn main(items: List[Int]) -> List[Int] { return append(items, ?item) }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "incomplete", report)
        hole = fields(report["holes"]["value"][0])
        self.assertEqual(scalar(hole["expectedType"]), "Int")

    def test_source_byte_builtin_signatures_are_checked(self):
        valid_cases = [
            ("fn main() -> SourceBytes { return source_bytes() }", "source_bytes()", "SourceBytes"),
            ("fn main() -> Int { return byte_length(source_bytes()) }", "byte_length(source_bytes())", "Int"),
            ("fn main() -> Int { return byte_at(source_bytes(), 0) }", "byte_at(source_bytes(), 0)", "Int"),
            ("fn main() -> SourceBytes { return byte_slice(source_bytes(), 0, 0) }", "byte_slice(source_bytes(), 0, 0)", "SourceBytes"),
            ("fn main() -> Str { return utf8_slice(source_bytes(), 0, 0) }", "utf8_slice(source_bytes(), 0, 0)", "Str"),
        ]
        for source, call, expected_type in valid_cases:
            _, report = self._analyze(source)
            self.assertEqual(scalar(report["status"]), "valid", report)
            types_by_start = {scalar(fields(item)["startByte"]): scalar(fields(item)["typeName"]) for item in report["expressionTypes"]["value"]}
            self.assertEqual(types_by_start[source.index(call)], expected_type)

        cases = [
            ("fn main() -> SourceBytes { return source_bytes(1) }", "PEP_ARGUMENT_COUNT"),
            ("fn main() -> Int { return byte_length(1) }", "PEP_TYPE_MISMATCH"),
            ("fn main() -> Int { return byte_at(source_bytes()) }", "PEP_ARGUMENT_COUNT"),
            ("fn main() -> SourceBytes { return byte_slice(source_bytes(), 0) }", "PEP_ARGUMENT_COUNT"),
            ("fn main() -> Str { return utf8_slice(source_bytes(), 0, true) }", "PEP_TYPE_MISMATCH"),
        ]
        for source, expected_code in cases:
            _, report = self._analyze(source)
            self.assertEqual(scalar(report["status"]), "invalid", report)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertIn(expected_code, codes)

    def _reference_check(self, name, source):
        path = BUILD / ("oracle-" + name + ".pep")
        path.write_text(source, encoding="utf-8", newline=NL)
        completed = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "check", str(path), "--json"],
            cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, timeout=60,
        )
        self.assertIn(completed.returncode, (0, 1), completed.stderr)
        return json.loads(completed.stdout)

    def test_unimplemented_semantics_fail_closed_against_ocaml(self):
        cases = [
            ("record-field", "type Point { x: Int }" + NL + "fn main() -> Int { let p = Point { x: true }; return 0 }", "PEP_TYPE_MISMATCH", "PEP_TYPE_MISMATCH"),
            ("constructor-payload", "type Maybe = Some(Int) | None()" + NL + "fn main() -> Int { let value = Some(true); return 0 }", "PEP_TYPE_MISMATCH", "PEP_TYPE_MISMATCH"),
            ("if-condition", "fn main() -> Int { if 1 { return 1 } else { return 2 } }", "PEP_TYPE_MISMATCH", "PEP_TYPE_MISMATCH"),
            ("while-condition", "fn main() -> Unit { while 1 {} }", "PEP_TYPE_MISMATCH", "PEP_TYPE_MISMATCH"),
            ("builtin-arity", "fn main() -> Int { return length() }", "PEP_ARGUMENT_COUNT", "PEP_ARGUMENT_COUNT"),
            ("builtin-type", "fn main() -> Int { return length(1) }", "PEP_LIST_EXPECTED", "PEP_LIST_EXPECTED"),
            ("for-in-source", "fn main() -> Int { for item in 1 {} return 0 }", "PEP_FOR_REQUIRES_LIST", "PEP_FOR_REQUIRES_LIST"),
            ("missing-return", "fn main() -> Int { let x: Int = 1 }", "PEP_MISSING_RETURN", "PEP_MISSING_RETURN"),
        ]
        for name, source, reference_code, checker_code in cases:
            reference = self._reference_check(name, source)
            _, report = self._analyze(source)
            self.assertEqual(reference["status"], "invalid", (name, reference))
            self.assertIn(reference_code, [item["code"] for item in reference["diagnostics"]], (name, reference))
            self.assertEqual(scalar(report["status"]), "invalid", (name, report))
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertIn(checker_code, codes, (name, codes))
            if name in {"record-field", "constructor-payload", "if-condition", "while-condition", "missing-return", "builtin-arity", "builtin-type"}:
                expected = [(item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"]) for item in reference["diagnostics"]]
                actual = [(scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"])) for item in report["diagnostics"]["value"]]
                self.assertEqual(actual, expected, (name, expected, actual))

        source = "type Point { x: Int }" + NL + "fn main() -> Int { let p = Point { x: ?field }; return 0 }"
        reference = self._reference_check("record-hole", source)
        _, report = self._analyze(source)
        self.assertEqual(reference["status"], "incomplete", reference)
        self.assertEqual(scalar(report["status"]), "incomplete", report)
        hole = fields(report["holes"]["value"][0])
        self.assertEqual(scalar(hole["name"]), "field")
        self.assertEqual(scalar(hole["expectedType"]), "Int")

    def test_for_in_item_types_scope_and_list_requirement_match_ocaml(self):
        cases = [
            ("literal", "fn main() -> Int { for item in [1, 2] { let copy: Int = item } return 0 }", "valid", None, ""),
            ("typed-list", "fn main() -> Int { let values: List[Int] = [1]; for item in values { let copy: Int = item } return 0 }", "valid", None, ""),
            ("record-list", "type Point { x: Int }" + NL + "fn main(points: List[Point]) -> Int { for point in points { let copy: Int = point.x } return 0 }", "valid", None, ""),
            ("nested-list", "fn main() -> Int { let values: List[List[Int]] = [[1]]; for item in values { let copy: List[Int] = item } return 0 }", "valid", None, ""),
            ("scalar-iterable", "fn main() -> Int { for item in 1 {} return 0 }", "invalid", "PEP_FOR_REQUIRES_LIST", "1"),
            ("empty-iterable", "fn main() -> Int { for item in [] {} return 0 }", "invalid", "PEP_EMPTY_LIST_NEEDS_TYPE", "[]"),
            ("unknown-iterable", "fn main() -> Int { for item in missing {} return 0 }", "invalid", "PEP_UNKNOWN_VARIABLE", "missing"),
            ("immutable-item", "fn main() -> Int { for item in [1] { item = 2 } return 0 }", "invalid", "PEP_ASSIGN_IMMUTABLE", "item = 2"),
        ]
        for name, source, expected_status, expected_code, span_text in cases:
            with self.subTest(name=name):
                reference = self._reference_check("for-in-" + name, source)
                opened, report = self._analyze(source)
                self.assertEqual(reference["status"], expected_status, reference)
                self.assertEqual(scalar(report["status"]), expected_status, report)
                expected_diagnostics = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual_diagnostics = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual_diagnostics, expected_diagnostics, report)
                if expected_code is None:
                    self.assertEqual(actual_diagnostics, [])
                else:
                    self.assertEqual(len(actual_diagnostics), 1)
                    self.assertEqual(actual_diagnostics[0][0], expected_code)
                    start = len(source[:source.index(span_text)].encode("utf-8"))
                    end = start + len(span_text.encode("utf-8"))
                    self.assertEqual(actual_diagnostics[0][1:], (start, end))
                if name in {"literal", "typed-list", "record-list", "nested-list"}:
                    expected_type = "Point" if name == "record-list" else ("List[Int]" if name == "nested-list" else "Int")
                    loop_name = "point" if name == "record-list" else "item"
                    loop = next(fields(item) for item in report["bindings"]["value"] if scalar(fields(item)["name"]) == loop_name)
                    function = fields(report["functions"]["value"][0])
                    self.assertEqual(scalar(loop["typeName"]), expected_type, report)
                    self.assertIs(loop["mutable"]["value"], False)
                    self.assertNotEqual(scalar(loop["scopeId"]), scalar(function["semanticId"]))
                    body_start = source.index("{", source.index("for "))
                    reference_start = len(source[:source.index(loop_name, body_start)].encode("utf-8"))
                    body_reference = next(fields(item) for item in report["references"]["value"] if scalar(fields(item)["startByte"]) == reference_start)
                    self.assertEqual(scalar(body_reference["bindingId"]), scalar(loop["semanticId"]))
                    if name == "record-list":
                        field_start = len(source[:source.index("point.x")].encode("utf-8"))
                        field_type = next(fields(item) for item in report["expressionTypes"]["value"] if scalar(fields(item)["startByte"]) == field_start)
                        self.assertEqual(scalar(field_type["typeName"]), "Int")

    def test_for_in_iterable_and_body_scopes_match_ocaml(self):
        cases = [
            (
                "loop-binding-not-visible-in-iterable",
                "fn main() -> Int { for item in item {} return 0 }",
                "PEP_UNKNOWN_VARIABLE",
                "item",
                lambda source: source.index("in item") + len("in "),
            ),
            (
                "loop-binding-does-not-escape",
                "fn main() -> Int { for item in [1] {} return item }",
                "PEP_UNKNOWN_VARIABLE",
                "item",
                lambda source: source.rindex("item"),
            ),
        ]
        for name, source, expected_code, span_text, offset_of in cases:
            with self.subTest(name=name):
                reference = self._reference_check("for-in-scope-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), reference["status"], report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, report)
                self.assertEqual(len(actual), 1)
                self.assertEqual(actual[0][0], expected_code)
                start = len(source[:offset_of(source)].encode("utf-8"))
                end = start + len(span_text.encode("utf-8"))
                self.assertEqual(actual[0][1:], (start, end))

        source = (
            "fn main() -> Int { let item: List[Int] = [1]; "
            "for item in item { let value: Int = item } return 0 }"
        )
        reference = self._reference_check("for-in-shadowed-name-scopes", source)
        _, report = self._analyze(source)
        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), reference["status"], report)
        self.assertEqual(report["diagnostics"]["value"], [])

        item_bindings = [
            fields(item) for item in report["bindings"]["value"]
            if scalar(fields(item)["name"]) == "item"
        ]
        self.assertEqual(len(item_bindings), 2, report)
        function_id = scalar(fields(report["functions"]["value"][0])["semanticId"])
        outer_binding = next(
            item for item in item_bindings if scalar(item["scopeId"]) == function_id
        )
        loop_binding = next(
            item for item in item_bindings if scalar(item["scopeId"]) != function_id
        )

        iterable_start_index = source.index("in item") + len("in ")
        body_start_index = source.index("item", source.index("let value: Int ="))
        reference_by_start = {
            scalar(fields(item)["startByte"]): fields(item)
            for item in report["references"]["value"]
            if scalar(fields(item)["name"]) == "item"
        }
        iterable_reference = reference_by_start[len(source[:iterable_start_index].encode("utf-8"))]
        body_reference = reference_by_start[len(source[:body_start_index].encode("utf-8"))]
        self.assertEqual(
            scalar(iterable_reference["bindingId"]), scalar(outer_binding["semanticId"]), report
        )
        self.assertEqual(
            scalar(body_reference["bindingId"]), scalar(loop_binding["semanticId"]), report
        )

    def test_assignment_typing_mutability_and_spans_match_ocaml(self):
        cases = [
            ("mutable-valid", "fn main() -> Int { var x: Int = 0; x = 1; return x }", "valid", None, "", {}),
            ("scalar-mismatch", "fn main() -> Int { var x: Int = 0; x = true; return x }", "invalid", "PEP_TYPE_MISMATCH", "true", {}),
            ("immutable-local", "fn main() -> Int { let x: Int = 0; x = 1; return x }", "invalid", "PEP_ASSIGN_IMMUTABLE", "x = 1", {}),
            ("immutable-precedence", "fn main() -> Int { let x: Int = 0; x = true; return x }", "invalid", "PEP_ASSIGN_IMMUTABLE", "x = true", {}),
            ("immutable-parameter", "fn set(x: Int) -> Int { x = 1; return x }", "invalid", "PEP_ASSIGN_IMMUTABLE", "x = 1", {}),
            ("unknown-target", "fn main() -> Int { missing = 1; return 0 }", "invalid", "PEP_UNKNOWN_VARIABLE", "missing = 1", {}),
            ("inferred-type-mismatch", "fn main() -> Int { var x = 0; x = true; return x }", "invalid", "PEP_TYPE_MISMATCH", "true", {}),
            ("nested-list-mismatch", "fn main() -> Int { var xs: List[List[Int]] = [[1]]; xs = [[true]]; return 0 }", "invalid", "PEP_TYPE_MISMATCH", "true", {}),
            ("contextual-empty-list", "fn main() -> Int { var xs: List[Int] = [1]; xs = []; return length(xs) }", "valid", None, "", {}),
            ("assignment-hole", "fn main() -> Int { var x: Int = 0; x = ?pending; return x }", "incomplete", None, "", {"pending": "Int"}),
        ]
        for name, source, expected_status, expected_code, span_text, expected_holes in cases:
            with self.subTest(name=name):
                reference = self._reference_check("assignment-" + name, source)
                opened, report = self._analyze(source)
                self.assertEqual(reference["status"], expected_status, reference)
                self.assertEqual(scalar(report["status"]), expected_status, report)
                reference_diagnostics = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual_diagnostics = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual_diagnostics, reference_diagnostics, report)
                if expected_code is None:
                    self.assertEqual(actual_diagnostics, [])
                else:
                    self.assertEqual(len(actual_diagnostics), 1)
                    self.assertEqual(actual_diagnostics[0][0], expected_code)
                    start = len(source[:source.index(span_text)].encode("utf-8"))
                    end = start + len(span_text.encode("utf-8"))
                    self.assertEqual(actual_diagnostics[0][1:], (start, end))
                reference_holes = {item["name"]: item["expectedType"] for item in opened.get("holes", [])}
                actual_holes = {
                    scalar(fields(item)["name"]): scalar(fields(item)["expectedType"])
                    for item in report["holes"]["value"]
                }
                self.assertEqual(reference_holes, expected_holes)
                self.assertEqual(actual_holes, expected_holes, report)
                if name == "mutable-valid":
                    binding = next(fields(item) for item in report["bindings"]["value"] if scalar(fields(item)["name"]) == "x")
                    target_start = len(source[:source.index("x = 1")].encode("utf-8"))
                    write = next(fields(item) for item in report["references"]["value"] if scalar(fields(item)["startByte"]) == target_start)
                    self.assertEqual(scalar(write["bindingId"]), scalar(binding["semanticId"]))

    def test_named_record_construction_fields_and_holes_are_checked(self):
        source = "type Point { x: Int, label: Str }" + NL + "fn main() -> Int { let point = Point { x: 3, label: \"home\" }; return point.x }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "valid", report)
        facts = [fields(item) for item in report["expressionTypes"]["value"]]
        field_fact = next(item for item in facts if scalar(item["startByte"]) == source.index("point.x"))
        self.assertEqual(scalar(field_fact["typeName"]), "Int")
        bindings = [fields(item) for item in report["bindings"]["value"]]
        binding_types = [scalar(item["typeName"]) for item in bindings]
        self.assertIn("Point", binding_types)
        point_binding = next(item for item in bindings if scalar(item["typeName"]) == "Point")
        point_shape = fields(point_binding["typeShape"])
        self.assertEqual(scalar(point_shape["kind"]), "nominal")
        self.assertEqual(scalar(point_shape["name"]), "Point")
        self.assertEqual(scalar(point_shape["listDepth"]), 0)

        source = "type Point { x: Int }" + NL + "fn read(point: Point) -> Int { return point.x }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "valid", report)
        field = next(fields(item) for item in report["expressionTypes"]["value"] if scalar(fields(item)["typeName"]) == "Int" and scalar(fields(item)["startByte"]) == source.index("point.x"))
        self.assertEqual(scalar(field["typeName"]), "Int")

        source = "type Point { x: Int }" + NL + "fn main() -> Int { let point = Point { x: ?coordinate }; return 0 }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "incomplete", report)
        hole = fields(report["holes"]["value"][0])
        self.assertEqual(scalar(hole["expectedType"]), "Int")

        invalid_cases = [
            ("fn main() -> Int { let point = Point { x: true }; return 0 }", "PEP_TYPE_MISMATCH"),
            ("fn main() -> Int { let point = Point { }; return 0 }", "PEP_MISSING_FIELD"),
            ("fn main() -> Int { let point = Point { x: 1, other: 2 }; return 0 }", "PEP_UNKNOWN_FIELD"),
            ("fn main() -> Int { let point = Point { x: 1, x: 2 }; return 0 }", "PEP_DUPLICATE_FIELD"),
            ("fn main(point: Point) -> Int { return point.missing }", "PEP_UNKNOWN_FIELD"),
        ]
        for body, expected_code in invalid_cases:
            _, report = self._analyze("type Point { x: Int }" + NL + body)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertEqual(scalar(report["status"]), "invalid", report)
            self.assertIn(expected_code, codes)

    def test_record_literal_diagnostics_match_ocaml_first_error_priority(self):
        cases = [
            ("multiple-missing", "type P { a: Int, b: Bool, c: Str }" + NL +
             "fn f() -> Int { let p = P { }; return 0 }", "a: Int"),
            ("missing-precedes-wrong-type", "type P { a: Int, b: Bool }" + NL +
             "fn f() -> Int { let p = P { b: 1 }; return 0 }", "a: Int"),
            ("missing-precedes-unknown", "type P { a: Int, b: Bool }" + NL +
             "fn f() -> Int { let p = P { extra: 2 }; return 0 }", "a: Int"),
            ("duplicate-precedes-missing", "type P { a: Int, b: Bool }" + NL +
             "fn f() -> Int { let p = P { a: 1, a: 2 }; return 0 }", "a: 2"),
            ("first-supplied-type-error", "type P { a: Int, b: Bool }" + NL +
             "fn f() -> Int { let p = P { b: 1, a: true }; return 0 }", "1"),
            ("unknown-only", "type P { a: Int }" + NL +
             "fn f() -> Int { let p = P { a: 1, extra: 2 }; return 0 }", "extra: 2"),
            ("unknown-precedes-earlier-type", "type P { x: Int }" + NL +
             "fn f() -> Int { let p = P { x: true, y: 1 }; return 0 }", "y: 1"),
        ]
        expected_codes = [
            "PEP_MISSING_FIELD", "PEP_MISSING_FIELD", "PEP_MISSING_FIELD",
            "PEP_DUPLICATE_FIELD", "PEP_TYPE_MISMATCH", "PEP_UNKNOWN_FIELD",
            "PEP_UNKNOWN_FIELD",
        ]
        for (name, source, marker), expected_code in zip(cases, expected_codes):
            with self.subTest(name=name):
                reference = self._reference_check("record-literal-priority-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(expected, [(expected_code, source.index(marker), source.index(marker) + len(marker))])
                self.assertEqual(actual, expected, report)

    def test_field_access_diagnostics_match_ocaml(self):
        cases = [
            ("primitive-receiver", "fn f(x: Int) -> Int { return x.y }", "PEP_FIELD_ON_NON_RECORD", "x.y"),
            ("unknown-record-field", "type Point { x: Int }" + NL + "fn f(point: Point) -> Int { return point.missing }", "PEP_UNKNOWN_FIELD", "point.missing"),
            ("untyped-hole-receiver", "fn f() -> Int { return ?.x }", "PEP_FIELD_ON_UNTYPED_VALUE", "?.x"),
            ("untyped-if-receiver", "fn f(flag: Bool) -> Int { return (if flag { ?a } else { ?b }).x }", "PEP_FIELD_ON_UNTYPED_VALUE", "(if flag { ?a } else { ?b }).x"),
            ("nested-untyped-if-receiver", "fn f(flag: Bool) -> Int { return (if flag { ?a } else { if flag { ?b } else { ?c } }).x }", "PEP_FIELD_ON_UNTYPED_VALUE", "(if flag { ?a } else { if flag { ?b } else { ?c } }).x"),
            ("if-hole-unknown", "fn f(flag: Bool) -> Int { return (if flag { ?a } else { missing }).x }", "PEP_UNKNOWN_VARIABLE", "missing"),
            ("if-hole-scalar", "fn f(flag: Bool) -> Int { return (if flag { ?a } else { 1 }).x }", "PEP_FIELD_ON_NON_RECORD", "(if flag { ?a } else { 1 }).x"),
            ("if-branch-record-mismatch", "type Point { x: Int }" + NL + "fn f(flag: Bool) -> Int { return (if flag { 1 } else { Point { x: 1 } }).x }", "PEP_TYPE_MISMATCH", "Point { x: 1 }"),
            ("if-branch-scalar-mismatch", "type Point { x: Int }" + NL + "fn f(flag: Bool) -> Int { return (if flag { Point { x: 5 } } else { 2 }).x }", "PEP_TYPE_MISMATCH", "2"),
            ("nested-if-branch-mismatch", "type Point { x: Int }" + NL + "fn f(flag: Bool) -> Int { return (if flag { 1 } else { if flag { Point { x: 1 } } else { 2 } }).x }", "PEP_TYPE_MISMATCH", "Point { x: 1 }"),
            ("nested-if-bad-condition", "fn f(flag: Bool) -> Int { return (if flag { ?a } else { if 1 { ?b } else { ?c } }).x }", "PEP_TYPE_MISMATCH", "1"),
            ("unknown-variable-receiver", "fn f() -> Int { return missing.x }", "PEP_UNKNOWN_VARIABLE", "missing"),
        ]
        for name, source, expected_code, marker in cases:
            with self.subTest(name=name):
                reference = self._reference_check("field-access-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                marker_start = len(source[:source.index(marker)].encode("utf-8"))
                marker_end = marker_start + len(marker.encode("utf-8"))
                self.assertEqual(expected, [(expected_code, marker_start, marker_end)])
                self.assertEqual(actual, expected, report)

    def test_record_field_duplicates_report_only_the_first_repetition(self):
        cases = [
            ("record-literal", "type Point { x: Int }" + NL +
             "fn main() -> Int { let p = Point { x: 1, x: 2, x: 3 }; return p.x }",
             "x: 2"),
            ("record-declaration", "type Point { x: Int, x: Bool, x: Str }" + NL +
             "fn main() -> Int { return 0 }",
             "x: Bool"),
        ]
        for name, source, repeated_field in cases:
            with self.subTest(name=name):
                reference = self._reference_check("duplicate-field-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                expected_diagnostics = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual_diagnostics = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual_diagnostics, expected_diagnostics, report)
                self.assertEqual(len(actual_diagnostics), 1)
                expected_start = len(source[:source.index(repeated_field)].encode("utf-8"))
                expected_end = expected_start + len(repeated_field.encode("utf-8"))
                self.assertEqual(actual_diagnostics, [("PEP_DUPLICATE_FIELD", expected_start, expected_end)])

    def test_declaration_duplicates_report_only_the_first_repetition(self):
        cases = [
            ("record-type", "type Point { x: Int }" + NL +
             "type Point { y: Int }" + NL +
             "type Point { z: Int }" + NL +
             "fn main() -> Int { return 0 }",
             "type Point { y: Int }", "PEP_DUPLICATE_TYPE"),
            ("record-union-type", "type Point { x: Int }" + NL +
             "type Point = A() | B()" + NL +
             "type Point { y: Int }" + NL +
             "fn main() -> Int { return 0 }",
             "type Point = A() | B()", "PEP_DUPLICATE_TYPE"),
            ("constructor", "type First = Same()" + NL +
             "type Second = Same()" + NL +
             "type Third = Same()" + NL +
             "fn main() -> Int { return 0 }",
             "Same()", "PEP_DUPLICATE_CONSTRUCTOR"),
            ("function", "fn same() -> Int { return 1 }" + NL +
             "fn same() -> Int { return 2 }" + NL +
             "fn same() -> Int { return 3 }",
             "fn same() -> Int { return 2 }", "PEP_DUPLICATE_FUNCTION"),
        ]
        for name, source, repeated_declaration, expected_code in cases:
            with self.subTest(name=name):
                reference = self._reference_check("duplicate-declaration-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                expected_diagnostics = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual_diagnostics = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual_diagnostics, expected_diagnostics, report)
                self.assertEqual(len(actual_diagnostics), 1)
                start_index = source.index(repeated_declaration)
                if name == "constructor":
                    start_index = source.index(repeated_declaration, start_index + len(repeated_declaration))
                expected_start = len(source[:start_index].encode("utf-8"))
                expected_end = expected_start + len(repeated_declaration.encode("utf-8"))
                self.assertEqual(actual_diagnostics, [(expected_code, expected_start, expected_end)])

    def test_reserved_function_duplicates_report_once_at_the_first_function(self):
        declaration = "fn Some(x: Int) -> Int { return x }"
        cases = [
            ("constructor", "type Maybe = Some(Int) | None()" + NL +
             declaration + NL + declaration + NL +
             "fn main() -> Int { return 0 }", declaration),
            ("builtin", "fn length() -> Int { return 0 }" + NL +
             "fn length() -> Int { return 1 }" + NL +
             "fn main() -> Int { return 0 }", "fn length() -> Int { return 0 }"),
        ]
        for name, source, first_declaration in cases:
            with self.subTest(name=name):
                reference = self._reference_check("reserved-function-duplicate-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, report)
                start = len(source[:source.index(first_declaration)].encode("utf-8"))
                self.assertEqual(actual, [("PEP_RESERVED_FUNCTION", start, start + len(first_declaration.encode("utf-8")))])

    def test_reserved_type_name_duplicates_report_once_at_the_first_declaration(self):
        cases = [
            ("single", "type Int { value: Bool }" + NL +
             "fn main() -> Int { return 0 }"),
            ("three-records", "type Int { a: Bool }" + NL +
             "type Int { b: Bool }" + NL +
             "type Int { c: Bool }" + NL +
             "fn main() -> Int { return 0 }"),
            ("record-union", "type Int { value: Bool }" + NL +
             "type Int = A() | B()" + NL +
             "fn main() -> Int { return 0 }"),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check("reserved-type-duplicate-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, report)
                first_declaration = source.split(NL)[0]
                expected_start = len(source[:source.index(first_declaration)].encode("utf-8"))
                expected_end = expected_start + len(first_declaration.encode("utf-8"))
                self.assertEqual(actual, [("PEP_DUPLICATE_TYPE", expected_start, expected_end)])

    def test_nested_list_constructor_payload_mismatches_match_ocaml(self):
        cases = [
            ("list-leaf", "type Boxed = Box(List[Int])\nfn f() -> Boxed { return Box([true]) }", "invalid"),
            ("nested-first-leaf", "type Boxed = Box(List[List[Int]])\nfn f() -> Boxed { return Box([[true], [1]]) }", "invalid"),
            ("nested-later-leaf", "type Boxed = Box(List[List[Int]])\nfn f() -> Boxed { return Box([[1], [true]]) }", "invalid"),
            ("nested-valid", "type Boxed = Box(List[List[Int]])\nfn f() -> Boxed { return Box([[1], [2]]) }", "valid"),
            ("nominal-list-leaf", "type P { x: Int }\ntype Q { x: Int }\ntype Container = Wrap(List[P])\nfn f() -> Container { return Wrap([Q { x: 1 }]) }", "invalid"),
            ("nominal-list-variable-mismatch", "type P { x: Int }\ntype Q { x: Int }\ntype Container = Wrap(List[P])\nfn f(values: List[Q]) -> Container { return Wrap(values) }", "invalid"),
            ("nominal-list-variable-valid", "type P { x: Int }\ntype Container = Wrap(List[P])\nfn f(values: List[P]) -> Container { return Wrap(values) }", "valid"),
        ]
        for name, source, expected_status in cases:
            with self.subTest(name=name):
                reference = self._reference_check("constructor-payload-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], expected_status, reference)
                self.assertEqual(scalar(report["status"]), expected_status, report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, report)

    def test_first_type_mismatch_matches_ocaml_across_binding_and_match_contexts(self):
        cases = [
            (
                "binding-before-match",
                "type M = A() | B()" + NL
                + "fn f(m: M) -> Int { let bad: Int = true; return match m { A() => true B() => 0 } }",
            ),
            (
                "match-before-binding",
                "type M = A() | B()" + NL
                + "fn f(m: M) -> Int { let matched: Int = match m { A() => true B() => 0 }; let bad: Int = true; return 0 }",
            ),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check("first-type-mismatch-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(len(expected), 1, reference)
                self.assertEqual(actual, expected, (name, expected, actual, report))

    def test_first_diagnostic_matches_ocaml_across_checker_categories(self):
        cases = [
            ("unknown-before-type", "fn f() -> Int { let x: Int = missing; return true }"),
            ("type-before-unknown", "fn f() -> Int { let x: Int = true; return missing }"),
            ("call-before-type", "fn g(x: Int) -> Int { return x } fn f() -> Int { let x: Int = g(); return true }"),
            ("type-before-call", "fn g(x: Int) -> Int { return x } fn f() -> Int { let x: Int = true; return g() }"),
            ("unknown-call-before-type", "fn f() -> Int { let x: Int = missing(); return true }"),
            ("unknown-constructor-call", "type M=A(Int)|B() fn f()->M{return C(1)}"),
            ("unknown-constructor-call-multiple-functions", "type M=A(Int)|B() fn helper()->Int{return 0} fn f()->M{return C(1)}"),
            ("multiple-unknown-constructor-calls", "fn f()->Bool{return C()==D()}"),
            ("multiple-list-expected-errors", "fn f()->Int{let a=length(1);let b=length(true);return 0}"),
            ("multiple-empty-list-needs-type-errors", "fn f()->Int{let a=length([]);let b=length([]);return 0}"),
            ("multiple-nonexhaustive-match-errors", "type M=A()|B() fn f(x:M)->Int{let a=match x{A()=>1};let b=match x{B()=>2};return 0}"),
            ("unknown-constructor-before-type", "type M=A(Int)|B() fn f()->Int{let x:Int=true; return C(1)}"),
            ("constructor-nested-list-payload", "type M=A(List[Int])|B() fn f()->M{return A([1,true])}"),
            ("mixed-unlisted-missing-field", "type P { x: Int } fn f() -> Int { let p = P { other: 2 }; let bad: Int = true; return missing }"),
            ("missing-field-before-unknown-name", "type P { x: Int } fn f() -> Int { let p = P { other: 2 }; return missing }"),
            ("unknown-name-before-missing-field", "type P { x: Int } fn f() -> Int { let x = missing; let p = P { other: 2 }; return 0 }"),
            ("missing-field-before-unknown-call", "type P { x: Int } fn f() -> Int { let p = P { other: 2 }; return missing() }"),
            ("unknown-top-level-constructor-before-type", "type M=A()|B() fn f(x:M)->Int{return match x{C()=>0 A()=>true _=>1}}"),
            ("known-wrong-union-pattern-no-false-arity", "type M=A()|B() type N=C(Int) fn f(x:M)->Int{return match x{C(1)=>0 A()=>1 _=>2}}"),
            ("unknown-type-declaration-priority", "fn f() -> Int { let bad: Int = true; return 0 } type R { x: Missing }"),
            ("unknown-type-before-missing-field", "type P{x:Int} fn f()->Int{let p=P{other:1};return 0} type R{x:Missing}"),
            ("unknown-type-before-unknown-field", "type P{x:Int} fn f()->Int{let p=P{bogus:1,x:2};return 0} type R{x:Missing}"),
            ("unknown-type-before-duplicate-field", "type P{x:Int} fn f()->Int{let p=P{x:1,x:2};return 0} type R{x:Missing}"),
            ("unknown-type-before-duplicate-function", "fn f() -> Int { return 0 } fn f() -> Int { return 0 } type R { x: Missing } fn g() -> Int { let bad: Int = true; return 0 }"),
            ("duplicate-type-before-unknown-type", "type P{x:Int} type P{y:Bool} type R{x:Missing}"),
            ("duplicate-type-after-unknown-type", "type R{x:Missing} type P{x:Int} type P{y:Bool}"),
            ("reserved-type-before-unknown-type", "type Int{x:Int} type R{x:Missing}"),
            ("duplicate-declared-field-before-unknown-type", "type P{x:Int,x:Bool} type R{x:Missing}"),
            ("duplicate-constructor-before-unknown-type", "type M=A()|B() type N=A()|C() type R{x:Missing}"),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check("first-diagnostic-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(len(expected), 1, reference)
                self.assertEqual(actual, expected, (name, expected, actual, report))

    def test_match_list_mismatch_reports_first_leaf_like_ocaml(self):
        cases = [
            ("leaf-mismatch", "type M=A()|B()\nfn f(x:M)->List[Int]{return match x{A()=>[0] B()=>[true]}}", "invalid"),
            ("heterogeneous-leaf", "type M=A()|B()\nfn f(x:M)->List[Int]{return match x{A()=>[0] B()=>[1,true]}}", "invalid"),
            ("valid-control", "type M=A()|B()\nfn f(x:M)->List[Int]{return match x{A()=>[0] B()=>[1]}}", "valid"),
        ]
        for name, source, expected_status in cases:
            with self.subTest(name=name):
                reference = self._reference_check("match-list-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], expected_status, reference)
                self.assertEqual(scalar(report["status"]), expected_status, report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, report)

    def test_union_constructors_and_duplicate_names_match_reference_errors(self):
        source = "type Maybe = Some(Int) | None()" + NL + "fn make() -> Maybe { return Some(4) }"
        reference = self._reference_check("constructor-valid", source)
        _, report = self._analyze(source)
        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        constructor = next(fields(item) for item in report["expressionTypes"]["value"] if scalar(fields(item)["startByte"]) == source.index("Some(4)"))
        self.assertEqual(scalar(constructor["typeName"]), "Maybe")

        source = "type Maybe = Some(Int) | None()" + NL + "fn main() -> Maybe { return Some(?payload) }"
        _, report = self._analyze(source)
        hole = fields(report["holes"]["value"][0])
        self.assertEqual(scalar(report["status"]), "incomplete", report)
        self.assertEqual(scalar(hole["expectedType"]), "Int")

        invalid_cases = [
            ("type Point { x: Int }" + NL + "type Point { y: Bool }" + NL + "fn main() -> Int { let p = Point { x: 1 }; return p.x }", "PEP_DUPLICATE_TYPE"),
            ("type Point { x: Int, x: Bool }" + NL + "fn main() -> Int { let p = Point { x: 1 }; return p.x }", "PEP_DUPLICATE_FIELD"),
            ("type Point { x: Int }" + NL + "type Point = A() | B()" + NL + "fn main() -> Int { return 0 }", "PEP_DUPLICATE_TYPE"),
            ("type First = Shared()" + NL + "type Second = Shared()" + NL + "fn main() -> Int { return 0 }", "PEP_DUPLICATE_CONSTRUCTOR"),
            ("type Int = A() | B()" + NL + "fn f(x: Int) -> Int { return 1 }", "PEP_DUPLICATE_TYPE"),
            ("type M = Value(Int) | Empty()" + NL + "fn Value(x: Int) -> Int { return x }" + NL + "fn f() -> Int { return Value(1) }", "PEP_RESERVED_FUNCTION"),
            ("type Maybe = Some(Int) | None()" + NL + "fn main() -> Maybe { return Some() }", "PEP_ARGUMENT_COUNT"),
            ("type Maybe = Some(Int) | None()" + NL + "fn main() -> Maybe { return Some(true) }", "PEP_TYPE_MISMATCH"),
        ]
        for source, expected_code in invalid_cases:
            reference = self._reference_check("nominal-invalid", source)
            _, report = self._analyze(source)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertEqual(reference["status"], "invalid", reference)
            self.assertEqual(scalar(report["status"]), "invalid", report)
            self.assertIn(expected_code, codes)

        for source in [
            "type Point { x: Int }" + NL + "fn same(a: Point, b: Point) -> Bool { return a == b }",
            "fn same(a: List[Int], b: List[Int]) -> Bool { return a == b }",
        ]:
            reference = self._reference_check("aggregate-equality", source)
            _, report = self._analyze(source)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertEqual(reference["status"], "invalid", reference)
            self.assertEqual(scalar(report["status"]), "invalid", report)
            self.assertIn("PEP_EQUALITY_UNSUPPORTED", codes)

    def test_deep_list_equality_is_rejected_like_ocaml(self):
        source = "fn same(a: List[List[List[Int]]], b: List[List[List[Bool]]]) -> Bool { return a == b }"
        reference = self._reference_check("deep-list-equality", source)
        _, report = self._analyze(source)
        expected = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in reference["diagnostics"]
        ]
        actual = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in report["diagnostics"]["value"]
        ]
        self.assertEqual(reference["status"], "invalid", reference)
        self.assertEqual(scalar(report["status"]), reference["status"], report)
        self.assertEqual(actual, expected, (reference, report))
        self.assertEqual([item[0] for item in actual], ["PEP_EQUALITY_UNSUPPORTED"])

    def test_deep_list_literal_equality_is_rejected_like_ocaml(self):
        source = "fn same() -> Bool { return [[[1]]] == [[[2]]] }"
        reference = self._reference_check("deep-list-literal-equality", source)
        _, report = self._analyze(source)
        expected = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in reference["diagnostics"]
        ]
        actual = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in report["diagnostics"]["value"]
        ]
        self.assertEqual(reference["status"], "invalid", reference)
        self.assertEqual(scalar(report["status"]), reference["status"], report)
        self.assertEqual(actual, expected, (reference, report))
        self.assertEqual([item[0] for item in actual], ["PEP_EQUALITY_UNSUPPORTED"])

    def test_deep_list_builtin_call_equality_is_rejected_like_ocaml(self):
        source = "fn same() -> Bool { return reverse([[[1]]]) == [[[2]]] }"
        reference = self._reference_check("deep-list-builtin-call-equality", source)
        _, report = self._analyze(source)
        expected = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in reference["diagnostics"]
        ]
        actual = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in report["diagnostics"]["value"]
        ]
        self.assertEqual(reference["status"], "invalid", reference)
        self.assertEqual(scalar(report["status"]), reference["status"], report)
        self.assertEqual(actual, expected, (reference, report))
        self.assertEqual([item[0] for item in actual], ["PEP_EQUALITY_UNSUPPORTED"])

    def test_match_deep_list_result_equality_is_rejected_like_ocaml(self):
        source = "type Flag = On()\nfn same(flag: Flag, values: List[List[List[Int]]]) -> Bool { return match flag { On() => values } == values }"
        reference = self._reference_check("match-result-deep-list-equality", source)
        _, report = self._analyze(source)
        expected = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in reference["diagnostics"]
        ]
        actual = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in report["diagnostics"]["value"]
        ]
        self.assertEqual(reference["status"], "invalid", reference)
        self.assertEqual(scalar(report["status"]), reference["status"], report)
        self.assertEqual(actual, expected, (reference, report))
        self.assertEqual([item[0] for item in actual], ["PEP_EQUALITY_UNSUPPORTED"])

    def test_deep_list_match_and_function_call_equality_match_ocaml(self):
        cases = [
            (
                "match-not-equal",
                "type Flag = On()" + NL + "fn same(flag: Flag, values: List[List[List[Int]]]) -> Bool { return match flag { On() => values } != values }",
            ),
            (
                "deep-identity-call",
                "fn id(x: List[List[List[Int]]]) -> List[List[List[Int]]] { return x }" + NL + "fn same(x: List[List[List[Int]]]) -> Bool { return id(x) == x }",
            ),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check("deep-list-" + name, source)
                _, report = self._analyze(source)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), reference["status"], report)
                self.assertEqual(actual, expected, (reference, report))
                self.assertEqual([item[0] for item in actual], ["PEP_EQUALITY_UNSUPPORTED"])

    def test_match_bindings_are_arm_local_and_union_coverage_is_checked(self):
        source = (
            "type Maybe = None() | Some(Int)" + NL
            + "fn pick(value: Maybe) -> Int { return match value { None() => 0 Some(number) => number } }"
        )
        reference = self._reference_check("match-valid", source)
        _, report = self._analyze(source)
        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        binding = next(fields(item) for item in report["bindings"]["value"] if scalar(fields(item)["name"]) == "number")
        self.assertEqual(scalar(binding["typeName"]), "Int")
        references = [fields(item) for item in report["references"]["value"]]
        number_reference = next(item for item in references if scalar(item["name"]) == "number")
        self.assertEqual(scalar(number_reference["bindingId"]), scalar(binding["semanticId"]))

        wildcard = "type Maybe = None() | Some(Int)" + NL + "fn pick(value: Maybe) -> Int { return match value { Some(number) => number _ => 0 } }"
        _, report = self._analyze(wildcard)
        self.assertEqual(scalar(report["status"]), "valid", report)

        invalid_cases = [
            ("type Maybe = None() | Some(Int)" + NL + "fn pick(value: Maybe) -> Int { return match value { Some(number) => number } }", "PEP_NON_EXHAUSTIVE_MATCH"),
            ("type Maybe = None() | Some(Int)" + NL + "fn pick(value: Maybe) -> Int { return match value { None() => 0 None() => 1 Some(number) => number } }", "PEP_DUPLICATE_MATCH_ARM"),
            ("type Maybe = None() | Some(Int)" + NL + "fn pick(value: Maybe) -> Int { return match value { None() => 0 Some() => 1 } }", "PEP_PATTERN_ARITY"),
            ("type Maybe = None() | Some(Int)" + NL + "type Other = Other()" + NL + "fn pick(value: Maybe) -> Int { return match value { Other() => 0 _ => 1 } }", "PEP_PATTERN_TYPE_MISMATCH"),
            ("type Maybe = None() | Some(Int)" + NL + "fn pick(value: Maybe) -> Int { return match value { None() => 0 Some(number) => true } }", "PEP_MATCH_ARM_TYPE_MISMATCH"),
        ]
        for source, expected_code in invalid_cases:
            reference = self._reference_check("match-invalid", source)
            _, report = self._analyze(source)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertEqual(reference["status"], "invalid", reference)
            self.assertEqual(scalar(report["status"]), "invalid", report)
            self.assertIn(expected_code, codes)

        out_of_scope = "type Maybe = None() | Some(Int)" + NL + "fn pick(value: Maybe) -> Int { match value { Some(number) => number _ => 0 }; return number }"
        reference = self._reference_check("match-out-of-scope", out_of_scope)
        _, report = self._analyze(out_of_scope)
        self.assertEqual(reference["status"], "invalid", reference)
        self.assertEqual(scalar(report["status"]), "invalid", report)
        expected = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in reference["diagnostics"]
        ]
        actual = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in report["diagnostics"]["value"]
        ]
        self.assertEqual(actual, expected, report)
        self.assertEqual(len(actual), 1)
        self.assertEqual(actual[0][0], "PEP_UNKNOWN_VARIABLE")

    def test_duplicate_pattern_binding_diagnostic_matches_ocaml(self):
        cases = [
            ("pattern", "type Pair = P(Int, Int) | N()" + NL + "fn f(x: Pair) -> Int { return match x { P(a, a) => a N() => 0 } }", "PEP_DUPLICATE_PATTERN_BINDING"),
            ("local-binding", "fn f() -> Int { let a = 1; let a = 2; return a }", "PEP_DUPLICATE_BINDING"),
        ]
        for name, source, expected_code in cases:
            with self.subTest(name=name):
                reference = self._reference_check("duplicate-binding-" + name, source)
                _, report = self._analyze(source)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                self.assertEqual(actual, expected, (name, expected, actual, report))
                self.assertEqual([item[0] for item in actual], [expected_code])

    def test_duplicate_binding_search_stops_at_function_boundary(self):
        source = NL.join([
            "fn first(value: Int) -> Int { let local = value; return local }",
            "fn second(value: Int) -> Int { let local = value; return local }",
            "fn main() -> Int { return 0 }",
        ])
        reference = self._reference_check("same-bindings-in-separate-functions", source)
        _, report = self._analyze(source)
        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
        self.assertNotIn("PEP_DUPLICATE_PARAMETER", codes)
        self.assertNotIn("PEP_DUPLICATE_BINDING", codes)

    def test_match_subject_diagnostics_match_ocaml(self):
        cases = [
            ("integer-literal", "fn f() -> Int { return match 1 { _ => 0 } }", "PEP_MATCH_NON_UNION"),
            ("string-literal", "fn f() -> Int { return match \"x\" { _ => 0 } }", "PEP_MATCH_NON_UNION"),
            ("list-literal", "fn f() -> Int { return match [1] { _ => 0 } }", "PEP_MATCH_NON_UNION"),
            ("binary-expression", "fn f() -> Int { return match (1 + 2) { _ => 0 } }", "PEP_MATCH_NON_UNION"),
            ("binary-error", "fn f() -> Int { return match (1 + true) { _ => 0 } }", "PEP_TYPE_MISMATCH"),
            ("unary-error", "fn f() -> Int { return match !1 { _ => 0 } }", "PEP_TYPE_MISMATCH"),
            ("call-argument-error", "fn g(x: Int) -> Int { return x }" + NL + "fn f() -> Int { return match g(true) { _ => 0 } }", "PEP_TYPE_MISMATCH"),
            ("call-list-argument-error", "fn g(xs: List[List[Int]]) -> Int { return 0 }" + NL + "fn f() -> Int { return match g([[true]]) { _ => 0 } }", "PEP_TYPE_MISMATCH"),
            ("equality-unsupported", "fn f() -> Int { return match ([1] == [2]) { _ => 0 } }", "PEP_EQUALITY_UNSUPPORTED"),
            ("if-expression", "fn f(flag: Bool) -> Int { return match (if flag { 1 } else { 2 }) { _ => 0 } }", "PEP_MATCH_NON_UNION"),
            ("if-branch-error", "fn f(flag: Bool) -> Int { return match (if flag { 1 } else { true }) { _ => 0 } }", "PEP_TYPE_MISMATCH"),
            ("if-condition-error", "fn f() -> Int { return match (if missing { 1 } else { 2 }) { _ => 0 } }", "PEP_UNKNOWN_VARIABLE"),
            ("if-unknown-arm", "fn f(flag: Bool) -> Int { return match (if flag { missing } else { 1 }) { _ => 0 } }", "PEP_UNKNOWN_VARIABLE"),
            ("binary-unknown-name", "fn f() -> Int { return match (missing + 1) { _ => 0 } }", "PEP_UNKNOWN_VARIABLE"),
            ("call-unknown-argument", "fn g(x: Int) -> Int { return x }" + NL + "fn f() -> Int { return match g(missing) { _ => 0 } }", "PEP_UNKNOWN_VARIABLE"),
            ("builtin-result", "fn f() -> Int { return match length([1]) { _ => 0 } }", "PEP_MATCH_NON_UNION"),
            ("builtin-list-expected-error", "fn f() -> Int { return match length(1) { _ => 0 } }", "PEP_LIST_EXPECTED"),
            ("builtin-arity-error", "fn f() -> Int { return match source_bytes(1) { _ => 0 } }", "PEP_ARGUMENT_COUNT"),
            ("builtin-type-error", "fn f() -> Int { return match byte_at(source_bytes(), true) { _ => 0 } }", "PEP_TYPE_MISMATCH"),
            ("builtin-empty-list", "fn f() -> Int { return match length([]) { _ => 0 } }", "PEP_EMPTY_LIST_NEEDS_TYPE"),
            ("builtin-element-type-error", "fn f() -> Int { return match append([1], \"text\") { _ => 0 } }", "PEP_TYPE_MISMATCH"),
            ("field-result", "type Point { x: Int }" + NL + "fn f(p: Point) -> Int { return match p.x { _ => 0 } }", "PEP_MATCH_NON_UNION"),
            ("typed-name", "fn f(value: Int) -> Int { return match value { _ => 0 } }", "PEP_MATCH_NON_UNION"),
            ("typed-call", "fn value() -> Int { return 1 }" + NL + "fn f() -> Int { return match value() { _ => 0 } }", "PEP_MATCH_NON_UNION"),
            ("unknown-name", "fn f() -> Int { return match missing { _ => 0 } }", "PEP_UNKNOWN_VARIABLE"),
            ("unknown-function", "fn f() -> Int { return match missing_fn() { _ => 0 } }", "PEP_UNKNOWN_FUNCTION"),
            ("unknown-constructor", "fn f() -> Int { return match Missing() { _ => 0 } }", "PEP_UNKNOWN_CONSTRUCTOR"),
            ("unknown-field", "type Point { x: Int }" + NL + "fn f(p: Point) -> Int { return match p.missing { _ => 0 } }", "PEP_UNKNOWN_FIELD"),
            ("untyped-field-receiver", "fn f() -> Int { return match ?.x { _ => 0 } }", "PEP_FIELD_ON_UNTYPED_VALUE"),
            ("non-record-field-receiver", "fn f() -> Int { return match 1.x { _ => 0 } }", "PEP_FIELD_ON_NON_RECORD"),
            ("wrong-call-arity", "fn value() -> Int { return 1 }" + NL + "fn f() -> Int { return match value(2) { _ => 0 } }", "PEP_ARGUMENT_COUNT"),
            ("hole", "fn f() -> Int { return match ?subject { _ => 0 } }", "PEP_MATCH_UNTYPED"),
        ]
        for name, source, expected_code in cases:
            with self.subTest(name=name):
                reference = self._reference_check("match-subject-" + name, source)
                _, report = self._analyze(source)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                self.assertEqual(actual, expected, (name, expected, actual, report))
                self.assertEqual([item[0] for item in actual], [expected_code])

    def test_builtin_match_subject_holes_preserve_reference_status(self):
        cases = [
            ("length-hole", "length(?items)"),
            ("reverse-hole", "reverse(?items)"),
            ("append-hole", "append(?items, 1)"),
            ("prepend-hole", "prepend(?items, 1)"),
            ("contains-hole", "contains(?items, 1)"),
        ]
        for name, call in cases:
            with self.subTest(name=name):
                source = "fn f() -> Int { return match " + call + " { _ => 0 } }"
                reference = self._reference_check("match-builtin-hole-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(scalar(report["status"]), reference["status"], (reference, report))
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, (reference, report))

    def test_empty_match_diagnostics_match_ocaml(self):
        cases = [
            ("union-subject", "type Maybe = A(Int) | B()" + NL + "fn f(x: Maybe) -> Int { return match x {} }"),
            ("scalar-subject", "fn f() -> Int { return match 1 {} }"),
            ("unknown-subject", "fn f() -> Int { return match missing {} }"),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check("empty-match-" + name, source)
                _, report = self._analyze(source)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                self.assertEqual(actual, expected, (name, expected, actual, report))
                self.assertEqual([item[0] for item in actual], ["PEP_EMPTY_MATCH"])

    def test_nested_single_variant_constructor_patterns_match_ocaml(self):
        cases = [
            ("singleton-valid", "type Inner = I(Int)" + NL + "type Outer = O(Inner) | N()" + NL + "fn f(x: Outer) -> Int { return match x { O(I(value)) => value N() => 0 } }", "valid"),
            ("multivariant-fallback", "type Inner = I(Int) | J()" + NL + "type Outer = O(Inner)" + NL + "fn f(x: Outer) -> Int { return match x { O(I(value)) => value O(_) => 0 } }", "valid"),
            ("multivariant-incomplete", "type Inner = I(Int) | J()" + NL + "type Outer = O(Inner)" + NL + "fn f(x: Outer) -> Int { return match x { O(I(value)) => value } }", "invalid"),
            ("wrong-nested-constructor", "type Inner = I(Int)" + NL + "type Other = Q()" + NL + "type Outer = O(Inner)" + NL + "fn f(x: Outer) -> Int { return match x { O(Q()) => 0 _ => 0 } }", "invalid"),
            ("wrong-nested-arity", "type Inner = I(Int)" + NL + "type Outer = O(Inner)" + NL + "fn f(x: Outer) -> Int { return match x { O(I()) => 0 _ => 0 } }", "invalid"),
        ]
        for name, source, expected_status in cases:
            with self.subTest(name=name):
                reference = self._reference_check("nested-pattern-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], expected_status, reference)
                self.assertEqual(scalar(report["status"]), expected_status, report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, report)
                if name == "singleton-valid":
                    binding = next(fields(item) for item in report["bindings"]["value"] if scalar(fields(item)["name"]) == "value")
                    self.assertEqual(scalar(binding["typeName"]), "Int")
                    reference_fact = next(fields(item) for item in report["references"]["value"] if scalar(fields(item)["name"]) == "value")
                    self.assertEqual(scalar(reference_fact["bindingId"]), scalar(binding["semanticId"]))

    def test_constructor_pattern_reachability_diagnostics_match_ocaml(self):
        cases = [
            ("nested-then-payload-wildcard", "type Inner = I(Int)" + NL + "type Outer = O(Inner)" + NL + "fn f(x: Outer) -> Int { return match x { O(I(value)) => value O(_) => 0 } }", "PEP_UNREACHABLE_MATCH_ARM"),
            ("payload-wildcard-then-nested", "type Inner = I(Int)" + NL + "type Outer = O(Inner)" + NL + "fn f(x: Outer) -> Int { return match x { O(_) => 0 O(I(value)) => value } }", "PEP_UNREACHABLE_MATCH_ARM"),
            ("duplicate-nested-pattern", "type Inner = I(Int)" + NL + "type Outer = O(Inner)" + NL + "fn f(x: Outer) -> Int { return match x { O(I(value)) => value O(I(other)) => other } }", "PEP_DUPLICATE_MATCH_ARM"),
            ("duplicate-partial-nested-pattern", "type Inner = I(Int) | J()" + NL + "type Outer = O(Inner)" + NL + "fn f(x: Outer) -> Int { return match x { O(I(_)) => 0 O(I(_)) => 1 } }", "PEP_DUPLICATE_MATCH_ARM"),
            ("covered-outer-then-partial-nested", "type Inner = I(Int) | J()" + NL + "type Outer = O(Inner)" + NL + "fn f(x: Outer) -> Int { return match x { O(_) => 0 O(I(_)) => 1 } }", "PEP_UNREACHABLE_MATCH_ARM"),
            ("duplicate-top-level-pattern", "type Maybe = None() | Some(Int)" + NL + "fn f(x: Maybe) -> Int { return match x { None() => 0 None() => 1 Some(value) => value } }", "PEP_DUPLICATE_MATCH_ARM"),
        ]
        for name, source, expected_code in cases:
            with self.subTest(name=name):
                reference = self._reference_check("pattern-reachability-" + name, source)
                _, report = self._analyze_staged(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertIn(expected_code, [item[0] for item in expected], reference)
                self.assertEqual(actual, expected, report)

    def test_deep_constructor_patterns_match_ocaml_or_report_one_shot_budget(self):
        source = "type Seed = K(Int)" + NL + "type Leaf = L(Seed)" + NL + "type Mid = M(Leaf)" + NL + "type Outer = O(Mid)" + NL + "fn f(x: Outer) -> Int { return match x { O(M(L(K(value)))) => value } }"
        reference = self._reference_check("nested-pattern-one-shot-depth-three", source)
        self.assertEqual(reference["status"], "valid", reference)
        opened = self._open(source)
        result = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_invoke", "tool": "pep-a13-checker", "arguments": [],
                                   "semanticTarget": {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}})
        if result.get("outcome") == "error":
            self.assertEqual(result["error"]["code"], "PEP_RUNTIME_STEP_LIMIT", result)
        else:
            report = fields(result["result"])
            self.assertEqual(scalar(report["status"]), "valid", report)
            self.assertEqual(report["diagnostics"]["value"], [])

    def test_scalar_union_match_bindings_holes_and_fail_closed_cases(self):
        source = "type M = A(Int) | B()" + NL + "fn f(x: M) -> Int { return match x { A(v) => v B() => 0 } }"
        reference = self._reference_check("match-valid", source)
        _, report = self._analyze(source)
        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(scalar(report["status"]), "valid", report)
        binding = next(fields(item) for item in report["bindings"]["value"] if scalar(fields(item)["name"]) == "v")
        self.assertEqual(scalar(binding["typeName"]), "Int")
        reference_fact = next(fields(item) for item in report["references"]["value"] if scalar(fields(item)["name"]) == "v")
        self.assertEqual(scalar(reference_fact["bindingId"]), scalar(binding["semanticId"]))

        source = "type M = A(Int) | B()" + NL + "fn f(x: M) -> Int { return match x { A(v) => ?answer B() => 0 } }"
        reference = self._reference_check("match-hole", source)
        _, report = self._analyze(source)
        self.assertEqual(reference["status"], "incomplete", reference)
        self.assertEqual(scalar(report["status"]), "incomplete", report)
        hole = fields(report["holes"]["value"][0])
        self.assertEqual(scalar(hole["expectedType"]), "Int")

        cases = [
            ("nonexhaustive", "type M = A(Int) | B()" + NL + "fn f(x: M) -> Int { return match x { A(v) => v } }", "PEP_NON_EXHAUSTIVE_MATCH"),
            ("wrong-union", "type M = A(Int) | B()" + NL + "type N = C(Int)" + NL + "fn f(x: M) -> Int { return match x { C(v) => v B() => 0 } }", "PEP_PATTERN_TYPE_MISMATCH"),
            ("duplicate", "type M = A() | B()" + NL + "fn f(x: M) -> Int { return match x { A() => 0 A() => 1 B() => 0 } }", "PEP_DUPLICATE_MATCH_ARM"),
            ("subject-hole", "type M = A(Int) | B()" + NL + "fn f() -> Int { return match ?subject { A(v) => v B() => 0 } }", "PEP_MATCH_UNTYPED"),
            ("scalar-subject", "fn f(x: Int) -> Int { return match x { A(v) => v } }", "PEP_MATCH_NON_UNION"),
        ]
        for name, source, expected_code in cases:
            with self.subTest(name=name):
                reference = self._reference_check("match-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                self.assertIn(expected_code, [item["code"] for item in reference["diagnostics"]])
                self.assertIn(expected_code, [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]])

    def test_contextual_match_expected_type_checks_each_arm(self):
        cases = [
            ("all-arms-mismatch", "type M = A() | B()" + NL + "fn f(x: M) -> Int { return match x { A() => true B() => false } }"),
            ("first-arm-mismatch", "type M = A() | B()" + NL + "fn f(x: M) -> Int { return match x { A() => true B() => 0 } }"),
            ("later-arm-mismatch", "type M = A() | B()" + NL + "fn f(x: M) -> Int { return match x { A() => 0 B() => true } }"),
            ("function-argument", "type M = A() | B()" + NL + "fn f(x: M) -> Int { return f(match x { A() => true B() => false }) }"),
            ("annotated-binding", "type M = A() | B()" + NL + "fn f(x: M) -> Int { let n: Int = match x { A() => true B() => false }; return n }"),
            ("conditional-branch", "type M = A() | B()" + NL + "fn f(x: M) -> Int { return if true { match x { A() => true B() => false } } else { 0 } }"),
            ("list-element", "type M = A() | B()" + NL + "fn f(x: M) -> List[Int] { return [match x { A() => true B() => false }] }"),
            ("record-field", "type M = A() | B()" + NL + "type R { x: Int }" + NL + "fn f(m: M) -> R { return R { x: match m { A() => true B() => false } } }"),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check("contextual-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(len(expected), 1, reference)
                self.assertEqual(expected[0][0], "PEP_MATCH_ARM_TYPE_MISMATCH")
                self.assertEqual(actual, expected)

    def test_match_wildcard_catchall_rejects_later_constructor_pattern(self):
        source = "type M = A(Int) | B()" + NL + "fn f(x: M) -> Int { return match x { _ => 0 A(v) => v } }"
        reference = self._reference_check("match-unreachable-wildcard", source)
        _, report = self._analyze(source)
        reference_diagnostic = next(item for item in reference["diagnostics"] if item["code"] == "PEP_UNREACHABLE_MATCH_ARM")
        report_diagnostic = next(
            fields(item) for item in report["diagnostics"]["value"]
            if scalar(fields(item)["code"]) == "PEP_UNREACHABLE_MATCH_ARM"
        )
        self.assertEqual(reference["status"], "invalid", reference)
        self.assertEqual(scalar(report["status"]), "invalid", report)
        self.assertEqual(scalar(report_diagnostic["startByte"]), reference_diagnostic["span"]["start"]["offset"])
        self.assertEqual(scalar(report_diagnostic["endByte"]), reference_diagnostic["span"]["endOffset"])

    def test_match_binding_catchall_rejects_later_wildcard(self):
        source = "type M = A(Int) | B()" + NL + "fn f(x: M) -> Int { return match x { rest => 0 _ => 1 } }"
        reference = self._reference_check("match-unreachable-binding", source)
        _, report = self._analyze(source)
        reference_diagnostic = next(item for item in reference["diagnostics"] if item["code"] == "PEP_UNREACHABLE_MATCH_ARM")
        report_diagnostic = next(
            fields(item) for item in report["diagnostics"]["value"]
            if scalar(fields(item)["code"]) == "PEP_UNREACHABLE_MATCH_ARM"
        )
        self.assertEqual(reference["status"], "invalid", reference)
        self.assertEqual(scalar(report["status"]), "invalid", report)
        self.assertEqual(scalar(report_diagnostic["startByte"]), reference_diagnostic["span"]["start"]["offset"])
        self.assertEqual(scalar(report_diagnostic["endByte"]), reference_diagnostic["span"]["endOffset"])

    def test_unknown_nominal_types_fail_closed(self):
        source = "fn identity(x: Missing) -> Missing { return x }"
        reference = self._reference_check("unknown-nominal", source)
        _, report = self._analyze(source)
        codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
        self.assertEqual(reference["status"], "invalid", reference)
        self.assertEqual(scalar(report["status"]), "invalid", report)
        self.assertIn("PEP_UNKNOWN_TYPE", [item["code"] for item in reference["diagnostics"]])
        self.assertIn("PEP_UNKNOWN_TYPE", codes)

    def test_missing_return_diagnostic_matches_ocaml(self):
        cases = [
            ("empty-body", "fn main() -> Int {}"),
            ("fallthrough-local", "fn main() -> Int { let x: Int = 1 }"),
            ("conditional-fallthrough", "fn main(flag: Bool) -> Int { if flag { return 1 } else { let x: Int = 2 } }"),
            ("nested-block-fallthrough", "fn main() -> Int { { let x: Int = 1 } }"),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check("missing-return-" + name, source)
                _, report = self._analyze(source)
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(scalar(report["status"]), "invalid", report)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual, expected, report)

    def test_unreachable_statements_match_ocaml_across_blocks(self):
        cases = [
            ("after-return", "fn main() -> Int { return 1; let x: Int = 2 }"),
            ("after-both-if-branches-return", "fn main(flag: Bool) -> Int { if flag { return 1 } else { return 2 }" + NL + "let x: Int = 3 }"),
            ("after-returning-nested-block", "fn main() -> Int { { return 1 }" + NL + "let x: Int = 2 }"),
            ("unreachable-invalid-statement", "fn main() -> Int { return 1; let x: Bool = 2 }"),
            ("unreachable-while-body", "fn main() -> Int { while false { return 1; let x: Int = 2 } return 3 }"),
            ("unreachable-for-body", "fn main() -> Int { for item in [1] { return item; let x: Int = 2 } return 3 }"),
        ]
        for name, source in cases:
            with self.subTest(name=name):
                reference = self._reference_check("unreachable-" + name, source)
                _, report = self._analyze(source)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(reference["status"], "invalid", reference)
                self.assertEqual(expected[0][0], "PEP_UNREACHABLE", (name, expected))
                self.assertEqual(scalar(report["status"]), "invalid", report)
                self.assertEqual(actual, expected, (name, expected, actual))

    def test_non_unit_return_completeness_follows_nested_blocks_and_if_branches(self):
        valid_sources = [
            "fn main() -> Int { return 1 }",
            "fn main(flag: Bool) -> Int { if flag { return 1 } else { return 2 } }",
            "fn main() -> Int { { return 1 } }",
        ]
        for source in valid_sources:
            _, report = self._analyze(source)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertEqual(scalar(report["status"]), "valid", (source, report))
            self.assertNotIn("PEP_A13_CONTROL_FLOW_UNSUPPORTED", codes)

        incomplete_sources = [
            "fn main() -> Int { let x = 1 }",
            "fn main(flag: Bool) -> Int { if flag { return 1 } else { let x = 2 } }",
        ]
        for source in incomplete_sources:
            _, report = self._analyze(source)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertEqual(scalar(report["status"]), "invalid", (source, report))
            self.assertIn("PEP_MISSING_RETURN", codes)

    def test_typed_holes_keep_context_scope_candidates_and_original_spans(self):
        source = ("fn id(value: Int) -> Int { return value }" + NL +
                  "fn main(outer: Int) -> Int { let local: Int = ?init; return id(?argument) }")
        opened, report = self._analyze(source)
        self.assertEqual(opened["status"], "incomplete")
        self.assertEqual(scalar(report["status"]), "incomplete", report)
        self.assertEqual(report["diagnostics"]["value"], [])
        holes = [fields(item) for item in report["holes"]["value"]]
        self.assertEqual([scalar(item["name"]) for item in holes], ["init", "argument"])
        self.assertEqual([scalar(item["expectedType"]) for item in holes], ["Int", "Int"])
        self.assertEqual([scalar(item["semanticId"]) for item in holes], [3000000, 3000001])
        starts = [len(source[:source.index("?init")].encode()), len(source[:source.index("?argument")].encode())]
        for hole, start in zip(holes, starts):
            self.assertEqual((scalar(hole["startByte"]), scalar(hole["endByte"])), (start, start + len(("?" + scalar(hole["name"])).encode())))
        self.assertEqual(len(holes[0]["visibleBindingIds"]["value"]), 1)
        bindings = [fields(item) for item in report["bindings"]["value"]]
        local_id = next(scalar(item["semanticId"]) for item in bindings if scalar(item["name"]) == "local")
        binding_names = {scalar(item["semanticId"]): scalar(item["name"]) for item in bindings}
        reference_holes = {item["name"]: item for item in opened["holes"]}
        for hole in holes:
            name = scalar(hole["name"])
            reference = reference_holes[name]
            self.assertEqual(scalar(hole["expectedType"]), reference["expectedType"])
            self.assertEqual(scalar(hole["startByte"]), reference["span"]["start"]["offset"])
            self.assertEqual(scalar(hole["endByte"]), reference["span"]["endOffset"])
            visible_names = {binding_names[scalar(item)] for item in hole["visibleBindingIds"]["value"]}
            self.assertEqual(visible_names, {item["name"] for item in reference["bindings"]})
            candidate_names = {binding_names[scalar(item)] for item in hole["candidateBindingIds"]["value"]}
            self.assertEqual(candidate_names, {item["name"] for item in reference["actions"][0]["candidates"]})
        self.assertNotIn(local_id, [scalar(item) for item in holes[0]["visibleBindingIds"]["value"]])
        self.assertIn(local_id, [scalar(item) for item in holes[1]["visibleBindingIds"]["value"]])
        self.assertIn(local_id, [scalar(item) for item in holes[1]["candidateBindingIds"]["value"]])
        self.assertGreater(len(report["expressionTypes"]["value"]), 0)

    def test_nested_hole_candidates_follow_shadowing_and_match_ocaml(self):
        source = "fn main(outer: Int) -> Int { let value: Int = 1; { let value: Int = 2; return ?nested } }"
        opened, report = self._analyze(source)
        self.assertEqual(opened["status"], "incomplete")
        self.assertEqual(scalar(report["status"]), "incomplete", report)
        hole = fields(report["holes"]["value"][0])
        bindings = [fields(item) for item in report["bindings"]["value"]]
        binding_names = {scalar(item["semanticId"]): scalar(item["name"]) for item in bindings}
        visible_names = {binding_names[scalar(item)] for item in hole["visibleBindingIds"]["value"]}
        candidate_names = {binding_names[scalar(item)] for item in hole["candidateBindingIds"]["value"]}
        reference = opened["holes"][0]
        self.assertEqual(visible_names, {item["name"] for item in reference["bindings"]})
        self.assertEqual(candidate_names, {item["name"] for item in reference["actions"][0]["candidates"]})
        self.assertEqual(visible_names, {"outer", "value"})
        same_name = [item for item in bindings if scalar(item["name"]) == "value"]
        self.assertEqual(len(same_name), 2)
        self.assertEqual(scalar(hole["scopeId"]), scalar(same_name[-1]["scopeId"]))
        self.assertEqual(scalar(hole["startByte"]), reference["span"]["start"]["offset"])
        self.assertEqual(scalar(hole["endByte"]), reference["span"]["endOffset"])

    def test_unconstrained_holes_stay_incomplete_and_semantic_errors_stay_invalid(self):
        source = "fn main() -> Int { let value = ?free; return 0 }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "incomplete", report)
        hole = fields(report["holes"]["value"][0])
        self.assertEqual(scalar(hole["name"]), "free")
        self.assertEqual(scalar(hole["expectedType"]), "")
        self.assertNotEqual(scalar(hole["scopeId"]), 0)
        source = "fn main(x: Bool) -> Int { let value: Int = ?waiting; return x }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "invalid", report)
        self.assertTrue(report["holes"]["value"], report)
        self.assertIn("PEP_TYPE_MISMATCH", [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]])

    def test_if_expression_propagates_context_and_reports_branch_spans(self):
        cases = [
            ("one-hole", "fn f(flag: Bool) -> Int { return if flag { ?yes } else { 0 } }", "incomplete", {"yes": "Int"}),
            ("both-holes", "fn f(flag: Bool) -> Int { return if flag { ?yes } else { ?no } }", "incomplete", {"yes": "Int", "no": "Int"}),
            ("annotated-binding", "fn f(flag: Bool) -> Int { let x: Int = if flag { ?h } else { 0 }; return x }", "incomplete", {"h": "Int"}),
            ("function-argument", "fn use(x: Int) -> Int { return x }\nfn f(flag: Bool) -> Int { return use(if flag { ?h } else { 0 }) }", "incomplete", {"h": "Int"}),
            ("list-element", "fn f(flag: Bool) -> List[Int] { return [if flag { ?h } else { 0 }] }", "incomplete", {"h": "Int"}),
            ("record-field", "type R { x: Int }\nfn f(flag: Bool) -> R { return R { x: if flag { ?h } else { 0 } } }", "incomplete", {"h": "Int"}),
            ("context-first-mismatch", "fn f(flag: Bool) -> Int { return if flag { true } else { 0 } }", "invalid", {}),
            ("context-last-mismatch", "fn f(flag: Bool) -> Int { return if flag { 0 } else { true } }", "invalid", {}),
            ("context-both-mismatch", "fn f(flag: Bool) -> Int { return if flag { true } else { false } }", "invalid", {}),
            ("uncontextual-mismatch", "fn f(flag: Bool) -> Int { let value = if flag { 0 } else { true }; return 1 }", "invalid", {}),
            ("nested-context-branch", "fn f(flag: Bool) -> Int { return if flag { if flag { true } else { 0 } } else { 0 } }", "invalid", {}),
            ("nested-condition-type", "fn f(flag: Bool) -> Int { return if flag { if 1 { 1 } else { 2 } } else { 3 } }", "invalid", {}),
            ("nested-condition-unresolved", "fn f(flag: Bool) -> Int { return if flag { if missing { 1 } else { 2 } } else { 3 } }", "invalid", {}),
            ("nested-list-then-leaf", "fn f(flag: Bool) -> List[List[Int]] { return if flag { if flag { [[1]] } else { [[true]] } } else { [[2]] } }", "invalid", {}),
            ("nested-list-else-leaf", "fn f(flag: Bool) -> List[List[Int]] { return if flag { if flag { [[true]] } else { [[1]] } } else { [[2]] } }", "invalid", {}),
            ("nested-call-unknown", "fn f(flag: Bool) -> Int { return if flag { if flag { missing() } else { 0 } } else { 1 } }", "invalid", {}),
            ("nested-hole-context", "fn f(flag: Bool) -> Int { return if flag { if flag { ?one } else { 0 } } else { 1 } }", "incomplete", {"one": "Int"}),
        ]
        for name, source, expected_status, expected_holes in cases:
            with self.subTest(name=name):
                reference = self._reference_check("if-expression-" + name, source)
                opened, report = self._analyze(source)
                self.assertEqual(reference["status"], expected_status, reference)
                self.assertEqual(scalar(report["status"]), expected_status, report)
                reference_diagnostics = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual_diagnostics = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(actual_diagnostics, reference_diagnostics, report)
                reference_holes = {item["name"]: item["expectedType"] for item in opened.get("holes", [])}
                actual_holes = {scalar(fields(item)["name"]): scalar(fields(item)["expectedType"]) for item in report["holes"]["value"]}
                self.assertEqual(reference_holes, expected_holes)
                self.assertEqual(actual_holes, expected_holes, report)

    def test_utf8_and_crlf_keep_original_function_byte_spans(self):
        prefix = '"λ🙂"' + CRLF
        source = prefix + "fn main() -> Int { return 1 }" + CRLF
        _, report = self._analyze(source)
        function = fields(report["functions"]["value"][0])
        self.assertEqual(scalar(function["startByte"]), len(prefix.encode("utf-8")))
        self.assertEqual(scalar(function["endByte"]), len(source.encode("utf-8")) - 2)

    def test_four_independent_call_errors_preserve_fixed_budget_boundary(self):
        bad_lines = ["fn accepts(x: Bool) -> Bool { return x }"]
        bad_lines.extend(f"fn bad{i}() -> Bool {{ return accepts({i}) }}" for i in range(4))
        bad_source = NL.join(bad_lines)
        self.assertEqual(len(bad_source.encode("utf-8")), 200)
        reference = self._reference_check("four-independent-call-errors", bad_source)
        self.assertEqual(reference["status"], "invalid", reference)
        expected = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in reference["diagnostics"]
        ]

        empty = self._open("")
        empty_parsed = typed_record("ParserProgress", [
            ("document", typed("Str", empty["document"])),
            ("revision", typed("Str", empty["revision"])),
            ("status", typed("Str", "complete")),
            ("nodes", typed_list("FlatAstNode", [])),
            ("done", typed("Bool", True)),
            ("errorCode", typed("Str", "")),
            ("message", typed("Str", "")),
            ("errorStart", typed("Int", "0")),
            ("errorEnd", typed("Int", "0")),
            ("errorLine", typed("Int", "0")),
            ("errorColumn", typed("Int", "0")),
        ])
        empty_target = {"document": empty["document"], "revision": empty["revision"], "entryFunctions": []}
        for tool, function, arguments, expected_result in [
            ("pep-a13-parser", "parser_parse_program", [], empty_parsed),
            ("pep-a13-checker-staged", "analyze_parsed", [empty_parsed], checker_report(empty["document"], "")),
        ]:
            registered = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_register", "tool": tool,
                                           "document": self.tool_document, "revision": self.tool_revision,
                                           "function": function})
            self.assertEqual(registered.get("status"), "Registered", registered)
            validated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_validate", "tool": tool,
                                          "document": self.tool_document, "revision": self.tool_revision,
                                          "testVectors": [{"arguments": arguments, "expect": expected_result,
                                                           "semanticTarget": empty_target}]})
            self.assertEqual(validated.get("status"), "Validated", validated)
            activated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_activate", "tool": tool,
                                          "document": self.tool_document, "revision": self.tool_revision})
            self.assertEqual(activated.get("status"), "Active", activated)

        def check_staged(source):
            opened = self._open(source)
            target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
            parsed = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_invoke", "tool": "pep-a13-parser", "arguments": [],
                                       "semanticTarget": target})
            self.assertEqual(parsed.get("outcome"), "ok", parsed)
            staged = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_invoke", "tool": "pep-a13-checker-staged",
                                       "arguments": [parsed["result"]], "semanticTarget": target})
            self.assertEqual(staged.get("outcome"), "ok", staged)
            return opened, fields(staged["result"])

        opened, staged_report = check_staged(bad_source)
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        staged_diagnostics = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in staged_report["diagnostics"]["value"]
        ]
        self.assertEqual(scalar(staged_report["status"]), reference["status"], staged_report)
        self.assertEqual(staged_diagnostics, expected, (expected, staged_diagnostics, staged_report))

        one_shot = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "pep-a13-checker", "arguments": [],
                                     "semanticTarget": target})
        self.assertEqual(one_shot.get("outcome"), "error", one_shot)
        self.assertEqual(one_shot["error"]["code"], "PEP_RUNTIME_STEP_LIMIT", one_shot)

        control_lines = ["fn accepts(x: Bool) -> Bool { return x }"]
        control_lines.extend(f"fn good{i}() -> Bool {{ return accepts(true) }}" for i in range(4))
        control_source = NL.join(control_lines)
        control_reference = self._reference_check("four-independent-call-control", control_source)
        _, control = check_staged(control_source)
        self.assertEqual(control_reference["status"], "valid", control_reference)
        self.assertEqual(scalar(control["status"]), control_reference["status"], control)
        self.assertEqual(control["diagnostics"]["value"], [], control)
        control_opened = self._open(control_source)
        control_target = {"document": control_opened["document"], "revision": control_opened["revision"], "entryFunctions": []}
        one_shot_control = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                             "op": "tool_invoke", "tool": "pep-a13-checker",
                                             "arguments": [], "semanticTarget": control_target})
        self.assertEqual(one_shot_control.get("outcome"), "error", one_shot_control)
        self.assertEqual(one_shot_control["error"]["code"], "PEP_RUNTIME_STEP_LIMIT", one_shot_control)
        hole_source = "fn accepts(x: Bool) -> Bool { return x }" + NL + "fn probe() -> Bool { return accepts(?arg) }"
        hole_reference = self._reference_check("independent-call-typed-hole", hole_source)
        _, hole_report = check_staged(hole_source)
        self.assertEqual(hole_reference["status"], "incomplete", hole_reference)
        self.assertEqual(scalar(hole_report["status"]), hole_reference["status"], hole_report)
        self.assertEqual([(scalar(fields(item)["name"]), scalar(fields(item)["expectedType"]))
                          for item in hole_report["holes"]["value"]], [("arg", "Bool")])

    def _assert_nested_list_cases_match_ocaml(self, cases):
        for name, source, expected_status in cases:
            with self.subTest(name=name):
                reference = self._reference_check("deep-nested-list-" + name, source)
                _, report = self._analyze(source)
                expected = [
                    (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
                    for item in reference["diagnostics"]
                ]
                actual = [
                    (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
                    for item in report["diagnostics"]["value"]
                ]
                self.assertEqual(reference["status"], expected_status, reference)
                self.assertEqual(scalar(report["status"]), reference["status"], report)
                self.assertEqual(actual, expected, (expected, actual, report))

    def test_deep_nested_list_signatures_and_returns_match_ocaml(self):
        self._assert_nested_list_cases_match_ocaml([
            ("signature", "fn identity(value: List[List[List[Int]]]) -> List[List[List[Int]]] { return value }", "valid"),
            ("four-level-signature", "fn identity(value: List[List[List[List[Int]]]]) -> List[List[List[List[Int]]]] { return value }", "valid"),
            ("literal-under-return-context", "fn make() -> List[List[List[Int]]] { return [[[1]]] }", "valid"),
            ("four-level-literal-under-return-context", "fn make() -> List[List[List[List[Int]]]] { return [[[[1]]]] }", "valid"),
        ])

    def test_deep_nested_list_calls_match_ocaml(self):
        self._assert_nested_list_cases_match_ocaml([
            ("four-level-reverse-result", "fn flip(value: List[List[List[List[Int]]]]) -> List[List[List[List[Int]]]] { return reverse(value) }", "valid"),
            ("three-level-append-element", "fn add(value: List[List[List[Int]]]) -> List[List[List[Int]]] { return append(value, [[1]]) }", "valid"),
            ("four-level-append-parameter", "fn add(value: List[List[List[List[Int]]]], item: List[List[List[Int]]]) -> List[List[List[List[Int]]]] { return append(value, item) }", "valid"),
            ("literal-under-call-context", "fn take(value: List[List[List[Int]]]) -> Int { return 0 } fn main() -> Int { return take([[[1]]]) }", "valid"),
        ])

    def _assert_valid_ocaml_source_hits_checker_budget(self, name, source):
        reference = self._reference_check(name, source)
        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(reference["diagnostics"], [], reference)

        empty = self._open("")
        empty_target = {"document": empty["document"], "revision": empty["revision"], "entryFunctions": []}
        empty_parsed = typed_record("ParserProgress", [
            ("document", typed("Str", empty["document"])),
            ("revision", typed("Str", empty["revision"])),
            ("status", typed("Str", "complete")),
            ("nodes", typed_list("FlatAstNode", [])),
            ("done", typed("Bool", True)),
            ("errorCode", typed("Str", "")),
            ("message", typed("Str", "")),
            ("errorStart", typed("Int", "0")),
            ("errorEnd", typed("Int", "0")),
            ("errorLine", typed("Int", "0")),
            ("errorColumn", typed("Int", "0")),
        ])
        for tool, function, arguments, expected in [
            ("pep-a13-parser", "parser_parse_program", [], empty_parsed),
            ("pep-a13-checker-staged", "analyze_parsed", [empty_parsed], checker_report(empty["document"], "")),
        ]:
            registered = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_register", "tool": tool,
                                           "document": self.tool_document, "revision": self.tool_revision,
                                           "function": function})
            self.assertEqual(registered.get("status"), "Registered", registered)
            validated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_validate", "tool": tool,
                                          "document": self.tool_document, "revision": self.tool_revision,
                                          "testVectors": [{"arguments": arguments, "expect": expected,
                                                           "semanticTarget": empty_target}]})
            self.assertEqual(validated.get("status"), "Validated", validated)
            activated = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                          "op": "tool_activate", "tool": tool,
                                          "document": self.tool_document, "revision": self.tool_revision})
            self.assertEqual(activated.get("status"), "Active", activated)

        opened = self._open(source)
        target = {"document": opened["document"], "revision": opened["revision"], "entryFunctions": []}
        parsed = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_invoke", "tool": "pep-a13-parser", "arguments": [],
                                   "semanticTarget": target})
        self.assertEqual(parsed.get("outcome"), "ok", parsed)
        staged = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_invoke", "tool": "pep-a13-checker-staged",
                                   "arguments": [parsed["result"]], "semanticTarget": target})
        self.assertEqual(staged.get("outcome"), "ok", staged)
        report = fields(staged["result"])
        actual = [
            (scalar(fields(item)["code"]), scalar(fields(item)["startByte"]), scalar(fields(item)["endByte"]))
            for item in report["diagnostics"]["value"]
        ]
        expected = [
            (item["code"], item["span"]["start"]["offset"], item["span"]["endOffset"])
            for item in reference["diagnostics"]
        ]
        self.assertEqual(scalar(report["status"]), reference["status"], report)
        self.assertEqual(actual, expected, (expected, actual, report))

        result = self.client.send({
            "schemaVersion": 3,
            "toolProtocolVersion": 2,
            "op": "tool_invoke",
            "tool": "pep-a13-checker",
            "arguments": [],
            "semanticTarget": target,
        })
        self.assertEqual(result.get("outcome"), "error", result)
        self.assertEqual(result.get("error", {}).get("code"), "PEP_RUNTIME_STEP_LIMIT", result)

    def test_four_level_append_single_list_matches_ocaml(self):
        self._assert_nested_list_cases_match_ocaml([
            ("four-level-append-single-list", "fn add(value: List[List[List[List[Int]]]], item: List[List[Int]]) -> List[List[List[List[Int]]]] { return append(value, [item]) }", "valid"),
        ])

    def test_four_level_append_nested_typed_literal_hits_known_runtime_boundary(self):
        source = "fn add(value: List[List[List[List[Int]]]], item: List[Int]) -> List[List[List[List[Int]]]] { return append(value, [[item]]) }"
        self._assert_valid_ocaml_source_hits_checker_budget("four-level-append-nested-typed-literal", source)

    def test_four_level_append_nested_literal_hits_known_runtime_boundary(self):
        source = "fn add(value: List[List[List[List[Int]]]]) -> List[List[List[List[Int]]]] { return append(value, [[[1]]]) }"
        self._assert_valid_ocaml_source_hits_checker_budget("four-level-append-nested-literal", source)

    def test_deep_nested_list_mismatches_match_ocaml(self):
        self._assert_nested_list_cases_match_ocaml([
            ("literal-leaf-mismatch", "fn bad(value: List[List[List[Int]]]) -> List[List[List[Int]]] { return [[['text']]] }", "invalid"),
            ("nested-call-argument", "fn take(value: List[List[List[Int]]]) -> Int { return 0 } fn main() -> Int { return take([[['text']]]) }", "invalid"),
            ("nested-return-leaf-mismatch", "fn bad() -> List[List[List[Int]]] { return [[['text']]] }", "invalid"),
            ("four-level-return-leaf-mismatch", "fn bad() -> List[List[List[List[Int]]]] { return [[[['text']]]] }", "invalid"),
            ("four-level-append-leaf-mismatch", "fn bad(value: List[List[List[List[Int]]]]) -> List[List[List[List[Int]]]] { return append(value, [[['text']]]) }", "invalid"),
        ])

    def test_nested_boolean_helper_calls_complete_within_tool_budget(self):
        source = (
            "fn identity(flag: Bool) -> Bool { return flag }\n"
            "fn negate(flag: Bool) -> Bool { return !flag }\n"
            "fn main() -> Int { return if identity(negate(false)) { 42 } else { 0 } }\n"
        )
        reference = self._reference_check("nested-boolean-helpers", source)
        self.assertEqual(reference["status"], "valid", reference)
        self.assertEqual(reference["diagnostics"], [], reference)
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "valid", report)


class PepC23LargeSourceInputTests(unittest.TestCase):
    def test_large_valid_utf8_source_uses_text_open_and_preserves_byte_revision(self):
        from pep_c23 import Session, open_source_target

        prefix = b"fn main() -> Int { return 42 }\n//"
        raw = prefix + (b"x" * (65_536 - len(prefix) - 1)) + "é".encode("utf-8")
        self.assertGreater(len(raw), 65_536)
        session = Session()
        try:
            target = open_source_target(session, raw, "large-valid-utf8")
        finally:
            session.close()

        self.assertEqual(target.get("outcome"), "ok", target)
        self.assertEqual(target.get("status"), "valid", target)
        self.assertEqual(
            target.get("revision"),
            "sha256:" + hashlib.sha256(raw).hexdigest(),
        )

    def test_small_source_bytes_remain_opaque_and_oversized_invalid_bytes_fail_closed(self):
        from pep_c23 import open_source_target

        class CaptureSession:
            def __init__(self):
                self.requests = []

            def send(self, request):
                self.requests.append(request)
                return {
                    "outcome": "ok",
                    "revision": "sha256:" + hashlib.sha256(source_bytes).hexdigest(),
                }

        source_bytes = b"\xff"
        session = CaptureSession()
        open_source_target(session, source_bytes, "raw-small")
        self.assertEqual(session.requests[0]["op"], "open_bytes")
        self.assertEqual(session.requests[0]["bytes"], [255])

        session = CaptureSession()
        oversized_invalid = b"x" * 65_536 + b"\xff"
        with self.assertRaisesRegex(RuntimeError, "PEP_SOURCE_BYTE_LIMIT"):
            open_source_target(session, oversized_invalid, "raw-large")
        self.assertEqual(session.requests, [])

    def test_open_source_target_checks_revision_against_original_bytes(self):
        from pep_c23 import open_source_target

        class MismatchedRevisionSession:
            def send(self, request):
                return {"outcome": "ok", "revision": "sha256:wrong"}

        with self.assertRaisesRegex(RuntimeError, "revision does not match"):
            open_source_target(MismatchedRevisionSession(), b"fn main() -> Int { return 0 }", "wrong")


if __name__ == "__main__":
    unittest.main()
