import hashlib
import json
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = ROOT / "_build" / "a6-tests"
PEP = ROOT / "pep.ps1"


def invoke(*args, input_text=None):
    return subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
        cwd=ROOT, text=True, input=input_text, capture_output=True, check=False,
    )


class A6CollectionsAndControlTests(unittest.TestCase):
    def check_source(self, source):
        BUILD.mkdir(parents=True, exist_ok=True)
        path = BUILD / "case.pep"
        path.write_text(source, encoding="utf-8", newline="")
        result = invoke("check", path, "--json")
        return result, json.loads(result.stdout)

    def test_required_and_additional_examples_run(self):
        result = invoke("run", ROOT / "examples" / "a6_collections_control.pep")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["42", "0", "1", "17", "22", "10", "0", "1", "42"])

    def test_describe_reports_implemented_collections_and_control_flow(self):
        result = invoke("describe", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        description = json.loads(result.stdout)
        self.assertIn("List[T]", description["parametricTypes"])
        self.assertEqual(description["runtime"], {"maxSteps": 1000000, "maxCallDepth": 512})
        for feature in ("typed_lists", "mutable_bindings", "for_in", "while", "short_circuit_boolean_logic", "scalar_equality"):
            self.assertIn(feature, description["features"])
        self.assertEqual([builtin["name"] for builtin in description["builtins"]], ["say", "int_text", "length", "append", "prepend", "reverse", "byte_length", "byte_at", "byte_slice", "utf8_slice", "source_bytes", "contains"])

    def test_list_and_binding_diagnostics(self):
        cases = {
            "let values = [1, true]": "PEP_TYPE_MISMATCH",
            "let values = []": "PEP_EMPTY_LIST_NEEDS_TYPE",
            "let values = [[], []]": "PEP_EMPTY_LIST_NEEDS_TYPE",
            "let values: List[Int] = [1]\nlet copy = append(values, true)": "PEP_TYPE_MISMATCH",
            "type Point { x: Int }\nlet points = [Point { x: 1 }]\nlet found = contains(points, Point { x: 1 })": "PEP_MEMBERSHIP_UNSUPPORTED",
            "let value = 1\nvalue = 2": "PEP_ASSIGN_IMMUTABLE",
            "missing = 2": "PEP_UNKNOWN_VARIABLE",
            "var value: Int = 1\nvalue = true": "PEP_TYPE_MISMATCH",
            "for item in [1] {}\nlet outside = item": "PEP_UNKNOWN_VARIABLE",
            "if 1 {} else {}": "PEP_TYPE_MISMATCH",
            "while 1 {}": "PEP_TYPE_MISMATCH",
        }
        for source, expected in cases.items():
            with self.subTest(expected=expected, source=source):
                result, response = self.check_source(source)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(response["status"], "invalid")
                self.assertEqual(response["diagnostics"][0]["code"], expected)

    def test_typed_list_hole_has_expected_element_type(self):
        source = "fn values() -> List[Int] { return [?missing] }\n"
        payload = json.dumps({"schemaVersion": 3, "op": "open", "source": source}) + "\n"
        opened = invoke("session", "--jsonl", input_text=payload)
        self.assertEqual(opened.returncode, 0, opened.stderr)
        response = json.loads(opened.stdout)
        self.assertEqual(response["status"], "incomplete")
        hole = response["holes"][0]
        self.assertEqual(hole["expectedType"], "Int")
        self.assertIn("revision", hole["identity"])

    def test_short_circuit_and_mutable_loop_execution(self):
        source = """fn count_down(value: Int) -> Int {
    var current = value
    while current != 0 {
        current = current - 1
    }
    return current
}
let safe = false && (1 / 0 == 0)
say(int_text(if safe { 0 } else { count_down(4) }))
"""
        BUILD.mkdir(parents=True, exist_ok=True)
        path = BUILD / "short_circuit.pep"
        path.write_text(source, encoding="utf-8", newline="")
        result = invoke("run", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "0\n")

    def test_unbounded_while_stops_at_runtime_budget(self):
        source = "while true {}\n"
        BUILD.mkdir(parents=True, exist_ok=True)
        path = BUILD / "budget.pep"
        path.write_text(source, encoding="utf-8", newline="")
        result = invoke("run", path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PEP_RUNTIME_STEP_LIMIT", result.stderr)

    def test_tool_call_scan_sees_effects_inside_new_control_flow(self):
        source = 'fn calculate(value: Int) -> Int { if true { say("blocked") } else {} return value }\n'
        revision = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
        requests = [
            {"schemaVersion": 3, "op": "open", "source": source},
            {"schemaVersion": 3, "toolProtocolVersion": 1, "op": "tool_register", "tool": "calculate", "document": "doc-1", "revision": revision, "function": "calculate"},
            {"schemaVersion": 3, "toolProtocolVersion": 1, "op": "tool_validate", "tool": "calculate", "document": "doc-1", "revision": revision, "testVectors": [{"arguments": [{"type": "Int", "value": "2"}], "expect": {"type": "Int", "value": "2"}}]},
        ]
        payload = "\n".join(json.dumps(item) for item in requests) + "\n"
        result = invoke("session", "--jsonl", input_text=payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[2]["status"], "Rejected")
        self.assertIn("say", responses[2]["error"].lower())


    def test_shadowing_nested_assignment_scopes_and_scalar_operators(self):
        source = """let value = 10
{
    let value = 2
}
var total = 0
if true {
    var inner = 1
    inner = inner + 1
    total = inner
} else {
    total = 99
}
for item in [3] {
    total = total + item
}
while total <= 5 {
    total = total + 1
}
say(int_text(if total == 6 && total != 5 && !false { total } else { 0 }))
say(int_text(value))
"""
        BUILD.mkdir(parents=True, exist_ok=True)
        path = BUILD / "scopes.pep"
        path.write_text(source, encoding="utf-8", newline="")
        result = invoke("run", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "6\n10\n")

    def test_loop_binding_is_immutable_and_loop_return_flow_is_conservative(self):
        cases = {
            "for item in [1] { item = 2 }": "PEP_ASSIGN_IMMUTABLE",
            "fn maybe() -> Int { while true { return 1 } }": "PEP_MISSING_RETURN",
            "fn branch(value: Bool) -> Int { if value { return 1 } else { return 2 } }": None,
        }
        for source, expected in cases.items():
            with self.subTest(expected=expected, source=source):
                result, response = self.check_source(source)
                if expected is None:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(response["status"], "valid")
                else:
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(response["diagnostics"][0]["code"], expected)

    def test_recursive_value_equality_is_not_implicitly_defined(self):
        source = "type Expr = Number(Int)\nlet value = Number(1) == Number(1)\n"
        result, response = self.check_source(source)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(response["diagnostics"][0]["code"], "PEP_EQUALITY_UNSUPPORTED")

    def test_tool_loop_and_collection_work_obey_step_budget(self):
        source = """fn count() -> Int { var value = 0 while value <= 100000 { value = value + 1 } return value }
fn build() -> Int {
    var values: List[Int] = []
    var item = 0
    while item <= 500 {
        values = append(values, item)
        item = item + 1
    }
    return length(values)
}
"""
        revision = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
        requests = [
            {"schemaVersion": 3, "op": "open", "source": source},
            {"schemaVersion": 3, "toolProtocolVersion": 1, "op": "tool_register", "tool": "count", "document": "doc-1", "revision": revision, "function": "count"},
            {"schemaVersion": 3, "toolProtocolVersion": 1, "op": "tool_validate", "tool": "count", "document": "doc-1", "revision": revision, "testVectors": [{"arguments": [], "expect": {"type": "Int", "value": "100001"}}]},
            {"schemaVersion": 3, "toolProtocolVersion": 1, "op": "tool_register", "tool": "build", "document": "doc-1", "revision": revision, "function": "build"},
            {"schemaVersion": 3, "toolProtocolVersion": 1, "op": "tool_validate", "tool": "build", "document": "doc-1", "revision": revision, "testVectors": [{"arguments": [], "expect": {"type": "Int", "value": "501"}}]},
        ]
        payload = "\n".join(json.dumps(item) for item in requests) + "\n"
        result = invoke("session", "--jsonl", input_text=payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        for index in (2, 4):
            self.assertEqual(responses[index]["status"], "Rejected")
            self.assertIn("budget", responses[index]["error"].lower())


if __name__ == "__main__":
    unittest.main()
