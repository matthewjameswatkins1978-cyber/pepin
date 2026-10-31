"""C23 lowering of List-valued record fields.

Before this capability existed every record type in Lucy's real Pep-written lexer
(``LexToken``, ``LexCursor``, ``LexProgress``) was refused by the emitter with
``Pep C23 record fields require Int, Bool, or a preceding record declaration``,
even though the checker types them and the interpreter runs them.

These tests pin the capability itself (construction, field projection, empty and
nested values), the fail-closed boundaries that must survive it, and native
Clang/GCC execution compared against Pep's own interpreter output.
"""

import pathlib
import re
import subprocess
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
LEXER = ROOT / "examples" / "pep_lexer.pep"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")
GCC = pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe")

NATIVE_AVAILABLE = CLANG.is_file() and GCC.is_file()


def lexer_type_block():
    """Return Lucy's real lexer record/union declarations, verbatim from source."""
    lines = LEXER.read_text(encoding="utf-8").splitlines()
    block = []
    for line in lines:
        if line.startswith("fn ") or line.startswith("//"):
            break
        block.append(line)
    return "\n".join(block).strip() + "\n"


def lexer_declaration(name):
    """Return one real lexer type declaration, verbatim, without its dependencies."""
    block = lexer_type_block()
    starts = [match.start() for match in re.finditer(r"(?m)^type ", block)]
    starts.append(len(block))
    for index in range(len(starts) - 1):
        declaration = block[starts[index]:starts[index + 1]].strip()
        if declaration.split()[1] == name:
            return declaration + "\n"
    raise AssertionError(f"lexer source has no declaration named {name}")


class PepC23ListRecordFieldTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
            cwd=ROOT, text=True, capture_output=True, check=False)

    def run_native(self, source_text, expected):
        """Emit C23, compile with Clang and GCC, and compare with the interpreter."""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            directory = pathlib.Path(temp_dir)
            source = directory / "case.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")

            reference_source = directory / "reference.pep"
            reference_source.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference_source)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, f"{expected}\n")

            generated = emit(source.read_bytes())
            generated_c = directory / "generated.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")

            if not NATIVE_AVAILABLE:
                return generated

            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name, source=source_text):
                    executable = directory / (compiler.stem + "-case.exe")
                    built = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic",
                         "-Werror", "-O2", str(generated_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(built.returncode, 0,
                                     built.stdout + built.stderr)
                    ran = subprocess.run([str(executable)], cwd=ROOT, text=True,
                                         capture_output=True, check=False)
                    self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                    self.assertEqual(ran.returncode, interpreted.returncode)
                    self.assertEqual(ran.stdout, interpreted.stdout)
            return generated

    def assert_refused(self, source_text, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            emit(source_text.encode("utf-8"))

    # --- positive capability -------------------------------------------------

    def test_list_int_record_field_constructs_and_projects_natively(self):
        generated = self.run_native(
            "type Box { xs: List[Int] }\n"
            "fn main() -> Int {\n"
            "  let box = Box { xs: [1, 2, 3] }\n"
            "  return length(box.xs)\n"
            "}\n",
            3)
        self.assertIn("typedef struct { const int64_t *data; size_t length; } pep_list_int;",
                      generated)
        self.assertRegex(generated, r"pep_list_int pep_field_0;")
        self.assertIn(".data = (const int64_t[]){1, 2, 3}", generated)
        self.assertIn(".pep_field_0.length)", generated)
        self.assertIn("pep_checked_length(pep_local_", generated)

    def test_empty_list_record_field_is_safe(self):
        generated = self.run_native(
            "type Box { xs: List[Int] }\n"
            "fn main() -> Int { let box = Box { xs: [] } return length(box.xs) }\n",
            0)
        self.assertIn(".data = NULL, .length = 0", generated)

    def test_list_str_record_field_constructs_and_projects_natively(self):
        generated = self.run_native(
            "type Parts { parts: List[Str] }\n"
            "fn main() -> Int {\n"
            "  let parts = Parts { parts: [\"ab\", \"cde\"] }\n"
            "  return length(parts.parts)\n"
            "}\n",
            2)
        self.assertIn("typedef struct { const pep_str *data; size_t length; } pep_list_str;",
                      generated)
        self.assertIn(".data = (const pep_str[]){", generated)

    def test_list_bool_record_field_constructs_and_projects_natively(self):
        self.run_native(
            "type Flags { bits: List[Bool] }\n"
            "fn main() -> Int {\n"
            "  let flags = Flags { bits: [true, false, true] }\n"
            "  return length(flags.bits)\n"
            "}\n",
            3)

    def test_list_record_record_field_constructs_and_projects_natively(self):
        generated = self.run_native(
            "type Inner { x: Int }\n"
            "type Outer { items: List[Inner] }\n"
            "fn main() -> Int {\n"
            "  let outer = Outer { items: [Inner { x: 1 }, Inner { x: 2 }] }\n"
            "  return length(outer.items)\n"
            "}\n",
            2)
        self.assertRegex(generated, r"pep_list_record_\d+ pep_field_0;")
        self.assertRegex(generated, r"\.data = \(const pep_record_\d+\[\]\)\{")

    def test_scalar_and_list_fields_combine_in_one_record(self):
        self.run_native(
            "type Token { kind: Str parts: List[Str] count: Int }\n"
            "fn main() -> Int {\n"
            "  let token = Token { kind: \"string\", parts: [\"a\"], count: 7 }\n"
            "  return token.count + length(token.parts)\n"
            "}\n",
            8)

    def test_real_lexer_token_type_compiles_and_runs_natively(self):
        token_declaration = lexer_declaration("LexToken")
        self.assertIn("stringParts: List[Str],", token_declaration)
        # Kept deliberately small: the Pep-written checker's fixed 100k-step
        # per-invocation budget is consumed by this real declaration plus the body,
        # so a larger main stops at the checker before the emitter is reached.
        source_text = token_declaration + (
            "fn main() -> Int {\n"
            "  let token = LexToken { kind: \"string\", text: \"\", integerValue: 0, "
            "stringParts: [\"ab\", \"cd\"], startByte: 3, endByte: 9, line: 1, column: 4 }\n"
            "  return length(token.stringParts)\n"
            "}\n")
        generated = self.run_native(source_text, 2)
        self.assertIn("pep_list_str", generated)

    def test_real_lexer_cursor_type_emits(self):
        cursor_declaration = lexer_declaration("LexCursor")
        self.assertIn("stringPartsReversed: List[Str]", cursor_declaration)
        generated = emit((cursor_declaration +
                          "fn main() -> Int { return 0 }\n").encode("utf-8"))
        self.assertIn("typedef struct { const pep_str *data; size_t length; } pep_list_str;",
                      generated)
        self.assertRegex(generated, r"pep_list_str pep_field_15;")

    def test_real_lexer_type_declaration_census(self):
        """Pin the measured census for Lucy's real lexer declarations.

        Baseline, parent commit 26be4be: SourcePosition and Utf8Check emitted,
        LexToken and LexCursor were refused by the emitter for their List-valued
        fields. LexProgress is unchanged either way: its complete closure stops at
        the Pep-written checker's fixed 100k-step budget before the emitter runs.
        """
        dependencies = {"LexProgress": ["LexToken", "LexCursor"]}
        census = {}
        for name in ("SourcePosition", "Utf8Check", "LexToken", "LexCursor", "LexProgress"):
            declarations = dependencies.get(name, []) + [name]
            source_text = "\n".join(lexer_declaration(item) for item in declarations)
            source_text += "fn main() -> Int { return 0 }\n"
            try:
                emit(source_text.encode("utf-8"))
            except RuntimeError as error:
                if "PEP_RUNTIME_STEP_LIMIT" not in str(error):
                    raise
                census[name] = "checker-budget"
            except ValueError:
                census[name] = "unsupported"
            else:
                census[name] = "emitted"
        self.assertEqual(census, {
            "SourcePosition": "emitted",
            "Utf8Check": "emitted",
            "LexToken": "emitted",
            "LexCursor": "emitted",
            "LexProgress": "checker-budget",
        })

    def test_real_lexer_complete_type_closure_is_bounded_by_the_checker(self):
        """The whole real lexer type block either emits, or stops at the checker budget.

        At this revision the Pep-written checker exhausts its fixed 100k-step
        per-invocation budget on the complete closure (LexToken + LexCursor +
        LexProgress). That is a checker-cost dependency, not an emitter gap.
        Either outcome is acceptable here; silently emitting invalid C is not.
        """
        source_text = lexer_type_block() + "fn main() -> Int { return 0 }\n"
        try:
            generated = emit(source_text.encode("utf-8"))
        except RuntimeError as error:
            self.assertIn("PEP_RUNTIME_STEP_LIMIT", str(error))
            self.skipTest("checker step budget still bounds the complete lexer "
                          "type closure (PEP_RUNTIME_STEP_LIMIT)")
        self.assertIn("pep_list_str", generated)
        self.assertRegex(generated, r"pep_list_record_\d+ pep_field_3;")

    # --- fail-closed boundaries that must survive the capability -------------

    def test_computed_list_field_element_still_fails_closed(self):
        self.assert_refused(
            "type Box { xs: List[Int] }\n"
            "fn main() -> Int { let box = Box { xs: [1 + 2] } return length(box.xs) }\n",
            "Pep C23 List\\[Int\\] record field values currently require integer literal elements")

    def test_forward_list_record_field_reference_still_fails_closed(self):
        self.assert_refused(
            "type Outer { items: List[Inner] }\n"
            "type Inner { x: Int }\n"
            "fn main() -> Int { return 0 }\n",
            "record fields require Int, Bool, or a preceding record declaration")

    def test_forward_scalar_record_field_reference_still_fails_closed(self):
        self.assert_refused(
            "type Box { point: Point }\n"
            "type Point { x: Int }\n"
            "fn main() -> Int { return 0 }\n",
            "record fields require Int, Bool, or a preceding record declaration")

    def test_two_genuinely_fallible_fields_still_fail_closed(self):
        self.assert_refused(
            "type Value { first: Int, second: Int }\n"
            "fn calculate() -> Int { return 42 }\n"
            "fn main() -> Int {\n"
            "  let value = Value { first: calculate(), second: calculate() }\n"
            "  return value.first + value.second\n"
            "}\n",
            "record construction rejects multiple fallible field expressions")

    def test_nested_list_field_access_is_not_silently_accepted(self):
        """A projection of one list field feeding another field must still fail closed."""
        self.assert_refused(
            "type Box { xs: List[Int] }\n"
            "type Pair { left: List[Int], right: List[Int] }\n"
            "fn main() -> Int {\n"
            "  let box = Box { xs: [1] }\n"
            "  let pair = Pair { left: box.xs, right: [2] }\n"
            "  return length(pair.right)\n"
            "}\n",
            "Pep C23 list record field values currently require a list literal")


if __name__ == "__main__":
    unittest.main()
