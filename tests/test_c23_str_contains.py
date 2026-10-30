import json
import pathlib
import re
import subprocess
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")
GCC = pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe")


class PepC23StrContainsTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
            cwd=ROOT, text=True, capture_output=True, check=False)

    def test_native_str_contains_matches_length_tagged_byte_semantics(self):
        source_text = (
            "fn has(haystack: Str, needle: Str) -> Bool {\n"
            "  return str_contains(haystack, needle)\n"
            "}\n"
            "fn relay(haystack: Str, needle: Str) -> Bool {\n"
            "  return has(haystack, needle)\n"
            "}\n"
            "fn main() -> Int { return 0 }\n")
        reference_text = source_text + (
            "fn bool_int(value: Bool) -> Int {\n"
            "  if value { return 1 } else { return 0 }\n"
            "}\n"
            'say(int_text(bool_int(str_contains("abc", "b"))))\n'
            'say(int_text(bool_int(str_contains("abc", "z"))))\n'
            'say(int_text(bool_int(str_contains("abc", ""))))\n'
            'say(int_text(bool_int(str_contains("", ""))))\n'
            'say(int_text(bool_int(str_contains("", "a"))))\n'
            'say(int_text(bool_int(str_contains("x\\0y", "\\0y"))))\n'
            'say(int_text(bool_int(str_contains("café", "é"))))\n'
            'say(int_text(bool_int(str_contains("abc", "abcd"))))\n')

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "str-contains.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertIn(checked.returncode, (0, 1), checked.stdout + checked.stderr)
            report = json.loads(checked.stdout)
            if report.get("status") == "invalid" and any(
                    item.get("code") == "PEP_UNKNOWN_FUNCTION" and
                    "str_contains" in item.get("message", "")
                    for item in report.get("diagnostics", [])):
                self.skipTest("the bundled checker predates Agent 1's str_contains contract")
            self.assertEqual(report.get("status"), "valid", checked.stdout)

            interpreted_source = folder / "str-contains-reference.pep"
            interpreted_source.write_text(reference_text, encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", interpreted_source)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "1\n0\n1\n1\n0\n1\n1\n0\n")

            generated = emit(source.read_bytes())
            self.assertIn("typedef struct { const unsigned char *data; size_t length; } pep_str;",
                          generated)
            self.assertIn("PEP_RUNTIME_INVALID_STR", generated)
            declarations = re.findall(
                r"_Bool pep_fn_(\d+)\(pep_str pep_arg_(\d+), pep_str pep_arg_(\d+)\);",
                generated)
            self.assertEqual(len(declarations), 2, generated)
            contains_id, contains_haystack_id, contains_needle_id = declarations[0]
            function_id, haystack_id, needle_id = declarations[1]
            self.assertIn(
                f"pep_str_contains(pep_arg_{contains_haystack_id}, pep_arg_{contains_needle_id})",
                generated)
            self.assertIn(
                f"pep_fn_{contains_id}(pep_arg_{haystack_id}, pep_arg_{needle_id})",
                generated)

            equality_source = folder / "str-equality.pep"
            equality_source.write_text(
                "fn equal(left: Str, right: Str) -> Bool { return left == right }\n"
                "fn main() -> Int { return 0 }\n",
                encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(
                    ValueError, "Str comparison and binary operations are not yet lowered"):
                emit(equality_source.read_bytes())

            generated_path = folder / "generated.c"
            harness_path = folder / "harness.c"
            harness_path.write_text(
                "#include <stddef.h>\n"
                "#include <stdio.h>\n"
                "#include <stdint.h>\n"
                "#define main pep_generated_main\n"
                '#include "generated.c"\n'
                "#undef main\n"
                "int main(int argc, char **argv) {\n"
                "  static const unsigned char ascii[] = {97, 98, 99};\n"
                "  static const unsigned char absent[] = {122};\n"
                "  static const unsigned char embedded[] = {120, 0, 121};\n"
                "  static const unsigned char nul_tail[] = {0, 121};\n"
                "  static const unsigned char unicode[] = {99, 97, 102, 195, 169};\n"
                "  static const unsigned char accented[] = {195, 169};\n"
                f"  const pep_str empty = {{ NULL, 0 }};\n"
                "  static const unsigned char longer[] = {97, 98, 99, 100};\n"
                "  if (argc > 1) { (void)pep_str_contains((pep_str){NULL, 1}, empty); }\n"
                f"  printf(\"%d\\n%d\\n%d\\n%d\\n%d\\n%d\\n%d\\n%d\\n\", "
                f"pep_fn_{function_id}((pep_str){{ascii, sizeof ascii}}, (pep_str){{ascii + 1, 1}}), "
                f"pep_fn_{function_id}((pep_str){{ascii, sizeof ascii}}, (pep_str){{absent, sizeof absent}}), "
                f"pep_fn_{function_id}((pep_str){{ascii, sizeof ascii}}, empty), "
                f"pep_fn_{function_id}(empty, empty), "
                f"pep_fn_{function_id}(empty, (pep_str){{ascii, 1}}), "
                f"pep_fn_{function_id}((pep_str){{embedded, sizeof embedded}}, (pep_str){{nul_tail, sizeof nul_tail}}), "
                f"pep_fn_{function_id}((pep_str){{unicode, sizeof unicode}}, (pep_str){{accented, sizeof accented}}), "
                f"pep_fn_{function_id}((pep_str){{ascii, sizeof ascii}}, (pep_str){{longer, sizeof longer}}));\n"
                "  (void)argv;\n"
                "  return 0;\n"
                "}\n", encoding="utf-8", newline="\n")
            generated_path.write_text(generated, encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"str-contains-{compiler.stem}.exe"
                    compiled = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", str(harness_path),
                         "-o", str(executable)],
                        cwd=folder, text=True, capture_output=True, check=False)
                    self.assertEqual(compiled.returncode, 0,
                                     compiled.stdout + compiled.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=folder, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "1\n0\n1\n1\n0\n1\n1\n0\n")
                    invalid = subprocess.run(
                        [str(executable), "invalid"], cwd=folder, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(invalid.returncode, 1)
                    self.assertEqual(invalid.stdout, "")
                    self.assertEqual(invalid.stderr, "PEP_RUNTIME_INVALID_STR\n")

    def test_native_string_literals_and_immutable_locals_preserve_source_bytes(self):
        source_text = r'''fn empty_literals() -> Bool {
  return str_contains("", "")
}
fn embedded_nul_literal() -> Bool {
  return str_contains("x\0y", "\0y")
}
fn utf8_and_escaped_literal() -> Bool {
  let value = "café\t\"\\"
  return str_contains(value, "é\t\"\\")
}
fn main() -> Int { return 0 }
'''
        reference_text = source_text + r'''fn bool_int(value: Bool) -> Int {
  if value { return 1 } else { return 0 }
}
say(int_text(bool_int(empty_literals())))
say(int_text(bool_int(embedded_nul_literal())))
say(int_text(bool_int(utf8_and_escaped_literal())))
'''
        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "str-literals.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertIn(checked.returncode, (0, 1), checked.stdout + checked.stderr)
            report = json.loads(checked.stdout)
            if report.get("status") == "invalid" and any(
                    item.get("code") == "PEP_UNKNOWN_FUNCTION" and
                    "str_contains" in item.get("message", "")
                    for item in report.get("diagnostics", [])):
                self.skipTest("the bundled checker predates Agent 1's str_contains contract")
            self.assertEqual(report.get("status"), "valid", checked.stdout)

            interpreted_source = folder / "str-literals-reference.pep"
            interpreted_source.write_text(reference_text, encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", interpreted_source)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "1\n1\n1\n")

            generated = emit(source.read_bytes())
            self.assertEqual(generated.count("pep_str pep_local_"), 1, generated)
            self.assertIn(".data = (const unsigned char[]){ 195, 169, 9, 34, 92 }", generated)
            self.assertIn(".length = 0", generated)
            ids = re.findall(r"_Bool pep_fn_(\d+)\(void\);", generated)
            self.assertEqual(len(ids), 3, generated)

            generated_path = folder / "generated.c"
            harness_path = folder / "harness.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            harness_path.write_text(
                "#include <stddef.h>\n#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n#include \"generated.c\"\n#undef main\n"
                "int main(void) {\n"
                f"  printf(\"%d\\n%d\\n%d\\n\", pep_fn_{ids[0]}(), pep_fn_{ids[1]}(), pep_fn_{ids[2]}());\n"
                "  return 0;\n}\n",
                encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"str-literals-{compiler.stem}.exe"
                    compiled = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", str(harness_path),
                         "-o", str(executable)],
                        cwd=folder, text=True, capture_output=True, check=False)
                    self.assertEqual(compiled.returncode, 0,
                                     compiled.stdout + compiled.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=folder, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "1\n1\n1\n")

            mutable_source = folder / "str-mutable-local.pep"
            mutable_source.write_text(
                'fn main() -> Int {\n  var text: Str = "x"\n  return 0\n}\n',
                encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(
                    ValueError, "Pep C23 mutable Str local bindings are not yet lowered"):
                emit(mutable_source.read_bytes())

    def test_native_str_contains_reads_record_fields_through_helpers(self):
        source_text = (
            "type TextBox { value: Str }\n"
            "fn has_fields(haystack: TextBox, needle: TextBox) -> Bool {\n"
            "  return str_contains(haystack.value, needle.value)\n"
            "}\n"
            "fn wrap_and_check(haystack: Str, needle: Str) -> Bool {\n"
            "  let left = TextBox { value: haystack }\n"
            "  let right = TextBox { value: needle }\n"
            "  return has_fields(left, right)\n"
            "}\n"
            "fn main() -> Int { return 0 }\n")
        reference_text = source_text + (
            "fn bool_int(value: Bool) -> Int {\n"
            "  if value { return 1 } else { return 0 }\n"
            "}\n"
            'say(int_text(bool_int(str_contains("abc", "b"))))\n'
            'say(int_text(bool_int(str_contains("x\\0y", "\\0y"))))\n'
            'say(int_text(bool_int(str_contains("", "x"))))\n')

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "str-records.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            checked = self.invoke("check", source, "--json")
            self.assertIn(checked.returncode, (0, 1), checked.stdout + checked.stderr)
            report = json.loads(checked.stdout)
            if report.get("status") == "invalid" and any(
                    item.get("code") == "PEP_UNKNOWN_FUNCTION" and
                    "str_contains" in item.get("message", "")
                    for item in report.get("diagnostics", [])):
                self.skipTest("the bundled checker predates Agent 1's str_contains contract")
            self.assertEqual(report.get("status"), "valid", checked.stdout)

            interpreted_source = folder / "str-records-reference.pep"
            interpreted_source.write_text(reference_text, encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", interpreted_source)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "1\n1\n0\n")

            generated = emit(source.read_bytes())
            self.assertRegex(generated,
                             r"typedef struct \{ pep_str pep_field_0; \} pep_record_\d+;")
            self.assertRegex(generated,
                             r"pep_arg_\d+\.pep_field_0")
            self.assertIn("pep_str_contains(", generated)
            wrapper = re.search(
                r"_Bool pep_fn_(\d+)\(pep_str pep_arg_(\d+), pep_str pep_arg_(\d+)\);",
                generated)
            self.assertIsNotNone(wrapper, generated)
            function_id = wrapper.group(1)

            generated_path = folder / "generated.c"
            harness_path = folder / "harness.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            harness_path.write_text(
                "#include <stddef.h>\n#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n#include \"generated.c\"\n#undef main\n"
                "int main(void) {\n"
                "  static const unsigned char ascii[] = {97, 98, 99};\n"
                "  static const unsigned char needle[] = {98};\n"
                "  static const unsigned char embedded[] = {120, 0, 121};\n"
                "  static const unsigned char nul_tail[] = {0, 121};\n"
                "  const pep_str empty = {NULL, 0};\n"
                f"  printf(\"%d\\n%d\\n%d\\n\", pep_fn_{function_id}((pep_str){{ascii, sizeof ascii}}, (pep_str){{needle, sizeof needle}}), "
                f"pep_fn_{function_id}((pep_str){{embedded, sizeof embedded}}, (pep_str){{nul_tail, sizeof nul_tail}}), "
                f"pep_fn_{function_id}(empty, (pep_str){{needle, sizeof needle}}));\n"
                "  return 0;\n}\n",
                encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"str-records-{compiler.stem}.exe"
                    compiled = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", str(harness_path),
                         "-o", str(executable)],
                        cwd=folder, text=True, capture_output=True, check=False)
                    self.assertEqual(compiled.returncode, 0,
                                     compiled.stdout + compiled.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=folder, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "1\n1\n0\n")


    def test_boolean_helper_calls_preserve_short_circuit_under_clang_and_gcc(self):
        source_text = """fn identity(value: Bool) -> Bool { return value }
fn bomb() -> Bool {
  return if 1 / 0 == 0 { true } else { false }
}
fn combine(value: Bool) -> Bool {
  return identity(value) == true && bomb() || identity(true) == true || bomb()
}
fn main() -> Int {
  return if combine(false) { 0 } else { 1 }
}
"""
        reference_text = source_text + "say(int_text(main()))\n"
        execute_rhs_text = source_text + "say(int_text(if combine(true) { 1 } else { 0 }))\n"

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "boolean-short-circuit.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "boolean-short-circuit-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            execute_rhs_reference = folder / "boolean-rhs-executes-reference.pep"
            execute_rhs_reference.write_text(execute_rhs_text, encoding="utf-8", newline="\n")
            interpreted_trap = self.invoke("run", execute_rhs_reference)
            self.assertNotEqual(interpreted_trap.returncode, 0,
                                interpreted_trap.stdout + interpreted_trap.stderr)
            self.assertEqual(interpreted_trap.stdout, "")
            self.assertIn("PEP_RUNTIME_DIVISION_BY_ZERO", interpreted_trap.stderr)

            generated = emit(source.read_bytes())
            self.assertIn(" && ", generated)
            self.assertIn(" || ", generated)
            self.assertIn("PEP_RUNTIME_DIVISION_BY_ZERO", generated)
            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            main_match = re.search(r"int64_t pep_fn_(\d+)\(void\);", generated)
            self.assertIsNotNone(main_match, generated)
            bool_parameter_ids = re.findall(
                r"_Bool pep_fn_(\d+)\(_Bool pep_arg_\d+\);", generated)
            self.assertEqual(len(bool_parameter_ids), 2, generated)
            harness_path = folder / "boolean-short-circuit-harness.c"
            harness_path.write_text(
                "#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n#include \"generated.c\"\n#undef main\n"
                "int main(int argc, char **argv) {\n"
                "  (void)argv;\n"
                f"  if (argc > 1) (void)pep_fn_{bool_parameter_ids[1]}(1);\n"
                f"  printf(\"%lld\\n\", (long long)pep_fn_{main_match.group(1)}());\n"
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"boolean-short-circuit-{compiler.stem}.exe"
                    compiled = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", str(harness_path),
                         "-o", str(executable)],
                        cwd=folder, text=True, capture_output=True, check=False)
                    self.assertEqual(compiled.returncode, 0,
                                     compiled.stdout + compiled.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=folder, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, interpreted.stdout)

                    trap = subprocess.run(
                        [str(executable), "execute-rhs"], cwd=folder,
                        text=True, capture_output=True, check=False)
                    self.assertNotEqual(trap.returncode, 0,
                                        trap.stdout + trap.stderr)
                    self.assertEqual(trap.returncode, interpreted_trap.returncode)
                    self.assertEqual(trap.stdout, interpreted_trap.stdout)
                    self.assertIn("PEP_RUNTIME_DIVISION_BY_ZERO", trap.stderr)

    def test_lucy_ascii_whitespace_condition_runs_natively(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")
        condition = "byte == 32 || byte == 9 || byte == 13 || byte == 10"
        self.assertIn(f"if {condition} {{", lexer)
        source_text = (
            "fn is_ascii_space(byte: Int) -> Bool { return " + condition + " }\n"
            "fn main() -> Int { return 0 }\n")
        values = (32, 9, 13, 10, 65, 0)
        expected = "1\n1\n1\n1\n0\n0\n"
        reference_text = source_text + "".join(
            f"say(int_text(if is_ascii_space({value}) {{ 1 }} else {{ 0 }}))\n"
            for value in values)

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-ascii-space.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "lucy-ascii-space-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, expected)

            generated = emit(source.read_bytes())
            predicate = re.search(
                r"_Bool pep_fn_(\d+)\(int64_t pep_arg_\d+\);", generated)
            self.assertIsNotNone(predicate, generated)
            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            harness_path = folder / "lucy-ascii-space-harness.c"
            call_ids = ", ".join(
                f"pep_fn_{predicate.group(1)}({value})" for value in values)
            harness_path.write_text(
                "#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n#include \"generated.c\"\n#undef main\n"
                "int main(void) {\n"
                f"  printf(\"%d\\n%d\\n%d\\n%d\\n%d\\n%d\\n\", {call_ids});\n"
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"lucy-ascii-space-{compiler.stem}.exe"
                    compiled = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", str(harness_path),
                         "-o", str(executable)],
                        cwd=folder, text=True, capture_output=True, check=False)
                    self.assertEqual(compiled.returncode, 0,
                                     compiled.stdout + compiled.stderr)
                    native = subprocess.run(
                        [str(executable)], cwd=folder, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(native.returncode, 0,
                                     native.stdout + native.stderr)
                    self.assertEqual(native.stdout, interpreted.stdout)

    def test_boolean_comparison_with_two_fallible_calls_fails_closed(self):
        source_text = """fn left() -> Bool { return true }
fn right() -> Bool { return true }
fn combined() -> Bool { return left() == right() && true }
fn main() -> Int { return 0 }
"""
        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "unordered-bool-calls.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            with self.assertRaisesRegex(ValueError, "two fallible operands"):
                emit(source.read_bytes())

if __name__ == "__main__":
    unittest.main()
