"""Negative ASan gate for the str_concat bump-pool overflow (A2 Reserve 2).

Reserve 1 measured that `acc = str_concat(acc, piece)` in a loop silently
corrupts past ~90 one-byte pieces because the monotonic bump pool
(`pep_concat_pool[4096]`) is re-checked per call for a single result, but NOT
re-checked for accumulated usage. This test confirms that observation under
Clang AddressSanitizer: the N=91 accumulator writes one byte past the pool and
must be reported as a `global-buffer-overflow` -- a genuine out-of-bounds write
into `pep_str_concat.pep_concat_pool`, not merely wrong output.

Skipped (not failed) when the Clang ASan runtime is unavailable on this host.
"""

import os
import pathlib
import subprocess
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARENA = ROOT / "runtime" / "pep_arena" / "pep_arena.c"
ARENA_INCLUDE = ROOT / "runtime" / "pep_arena"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")


def _accumulator(n):
    return (
        "fn main() -> Int {\n"
        "  var acc: Str = \"\"\n"
        "  var o = 0\n"
        f"  while !({n} <= o) {{\n"
        "    acc = str_concat(acc, \"x\")\n"
        "    o = o + 1\n"
        "  }\n"
        "  say(acc)\n"
        "  return 0\n"
        "}\n")


def _sanitizer_runtime_dir():
    result = subprocess.run([str(CLANG), "--print-runtime-dir"], text=True,
                            capture_output=True, check=False)
    roots = [pathlib.Path(result.stdout.strip())] if result.stdout.strip() else []
    roots.append(CLANG.parent.parent / "lib" / "clang")
    for root in roots:
        if root.is_dir():
            for dll in root.rglob("clang_rt.asan_dynamic-x86_64.dll"):
                return dll.parent
    return None


@unittest.skipUnless(CLANG.is_file(), "Clang is required for the ASan overflow gate")
class BumpPoolOverflowAsan(unittest.TestCase):
    def test_accumulator_overflows_bump_pool_under_asan(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            directory = pathlib.Path(temp)
            c_path = directory / "accum91.c"
            c_path.write_text(emit(_accumulator(91).encode("utf-8")),
                              encoding="utf-8", newline="\n")
            executable = directory / "accum91.exe"
            built = subprocess.run(
                [str(CLANG), "-std=c23", "-g", "-O1", "-fsanitize=address",
                 f"-I{ARENA_INCLUDE}", str(c_path), str(ARENA), "-o", str(executable)],
                cwd=ROOT, text=True, capture_output=True, check=False)
            if built.returncode != 0:
                self.skipTest("ASan build unavailable: "
                              + (built.stdout + built.stderr)[-200:])
            environment = dict(os.environ)
            runtime = _sanitizer_runtime_dir()
            if runtime is not None:
                environment["PATH"] = str(runtime) + os.pathsep + environment.get("PATH", "")
            ran = subprocess.run([str(executable)], cwd=ROOT, text=True,
                                 capture_output=True, check=False, env=environment)
            if ran.returncode in (-1073741515, 3221225781):
                self.skipTest("ASan runtime DLL not loadable on this host")
            self.assertIn("global-buffer-overflow", ran.stderr)
            self.assertIn("pep_concat_pool", ran.stderr)


if __name__ == "__main__":
    unittest.main()
