"""Executable smoke test using the *actual* Pep-written Lucy lexer classifier closure.

This is a deliberately small native-compiler vertical slice, not a claim that
pep_lexer.pep in its entirety or the Lucy compiler is self-hosted.
"""

import hashlib
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEXER = ROOT / "examples" / "pep_lexer.pep"
BUILD = ROOT / "_build"
EXPECTED_LEXER_BLOB = "12bd93a1dfc5dba3b1cab49abefffed5e406b17d"
COMPILER_FALLBACKS = {
    "clang": pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe"),
    "gcc": pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe"),
}


def actual_lexer_classifiers():
    """Extract the unchanged three-function classification closure from Lucy.

    The Git blob identity is pinned so a future lexer edit cannot silently turn
    this test into evidence for different source code.
    """
    source = LEXER.read_bytes().replace(b"\r\n", b"\n")
    header = f"blob {len(source)}\0".encode("ascii")
    actual_blob = hashlib.sha1(header + source).hexdigest()
    if actual_blob != EXPECTED_LEXER_BLOB:
        raise AssertionError(
            f"lexer source changed ({actual_blob}); audit/re-pin the native slice"
        )
    text = source.decode("utf-8")
    start = text.index("fn ascii_letter(")
    end = text.index("fn utf8_check(", start)
    closure = text[start:end].strip() + "\n"
    names = re.findall(r"(?m)^fn ([a-z_]+)\(", closure)
    if names != ["ascii_letter", "ascii_digit", "ascii_continue"]:
        raise AssertionError(f"unexpected real lexer classifier closure: {names!r}")
    return closure


def compiler_path(name):
    discovered = shutil.which(name)
    if discovered:
        return str(discovered)
    fallback = COMPILER_FALLBACKS[name]
    if fallback.is_file():
        return str(fallback)
    raise FileNotFoundError(f"required native compiler {name} unavailable")


def normalized_output(stream):
    # Windows C text-mode stdout converts LF to CRLF. Do not otherwise
    # discard or alter bytes, so the Pep and C results stay comparable.
    return stream.replace(b"\r\n", b"\n")


class RealPepLexerNativeSlice(unittest.TestCase):
    def test_real_lexer_ascii_classifiers_under_clang_and_gcc(self):
        if not shutil.which("pwsh"):
            self.fail("Pep reference runner unavailable: pwsh is required")
        compilers = [(name, compiler_path(name)) for name in ("clang", "gcc")]
        closure = actual_lexer_classifiers()
        BUILD.mkdir(parents=True, exist_ok=True)
        cases = ((65, b"42\n"), (57, b"42\n"), (95, b"42\n"),
                 (64, b"0\n"), (128, b"0\n"))
        with tempfile.TemporaryDirectory(prefix="real-lexer-c23-", dir=BUILD) as temp:
            directory = pathlib.Path(temp)
            for byte, expected in cases:
                with self.subTest(lexer_byte=byte):
                    # The only authored Pep here is a tiny executable harness;
                    # all three classifier definitions come byte-for-byte from
                    # the existing, source-hash-pinned production lexer.
                    pep = (closure + "\nfn main() -> Int {\n"
                           f"  if ascii_continue({byte}) {{ return 42 }} else {{ return 0 }}\n"
                           "}\n")
                    target = directory / f"classifier-{byte}.pep"
                    target.write_text(pep, encoding="utf-8", newline="\n")
                    reference = directory / f"classifier-{byte}-reference.pep"
                    reference.write_text(pep + "say(int_text(main()))\n", encoding="utf-8", newline="\n")
                    interpreted = subprocess.run(
                        ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"),
                         "run", str(reference)], cwd=ROOT, capture_output=True, check=False,
                    )
                    self.assertEqual(interpreted.returncode, 0,
                                     interpreted.stderr.decode("utf-8", "replace"))
                    self.assertEqual(normalized_output(interpreted.stdout), expected)

                    generated = emit(target.read_bytes())
                    self.assertIn("pep_fn_", generated)
                    c_source = directory / f"classifier-{byte}.c"
                    c_source.write_text(generated, encoding="utf-8", newline="\n")
                    for compiler_name, compiler in compilers:
                        with self.subTest(lexer_byte=byte, compiler=compiler_name):
                            binary = directory / f"classifier-{byte}-{compiler_name}.exe"
                            compiled = subprocess.run(
                                [compiler, "-std=c23", "-Wall", "-Wextra", "-Wpedantic",
                                 "-Werror", "-O2", str(c_source), "-o", str(binary)],
                                cwd=ROOT, capture_output=True, check=False,
                            )
                            self.assertEqual(compiled.returncode, 0,
                                             compiled.stderr.decode("utf-8", "replace"))
                            executed = subprocess.run([str(binary)], cwd=ROOT,
                                                      capture_output=True, check=False)
                            self.assertEqual(executed.returncode, 0,
                                             executed.stderr.decode("utf-8", "replace"))
                            self.assertEqual(normalized_output(executed.stdout), expected)
                            self.assertEqual(normalized_output(executed.stdout),
                                             normalized_output(interpreted.stdout))


if __name__ == "__main__":
    unittest.main()
