import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")
GCC = pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe")


class PepC23CollectionLoopTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
                              cwd=ROOT, text=True, capture_output=True, check=False)

    def test_integer_list_for_in_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var total = 0\n"
            "  for item in [1, 2, 3, 4] { total = total + item }\n"
            "  return total\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "sum.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "10\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)


if __name__ == "__main__":
    unittest.main()
