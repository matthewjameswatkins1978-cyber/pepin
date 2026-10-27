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
            source.write_text("fn main() -> Int { if 19 <= 23 { return 23 } else { return 0 } }\n",
                              encoding="utf-8", newline="\n")
            result = self.invoke("run-c23", source, "--compiler", CLANG)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "23\n")
            source.write_text(
                "fn main() -> Int { return countdown(6) }\n"
                "fn countdown(value: Int) -> Int {\n"
                "  if value <= 0 { return 42 } else { return countdown(value - 1) }\n"
                "}\n",
                encoding="utf-8", newline="\n")
            recursive = self.invoke("run-c23", source, "--compiler", CLANG)
            self.assertEqual(recursive.returncode, 0, recursive.stdout + recursive.stderr)
            self.assertEqual(recursive.stdout, "42\n")
            source.write_text(
                "fn main() -> Int { return countdown(600) }\n"
                "fn countdown(value: Int) -> Int {\n"
                "  if value <= 0 { return 42 } else { return countdown(value - 1) }\n"
                "}\n",
                encoding="utf-8", newline="\n")
            too_deep = self.invoke("run-c23", source, "--compiler", CLANG)
            self.assertNotEqual(too_deep.returncode, 0)
            self.assertIn("PEP_RUNTIME_CALL_DEPTH", too_deep.stderr)
            source.write_text("fn main() -> Int { return length([1, 2]) }\n",
                              encoding="utf-8", newline="\n")
            rejected = self.invoke("run-c23", source, "--compiler", CLANG)
            self.assertEqual(rejected.returncode, 2, rejected.stdout + rejected.stderr)
            self.assertIn("Pep C23 unsupported:", rejected.stderr)
            self.assertFalse((folder / "answer.exe").exists())


    def test_emit_c_collision_does_not_overwrite_pep_source(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            source = pathlib.Path(temp) / "protected.pep"
            original = b"fn main() -> Int { return 42 }\\n"
            source.write_bytes(original)
            result = self.invoke("build-c23", source, "--output",
                                 pathlib.Path(temp) / "program.exe", "--emit-c", source,
                                 "--compiler", CLANG)
            self.assertEqual(result.returncode, 2)
            self.assertIn("paths must be distinct", result.stderr)
            self.assertEqual(source.read_bytes(), original)

if __name__ == "__main__":
    unittest.main()