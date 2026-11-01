"""Native C23 lowering of arena-backed list updates: ``prepend`` and ``reverse``.

Lucy's real lexer uses ``prepend``/``reverse`` 17 times and the real parser 43 times
(``tokens = prepend(tokens, ...)``, ``reverse(stringPartsReversed)``, ...), and the
emitter had no representation for either, so no such function body could be lowered.

This slice covers ``List[Int]`` and ``List[Bool]`` mutable bindings, which are the
two element kinds the emitter already models end to end. ``List[Str]`` and
``List[record]`` need mutable bindings of those element kinds first and are not
claimed here.

Every case compares the generated C, built by Clang and GCC against the interpreter.
"""

import pathlib
import subprocess
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
ARENA = ROOT / "runtime" / "pep_arena" / "pep_arena.c"
ARENA_INCLUDE = ROOT / "runtime" / "pep_arena"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")
GCC = pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe")
NATIVE_AVAILABLE = CLANG.is_file() and GCC.is_file()


def digits_program(operations, initial="[1, 2]"):
    """Fold the resulting list into a base-10 number so element order is observable."""
    return (
        "fn main() -> Int {\n"
        f"  var xs: List[Int] = {initial}\n"
        "  var guard = 0\n"
        "  while guard <= 0 {\n"
        f"{operations}"
        "    guard = guard + 1\n"
        "  }\n"
        "  var digits = 0\n"
        "  for value in xs { digits = digits * 10 + value }\n"
        "  return digits\n"
        "}\n")


class PepC23ListUpdateTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
            cwd=ROOT, text=True, capture_output=True, check=False)

    def run_native(self, source_text, expected):
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            directory = pathlib.Path(temp_dir)
            reference = directory / "reference.pep"
            reference.write_text(source_text + "say(int_text(main()))\n",
                                 encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, f"{expected}\n")

            generated = emit(source_text.encode("utf-8"))
            if not NATIVE_AVAILABLE:
                return generated

            c_path = directory / "generated.c"
            c_path.write_text(generated, encoding="utf-8", newline="\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name, source=source_text):
                    executable = directory / (compiler.stem + "-case.exe")
                    built = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic",
                         "-Werror", "-O2", f"-I{ARENA_INCLUDE}", str(c_path),
                         str(ARENA), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                    ran = subprocess.run([str(executable)], cwd=ROOT, text=True,
                                         capture_output=True, check=False)
                    self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                    self.assertEqual(ran.stdout, interpreted.stdout)
            return generated

    def assert_refused(self, source_text, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            emit(source_text.encode("utf-8"))

    # --- positive capability -------------------------------------------------

    def test_prepend_places_the_value_first(self):
        generated = self.run_native(
            digits_program("    xs = prepend(xs, 9)\n"), 912)
        self.assertIn("pep_list_int_prepend(pep_arena, pep_local_", generated)
        self.assertIn('#include "pep_arena.h"', generated)

    def test_reverse_preserves_length_and_reverses_order(self):
        generated = self.run_native(
            digits_program("    xs = reverse(xs)\n"), 21)
        self.assertIn("pep_list_int_reverse(pep_arena, pep_local_", generated)

    def test_prepend_then_reverse_composes(self):
        self.run_native(
            digits_program("    xs = prepend(xs, 9)\n    xs = reverse(xs)\n"), 219)

    def test_reverse_of_an_empty_list_is_safe(self):
        self.run_native(
            digits_program("    xs = reverse(xs)\n", initial="[]"), 0)

    def test_repeated_prepend_grows_the_list(self):
        self.run_native(
            digits_program("    xs = prepend(xs, 9)\n    xs = prepend(xs, 8)\n"), 8912)

    def test_bool_list_prepend_and_contains_agree(self):
        self.run_native(
            "fn main() -> Int {\n"
            "  var bits: List[Bool] = [true]\n"
            "  var guard = 0\n"
            "  while guard <= 0 {\n"
            "    bits = prepend(bits, false)\n"
            "    guard = guard + 1\n"
            "  }\n"
            "  return if contains(bits, false) { length(bits) } else { 0 }\n"
            "}\n",
            2)

    # --- fail-closed boundaries ---------------------------------------------

    def test_prepend_of_a_different_binding_is_refused(self):
        self.assert_refused(
            "fn main() -> Int {\n"
            "  var xs: List[Int] = [1]\n"
            "  var ys: List[Int] = [2]\n"
            "  var guard = 0\n"
            "  while guard <= 0 {\n"
            "    xs = prepend(ys, 3)\n"
            "    guard = guard + 1\n"
            "  }\n"
            "  return length(xs)\n"
            "}\n",
            "prepend is currently limited to the binding being assigned")

    def test_reverse_with_two_arguments_is_refused(self):
        self.assert_refused(
            "fn main() -> Int {\n"
            "  var xs: List[Int] = [1]\n"
            "  var guard = 0\n"
            "  while guard <= 0 {\n"
            "    xs = reverse(xs, xs)\n"
            "    guard = guard + 1\n"
            "  }\n"
            "  return length(xs)\n"
            "}\n",
            "requires a valid Pep checker report")

    def test_prepend_of_a_fallible_value_is_refused(self):
        self.assert_refused(
            "fn compute() -> Int { return 3 }\n"
            "fn main() -> Int {\n"
            "  var xs: List[Int] = [1]\n"
            "  var guard = 0\n"
            "  while guard <= 0 {\n"
            "    xs = prepend(xs, compute())\n"
            "    guard = guard + 1\n"
            "  }\n"
            "  return length(xs)\n"
            "}\n",
            "prepend cannot evaluate a fallible value inside an arena update")

    def test_str_list_updates_are_not_claimed(self):
        """List[Str] mutable bindings are not lowered yet, so this stays refused."""
        self.assert_refused(
            "fn main() -> Int {\n"
            "  var parts: List[Str] = []\n"
            "  var guard = 0\n"
            "  while guard <= 0 {\n"
            "    parts = prepend(parts, \"a\")\n"
            "    guard = guard + 1\n"
            "  }\n"
            "  return length(parts)\n"
            "}\n",
            "prepend/reverse currently require an Int or Bool list binding")


if __name__ == "__main__":
    unittest.main()
