import json
import os
import pathlib
import subprocess
import unittest

from tests.test_a11 import JsonLineClient, revision, typed, typed_list, typed_record

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = ROOT / "_build" / "a14"
LEXER = ROOT / "examples" / "pep_lexer.pep"
PARSER = ROOT / "examples" / "pep_parser.pep"
CHECKER = ROOT / "tests" / "pep_checker_a13.pep"
EMITTER = ROOT / "tests" / "pep_c23_emitter.pep"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")
GCC = pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe")


def fields(value):
    return {item["name"]: item["value"] for item in value["fields"]}


def scalar(value):
    return int(value["value"]) if value["type"] == "Int" else value["value"]


def emission(status, parts=(), diagnostic=""):
    return typed_record("PepC23Emission", [
        ("status", typed("Str", status)),
        ("sourceParts", typed_list("Str", [typed("Str", part) for part in parts])),
        ("diagnostic", typed("Str", diagnostic)),
    ])


class A14C23EmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BUILD.mkdir(parents=True, exist_ok=True)
        cls.bundle = "\n".join(path.read_text(encoding="utf-8") for path in
                                (LEXER, PARSER, CHECKER, EMITTER))
        (BUILD / "emitter_bundle.pep").write_text(cls.bundle, encoding="utf-8", newline="\n")
        for compiler in (CLANG, GCC):
            if not compiler.is_file():
                raise unittest.SkipTest(f"required C23 compiler unavailable: {compiler}")

    def setUp(self):
        self.client = JsonLineClient(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "session", "--jsonl"],
            ROOT, os.environ.copy(),
        )
        opened = self.client.send({"schemaVersion": 3, "op": "open", "source": self.bundle,
                                   "name": "a14-c23-emitter", "metadataOnly": True})
        self.assertEqual(opened.get("outcome"), "ok", opened)
        self.assertEqual(opened.get("status"), "valid", opened)
        self.tool_document = opened["document"]
        self.tool_revision = revision(self.bundle.encode("utf-8"))
        registered = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                                       "tool": "pep-c23-emitter", "document": self.tool_document,
                                       "revision": self.tool_revision, "function": "emit_c23"})
        self.assertEqual(registered.get("status"), "Registered", registered)
        sample = "fn main() -> Int { return true }"
        target = self._open(sample)
        expected = emission("unsupported", (), "Pep C23 emission requires a valid Pep checker report")
        validated = self.client.send({
            "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
            "tool": "pep-c23-emitter", "document": self.tool_document, "revision": self.tool_revision,
            "testVectors": [{
                "arguments": [], "expect": expected,
                "semanticTarget": {"document": target["document"], "revision": target["revision"],
                                   "entryFunctions": []},
            }],
        })
        self.assertEqual(validated.get("status"), "Validated", validated)
        active = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                                   "tool": "pep-c23-emitter", "document": self.tool_document,
                                   "revision": self.tool_revision})
        self.assertEqual(active.get("status"), "Active", active)

    def tearDown(self):
        self.client.close()

    def _open(self, source):
        return self.client.send({"schemaVersion": 3, "op": "open_bytes", "name": "a14-target",
                                 "bytes": list(source.encode("utf-8"))})

    def _emit(self, source):
        opened = self._open(source)
        self.assertEqual(opened.get("outcome"), "ok", opened)
        result = self.client.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                   "tool": "pep-c23-emitter", "arguments": [],
                                   "semanticTarget": {"document": opened["document"],
                                                      "revision": opened["revision"],
                                                      "entryFunctions": []}})
        self.assertEqual(result.get("outcome"), "ok", result)
        self.assertEqual(result.get("revision"), self.tool_revision)
        return fields(result["result"])

    def _run_reference(self, source):
        pep_path = BUILD / "reference.pep"
        pep_path.write_text(source + "\nsay(int_text(main()))\n", encoding="utf-8", newline="\n")
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "run", str(pep_path)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )

    def _compile_and_run(self, source, expected):
        reference = self._run_reference(source)
        self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
        emitted = self._emit(source)
        self.assertEqual(scalar(emitted["status"]), "emitted", emitted)
        c_source = "".join(scalar(part) for part in emitted["sourceParts"]["value"])
        c_path = BUILD / "generated.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        for compiler in (CLANG, GCC):
            with self.subTest(compiler=compiler.name, source=source):
                exe = BUILD / (compiler.stem + ".exe")
                built = subprocess.run(
                    [str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
                     "-O2", str(c_path), "-o", str(exe)],
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                ran = subprocess.run([str(exe)], text=True, capture_output=True, check=False)
                self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                self.assertEqual(ran.returncode, reference.returncode)
                self.assertEqual(ran.stdout, f"{expected}\n")
                self.assertEqual(ran.stdout, reference.stdout)

    def test_generated_c23_executes_source_backed_programs_under_clang_and_gcc(self):
        self.assertEqual(subprocess.run([str(CLANG), "--version"], text=True, capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run([str(GCC), "--version"], text=True, capture_output=True).returncode, 0)
        for value in (0, 17, 2147483647, 9223372036854775807):
            with self.subTest(value=value):
                self._compile_and_run(f"fn main() -> Int {{ return {value} }}", value)
        self._compile_and_run(
            "fn main() -> Int { return answer() } fn answer() -> Int { return 29 }",
            29,
        )
        self._compile_and_run(
            "fn main() -> Int {\n  let answer = 6 * 7\n  return answer\n}",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int {\n  let first = 6 * 7\n  let second = first + 5\n  return second\n}",
            47,
        )
        self._compile_and_run(
            "fn main() -> Int { return answer() }\nfn answer() -> Int { return 20 + 22 }",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int { return increment(41) }\n"
            "fn increment(value: Int) -> Int { return value + 1 }",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int { return countdown(6) }\n"
            "fn countdown(value: Int) -> Int {\n"
            "  if value <= 0 { return 42 } else { return countdown(value - 1) }\n"
            "}",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int { return constant(41) }\n"
            "fn constant(unused: Int) -> Int { return 42 }",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int { return combine(19, 23) }\n"
            "fn combine(left: Int, right: Int) -> Int { return right }",
            23,
        )
        self._compile_and_run(
            "fn main() -> Int { return first(41, 900) }\n"
            "fn first(value: Int, unused: Int) -> Int { return value }",
            41,
        )
        self._compile_and_run(
            "fn main() -> Int { return if true { 17 } else { 29 } }",
            17,
        )
        self._compile_and_run(
            "fn main() -> Int { return if false { 17 } else { 29 } }",
            29,
        )
        self._compile_and_run(
            "fn main() -> Int { return if 1 <= 2 { 17 } else { 29 } }",
            17,
        )
        self._compile_and_run(
            "fn main() -> Int { return if false { 1 / 0 } else { 42 } }",
            42,
        )

    def test_statement_conditionals_execute_only_the_selected_return_branch(self):
        self._compile_and_run(
            "fn main() -> Int { if true { return 17 } else { return 29 } }",
            17,
        )
        self._compile_and_run(
            "fn main() -> Int { if false { return 1 / 0 } else { return 42 } }",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int {\n  let base = 41\n  if base <= 42 { return base + 1 } else { return 0 }\n}",
            42,
        )

    def test_c23_comparisons_and_short_circuit_logic_match_the_interpreter(self):
        self._compile_and_run(
            "fn main() -> Int { if 2 == 2 && 2 != 3 && 2 <= 3 { return 42 } else { return 0 } }",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int { if false && (1 / 0 == 0) { return 0 } else { return 42 } }",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int { if true || (1 / 0 == 0) { return 42 } else { return 0 } }",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int { if (0 / 1 == 1) && (1 / 0 == 0) { return 0 } else { return 42 } }",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int { if (1 / 1 == 1) || (1 / 0 == 0) { return 42 } else { return 0 } }",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int { if !false { return 42 } else { return 0 } }",
            42,
        )
        self._compile_and_run(
            "fn main() -> Int { if !true { return 0 } else { return 42 } }",
            42,
        )

    def test_generated_c23_executes_checked_arithmetic(self):
        cases = (
            ("fn main() -> Int { return 1 + 2 * 3 }", 7),
            ("fn main() -> Int { return 5 - 8 }", -3),
            ("fn main() -> Int { return -7 / 3 }", -2),
            ("fn main() -> Int { return 24 / 6 + 2 }", 6),
            ("fn main() -> Int { return 0 - 9223372036854775807 - 1 }", -9223372036854775808),
            ("fn main() -> Int { return (0 - 9223372036854775807) * -1 }", 9223372036854775807),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                self._compile_and_run(source, expected)

    def _compile_and_expect_runtime_error(self, source, expected_code):
        reference = self._run_reference(source)
        self.assertNotEqual(reference.returncode, 0, reference.stdout + reference.stderr)
        self.assertIn(expected_code, reference.stdout + reference.stderr)
        emitted = self._emit(source)
        self.assertEqual(scalar(emitted["status"]), "emitted", emitted)
        c_source = "".join(scalar(part) for part in emitted["sourceParts"]["value"])
        c_path = BUILD / "generated-error.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        for compiler in (CLANG, GCC):
            with self.subTest(compiler=compiler.name, source=source):
                exe = BUILD / (compiler.stem + "-error.exe")
                built = subprocess.run(
                    [str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
                     "-O2", str(c_path), "-o", str(exe)],
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                ran = subprocess.run([str(exe)], text=True, capture_output=True, check=False)
                self.assertNotEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                self.assertEqual(ran.returncode, reference.returncode)
                self.assertEqual(ran.stderr.strip(), expected_code)

    def test_arithmetic_errors_match_pep_runtime_codes(self):
        cases = (
            ("fn main() -> Int { return 9223372036854775807 + 1 }", "PEP_RUNTIME_OVERFLOW"),
            ("fn main() -> Int { return 0 - 9223372036854775807 - 2 }", "PEP_RUNTIME_OVERFLOW"),
            ("fn main() -> Int { return 9223372036854775807 * 2 }", "PEP_RUNTIME_OVERFLOW"),
            ("fn main() -> Int { return (0 - 9223372036854775807 - 1) * -1 }", "PEP_RUNTIME_OVERFLOW"),
            ("fn main() -> Int { return 1 / 0 }", "PEP_RUNTIME_DIVISION_BY_ZERO"),
            ("fn main() -> Int { return (0 - 9223372036854775807 - 1) / -1 }", "PEP_RUNTIME_OVERFLOW"),
            ("fn main() -> Int { return -(0 - 9223372036854775807 - 1) }", "PEP_RUNTIME_OVERFLOW"),
            ("fn main() -> Int { return fail() }\nfn fail() -> Int { return 1 / 0 }", "PEP_RUNTIME_DIVISION_BY_ZERO"),
            ("fn main() -> Int {\n  let first = 1 / 0\n  let second = 9223372036854775807 + 1\n  return first + second\n}",
             "PEP_RUNTIME_DIVISION_BY_ZERO"),
        )
        for source, expected_code in cases:
            with self.subTest(source=source):
                self._compile_and_expect_runtime_error(source, expected_code)

    def test_recursive_native_calls_enforce_pep_depth(self):
        recursive_source = (
            "fn main() -> Int { return countdown({DEPTH}) }\n"
            "fn countdown(value: Int) -> Int {\n"
            "  if value <= 0 { return 42 } else { return countdown(value - 1) }\n"
            "}"
        )
        self._compile_and_run(recursive_source.replace("{DEPTH}", "510"), 42)
        self._compile_and_expect_runtime_error(
            recursive_source.replace("{DEPTH}", "511"),
            "PEP_RUNTIME_CALL_DEPTH",
        )

    def test_unsupported_valid_program_is_reported_without_c_output(self):
        emitted = self._emit("fn main() -> Int { return length([1, 2]) }")
        self.assertEqual(scalar(emitted["status"]), "unsupported")
        self.assertEqual(emitted["sourceParts"]["value"], [])
        self.assertNotEqual(scalar(emitted["diagnostic"]), "")
        dual_failure = self._emit(
            "fn main() -> Int { return (9223372036854775807 + 1) + (1 / 0) }"
        )
        self.assertEqual(scalar(dual_failure["status"]), "unsupported")
        self.assertEqual(dual_failure["sourceParts"]["value"], [])
        self.assertIn("evaluation order is unspecified", scalar(dual_failure["diagnostic"]))
        comparison_order_failure = self._emit(
            "fn main() -> Int { return if (1 / 1 == 1 / 1) { 1 } else { 0 } }"
        )
        self.assertEqual(scalar(comparison_order_failure["status"]), "unsupported")
        self.assertEqual(comparison_order_failure["sourceParts"]["value"], [])
        self.assertIn("evaluation order is unspecified", scalar(comparison_order_failure["diagnostic"]))
        call_order_failure = self._emit(
            "fn main() -> Int { return maybe() + (9223372036854775807 + 1) }\n"
            "fn maybe() -> Int { return 1 / 0 }"
        )
        self.assertEqual(scalar(call_order_failure["status"]), "unsupported")
        self.assertEqual(call_order_failure["sourceParts"]["value"], [])
        self.assertIn("evaluation order is unspecified", scalar(call_order_failure["diagnostic"]))
        two_argument_failures = self._emit(
            "fn main() -> Int { return combine(1 / 0, 2 / 0) }\n"
            "fn combine(left: Int, right: Int) -> Int { return left }"
        )
        self.assertEqual(scalar(two_argument_failures["status"]), "unsupported")
        self.assertEqual(two_argument_failures["sourceParts"]["value"], [])
        self.assertIn("two fallible call arguments", scalar(two_argument_failures["diagnostic"]))
        parameterized_main = self._emit("fn main(value: Int) -> Int { return value }")
        self.assertEqual(scalar(parameterized_main["status"]), "unsupported")
        self.assertEqual(parameterized_main["sourceParts"]["value"], [])
        self.assertIn("functions require zero to two Int parameters", scalar(parameterized_main["diagnostic"]))
        conditional_parameterized_main = self._emit(
            "fn main(flag: Bool) -> Int { if flag { return 1 } else { return 0 } }"
        )
        self.assertEqual(scalar(conditional_parameterized_main["status"]), "unsupported")
        self.assertEqual(conditional_parameterized_main["sourceParts"]["value"], [])
        conditional_non_int_helper = self._emit(
            'fn main() -> Int { return helper() }\n'
            'fn helper() -> Str { if true { return "yes" } else { return "no" } }'
        )
        self.assertEqual(scalar(conditional_non_int_helper["status"]), "unsupported")
        self.assertEqual(conditional_non_int_helper["sourceParts"]["value"], [])
        local_return_call = self._emit(
            "fn main() -> Int { return maybe() }\n"
            "fn maybe() -> Int {\n  let seed = 0\n  return 1 / seed\n}"
        )
        self.assertEqual(scalar(local_return_call["status"]), "unsupported")
        self.assertEqual(local_return_call["sourceParts"]["value"], [])

    def test_recursive_call_is_rejected_before_native_lowering(self):
        emitted = self._emit(
            "fn main() -> Int { return loop() } fn loop() -> Int { return loop() }"
        )
        self.assertEqual(scalar(emitted["status"]), "unsupported")
        self.assertEqual(emitted["sourceParts"]["value"], [])
        self.assertIn("recursive calls are unsupported", scalar(emitted["diagnostic"]))
        parameter_recursive = self._emit(
            "fn main() -> Int { return loop(2) }\n"
            "fn loop(value: Int) -> Int { return loop(value) }"
        )
        self.assertEqual(scalar(parameter_recursive["status"]), "unsupported")
        self.assertEqual(parameter_recursive["sourceParts"]["value"], [])

    def test_checker_invalid_program_is_not_emitted(self):
        emitted = self._emit("fn main() -> Int { return true }")
        self.assertEqual(scalar(emitted["status"]), "unsupported")
        self.assertEqual(emitted["sourceParts"]["value"], [])
        self.assertIn("valid Pep checker report", scalar(emitted["diagnostic"]))


if __name__ == "__main__":
    unittest.main()
