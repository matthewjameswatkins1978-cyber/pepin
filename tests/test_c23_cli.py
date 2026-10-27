import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")


@unittest.skipUnless(CLANG.is_file(), f"Clang not installed at {CLANG}")
class PepC23CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "_build").mkdir(exist_ok=True)

    def invoke(self, *args):
        return subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
                              cwd=ROOT, text=True, capture_output=True, check=False)

    def test_build_c23_generates_and_compiles_checked_pep_source(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "answer.pep"
            output = folder / "answer.exe"
            source.write_text(
                "fn main() -> Int { return if 6 <= 7 { 42 } else { 0 } }\n",
                encoding="utf-8", newline="\n")
            result = self.invoke("build-c23", source, "--output", output,
                                 "--compiler", CLANG)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(output.is_file())
            c_source = output.with_suffix(".c").read_text(encoding="utf-8")
            self.assertIn("int64_t pep_fn_", c_source)
            self.assertIn(" ? ", c_source)

    def test_run_c23_executes_native_output_and_rejects_unsupported_valid_program(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "answer.pep"
            source.write_text("fn main() -> Int { return combine(19, 23) }\n"
                              "fn combine(a: Int, b: Int) -> Int { return b }\n",
                              encoding="utf-8", newline="\n")
            result = self.invoke("run-c23", source, "--compiler", CLANG)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "23\n")
            source.write_text("fn main() -> Int { if true { return 1 } else { return 2 } }\n",
                              encoding="utf-8", newline="\n")
            rejected = self.invoke("run-c23", source, "--compiler", CLANG)
            self.assertEqual(rejected.returncode, 2, rejected.stdout + rejected.stderr)
            self.assertIn("Pep C23 unsupported:", rejected.stderr)
            self.assertFalse((folder / "answer.exe").exists())


if __name__ == "__main__":
    unittest.main()