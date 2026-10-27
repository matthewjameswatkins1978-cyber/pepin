import os
import pathlib
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

        source = "fn main() -> Int { return missing }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "invalid", report)
        diagnostic = fields(report["diagnostics"]["value"][0])
        self.assertEqual(scalar(diagnostic["code"]), "PEP_UNKNOWN_BINDING")
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
        binary = next(item for item in types if scalar(item["startByte"]) == source.index("x + 1"))
        self.assertEqual((scalar(binary["startByte"]), scalar(binary["endByte"])),
                         (source.index("x + 1"), source.index("x + 1") + len("x + 1")))

    def test_return_argument_and_operator_type_errors_are_explicit(self):
        source = "fn wrong(x: Bool) -> Int { return x }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "invalid", report)
        codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
        self.assertIn("PEP_RETURN_TYPE", codes)

        source = "fn id(x: Int) -> Int { return x }" + NL + "fn main() -> Int { return id(true) }"
        _, report = self._analyze(source)
        codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
        self.assertIn("PEP_ARGUMENT_TYPE", codes)

        source = "fn main() -> Int { return 1 + true }"
        _, report = self._analyze(source)
        codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
        self.assertIn("PEP_TYPE_MISMATCH", codes)

    def test_primitive_builtin_signatures_are_checked(self):
        source = "fn main() -> Unit { say(int_text(7)); return say(\"done\") }"
        _, report = self._analyze(source)
        self.assertEqual(scalar(report["status"]), "valid", report)
        types_by_start = {scalar(fields(item)["startByte"]): scalar(fields(item)["typeName"]) for item in report["expressionTypes"]["value"]}
        for call, expected_type in [("say(int_text(7))", "Unit"), ("int_text(7)", "Str"), ("say(\"done\")", "Unit")]:
            self.assertEqual(types_by_start[source.index(call)], expected_type)

        cases = [
            ("fn main() -> Unit { return say() }", "PEP_ARGUMENT_COUNT"),
            ("fn main() -> Unit { return say(1) }", "PEP_ARGUMENT_TYPE"),
            ("fn main() -> Str { return int_text() }", "PEP_ARGUMENT_COUNT"),
            ("fn main() -> Str { return int_text(true) }", "PEP_ARGUMENT_TYPE"),
        ]
        for source, expected_code in cases:
            _, report = self._analyze(source)
            self.assertEqual(scalar(report["status"]), "invalid", report)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertIn(expected_code, codes)

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
            ("fn main() -> Int { return byte_length(1) }", "PEP_ARGUMENT_TYPE"),
            ("fn main() -> Int { return byte_at(source_bytes()) }", "PEP_ARGUMENT_COUNT"),
            ("fn main() -> SourceBytes { return byte_slice(source_bytes(), 0) }", "PEP_ARGUMENT_COUNT"),
            ("fn main() -> Str { return utf8_slice(source_bytes(), 0, true) }", "PEP_ARGUMENT_TYPE"),
        ]
        for source, expected_code in cases:
            _, report = self._analyze(source)
            self.assertEqual(scalar(report["status"]), "invalid", report)
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertIn(expected_code, codes)

    def test_unimplemented_nominal_and_list_types_fail_closed(self):
        source = "fn identity(x: Missing) -> Missing { return x }"
        _, report = self._analyze(source)
        codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
        self.assertEqual(scalar(report["status"]), "invalid", report)
        self.assertIn("PEP_A13_TYPE_UNSUPPORTED", codes)

        source = "fn empty() -> List[Int] { return [] }"
        _, report = self._analyze(source)
        codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
        self.assertEqual(scalar(report["status"]), "invalid", report)
        self.assertIn("PEP_A13_TYPE_UNSUPPORTED", codes)

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
        self.assertIn("PEP_RETURN_TYPE", [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]])

    def test_utf8_and_crlf_keep_original_function_byte_spans(self):
        prefix = '"λ🙂"' + CRLF
        source = prefix + "fn main() -> Int { return 1 }" + CRLF
        _, report = self._analyze(source)
        function = fields(report["functions"]["value"][0])
        self.assertEqual(scalar(function["startByte"]), len(prefix.encode("utf-8")))
        self.assertEqual(scalar(function["endByte"]), len(source.encode("utf-8")) - 2)


if __name__ == "__main__":
    unittest.main()