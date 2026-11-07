"""In-repo runnable proofs for the compiler-A backend capabilities at 1885566.

These are the audit-ready pins for A2 Slice 1 (Lucy-20261107-014): committed,
deterministic, end-to-end proofs (not `_build/` scratch) that the C23 emitter
supports the three shapes compiler-A needs to accumulate source-derived text:

  1. mutable `Str` local accumulation (`var text = "..."` + reassignment via
     `str_concat`) -- A1's named rung-iii blocker (ee1a275);
  2. loop-local `let piece = utf8_slice(source, o, o + 1)` in a `while` body,
     classified as a Str value (1885566);
  3. `List[Str]` accumulation via `prepend`, with the same loop-local piece.

Every test builds with strict Clang AND GCC, then executes the native binary
with an unseen argv[1] file so the emitted C genuinely depends on the input
source bytes (DIVERGENCE-2 discipline). No OCaml/Python semantic compilation is
involved past `pep.ps1 build-c23` itself.
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
class CompilerABackendProofs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "_build").mkdir(exist_ok=True)

    def invoke(self, *args):
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
            cwd=ROOT, text=True, capture_output=True, check=False)

    def _emit_and_run(self, compiler, folder, name, source_text, input_bytes):
        source = folder / f"{name}.pep"
        source.write_text(source_text, encoding="utf-8", newline="\n")
        generated = folder / f"{name}.c"
        built = folder / f"{name}.exe"
        build = self.invoke("build-c23", source, "--compiler", compiler,
                            "--emit-c", generated, "--output", built)
        if build.returncode != 0:
            return build, None
        input_path = folder / f"{name}.txt"
        input_path.write_bytes(input_bytes)
        ran = subprocess.run([str(built), str(input_path)],
                             capture_output=True, text=True,
                             encoding="utf-8", check=False)
        return build, ran

    def test_mutable_str_accumulation_matches_byte_oracle(self):
        # A1's accum_str_loop shape: start with a Str seed, append byte-derived
        # int_text pieces inside the loop, then say the accumulated text.
        source_text = (
            "fn main(source: SourceBytes) -> Int {\n"
            "  var text = \"head:\"\n"
            "  var o = 0\n"
            "  while !(byte_length(source) <= o) {\n"
            "    let b = byte_at(source, o)\n"
            "    text = str_concat(text, int_text(b))\n"
            "    o = o + 1\n"
            "  }\n"
            "  say(str_concat(\"TEXT:\", text))\n"
            "  return 0\n"
            "}\n")
        for compiler in COMPILERS:
            with self.subTest(compiler=compiler.stem):
                with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
                    folder = pathlib.Path(temp)
                    build, ran = self._emit_and_run(
                        compiler, folder, "accum_str_loop", source_text, b"ab\n")
                    self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
                    self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                    # bytes 97 ('a'), 98 ('b'), 10 (newline) -> "979810"; say adds
                    # a newline, then the wrapper prints main()'s Int return (0).
                    self.assertEqual(ran.stdout, "TEXT:head:979810\n0\n")

    def test_loop_local_utf8_slice_let_reproduces_input_byte_for_byte(self):
        # The 1885566 shape: a loop-local `let piece = utf8_slice(...)` (a Str),
        # accumulated into a mutable Str via str_concat, reproduces the granted
        # input exactly. This exercises both mutable-Str lowering AND loop-local
        # utf8_slice classification in one vertical.
        source_text = (
            "fn main(source: SourceBytes) -> Int {\n"
            "  var acc: Str = \"\"\n"
            "  var o = 0\n"
            "  while !(byte_length(source) <= o) {\n"
            "    let piece = utf8_slice(source, o, o + 1)\n"
            "    acc = str_concat(acc, piece)\n"
            "    o = o + 1\n"
            "  }\n"
            "  say(acc)\n"
            "  return 0\n"
            "}\n")
        for compiler in COMPILERS:
            with self.subTest(compiler=compiler.stem):
                with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
                    folder = pathlib.Path(temp)
                    build, ran = self._emit_and_run(
                        compiler, folder, "utf8_let_concat", source_text, b"abc")
                    self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
                    self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                    self.assertEqual(ran.stdout, "abc\n0\n")

    def test_list_str_prepend_with_loop_local_utf8_slice(self):
        # A1's list_then_concat shape (p33), made observable: prepend a
        # loop-local utf8_slice piece onto a mutable List[Str] each iteration and
        # read back the accumulated length. Proves List[Str] prepend + loop-local
        # utf8_slice classification together.
        source_text = (
            "fn main(source: SourceBytes) -> Int {\n"
            "  var parts: List[Str] = []\n"
            "  var o = 0\n"
            "  while !(byte_length(source) <= o) {\n"
            "    let piece = utf8_slice(source, o, o + 1)\n"
            "    parts = prepend(parts, piece)\n"
            "    o = o + 1\n"
            "  }\n"
            "  say(int_text(length(parts)))\n"
            "  return 0\n"
            "}\n")
        for compiler in COMPILERS:
            with self.subTest(compiler=compiler.stem):
                with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
                    folder = pathlib.Path(temp)
                    build, ran = self._emit_and_run(
                        compiler, folder, "list_prepend_len", source_text, b"abc")
                    self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
                    self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                    self.assertEqual(ran.stdout, "3\n0\n")
                    generated = (folder / "list_prepend_len.c").read_text(encoding="utf-8")
                    self.assertIn("pep_list_str", generated)
                    self.assertIn("pep_utf8_slice(", generated)


if __name__ == "__main__":
    unittest.main()
