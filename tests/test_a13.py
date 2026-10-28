import json
import os
import pathlib
import subprocess
import unittest

from tests.test_a11 import JsonLineClient, revision, typed, typed_list, typed_record

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
            ("builtin-result", "fn f() -> Int { return match length([1]) { _ => 0 } }", "PEP_MATCH_NON_UNION"),
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


if __name__ == "__main__":
    unittest.main()