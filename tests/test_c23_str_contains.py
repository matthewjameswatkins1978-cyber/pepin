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

            literal_source = folder / "str-contains-literal.pep"
            literal_source.write_text(
                'fn has() -> Bool { return str_contains("x", "x") }\n'
                'fn main() -> Int { return 0 }\n',
                encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(
                    ValueError, "str_contains arguments must resolve to Str parameters or declared record fields"):
                emit(literal_source.read_bytes())

            local_source = folder / "str-contains-local.pep"
            local_source.write_text(
                "fn has(haystack: Str, needle: Str) -> Bool {\n"
                "  let copy = haystack\n"
                "  return str_contains(copy, needle)\n"
                "}\n"
                "fn main() -> Int { return 0 }\n",
                encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(
                    ValueError, "Str local bindings are not yet lowered"):
                emit(local_source.read_bytes())

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


if __name__ == "__main__":
    unittest.main()
