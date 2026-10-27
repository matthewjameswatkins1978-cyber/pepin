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
            ("fn bad() -> List[Int] { return [\"text\"] }", "PEP_RETURN_TYPE"),
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
            ("assignment-type", "fn main() -> Int { var x: Int = 0; x = true; return x }", "PEP_TYPE_MISMATCH", "PEP_A13_CONTROL_FLOW_UNSUPPORTED"),
            ("for-in-source", "fn main() -> Int { for item in 1 {} return 0 }", "PEP_FOR_REQUIRES_LIST", "PEP_A13_CONTROL_FLOW_UNSUPPORTED"),
            ("missing-return", "fn main() -> Int { let x: Int = 1 }", "PEP_MISSING_RETURN", "PEP_A13_CONTROL_FLOW_UNSUPPORTED"),
        ]
        for name, source, reference_code, checker_code in cases:
            reference = self._reference_check(name, source)
            _, report = self._analyze(source)
            self.assertEqual(reference["status"], "invalid", (name, reference))
            self.assertIn(reference_code, [item["code"] for item in reference["diagnostics"]], (name, reference))
            self.assertEqual(scalar(report["status"]), "invalid", (name, report))
            codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
            self.assertIn(checker_code, codes, (name, codes))
            if name in {"record-field", "constructor-payload", "if-condition", "while-condition", "builtin-arity", "builtin-type"}:
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
        _, report = self._analyze(out_of_scope)
        codes = [scalar(fields(item)["code"]) for item in report["diagnostics"]["value"]]
        self.assertIn("PEP_UNKNOWN_BINDING", codes)

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
            self.assertIn("PEP_A13_CONTROL_FLOW_UNSUPPORTED", codes)

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


if __name__ == "__main__":
    unittest.main()