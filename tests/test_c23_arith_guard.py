"""Regression pin for the arithmetic-guard may_fail fix (A1's first emit-side refusal).

compiler_a's bounds guards are all of the form `X + N <= byte_length(source)`
(e.g. `o + 1 <= byte_length(source)`). Before the fix, `pep_c23_expression_may_fail`
treated every arithmetic binary (`+ - * /`) as fallible, so such a guard counted
TWO fallible operands and refused with "two fallible operands". The fix propagates
operand fallibility by OR for arithmetic (a variable operand is not statically
aborting) and keeps literal division-by-zero fallible.

This pins the exact compiler_a guard shape end-to-end (build + run with an unseen
argv[1] file) on strict Clang and GCC.
"""

import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")
GCC = pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe")

COMPILERS = [c for c in (CLANG, GCC) if c.is_file()]

SOURCE = (
    "fn main(source: SourceBytes) -> Int {\n"
    "  var o = 0\n"
    "  while o + 1 <= byte_length(source) {\n"
    "    o = o + 1\n"
    "  }\n"
    "  say(int_text(o))\n"
    "  return 0\n"
    "}\n")


@unittest.skipUnless(COMPILERS, "neither Clang nor GCC is installed")
class ArithmeticGuardFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "_build").mkdir(exist_ok=True)

    def invoke(self, *args):
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
            cwd=ROOT, text=True, capture_output=True, check=False)

    def test_arith_guard_counts_all_bytes_natively(self):
        # `o + 1 <= byte_length(source)` must no longer refuse as "two fallible
        # operands"; it counts every input byte (the guard advances o by 1 each
        # iteration until o+1 exceeds the length).
        for compiler in COMPILERS:
            with self.subTest(compiler=compiler.stem):
                with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
                    folder = pathlib.Path(temp)
                    source = folder / "arith_guard.pep"
                    source.write_text(SOURCE, encoding="utf-8", newline="\n")
                    built = folder / "arith_guard.exe"
                    build = self.invoke("build-c23", source, "--compiler", compiler,
                                        "--output", built)
                    self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
                    input_path = folder / "input.txt"
                    input_path.write_bytes(b"abcd")
                    ran = subprocess.run([str(built), str(input_path)],
                                         capture_output=True, text=True,
                                         encoding="utf-8", check=False)
                    self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                    self.assertEqual(ran.stdout, "4\n0\n")


if __name__ == "__main__":
    unittest.main()
