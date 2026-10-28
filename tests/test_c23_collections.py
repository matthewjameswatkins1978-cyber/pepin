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
            "  let values = [1, 2, 3, 4]\n"
            "  for item in values { total = total + item }\n"
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


    def test_integer_list_length_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = "fn main() -> Int { let values = [10, 20, 30]; return length(values) }\n"
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "length.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "3\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)


    def test_integer_while_assignment_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var value = 0\n"
            "  while value <= 4 { value = value + 1 }\n"
            "  return value\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "while.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "5\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)


    def test_integer_contains_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  let values = [3, 5, 7]\n"
            "  return if contains(values, 5) { 1 } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "contains.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "1\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_integer_contains_absent_and_empty_list_matches_interpreter(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  let empty: List[Int] = []\n"
            "  return if contains([2], 9) || contains(empty, 9) { 1 } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "contains-empty.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "0\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_empty_typed_list_for_in_executes_zero_iterations(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  let empty: List[Int] = []\n"
            "  var total = 9\n"
            "  for item in empty { total = total + item }\n"
            "  return total\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "empty-for.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "9\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_boolean_contains_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  return if contains([false, true], true) { 1 } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "contains-bool.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "1\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_boolean_binding_contains_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  let flags = [false, true]\n"
            "  return if contains(flags, true) { 1 } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "contains-bool-binding.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "1\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_boolean_list_for_in_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  let flags = [false, true]\n"
            "  var seen = false\n"
            "  for flag in flags { seen = seen || flag }\n"
            "  return if seen { 1 } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "bool-for.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "1\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_integer_list_parameter_and_length_call_matches_interpreter(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn size(values: List[Int]) -> Int { return length(values) }\n"
            "fn main() -> Int { return size([4, 8, 15]) }\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "list-parameter.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "3\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_integer_list_parameter_contains_matches_interpreter(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn has_two(values: List[Int]) -> Int {\n"
            "  return if contains(values, 2) { 1 } else { 0 }\n"
            "}\n"
            "fn main() -> Int { return has_two([1, 2, 3]) }\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "list-parameter-contains.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "1\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_empty_integer_list_parameter_is_safe(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn has_two(values: List[Int]) -> Int {\n"
            "  return if contains(values, 2) { 1 } else { 0 }\n"
            "}\n"
            "fn main() -> Int { return has_two([]) }\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "empty-list-parameter.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "0\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_integer_list_and_needle_function_parameters_match(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn has_value(values: List[Int], needle: Int) -> Int {\n"
            "  return if contains(values, needle) { 1 } else { 0 }\n"
            "}\n"
            "fn main() -> Int { return has_value([4, 8, 15], 8) }\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "list-and-needle-parameters.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "1\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_integer_list_parameter_for_in_matches_interpreter(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn sum(values: List[Int]) -> Int {\n"
            "  var total = 0\n"
            "  for item in values { total = total + item }\n"
            "  return total\n"
            "}\n"
            "fn main() -> Int { return sum([1, 2, 3, 4]) }\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "list-parameter-for-in.pep"
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

    def test_integer_list_parameter_can_be_forwarded_to_another_function(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn sum(values: List[Int]) -> Int {\n"
            "  var total = 0\n"
            "  for item in values { total = total + item }\n"
            "  return total\n"
            "}\n"
            "fn forward(values: List[Int]) -> Int { return sum(values) }\n"
            "fn main() -> Int { return forward([1, 2, 3, 4]) }\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "list-parameter-forwarding.pep"
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
