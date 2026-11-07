"""Tracked bump-pool boundary fixture for str_concat (A2 reserve 1, Lucy-20261107-014).

The C23 runtime lowers `str_concat` into a per-run *monotonic bump pool* of
`PEP_STR_CONCAT_CAPACITY` (4096) bytes. Two distinct boundaries matter for
compiler-A's text emission, measured 2026-11-07 via the public `build-c23`
path on strict Clang and GCC:

  1. **Per-call fail-closed guard.** A single `str_concat` result longer than
     4096 bytes aborts at runtime with `PEP_RUNTIME_STR_CONCAT_RANGE`. This is
     the documented, safe boundary (tested here).

  2. **Accumulated bump-pool overflow is NOT fail-closed.** Each
     `acc = str_concat(acc, piece)` call writes `acc.length + piece.length`
     bytes into the pool and advances the monotonic cursor without re-checking
     the 4096 ceiling, so an accumulator consumes O(N^2) pool bytes and
     overflows *silently* past ~90 one-byte pieces:
       N=90 -> 4095 bytes total -> clean output (pinned safe ceiling below);
       N=91 -> 4186 bytes -> adjacent storage corrupted (observed `Z\x10...`);
       N>=120 -> access violation (0xC0000005).
     This is recorded as a measured constraint for compiler-A authoring (do NOT
     accumulate emitted C via repeated in-loop str_concat past ~90 bytes); it is
     undefined behaviour, so the corruption/segfault itself is deliberately NOT
     pinned as an assertion.
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


@unittest.skipUnless(COMPILERS, "neither Clang nor GCC is installed")
class StrConcatBumpPoolBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "_build").mkdir(exist_ok=True)

    def invoke(self, *args):
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
            cwd=ROOT, text=True, capture_output=True, check=False)

    def test_accumulator_safe_ceiling_90_bytes(self):
        # N=90 one-byte concats -> sum_{k=1..90} k = 4095 bytes, the largest
        # accumulation that stays inside the monotonic bump pool. Deterministic.
        source_text = (
            "fn main() -> Int {\n"
            "  var acc: Str = \"\"\n"
            "  var o = 0\n"
            "  while !(90 <= o) {\n"
            "    acc = str_concat(acc, \"x\")\n"
            "    o = o + 1\n"
            "  }\n"
            "  say(acc)\n"
            "  return 0\n"
            "}\n")
        for compiler in COMPILERS:
            with self.subTest(compiler=compiler.stem):
                with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
                    folder = pathlib.Path(temp)
                    source = folder / "accum_ceiling.pep"
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    built = folder / "accum_ceiling.exe"
                    build = self.invoke("build-c23", source, "--compiler", compiler,
                                        "--output", built)
                    self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
                    ran = subprocess.run([str(built)], capture_output=True,
                                         text=True, encoding="utf-8", check=False)
                    self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                    self.assertEqual(ran.stdout, "x" * 90 + "\n0\n")

    def test_single_concat_over_capacity_fails_closed(self):
        # Doubling lets build a 5120-byte single result (160 -> ... -> 5120), which
        # must abort with PEP_RUNTIME_STR_CONCAT_RANGE on both compilers -- the
        # documented fail-closed guard (never a silent truncation).
        base = "A" * 160
        source_text = (
            "fn main() -> Int {\n"
            f"  let x0 = str_concat(\"{base}\", \"{base}\")\n"
            "  let x1 = str_concat(x0, x0)\n"
            "  let x2 = str_concat(x1, x1)\n"
            "  let x3 = str_concat(x2, x2)\n"
            "  let x4 = str_concat(x3, x3)\n"
            "  say(x4)\n"
            "  return 0\n"
            "}\n")
        for compiler in COMPILERS:
            with self.subTest(compiler=compiler.stem):
                with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
                    folder = pathlib.Path(temp)
                    source = folder / "concat_over_cap.pep"
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    built = folder / "concat_over_cap.exe"
                    build = self.invoke("build-c23", source, "--compiler", compiler,
                                        "--output", built)
                    self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
                    ran = subprocess.run([str(built)], capture_output=True,
                                         text=True, encoding="utf-8", check=False)
                    self.assertEqual(ran.returncode, 1)
                    self.assertIn("PEP_RUNTIME_STR_CONCAT_RANGE", ran.stderr)


if __name__ == "__main__":
    unittest.main()
