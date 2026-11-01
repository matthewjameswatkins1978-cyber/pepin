"""Stage ledger for Lucy's real lexer functions.

Records, per real function in examples/pep_lexer.pep, whether the emitter reaches it
today and — when it does not — which stage blocks it. This is a *ledger*, not an
aspiration: the assertions name the current dependency so that when the checker or the
transport improves, this test fails and forces a deliberate re-measure instead of the
improvement passing unnoticed.

Two kinds of assertion:

- functions the emitter reaches are compiled by Clang and GCC and their stdout is
  compared with the interpreter;
- functions the emitter does not reach must fail at the stage recorded here, and must
  not be silently emitter-refused.
"""

import pathlib
import subprocess
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
LEXER = ROOT / "examples" / "pep_lexer.pep"
TEXT = LEXER.read_text(encoding="utf-8")
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")
GCC = pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe")
NATIVE_AVAILABLE = CLANG.is_file() and GCC.is_file()


def block(header):
    """Extract one top-level `type`/`fn` block from the real lexer source."""
    start = TEXT.index(f"\n{header}") if f"\n{header}" in TEXT else TEXT.index(header)
    if TEXT[start] == "\n":
        start += 1
    depth = 0
    index = TEXT.index("{", start)
    for position in range(index, len(TEXT)):
        character = TEXT[position]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return TEXT[start:position + 1]
    raise AssertionError(header)


def emitter_stage(source_text):
    """Return 'emitted' or the pipeline stage that stopped it."""
    try:
        emit(source_text.encode("utf-8"))
        return "emitted"
    except ValueError:
        return "emitter-refused"
    except RuntimeError as error:
        text = str(error)
        if "check parsed source" in text:
            return "checker-step-limit"
        if "emit checked source" in text:
            return "emitter-step-limit"
        if "1 MiB" in text or "message limit" in text:
            return "transport-1MiB"
        return "other:" + text[:60]


FUNCTION_BLOCKS = {
    "ascii_letter": block("fn ascii_letter"),
    "ascii_digit": block("fn ascii_digit"),
    "ascii_continue": block("fn ascii_continue"),
    "utf8_check": block("fn utf8_check"),
    "advance_position": block("fn advance_position"),
}


class PepC23RealLexerStageTests(unittest.TestCase):
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
                return
            c_path = directory / "generated.c"
            c_path.write_text(generated, encoding="utf-8", newline="\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = directory / (compiler.stem + "-case.exe")
                    built = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic",
                         "-Werror", "-O2", str(c_path), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                    ran = subprocess.run([str(executable)], cwd=ROOT, text=True,
                                         capture_output=True, check=False)
                    self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                    self.assertEqual(ran.stdout, interpreted.stdout)

    # --- functions the emitter reaches today --------------------------------

    def test_real_character_classifiers_run_natively(self):
        for name, argument, expected in (("ascii_letter", 95, 1),
                                         ("ascii_digit", 55, 1)):
            with self.subTest(function=name):
                source = FUNCTION_BLOCKS[name] + (
                    f"\nfn main() -> Int {{ return if {name}({argument}) {{ 1 }} else {{ 0 }} }}\n")
                self.run_native(source, expected)

    def test_real_ascii_continue_composite_emits(self):
        """Three real lexer functions together: the composite the lexer actually uses."""
        self.assertEqual(
            emitter_stage(FUNCTION_BLOCKS["ascii_letter"] + "\n"
                          + FUNCTION_BLOCKS["ascii_digit"] + "\n"
                          + FUNCTION_BLOCKS["ascii_continue"] + "\n"
                          + "fn main() -> Int { return 0 }\n"),
            "emitted")

    def test_real_advance_position_runs_natively(self):
        source = block("type SourcePosition") + "\n" + FUNCTION_BLOCKS["advance_position"] + (
            "\nfn main() -> Int {\n"
            "  let next = advance_position(1, 9, 10)\n"
            "  return next.line * 100 + next.column\n"
            "}\n")
        self.run_native(source, 201)

    # --- ledger: what the checker still blocks ------------------------------

    def test_real_constructors_are_blocked_by_the_checker_not_the_emitter(self):
        """Current dependency, recorded so an improvement forces a re-measure.

        The emitter has native support for every construct these bodies use; they stop
        in the Pep-written checker. If this assertion starts failing, the checker has
        reached them and the constructor census must be re-run deliberately.
        """
        for name, header in (("make_token", "fn make_token"),
                             ("utf8_check", "fn utf8_check")):
            with self.subTest(function=name):
                body = block(header)
                types = ""
                if "LexToken" in body:
                    types = block("type LexToken") + "\n"
                if "Utf8Check" in body:
                    types = block("type Utf8Check") + "\n"
                stage = emitter_stage(types + body + "\nfn main() -> Int { return 0 }\n")
                self.assertEqual(stage, "checker-step-limit")
                self.assertNotEqual(stage, "emitter-refused")


if __name__ == "__main__":
    unittest.main()
