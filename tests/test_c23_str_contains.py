import hashlib
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

    def test_native_str_equality_is_length_tagged_and_byte_exact(self):
        source_text = """fn equal(left: Str, right: Str) -> Bool {
  return left == right
}
fn relay(left: Str, right: Str) -> Bool {
  return equal(left, right)
}
fn different(left: Str, right: Str) -> Bool {
  return left != right
}
fn main() -> Int { return 0 }
"""
        reference_text = source_text + """fn bool_int(value: Bool) -> Int {
  if value { return 1 } else { return 0 }
}
say(int_text(bool_int(equal("", ""))))
say(int_text(bool_int(equal("abc", "ab"))))
say(int_text(bool_int(relay("x\\0y", "x\\0y"))))
say(int_text(bool_int(equal("x\\0y", "y"))))
say(int_text(bool_int(equal("café", "café"))))
say(int_text(bool_int(equal("café", "café"))))
say(int_text(bool_int(different("café", "café"))))
"""
        expected = "1\n0\n1\n0\n1\n0\n1\n"

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "str-equality.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "str-equality-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, expected)

            generated = emit(source.read_bytes())
            self.assertIn("static _Bool pep_str_equal(pep_str left, pep_str right)", generated)
            self.assertIn("PEP_RUNTIME_INVALID_STR", generated)
            declarations = re.findall(
                r"_Bool pep_fn_(\d+)\(pep_str pep_arg_\d+, pep_str pep_arg_\d+\);",
                generated)
            self.assertEqual(len(declarations), 3, generated)
            equal_id, relay_id, different_id = declarations
            self.assertIn(f"pep_str_equal(pep_arg_", generated)
            self.assertIn(f"pep_fn_{equal_id}(pep_arg_", generated)

            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            harness_path = folder / "str-equality-harness.c"
            harness_path.write_text(
                "#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n"
                '#include "generated.c"\n'
                "#undef main\n"
                "int main(int argc, char **argv) {\n"
                "  (void)argv;\n"
                "  static const unsigned char abc[] = {97, 98, 99};\n"
                "  static const unsigned char ab[] = {97, 98};\n"
                "  static const unsigned char embedded[] = {120, 0, 121};\n"
                "  static const unsigned char y[] = {121};\n"
                "  static const unsigned char cafe_nfc[] = {99, 97, 102, 195, 169};\n"
                "  static const unsigned char cafe_nfd[] = {99, 97, 102, 101, 204, 129};\n"
                "  if (argc > 1) {\n"
                f"    (void)pep_fn_{equal_id}((pep_str){{NULL, 1}}, (pep_str){{NULL, 0}});\n"
                "    return 0;\n"
                "  }\n"
                f'  printf("%d\\n%d\\n%d\\n%d\\n%d\\n%d\\n%d\\n", '
                f"pep_fn_{equal_id}((pep_str){{NULL, 0}}, (pep_str){{NULL, 0}}), "
                f"pep_fn_{equal_id}((pep_str){{abc, sizeof abc}}, (pep_str){{ab, sizeof ab}}), "
                f"pep_fn_{relay_id}((pep_str){{embedded, sizeof embedded}}, (pep_str){{embedded, sizeof embedded}}), "
                f"pep_fn_{equal_id}((pep_str){{embedded, sizeof embedded}}, (pep_str){{y, sizeof y}}), "
                f"pep_fn_{equal_id}((pep_str){{cafe_nfc, sizeof cafe_nfc}}, (pep_str){{cafe_nfc, sizeof cafe_nfc}}), "
                f"pep_fn_{equal_id}((pep_str){{cafe_nfc, sizeof cafe_nfc}}, (pep_str){{cafe_nfd, sizeof cafe_nfd}}), "
                f"pep_fn_{different_id}((pep_str){{cafe_nfc, sizeof cafe_nfc}}, (pep_str){{cafe_nfd, sizeof cafe_nfd}}));\n"
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"str-equality-{compiler.stem}.exe"
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

                    malformed = subprocess.run(
                        [str(executable), "malformed"], cwd=folder, text=True,
                        capture_output=True, check=False)
                    self.assertNotEqual(malformed.returncode, 0)
                    self.assertEqual(malformed.stdout, "")
                    self.assertIn("PEP_RUNTIME_INVALID_STR", malformed.stderr)

    def test_lucy_stage_string_conditions_compose_natively(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")
        self.assertIn(
            'if cursor.stage == "validate" && cursor.mode != "" {', lexer)
        self.assertIn(
            'if cursor.stage == "done" || cursor.stage == "error" {', lexer)
        source_text = """fn requires_validate(stage: Str, mode: Str) -> Bool {
  return stage == "validate" && mode != ""
}
fn is_terminal(stage: Str) -> Bool {
  return stage == "done" || stage == "error"
}
fn main() -> Int { return 0 }
"""
        reference_text = source_text + """fn bool_int(value: Bool) -> Int {
  if value { return 1 } else { return 0 }
}
say(int_text(bool_int(requires_validate("validate", "scan"))))
say(int_text(bool_int(requires_validate("validate", ""))))
say(int_text(bool_int(requires_validate("scan", "scan"))))
say(int_text(bool_int(is_terminal("done"))))
say(int_text(bool_int(is_terminal("error"))))
say(int_text(bool_int(is_terminal("validate"))))
"""
        expected = "1\n0\n0\n1\n1\n0\n"

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-stage-conditions.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "lucy-stage-conditions-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, expected)

            generated = emit(source.read_bytes())
            declarations = re.findall(
                r"_Bool pep_fn_(\d+)\(pep_str pep_arg_\d+, pep_str pep_arg_\d+\);",
                generated)
            terminal = re.search(
                r"_Bool pep_fn_(\d+)\(pep_str pep_arg_\d+\);", generated)
            self.assertEqual(len(declarations), 1, generated)
            self.assertIsNotNone(terminal, generated)
            self.assertIn(" && ", generated)
            self.assertIn(" || ", generated)

            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            harness_path = folder / "lucy-stage-conditions-harness.c"
            harness_path.write_text(
                "#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n"
                '#include "generated.c"\n'
                "#undef main\n"
                "int main(void) {\n"
                "  static const unsigned char validate[] = {118, 97, 108, 105, 100, 97, 116, 101};\n"
                "  static const unsigned char scan[] = {115, 99, 97, 110};\n"
                "  static const unsigned char done[] = {100, 111, 110, 101};\n"
                "  static const unsigned char error[] = {101, 114, 114, 111, 114};\n"
                f'  printf("%d\\n%d\\n%d\\n%d\\n%d\\n%d\\n", '
                f"pep_fn_{declarations[0][0]}((pep_str){{validate, sizeof validate}}, (pep_str){{scan, sizeof scan}}), "
                f"pep_fn_{declarations[0][0]}((pep_str){{validate, sizeof validate}}, (pep_str){{NULL, 0}}), "
                f"pep_fn_{declarations[0][0]}((pep_str){{scan, sizeof scan}}, (pep_str){{scan, sizeof scan}}), "
                f"pep_fn_{terminal.group(1)}((pep_str){{done, sizeof done}}), "
                f"pep_fn_{terminal.group(1)}((pep_str){{error, sizeof error}}), "
                f"pep_fn_{terminal.group(1)}((pep_str){{validate, sizeof validate}}));\n"
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"lucy-stage-conditions-{compiler.stem}.exe"
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

    def test_lucy_cursor_record_string_conditions_lower_natively(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")
        self.assertIn('if cursor.stage == "validate" && cursor.mode != "" {', lexer)
        self.assertIn('if cursor.stage == "done" || cursor.stage == "error" {', lexer)
        source_text = """type LexState { stage: Str, mode: Str }
fn should_validate(cursor: LexState) -> Bool {
  return cursor.stage == "validate" && cursor.mode != ""
}
fn is_terminal(cursor: LexState) -> Bool {
  return cursor.stage == "done" || cursor.stage == "error"
}
fn main() -> Int { return 0 }
"""
        reference_text = source_text + """fn bool_int(value: Bool) -> Int {
  if value { return 1 } else { return 0 }
}
say(int_text(bool_int(should_validate(LexState { stage: "validate", mode: "scan" }))))
say(int_text(bool_int(should_validate(LexState { stage: "validate", mode: "" }))))
say(int_text(bool_int(should_validate(LexState { stage: "scan", mode: "scan" }))))
say(int_text(bool_int(is_terminal(LexState { stage: "done", mode: "" }))))
say(int_text(bool_int(is_terminal(LexState { stage: "error", mode: "" }))))
say(int_text(bool_int(is_terminal(LexState { stage: "validate", mode: "scan" }))))
"""
        expected = "1\n0\n0\n1\n1\n0\n"

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-cursor-string-conditions.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "lucy-cursor-string-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, expected)

            generated = emit(source.read_bytes())
            record = re.search(
                r"typedef struct \{(.*?)\} pep_record_(\d+);", generated, re.DOTALL)
            self.assertIsNotNone(record, generated)
            self.assertIn("pep_str pep_field_0;", record.group(1))
            self.assertIn("pep_str pep_field_1;", record.group(1))
            declarations = re.findall(
                r"_Bool pep_fn_(\d+)\(pep_record_(\d+) pep_arg_\d+\);", generated)
            self.assertEqual(len(declarations), 2, generated)
            validate_id, record_id = declarations[0]
            terminal_id, terminal_record_id = declarations[1]
            self.assertEqual(record_id, terminal_record_id)

            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            harness_path = folder / "lucy-cursor-string-harness.c"
            harness_path.write_text(
                "#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n"
                '#include "generated.c"\n'
                "#undef main\n"
                "int main(void) {\n"
                "  static const unsigned char validate[] = {118, 97, 108, 105, 100, 97, 116, 101};\n"
                "  static const unsigned char scan[] = {115, 99, 97, 110};\n"
                "  static const unsigned char done[] = {100, 111, 110, 101};\n"
                "  static const unsigned char error[] = {101, 114, 114, 111, 114};\n"
                f"  pep_record_{record_id} active = {{ .pep_field_0 = {{ validate, sizeof validate }}, .pep_field_1 = {{ scan, sizeof scan }} }};\n"
                f"  pep_record_{record_id} no_mode = {{ .pep_field_0 = {{ validate, sizeof validate }}, .pep_field_1 = {{ NULL, 0 }} }};\n"
                f"  pep_record_{record_id} scanning = {{ .pep_field_0 = {{ scan, sizeof scan }}, .pep_field_1 = {{ scan, sizeof scan }} }};\n"
                f"  pep_record_{record_id} completed = {{ .pep_field_0 = {{ done, sizeof done }}, .pep_field_1 = {{ NULL, 0 }} }};\n"
                f"  pep_record_{record_id} failed = {{ .pep_field_0 = {{ error, sizeof error }}, .pep_field_1 = {{ NULL, 0 }} }};\n"
                "  printf(\"%d\\n%d\\n%d\\n%d\\n%d\\n%d\\n\", "
                f"pep_fn_{validate_id}(active), pep_fn_{validate_id}(no_mode), pep_fn_{validate_id}(scanning), "
                f"pep_fn_{terminal_id}(completed), pep_fn_{terminal_id}(failed), pep_fn_{terminal_id}(active));\n"
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"lucy-cursor-string-{compiler.stem}.exe"
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

    def test_lucy_operator_pair_condition_runs_natively(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")
        condition = (
            "(byte == 60 && next == 61) || "
            "(byte == 61 && (next == 61 || next == 62)) || "
            "(byte == 33 && next == 61)")
        self.assertIn("(byte == 60 && next == 61) ||", lexer)
        self.assertIn("(byte == 61 && (next == 61 || next == 62)) ||", lexer)
        self.assertIn("(byte == 33 && next == 61) ||", lexer)
        source_text = (
            "fn is_operator_pair(byte: Int, next: Int) -> Bool { return "
            + condition + " }\n"
            "fn main() -> Int { return 0 }\n")
        pairs = ((60, 61), (61, 61), (61, 62), (33, 61), (38, 38),
                 (124, 124), (45, 62), (60, 60), (38, 65), (124, 1240),
                 (45, 0), (0, 0))
        expected = "".join(
            "1\n" if (left, right) in {
                (60, 61), (61, 61), (61, 62), (33, 61)} else "0\n"
            for left, right in pairs)
        reference_text = source_text + "".join(
            f"say(int_text(if is_operator_pair({left}, {right}) {{ 1 }} else {{ 0 }}))\n"
            for left, right in pairs)

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-operator-pair.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "lucy-operator-pair-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, expected)

            generated = emit(source.read_bytes())
            predicate = re.search(
                r"_Bool pep_fn_(\d+)\(int64_t pep_arg_\d+, int64_t pep_arg_\d+\);",
                generated)
            self.assertIsNotNone(predicate, generated)
            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            harness_path = folder / "lucy-operator-pair-harness.c"
            calls = ", ".join(
                f"pep_fn_{predicate.group(1)}({left}, {right})"
                for left, right in pairs)
            harness_path.write_text(
                "#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n#include \"generated.c\"\n#undef main\n"
                "int main(void) {\n"
                f"  printf(\"{''.join('%d\\n' for _ in pairs)}\", {calls});\n"
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"lucy-operator-pair-{compiler.stem}.exe"
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

    def test_lucy_ascii_identifier_predicates_compose_natively(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")
        source_functions = """fn ascii_letter(byte: Int) -> Bool {
  return (65 <= byte && byte <= 90) || (97 <= byte && byte <= 122) || byte == 95
}

fn ascii_digit(byte: Int) -> Bool {
  return 48 <= byte && byte <= 57
}

fn ascii_continue(byte: Int) -> Bool {
  return ascii_letter(byte) || ascii_digit(byte)
}
"""
        for fragment in (
                "return (65 <= byte && byte <= 90) || "
                "(97 <= byte && byte <= 122) || byte == 95",
                "return 48 <= byte && byte <= 57",
                "return ascii_letter(byte) || ascii_digit(byte)"):
            self.assertIn(fragment, lexer)
        source_text = source_functions + "fn main() -> Int { return 0 }\n"
        values = (65, 90, 97, 122, 95, 48, 57, 64, 96, 128, 0)
        expected = "".join(
            f"{1 if (65 <= value <= 90 or 97 <= value <= 122 or value == 95 or 48 <= value <= 57) else 0}\n"
            for value in values)
        reference_text = source_text + "".join(
            f"say(int_text(if ascii_continue({value}) {{ 1 }} else {{ 0 }}))\n"
            for value in values)

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-ascii-continue.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "lucy-ascii-continue-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, expected)

            generated = emit(source.read_bytes())
            self.assertIn(" || ", generated)
            functions = re.findall(
                r"_Bool pep_fn_(\d+)\(int64_t pep_arg_\d+\);", generated)
            self.assertEqual(len(functions), 3, generated)
            continue_function = functions[-1]
            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            harness_path = folder / "lucy-ascii-continue-harness.c"
            calls = ", ".join(
                f"pep_fn_{continue_function}({value})" for value in values)
            format_string = "\\n".join("%d" for _ in values) + "\\n"
            harness_path.write_text(
                "#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n"
                '#include "generated.c"\n'
                "#undef main\n"
                "int main(void) {\n"
                f'  printf("{format_string}", {calls});\n'
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"lucy-ascii-continue-{compiler.stem}.exe"
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

    def test_lucy_guarded_ascii_digit_condition_matches_lexer_natively(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")
        self.assertIn(
            "if !(length <= offset) && ascii_digit(byte_at(source, offset)) {",
            lexer)
        source_text = """fn ascii_digit(byte: Int) -> Bool {
  return 48 <= byte && byte <= 57
}

fn available_digit_byte(length: Int, offset: Int, byte: Int) -> Int {
  return if !(length <= offset) && ascii_digit(byte) { 1 } else { 0 }
}

fn main() -> Int { return 0 }
"""
        cases = ((0, 0, 48), (1, 0, 48), (1, 0, 57), (1, 0, 47),
                 (2, 1, 56), (2, 2, 57), (3, 1, 65), (3, 1, 128))
        def is_ascii_digit(value):
            return 48 <= value <= 57
        expected = "".join(
            f"{int(length > offset and is_ascii_digit(byte))}\n"
            for length, offset, byte in cases)
        reference_text = source_text + "".join(
            f"say(int_text(available_digit_byte({length}, {offset}, {byte})))\n"
            for length, offset, byte in cases)

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-guarded-identifier.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "lucy-guarded-identifier-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, expected)

            generated = emit(source.read_bytes())
            function = re.search(
                r"int64_t pep_fn_(\d+)\(int64_t pep_arg_\d+, int64_t pep_arg_\d+, int64_t pep_arg_\d+\);",
                generated)
            self.assertIsNotNone(function, generated)
            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            calls = ", ".join(
                f"(long long)pep_fn_{function.group(1)}({length}, {offset}, {byte})"
                for length, offset, byte in cases)
            format_string = "\\n".join("%lld" for _ in cases) + "\\n"
            harness_path = folder / "lucy-guarded-identifier-harness.c"
            harness_path.write_text(
                "#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n"
                '#include "generated.c"\n'
                "#undef main\n"
                "int main(void) {\n"
                f'  printf("{format_string}", {calls});\n'
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"lucy-guarded-identifier-{compiler.stem}.exe"
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

    def test_lucy_utf8_check_boolean_ranges_lower_natively(self):
        lexer_bytes = (ROOT / "examples" / "pep_lexer.pep").read_bytes().replace(b"\r\n", b"\n")
        blob = hashlib.sha1(f"blob {len(lexer_bytes)}\0".encode("ascii") + lexer_bytes).hexdigest()
        self.assertEqual(blob, "12bd93a1dfc5dba3b1cab49abefffed5e406b17d",
                         "Lucy lexer changed; review these source-derived predicates")
        lexer = lexer_bytes.decode("utf-8")
        continuation_condition = "!(128 <= next) || !(next <= 191)"
        scalar_condition = (
            "!(minimum <= codepoint) || !(codepoint <= 1114111) || "
            "(55296 <= codepoint && codepoint <= 57343)")
        self.assertIn(f"if {continuation_condition} {{", lexer)
        self.assertIn(f"if {scalar_condition} {{", lexer)

        source_text = (
            "fn invalid_continuation(next: Int) -> Bool { return "
            + continuation_condition + " }\n"
            "fn invalid_scalar(minimum: Int, codepoint: Int) -> Bool { return "
            + scalar_condition + " }\n"
            "fn main() -> Int { return 0 }\n")
        continuation_cases = ((127, 1), (128, 0), (191, 0), (192, 1))
        scalar_cases = (
            (128, 128, 0), (2048, 2047, 1), (2048, 2048, 0),
            (0, 1114111, 0), (0, 1114112, 1), (0, 55296, 1),
            (0, 57343, 1), (0, 55295, 0), (0, 57344, 0))
        expected = "".join(
            f"{answer}\n" for _, answer in continuation_cases) + "".join(
            f"{answer}\n" for _, _, answer in scalar_cases)
        reference_text = source_text + "".join(
            f"say(int_text(if invalid_continuation({value}) {{ 1 }} else {{ 0 }}))\n"
            for value, _ in continuation_cases) + "".join(
            f"say(int_text(if invalid_scalar({minimum}, {codepoint}) "
            f"{{ 1 }} else {{ 0 }}))\n"
            for minimum, codepoint, _ in scalar_cases)

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-utf8-ranges.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "lucy-utf8-ranges-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, expected)

            generated = emit(source.read_bytes())
            continuation = re.search(
                r"_Bool pep_fn_(\d+)\(int64_t pep_arg_\d+\);", generated)
            scalar = re.search(
                r"_Bool pep_fn_(\d+)\(int64_t pep_arg_\d+, int64_t pep_arg_\d+\);",
                generated)
            self.assertIsNotNone(continuation, generated)
            self.assertIsNotNone(scalar, generated)
            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            harness_path = folder / "lucy-utf8-ranges-harness.c"
            calls = [
                *(f"  printf(\"%d\\n\", pep_fn_{continuation.group(1)}({value}));"
                  for value, _ in continuation_cases),
                *(f"  printf(\"%d\\n\", pep_fn_{scalar.group(1)}({minimum}, {codepoint}));"
                  for minimum, codepoint, _ in scalar_cases),
            ]
            harness_path.write_text(
                "#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n#include \"generated.c\"\n#undef main\n"
                "int main(void) {\n"
                + "\n".join(calls) + "\n"
                + "  return 0;\n"
                + "}\n",
                encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"lucy-utf8-ranges-{compiler.stem}.exe"
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

    def test_lucy_ascii_digit_composes_with_checked_native_byte_at(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")
        start = lexer.index("fn ascii_digit(byte: Int) -> Bool {")
        end = lexer.index("\nfn ascii_continue", start)
        ascii_digit = lexer[start:end].rstrip()
        self.assertEqual(ascii_digit,
                         "fn ascii_digit(byte: Int) -> Bool {\n"
                         "  return 48 <= byte && byte <= 57\n"
                         "}")

        source_text = (
            ascii_digit + "\n\n"
            "fn classify(source: SourceBytes, offset: Int) -> Bool {\n"
            "  return ascii_digit(byte_at(source, offset))\n"
            "}\n"
            "fn main() -> Int { return 0 }\n")
        reference_text = source_text + (
            "fn probe() -> Int {\n"
            "  if classify(source_bytes(), 0) { return 1 } else { return 0 }\n"
            "}\n")
        vectors = [
            ("nul", bytes([0]), 0),
            ("below-digit", bytes([47]), 0),
            ("zero", bytes([48]), 1),
            ("nine", bytes([57]), 1),
            ("above-digit", bytes([58]), 0),
            ("ascii-max", bytes([127]), 0),
            ("continuation", bytes([128]), 0),
            ("byte-max", bytes([255]), 0),
        ]

        def digest(raw):
            return "sha256:" + hashlib.sha256(raw).hexdigest()

        def req(op, **fields):
            return {"schemaVersion": 3, "toolProtocolVersion": 2, "op": op, **fields}

        def encoded(value):
            return {"type": "Int", "value": str(value)}

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-ascii-digit-source-bytes.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

            generated = emit(source.read_bytes())
            declaration = re.search(
                r"_Bool pep_fn_(\d+)\(pep_source_bytes pep_arg_(\d+), "
                r"int64_t pep_arg_(\d+)\);",
                generated)
            self.assertIsNotNone(declaration, generated)
            function_id = declaration.group(1)
            self.assertIn("typedef struct { const unsigned char *data; size_t length; } pep_source_bytes;",
                          generated)
            self.assertIn("pep_byte_at(pep_arg_", generated)
            self.assertIn("PEP_RUNTIME_INVALID_SOURCE_BYTES", generated)
            self.assertIn("PEP_RUNTIME_BYTE_RANGE", generated)

            reference_revision = digest(reference_text.encode("utf-8"))
            requests = [req("open", source=reference_text, name="ascii-digit-program")]
            targets = []
            for name, raw, expected in vectors:
                document = "doc-" + str(len(targets) + 2)
                targets.append((name, raw, expected, document))
                requests.append(req("open_bytes", bytes=list(raw)))
            empty_document = "doc-" + str(len(targets) + 2)
            requests.append(req("open_bytes", bytes=[]))
            requests.append(req("tool_register", tool="ascii-digit-probe",
                                document="doc-1", revision=reference_revision,
                                function="probe"))
            validate_index = len(requests)
            requests.append(req("tool_validate", tool="ascii-digit-probe",
                                document="doc-1", revision=reference_revision,
                                testVectors=[
                                    {"arguments": [], "expect": encoded(expected),
                                     "semanticTarget": {"document": document,
                                                        "revision": digest(raw),
                                                        "entryFunctions": []}}
                                    for _, raw, expected, document in targets
                                ]))
            activate_index = len(requests)
            requests.append(req("tool_activate", tool="ascii-digit-probe",
                                document="doc-1", revision=reference_revision))
            invoke_start = len(requests)
            for _, raw, _, document in targets:
                requests.append(req("tool_invoke", tool="ascii-digit-probe", arguments=[],
                                    semanticTarget={"document": document,
                                                    "revision": digest(raw),
                                                    "entryFunctions": []}))
            requests.append(req("tool_invoke", tool="ascii-digit-probe", arguments=[],
                                semanticTarget={"document": empty_document,
                                                "revision": digest(b""),
                                                "entryFunctions": []}))

            session = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(PEP), "session", "--jsonl"],
                cwd=ROOT, text=True,
                input="".join(json.dumps(item, ensure_ascii=True) + "\n" for item in requests),
                capture_output=True, check=False)
            self.assertEqual(session.returncode, 0, session.stderr)
            responses = [json.loads(line) for line in session.stdout.splitlines()]
            self.assertEqual(responses[validate_index]["status"], "Validated",
                             responses[validate_index])
            self.assertEqual(responses[activate_index]["status"], "Active",
                             responses[activate_index])
            interpreter_values = []
            for index, (_, _, expected, _) in enumerate(targets):
                response = responses[invoke_start + index]
                self.assertNotIn("error", response, response)
                result = response["result"]
                self.assertEqual(result, encoded(expected), response)
                interpreter_values.append(result["value"])
            range_error = responses[invoke_start + len(targets)]
            self.assertEqual(range_error["error"]["code"], "PEP_RUNTIME_BYTE_RANGE",
                             range_error)

            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            byte_rows = []
            calls = []
            for index, (_, raw, _) in enumerate(vectors):
                byte_rows.append(
                    f"  static const unsigned char input_{index}[] = "
                    f"{{{', '.join(str(value) for value in raw)}}};\n")
                calls.append(
                    f"  (void)printf(\"%d\\n\", pep_fn_{function_id}("
                    f"(pep_source_bytes){{input_{index}, sizeof input_{index}}}, 0));\n")
            harness = (
                "#include <stddef.h>\n#include <stdint.h>\n#include <stdio.h>\n"
                "#define main pep_generated_main\n#include \"generated.c\"\n#undef main\n"
                "int main(int argc, char **argv) {\n" +
                "".join(byte_rows) +
                "  if (argc > 1) {\n"
                f"    if (argv[1][0] == 'r') (void)pep_fn_{function_id}("
                "(pep_source_bytes){input_0, sizeof input_0}, -1);\n"
                f"    else if (argv[1][0] == 'u') (void)pep_fn_{function_id}("
                "(pep_source_bytes){input_0, sizeof input_0}, 1);\n"
                f"    else if (argv[1][0] == 'e') (void)pep_fn_{function_id}((pep_source_bytes){{NULL, 0}}, 0);\n"
                f"    else (void)pep_fn_{function_id}((pep_source_bytes){{NULL, 1}}, 0);\n"
                "    return 0;\n  }\n" +
                "".join(calls) +
                "  return 0;\n}\n")
            harness_path = folder / "lucy-ascii-digit-source-bytes-harness.c"
            harness_path.write_text(harness, encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"lucy-ascii-digit-source-bytes-{compiler.stem}.exe"
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
                    self.assertEqual(native.stdout.splitlines(), interpreter_values)
                    for invalid_case in ("range", "upper", "empty"):
                        with self.subTest(invalid_case=invalid_case):
                            bad_offset = subprocess.run(
                                [str(executable), invalid_case], cwd=folder,
                                text=True, capture_output=True, check=False)
                            self.assertNotEqual(bad_offset.returncode, 0)
                            self.assertEqual(bad_offset.stdout, "")
                            self.assertIn("PEP_RUNTIME_BYTE_RANGE", bad_offset.stderr)
                    malformed = subprocess.run(
                        [str(executable), "malformed"], cwd=folder,
                        text=True, capture_output=True, check=False)
                    self.assertNotEqual(malformed.returncode, 0)
                    self.assertEqual(malformed.stdout, "")
                    self.assertIn("PEP_RUNTIME_INVALID_SOURCE_BYTES",
                                  malformed.stderr)

    def test_lucy_named_hole_continuation_guard_runs_natively(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")
        guard = "!(length <= offset) && ascii_continue(byte_at(source, offset))"
        self.assertIn(guard, lexer)

        start = lexer.index("fn ascii_digit(")
        end = lexer.index("\nfn ascii_continue", start)
        digit_predicate = lexer[start:end].rstrip()
        predicates = (
            digit_predicate + "\n\n"
            "fn ascii_continue(byte: Int) -> Bool {\n"
            "  return byte == 102 || byte == 95 || ascii_digit(byte)\n"
            "}")
        source_text = (
            predicates + "\n\n"
            "fn has_next_identifier_byte(source: SourceBytes, offset: Int) -> Bool {\n"
            "  let length = byte_length(source)\n"
            "  return !(length <= offset) && ascii_continue(byte_at(source, offset))\n"
            "}\n"
            "fn main() -> Int { return 0 }\n")
        reference_text = source_text + (
            "fn probe(offset: Int) -> Bool {\n"
            "  return has_next_identifier_byte(source_bytes(), offset)\n"
            "}\n")

        def digest(raw):
            return "sha256:" + hashlib.sha256(raw).hexdigest()

        def req(op, **fields):
            return {"schemaVersion": 3, "toolProtocolVersion": 2, "op": op, **fields}

        def encoded_int(value):
            return {"type": "Int", "value": str(value)}

        def encoded_bool(value):
            return {"type": "Bool", "value": value}

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-named-hole-continuation.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "lucy-named-hole-continuation-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            input_bytes = reference.read_bytes()
            source_revision = digest(reference_text.encode("utf-8"))
            input_revision = digest(input_bytes)
            requests = [
                req("open", source=reference_text, name="lucy-named-hole-continuation"),
                req("open_bytes", bytes=list(input_bytes)),
                req("tool_register", tool="named-hole-continuation",
                    document="doc-1", revision=source_revision, function="probe"),
                req("tool_validate", tool="named-hole-continuation",
                    document="doc-1", revision=source_revision,
                    testVectors=[
                        {"arguments": [encoded_int(offset)],
                         "expect": encoded_bool(expected),
                         "semanticTarget": {"document": "doc-2",
                                            "revision": input_revision,
                                            "entryFunctions": []}}
                        for offset, expected in ((0, True), (len(input_bytes), False))
                    ]),
                req("tool_activate", tool="named-hole-continuation",
                    document="doc-1", revision=source_revision),
                req("tool_invoke", tool="named-hole-continuation",
                    arguments=[encoded_int(0)],
                    semanticTarget={"document": "doc-2", "revision": input_revision,
                                    "entryFunctions": []}),
                req("tool_invoke", tool="named-hole-continuation",
                    arguments=[encoded_int(len(input_bytes))],
                    semanticTarget={"document": "doc-2", "revision": input_revision,
                                    "entryFunctions": []}),
            ]
            session = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(PEP), "session", "--jsonl"],
                cwd=ROOT, text=True,
                input="".join(json.dumps(item, ensure_ascii=True) + "\n" for item in requests),
                capture_output=True, check=False)
            self.assertEqual(session.returncode, 0, session.stderr)
            responses = [json.loads(line) for line in session.stdout.splitlines()]
            self.assertEqual(responses[3]["status"], "Validated", responses[3])
            self.assertEqual(responses[4]["status"], "Active", responses[4])
            interpreted_values = [responses[5]["result"], responses[6]["result"]]
            self.assertEqual(interpreted_values,
                             [encoded_bool(True), encoded_bool(False)], responses[5:])
            interpreted_output = "".join(
                "1\n" if result["value"] else "0\n" for result in interpreted_values)

            generated = emit(source.read_bytes())
            declaration = re.search(
                r"_Bool pep_fn_(\d+)\(pep_source_bytes pep_arg_(\d+), "
                r"int64_t pep_arg_(\d+)\);", generated)
            self.assertIsNotNone(declaration, generated)
            function_id = declaration.group(1)
            self.assertIn(" && ", generated)
            self.assertIn("pep_byte_at(pep_arg_", generated)
            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")

            input_bytes = reference.read_bytes()
            byte_initializer = ", ".join(str(byte) for byte in input_bytes)
            harness_path = folder / "named-hole-continuation-harness.c"
            harness_path.write_text(
                "#include <stddef.h>\n#include <stdint.h>\n#include <stdio.h>\n"
                "#define main pep_generated_main\n#include \"generated.c\"\n#undef main\n"
                "int main(void) {\n"
                f"  static const unsigned char input[] = {{{byte_initializer}}};\n"
                "  pep_source_bytes source = {input, sizeof input};\n"
                f'  (void)printf("%d\\n%d\\n", '
                f"pep_fn_{function_id}(source, 0), "
                f"pep_fn_{function_id}(source, (int64_t)sizeof input));\n"
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"named-hole-continuation-{compiler.stem}.exe"
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", str(harness_path),
                         "-o", str(executable)],
                        cwd=folder, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    native = subprocess.run(
                        [str(executable)], cwd=folder, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(native.returncode, 0,
                                     native.stdout + native.stderr)
                    self.assertEqual(native.stdout, interpreted_output)

    def test_lucy_compound_comment_guard_short_circuits_at_end_of_source(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")
        guard = "byte == 47 && !(length <= offset + 1) && byte_at(source, offset + 1) == 47"
        self.assertIn(guard, lexer)

        source_text = (
            "fn starts_line_comment(byte: Int, source: SourceBytes, offset: Int) -> Bool {\n"
            "  let length = byte_length(source)\n"
            "  return byte == 47 && !(length <= offset + 1) && byte_at(source, offset + 1) == 47\n"
            "}\n"
            "fn main() -> Int { return 0 }\n")
        reference_text = source_text + (
            "fn probe(byte: Int, offset: Int) -> Bool {\n"
            "  return starts_line_comment(byte, source_bytes(), offset)\n"
            "}\n")

        def digest(raw):
            return "sha256:" + hashlib.sha256(raw).hexdigest()

        def req(op, **fields):
            return {"schemaVersion": 3, "toolProtocolVersion": 2, "op": op, **fields}

        def encoded_int(value):
            return {"type": "Int", "value": str(value)}

        def encoded_bool(value):
            return {"type": "Bool", "value": value}

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-comment-guard.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "lucy-comment-guard-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")

            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            source_revision = digest(reference_text.encode("utf-8"))
            requests = [
                req("open", source=reference_text, name="lucy-comment-guard"),
                req("open_bytes", bytes=list(b"/")),
                req("open_bytes", bytes=list(b"//")),
                req("open_bytes", bytes=list(b"x")),
                req("tool_register", tool="lucy-comment-guard",
                    document="doc-1", revision=source_revision, function="probe"),
                req("tool_validate", tool="lucy-comment-guard",
                    document="doc-1", revision=source_revision,
                    testVectors=[
                        {"arguments": [encoded_int(byte), encoded_int(0)],
                         "expect": encoded_bool(expected),
                         "semanticTarget": {"document": document,
                                            "revision": digest(raw),
                                            "entryFunctions": []}}
                        for byte, raw, expected, document in (
                            (47, b"/", False, "doc-2"),
                            (47, b"//", True, "doc-3"),
                            (120, b"x", False, "doc-4"))
                    ]),
                req("tool_activate", tool="lucy-comment-guard",
                    document="doc-1", revision=source_revision),
                req("tool_invoke", tool="lucy-comment-guard",
                    arguments=[encoded_int(47), encoded_int(0)],
                    semanticTarget={"document": "doc-2", "revision": digest(b"/"),
                                    "entryFunctions": []}),
                req("tool_invoke", tool="lucy-comment-guard",
                    arguments=[encoded_int(47), encoded_int(0)],
                    semanticTarget={"document": "doc-3", "revision": digest(b"//"),
                                    "entryFunctions": []}),
                req("tool_invoke", tool="lucy-comment-guard",
                    arguments=[encoded_int(120), encoded_int(0)],
                    semanticTarget={"document": "doc-4", "revision": digest(b"x"),
                                    "entryFunctions": []}),
            ]
            session = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(PEP), "session", "--jsonl"],
                cwd=ROOT, text=True,
                input="".join(json.dumps(item, ensure_ascii=True) + "\n" for item in requests),
                capture_output=True, check=False)
            self.assertEqual(session.returncode, 0, session.stderr)
            responses = [json.loads(line) for line in session.stdout.splitlines()]
            self.assertEqual(responses[5]["status"], "Validated", responses[5])
            self.assertEqual(responses[6]["status"], "Active", responses[6])
            interpreted_values = [response["result"] for response in responses[7:10]]
            self.assertEqual(interpreted_values, [
                encoded_bool(False), encoded_bool(True), encoded_bool(False)
            ], responses[7:10])
            interpreted_output = "".join(
                "1\n" if result["value"] else "0\n" for result in interpreted_values)

            generated = emit(source.read_bytes())
            declaration = re.search(
                r"_Bool pep_fn_(\d+)\(int64_t pep_arg_(\d+), "
                r"pep_source_bytes pep_arg_(\d+), int64_t pep_arg_(\d+)\);",
                generated)
            self.assertIsNotNone(declaration, generated)
            function_id = declaration.group(1)
            self.assertIn(" && ", generated)
            self.assertIn("pep_byte_at(pep_arg_", generated)
            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            harness_path = folder / "comment-guard-harness.c"
            harness_path.write_text(
                "#include <stddef.h>\n#include <stdint.h>\n#include <stdio.h>\n"
                "#define main pep_generated_main\n#include \"generated.c\"\n#undef main\n"
                "int main(void) {\n"
                "  static const unsigned char one_slash[] = {47};\n"
                "  static const unsigned char two_slashes[] = {47, 47};\n"
                "  static const unsigned char other[] = {120};\n"
                "  pep_source_bytes short_source = {one_slash, sizeof one_slash};\n"
                "  pep_source_bytes comment_source = {two_slashes, sizeof two_slashes};\n"
                "  pep_source_bytes other_source = {other, sizeof other};\n"
                f'  (void)printf("%d\\n%d\\n%d\\n", '
                f"pep_fn_{function_id}(47, short_source, 0), "
                f"pep_fn_{function_id}(47, comment_source, 0), "
                f"pep_fn_{function_id}(120, other_source, 0));\n"
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"lucy-comment-guard-{compiler.stem}.exe"
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
                    self.assertEqual(native.stdout, interpreted_output)

    def test_lucy_source_byte_length_matches_interpreter_and_native_c23(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_text(encoding="utf-8")
        length_binding = next(
            line.strip() for line in lexer.splitlines()
            if line.strip().startswith("let length = byte_length("))
        self.assertEqual(length_binding, "let length = byte_length(source)")
        source_text = (
            "fn measure(source: SourceBytes) -> Int {\n"
            f"  {length_binding}\n"
            "  return length\n"
            "}\n"
            "fn main() -> Int { return 0 }\n")
        reference_text = source_text + (
            "fn probe() -> Int { return byte_length(source_bytes()) }\n")
        vectors = [
            ("empty", b""),
            ("nul", bytes([0])),
            ("ascii", b"Lucy"),
            ("utf8", "λ🐇".encode("utf-8")),
            ("all-bytes", bytes(range(256))),
        ]

        def digest(raw):
            return "sha256:" + hashlib.sha256(raw).hexdigest()

        def req(op, **fields):
            return {"schemaVersion": 3, "toolProtocolVersion": 2, "op": op, **fields}

        def encoded(value):
            return {"type": "Int", "value": str(value)}

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-byte-length.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            checked = self.invoke("check", source, "--json")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

            generated = emit(source.read_bytes())
            declaration = re.search(
                r"int64_t pep_fn_(\d+)\(pep_source_bytes pep_arg_(\d+)\);",
                generated)
            self.assertIsNotNone(declaration, generated)
            function_id = declaration.group(1)
            self.assertIn(
                "typedef struct { const unsigned char *data; size_t length; } pep_source_bytes;",
                generated)
            self.assertIn("pep_byte_length(pep_arg_", generated)
            self.assertIn("PEP_RUNTIME_INVALID_SOURCE_BYTES", generated)
            self.assertIn("PEP_RUNTIME_LENGTH_RANGE", generated)

            reference_revision = digest(reference_text.encode("utf-8"))
            requests = [req("open", source=reference_text, name="byte-length-program")]
            targets = []
            for index, (name, raw) in enumerate(vectors):
                document = "doc-" + str(index + 2)
                targets.append((name, raw, document))
                requests.append(req("open_bytes", bytes=list(raw)))
            requests.append(req("tool_register", tool="byte-length-probe",
                                document="doc-1", revision=reference_revision,
                                function="probe"))
            validate_index = len(requests)
            requests.append(req("tool_validate", tool="byte-length-probe",
                                document="doc-1", revision=reference_revision,
                                testVectors=[
                                    {"arguments": [], "expect": encoded(len(raw)),
                                     "semanticTarget": {"document": document,
                                                        "revision": digest(raw),
                                                        "entryFunctions": []}}
                                    for _, raw, document in targets
                                ]))
            activate_index = len(requests)
            requests.append(req("tool_activate", tool="byte-length-probe",
                                document="doc-1", revision=reference_revision))
            invoke_start = len(requests)
            for _, raw, document in targets:
                requests.append(req("tool_invoke", tool="byte-length-probe", arguments=[],
                                    semanticTarget={"document": document,
                                                    "revision": digest(raw),
                                                    "entryFunctions": []}))

            session = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(PEP), "session", "--jsonl"],
                cwd=ROOT, text=True,
                input="".join(json.dumps(item, ensure_ascii=True) + "\n" for item in requests),
                capture_output=True, check=False)
            self.assertEqual(session.returncode, 0, session.stderr)
            responses = [json.loads(line) for line in session.stdout.splitlines()]
            self.assertEqual(responses[validate_index]["status"], "Validated",
                             responses[validate_index])
            self.assertEqual(responses[activate_index]["status"], "Active",
                             responses[activate_index])
            interpreter_values = []
            for index, (_, raw, _) in enumerate(targets):
                response = responses[invoke_start + index]
                self.assertNotIn("error", response, response)
                result = response["result"]
                self.assertEqual(result, encoded(len(raw)), response)
                interpreter_values.append(result["value"])

            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            byte_rows = []
            calls = []
            for index, (_, raw, _) in enumerate(targets):
                if raw:
                    byte_rows.append(
                        f"  static const unsigned char input_{index}[] = "
                        f"{{{', '.join(str(value) for value in raw)}}};\n")
                    source_view = (
                        f"(pep_source_bytes){{input_{index}, sizeof input_{index}}}")
                else:
                    source_view = "(pep_source_bytes){NULL, 0}"
                calls.append(
                    f"  (void)printf(\"%lld\\n\", (long long)pep_fn_{function_id}("
                    f"{source_view}));\n")
            harness = (
                "#include <stddef.h>\n#include <stdint.h>\n#include <stdio.h>\n"
                "#define main pep_generated_main\n#include \"generated.c\"\n#undef main\n"
                "int main(int argc, char **argv) {\n"
                "  static const unsigned char byte = 0;\n"
                "  if (argc > 1) {\n"
                f"    if (argv[1][0] == 'm') (void)pep_fn_{function_id}((pep_source_bytes){{NULL, 1}});\n"
                f"    if (argv[1][0] == 'r' && SIZE_MAX > (size_t)INT64_MAX) "
                f"(void)pep_fn_{function_id}((pep_source_bytes){{&byte, (size_t)((uintmax_t)INT64_MAX + UINTMAX_C(1))}});\n"
                "    return 0;\n  }\n" +
                "".join(byte_rows) +
                "".join(calls) +
                "  return 0;\n}\n")
            harness_path = folder / "lucy-byte-length-harness.c"
            harness_path.write_text(harness, encoding="utf-8", newline="\n")

            if not (CLANG.is_file() and GCC.is_file()):
                self.skipTest("Clang and GCC are required for native C23 verification")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"lucy-byte-length-{compiler.stem}.exe"
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
                    self.assertEqual(native.stdout.splitlines(), interpreter_values)
                    malformed = subprocess.run(
                        [str(executable), "malformed"], cwd=folder,
                        text=True, capture_output=True, check=False)
                    self.assertNotEqual(malformed.returncode, 0)
                    self.assertEqual(malformed.stdout, "")
                    self.assertIn("PEP_RUNTIME_INVALID_SOURCE_BYTES",
                                  malformed.stderr)
                    overflow = subprocess.run(
                        [str(executable), "range"], cwd=folder,
                        text=True, capture_output=True, check=False)
                    if "PEP_RUNTIME_LENGTH_RANGE" in generated:
                        self.assertNotEqual(overflow.returncode, 0)
                        self.assertEqual(overflow.stdout, "")
                        self.assertIn("PEP_RUNTIME_LENGTH_RANGE", overflow.stderr)


if __name__ == "__main__":
    unittest.main()
