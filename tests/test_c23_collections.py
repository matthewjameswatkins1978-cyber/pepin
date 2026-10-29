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


    def test_negative_integer_literal_for_in_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var total = 0\n"
            "  for item in [-2, 0, 3] { total = total + item }\n"
            "  return total\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "negative-for-in.pep"
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

    def test_negative_integer_list_initializer_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var values = [-2, 0, 3]\n"
            "  var total = 0\n"
            "  for item in values { total = total + item }\n"
            "  return if total == 1 && length(values) == 3 { 42 } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "negative-list.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "42\n")
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


    def test_mutable_list_binding_keeps_value_semantics_in_native_loops(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var values = [1, 2, 3]\n"
            "  var total = 0\n"
            "  for item in values { total = total + item }\n"
            "  return total + length(values)\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "mutable_list.pep"
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

    def test_mutable_list_for_in_uses_runtime_descriptor_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        cases = (
            ("var values = [1, 2, 3]\n  var total = 0\n  for item in values { total = total + item }\n  return total + length(values)", "9"),
            ("var values = [true, false, true]\n  var total = 0\n  for item in values { total = if item { total + 1 } else { total } }\n  return total + length(values)", "5"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            for index, (body, expected) in enumerate(cases):
                source_text = f"fn main() -> Int {{\n  {body}\n}}\n"
                source = folder / f"mutable-loop-{index}.pep"
                reference_source = folder / f"reference-{index}.pep"
                source.write_text(source_text, encoding="utf-8", newline="\n")
                reference_source.write_text(source_text + "say(int_text(main()))\n",
                                            encoding="utf-8", newline="\n")
                reference = self.invoke("run", reference_source)
                self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                self.assertEqual(reference.stdout, expected + "\n")
                for compiler in (CLANG, GCC):
                    with self.subTest(index=index, compiler=compiler.name):
                        generated_c = folder / f"mutable-loop-{index}-{compiler.stem}.c"
                        result = self.invoke("run-c23", source, "--compiler", compiler,
                                             "--emit-c", generated_c)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertEqual(result.stdout, reference.stdout)
                        c_source = generated_c.read_text(encoding="utf-8")
                        self.assertRegex(c_source, r"pep_local_\d+\.data\[pep_index_\d+\]")

    def test_mutable_list_contains_scans_runtime_descriptor_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        cases = (
            ("var values = [3, 5, 7]\n  return if contains(values, 5) { 1 } else { 0 }", "1", "pep_contains_int"),
            ("var values = [false, true]\n  return if contains(values, true) { 1 } else { 0 }", "1", "pep_contains_bool"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            for index, (body, expected, helper) in enumerate(cases):
                source_text = f"fn main() -> Int {{\n  {body}\n}}\n"
                source = folder / f"mutable-contains-{index}.pep"
                reference_source = folder / f"reference-{index}.pep"
                source.write_text(source_text, encoding="utf-8", newline="\n")
                reference_source.write_text(source_text + "say(int_text(main()))\n",
                                            encoding="utf-8", newline="\n")
                reference = self.invoke("run", reference_source)
                self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                self.assertEqual(reference.stdout, expected + "\n")
                for compiler in (CLANG, GCC):
                    with self.subTest(index=index, compiler=compiler.name):
                        generated_c = folder / f"mutable-contains-{index}-{compiler.stem}.c"
                        result = self.invoke("run-c23", source, "--compiler", compiler,
                                             "--emit-c", generated_c)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertEqual(result.stdout, reference.stdout)
                        c_source = generated_c.read_text(encoding="utf-8")
                        self.assertRegex(c_source, rf"{helper}\(pep_local_\d+,")

    def test_mutable_list_bindings_forward_to_native_helpers(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        cases = (
            ("fn aggregate(values: List[Int]) -> Int {\n"
             "  var total = 0\n  for item in values { total = total + item }\n"
             "  return total\n}\n"
             "fn main() -> Int { var values = [1, 2, 3]; return aggregate(values) }\n", "6"),
            ("fn count_true(values: List[Bool]) -> Int {\n"
             "  var total = 0\n  for item in values { total = if item { total + 1 } else { total } }\n"
             "  return total\n}\n"
             "fn main() -> Int { var values = [true, false, true]; return count_true(values) }\n", "2"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            for index, (source_text, expected) in enumerate(cases):
                source = folder / f"mutable-forward-{index}.pep"
                reference_source = folder / f"reference-{index}.pep"
                source.write_text(source_text, encoding="utf-8", newline="\n")
                reference_source.write_text(source_text + "say(int_text(main()))\n",
                                            encoding="utf-8", newline="\n")
                reference = self.invoke("run", reference_source)
                self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                self.assertEqual(reference.stdout, expected + "\n")
                for compiler in (CLANG, GCC):
                    with self.subTest(index=index, compiler=compiler.name):
                        generated_c = folder / f"mutable-forward-{index}-{compiler.stem}.c"
                        result = self.invoke("run-c23", source, "--compiler", compiler,
                                             "--emit-c", generated_c)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertEqual(result.stdout, reference.stdout)
                        c_source = generated_c.read_text(encoding="utf-8")
                        self.assertRegex(c_source, r"pep_fn_\d+\(pep_local_\d+\)")

    def test_mutable_list_reassignment_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var values = [1]\n"
            "  var replacement = [2, 3]\n"
            "  var count = 0\n"
            "  while count <= 0 { values = replacement; count = count + 1 }\n"
            "  return length(values)\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            source = pathlib.Path(temp) / "reassigned_list.pep"
            reference_source = pathlib.Path(temp) / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "2\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)
                    self.assertEqual(result.stdout, "2\n")

    def test_same_named_list_bindings_in_different_functions_do_not_block_emission(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn helper() -> Int {\n"
            "  let values = [7, 8]\n"
            "  return length(values)\n"
            "}\n"
            "fn main() -> Int {\n"
            "  var values = [1]\n"
            "  var replacement = [2, 3]\n"
            "  var count = 0\n"
            "  while count <= 0 { values = replacement; count = count + 1 }\n"
            "  return length(values)\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "same_name_bindings.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "2\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_typed_empty_boolean_list_reassignment_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var values: List[Bool] = []\n"
            "  var replacement = [true, false]\n"
            "  var count = 0\n"
            "  while count <= 0 { values = replacement; count = count + 1 }\n"
            "  return if contains(values, true) && length(values) == 2 { 42 } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            source = pathlib.Path(temp) / "reassigned_empty_bool_list.pep"
            reference_source = pathlib.Path(temp) / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "42\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_mutable_boolean_list_binding_matches_interpreter(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var values = [true, false, true]\n"
            "  return if contains(values, true) { length(values) } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "mutable_bool_list.pep"
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

    def test_negative_integer_contains_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  let values = [-2]\n"
            "  return if contains(values, -2) { 42 } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "contains-negative.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "42\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_negative_mutable_integer_contains_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var values = [-2, 0, 3]\n"
            "  return if contains(values, -2) { 42 } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "contains-negative-mutable.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "42\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_negative_parameter_contains_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn contains_negative(values: List[Int]) -> Bool {\n"
            "  return if contains(values, -2) { true } else { false }\n"
            "}\n"
            "fn main() -> Int {\n"
            "  return if contains_negative([-2, 0, 3]) { 42 } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "contains-negative-parameter.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "42\n")
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

    def test_for_in_preserves_order_of_multiple_assignments(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var current = 1\n"
            "  var last = 0\n"
            "  for item in [2, 4] { current = current + item; last = current }\n"
            "  return last\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "ordered_loop_assignments.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "7\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)

    def test_while_preserves_order_of_multiple_assignments(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var current = 1\n"
            "  var last = 0\n"
            "  while current <= 6 { current = current + 2; last = current }\n"
            "  return last\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "ordered_while_assignments.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "7\n")
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

    def test_boolean_list_parameter_contains_and_length_match_interpreter(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        cases = (("[false, true, false]", "3"), ("[]", "0"))
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            for index, (values, expected) in enumerate(cases):
                source_text = (
                    "fn score(values: List[Bool]) -> Int {\n"
                    "  return if contains(values, true) { length(values) } else { 0 }\n"
                    "}\n"
                    f"fn main() -> Int {{ return score({values}) }}\n"
                )
                source = folder / f"bool-list-parameter-{index}.pep"
                reference_source = folder / f"reference-{index}.pep"
                source.write_text(source_text, encoding="utf-8", newline="\n")
                reference_source.write_text(source_text + "say(int_text(main()))\n",
                                            encoding="utf-8", newline="\n")
                reference = self.invoke("run", reference_source)
                self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                self.assertEqual(reference.stdout, expected + "\n")
                for compiler in (CLANG, GCC):
                    with self.subTest(values=values, compiler=compiler.name):
                        result = self.invoke("run-c23", source, "--compiler", compiler)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertEqual(result.stdout, reference.stdout)

    def test_boolean_list_parameter_for_in_matches_interpreter(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        cases = (("[false, true, true]", "2"), ("[]", "0"))
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            for index, (values, expected) in enumerate(cases):
                source_text = (
                    "fn count_true(values: List[Bool]) -> Int {\n"
                    "  var total = 0\n"
                    "  for item in values { total = if item { total + 1 } else { total } }\n"
                    "  return total\n"
                    "}\n"
                    f"fn main() -> Int {{ return count_true({values}) }}\n"
                )
                source = folder / f"bool-list-parameter-for-in-{index}.pep"
                reference_source = folder / f"reference-{index}.pep"
                source.write_text(source_text, encoding="utf-8", newline="\n")
                reference_source.write_text(source_text + "say(int_text(main()))\n",
                                            encoding="utf-8", newline="\n")
                reference = self.invoke("run", reference_source)
                self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                self.assertEqual(reference.stdout, expected + "\n")
                for compiler in (CLANG, GCC):
                    with self.subTest(values=values, compiler=compiler.name):
                        result = self.invoke("run-c23", source, "--compiler", compiler)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertEqual(result.stdout, reference.stdout)


    def test_boolean_list_parameter_forwarding_matches_interpreter(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn score(values: List[Bool]) -> Int {\n"
            "  return if contains(values, true) { length(values) } else { 0 }\n"
            "}\n"
            "fn forward(values: List[Bool]) -> Int { return score(values) }\n"
            "fn main() -> Int { return forward([false, true, false]) }\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "bool-list-parameter-forwarding.pep"
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


    def test_pep_written_all_false_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")

        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_bool_all_false(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (("[false, false, false]", 42), ("[true, false]", 0), ("[]", 42))
        with tempfile.TemporaryDirectory() as temp_dir:
            for index, (values, expected) in enumerate(cases):
                with self.subTest(values=values):
                    source = pathlib.Path(temp_dir) / f"all_false_{index}.pep"
                    source.write_text(
                        helper + f"\nfn main() -> Int {{\n  return if list_bool_all_false({values}) {{ 42 }} else {{ 0 }}\n}}\n",
                        encoding="utf-8", newline="\n")
                    reference_source = pathlib.Path(temp_dir) / f"all_false_ref_{index}.pep"
                    reference_source.write_text(
                        source.read_text(encoding="utf-8") + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            result = self.invoke("run-c23", source, "--compiler", compiler)
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                            self.assertEqual(result.stdout, reference.stdout)

    def test_pep_written_count_at_most_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")

        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_count_at_most(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (("[1, 2, 3, 4]", 3, 3), ("[-3, -2, -1, 0]", -1, 3), ("[]", -1, 0), ("[1, 2]", 0, 0))
        with tempfile.TemporaryDirectory() as temp_dir:
            for index, (values, upper, expected_count) in enumerate(cases):
                with self.subTest(values=values, upper=upper):
                    source = pathlib.Path(temp_dir) / f"count_at_most_{index}.pep"
                    source_text = (
                        helper + f"\nfn main() -> Int {{\n  return list_int_count_at_most({values}, {upper})\n}}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = pathlib.Path(temp_dir) / f"count_at_most_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n", encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected_count) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            result = self.invoke("run-c23", source, "--compiler", compiler)
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                            self.assertEqual(result.stdout, reference.stdout)

    def test_pep_written_all_equal_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")

        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_all_equal(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (("[2, 2, 2]", 2, 42), ("[2, 3]", 2, 0), ("[]", 8, 42))
        with tempfile.TemporaryDirectory() as temp_dir:
            for index, (values, expected_value, expected_result) in enumerate(cases):
                with self.subTest(values=values, expected_value=expected_value):
                    source = pathlib.Path(temp_dir) / f"all_equal_{index}.pep"
                    source_text = (
                        helper + f"\nfn main() -> Int {{\n  return if list_int_all_equal({values}, {expected_value}) {{ 42 }} else {{ 0 }}\n}}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = pathlib.Path(temp_dir) / f"all_equal_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n", encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected_result) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            result = self.invoke("run-c23", source, "--compiler", compiler)
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                            self.assertEqual(result.stdout, reference.stdout)

    def test_pep_written_count_equal_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")

        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_count_equal(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (("[5, 4, 5, 5]", 5, 3), ("[-1, 0, -1]", -1, 2), ("[]", 4, 0))
        with tempfile.TemporaryDirectory() as temp_dir:
            for index, (values, expected_value, expected_count) in enumerate(cases):
                with self.subTest(values=values, expected_value=expected_value):
                    source = pathlib.Path(temp_dir) / f"count_equal_{index}.pep"
                    source_text = (
                        helper + f"\nfn main() -> Int {{\n  return list_int_count_equal({values}, {expected_value})\n}}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = pathlib.Path(temp_dir) / f"count_equal_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n", encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected_count) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            result = self.invoke("run-c23", source, "--compiler", compiler)
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                            self.assertEqual(result.stdout, reference.stdout)

    def test_pep_written_count_greater_than_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_count_greater_than(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (("[1, 3, 5]", 3, 1), ("[1, 3, 5]", 5, 0),
                 ("[-2, 0, 3]", -1, 2), ("[]", 0, 0))
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            for index, (values, lower, expected) in enumerate(cases):
                with self.subTest(values=values, lower=lower):
                    source_text = (
                        helper + f"\nfn main() -> Int {{ return list_int_count_greater_than({values}, {lower}) }}\n")
                    source = folder / f"count-greater-than-{index}.pep"
                    source.write_text(source_text, encoding="utf-8", newline="")
                    reference_source = folder / f"count-greater-than-reference-{index}.pep"
                    reference_source.write_text(source_text + "say(int_text(main()))\n",
                                                encoding="utf-8", newline="")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + "\n")
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            result = self.invoke("run-c23", source, "--compiler", compiler)
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                            self.assertEqual(result.stdout, reference.stdout)

    def test_pep_written_collection_helpers_match_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        functions = {
            definition.split("(", 1)[0].removeprefix("fn "): definition
            for definition in library.strip().split("\n\n")
        }
        cases = (
            ("list_int_sum",
             "fn main() -> Int { return if list_int_sum([1, 2, 3]) == 6 && "
             "list_int_sum([]) == 0 { 42 } else { 0 } }\n"),
            ("list_int_product",
             "fn main() -> Int { return if list_int_product([2, 3, 4]) == 24 && "
             "list_int_product([]) == 1 { 42 } else { 0 } }\n"),
            ("list_int_count_nonzero",
             "fn main() -> Int { return if list_int_count_nonzero([-2, 0, 3]) == 2 { 42 } else { 0 } }\n"),
            ("list_int_count_zero",
             "fn main() -> Int { return if list_int_count_zero([-2, 0, 3, 0]) == 2 { 42 } else { 0 } }\n"),
            ("list_int_count_zero",
             "fn main() -> Int { return if list_int_count_zero([]) == 0 { 42 } else { 0 } }\n"),
            ("list_int_any_zero",
             "fn main() -> Int { return if list_int_any_zero([-2, 0, 3]) { 42 } else { 0 } }\n"),
            ("list_int_any_zero",
             "fn main() -> Int { return if list_int_any_zero([-2, 3]) { 0 } else { 42 } }\n"),
            ("list_int_any_zero",
             "fn main() -> Int { return if list_int_any_zero([]) { 0 } else { 42 } }\n"),
            ("list_int_any_nonzero",
             "fn main() -> Int { return if list_int_any_nonzero([-2, 0, 3]) { 42 } else { 0 } }\n"),
            ("list_int_any_nonzero",
             "fn main() -> Int { return if list_int_any_nonzero([0, 0]) { 0 } else { 42 } }\n"),
            ("list_int_any_nonzero",
             "fn main() -> Int { return if list_int_any_nonzero([]) { 0 } else { 42 } }\n"),
            ("list_int_count_negative",
             "fn main() -> Int { return if list_int_count_negative([-2, 0, 3]) == 1 { 42 } else { 0 } }\n"),
            ("list_int_any_negative",
             "fn main() -> Int { return if list_int_any_negative([-2, 0, 3]) { 42 } else { 0 } }\n"),
            ("list_int_all_negative",
             "fn main() -> Int { return if list_int_all_negative([-2, -1]) { 42 } else { 0 } }\n"),
            ("list_int_all_negative",
             "fn main() -> Int { return if list_int_all_negative([-2, 0]) { 0 } else { 42 } }\n"),
            ("list_int_all_negative",
             "fn main() -> Int { return if list_int_all_negative([]) { 42 } else { 0 } }\n"),
            ("list_int_all_nonnegative",
             "fn main() -> Int { return if list_int_all_nonnegative([0, 2]) { 42 } else { 0 } }\n"),
            ("list_int_all_nonnegative",
             "fn main() -> Int { return if list_int_all_nonnegative([-1, 0, 2]) { 0 } else { 42 } }\n"),
            ("list_int_all_nonnegative",
             "fn main() -> Int { return if list_int_all_nonnegative([]) { 42 } else { 0 } }\n"),
            ("list_int_all_nonpositive",
             "fn main() -> Int { return if list_int_all_nonpositive([-2, 0]) { 42 } else { 0 } }\n"),
            ("list_int_all_nonpositive",
             "fn main() -> Int { return if list_int_all_nonpositive([0, 1]) { 0 } else { 42 } }\n"),
            ("list_int_all_nonpositive",
             "fn main() -> Int { return if list_int_all_nonpositive([]) { 42 } else { 0 } }\n"),
            ("list_int_all_positive",
             "fn main() -> Int { return if list_int_all_positive([1, 2]) { 42 } else { 0 } }\n"),
            ("list_int_all_positive",
             "fn main() -> Int { return if list_int_all_positive([0, 2]) { 0 } else { 42 } }\n"),
            ("list_int_all_positive",
             "fn main() -> Int { return if list_int_all_positive([-1, 2]) { 0 } else { 42 } }\n"),
            ("list_int_all_positive",
             "fn main() -> Int { return if list_int_all_positive([]) { 42 } else { 0 } }\n"),
            ("list_int_any_positive",
             "fn main() -> Int { return if list_int_any_positive([-2, 0, 3]) { 42 } else { 0 } }\n"),
            ("list_int_any_positive",
             "fn main() -> Int { return if list_int_any_positive([-2, 0]) { 0 } else { 42 } }\n"),
            ("list_int_any_positive",
             "fn main() -> Int { return if list_int_any_positive([]) { 0 } else { 42 } }\n"),
            ("list_int_sum_positive",
             "fn main() -> Int { return if list_int_sum_positive([-2, 0, 3, 5]) == 8 { 42 } else { 0 } }\n"),
            ("list_int_sum_positive",
             "fn main() -> Int { return if list_int_sum_positive([]) == 0 { 42 } else { 0 } }\n"),
            ("list_int_sum_negative",
             "fn main() -> Int { return if list_int_sum_negative([-2, 0, 3]) == -2 { 42 } else { 0 } }\n"),
            ("list_int_sum_negative",
             "fn main() -> Int { return if list_int_sum_negative([]) == 0 { 42 } else { 0 } }\n"),
            ("list_int_count_positive",
             "fn main() -> Int { return if list_int_count_positive([-2, 0, 3]) == 1 { 42 } else { 0 } }\n"),
            ("list_int_contains",
             "fn main() -> Int { var values = [2, 4, 6]; "
             "return if list_int_contains(values, 4) { 42 } else { 0 } }\n"),
            ("list_int_contains",
             "fn main() -> Int { var values = [-2, 0, 3]; "
             "return if list_int_contains(values, -2) { 42 } else { 0 } }\n"),
            ("list_bool_contains",
             "fn main() -> Int { var flags = [false, true, false]; "
             "return if list_bool_contains(flags, true) { 42 } else { 0 } }\n"),
            ("list_bool_count_true",
             "fn main() -> Int { return if list_bool_count_true([false, true, true]) == 2 "
             "{ 42 } else { 0 } }\n"),
            ("list_bool_count_false",
             "fn main() -> Int { return if list_bool_count_false([false, true, false]) == 2 "
             "{ 42 } else { 0 } }\n"),
            ("list_bool_any_false",
             "fn main() -> Int { return if list_bool_any_false([true, false]) { 42 } else { 0 } }\n"),
            ("list_bool_any_false",
             "fn main() -> Int { return if list_bool_any_false([true]) { 0 } else { 42 } }\n"),
            ("list_bool_any_false",
             "fn main() -> Int { return if list_bool_any_false([]) { 0 } else { 42 } }\n"),
            ("list_bool_any",
             "fn main() -> Int { return if list_bool_any([false, true]) && "
             "!list_bool_any([]) { 42 } else { 0 } }\n"),
            ("list_bool_none",
             "fn main() -> Int { return if list_bool_none([false, false]) && "
             "!list_bool_none([false, true]) && list_bool_none([]) { 42 } else { 0 } }\n"),
            ("list_bool_all",
             "fn main() -> Int { return if !list_bool_all([true, false]) && "
             "list_bool_all([]) { 42 } else { 0 } }\n"),
        )
        for function_name, caller in cases:
            with self.subTest(function=function_name):
                source_text = functions[function_name] + "\n" + caller
                with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
                    folder = pathlib.Path(temp)
                    source = folder / f"{function_name}.pep"
                    reference_source = folder / "reference.pep"
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source.write_text(source_text + "say(int_text(main()))\n",
                                                encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, "42\n")
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            result = self.invoke("run-c23", source, "--compiler", compiler)
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                            self.assertEqual(result.stdout, reference.stdout)



    def test_integer_runtime_failures_match_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        cases = (
            ("subtraction_overflow",
             "fn main() -> Int { return 0 - 9223372036854775807 - 2 }\n",
             "PEP_RUNTIME_OVERFLOW"),
            ("division_by_zero",
             "fn main() -> Int { return 1 / 0 }\n",
             "PEP_RUNTIME_DIVISION_BY_ZERO"),
            ("negation_overflow",
             "fn main() -> Int { var value = 0 - 9223372036854775807 - 1; return -value }\n",
             "PEP_RUNTIME_OVERFLOW"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            for name, source_text, runtime_code in cases:
                with self.subTest(case=name):
                    source = folder / f"{name}.pep"
                    reference_source = folder / f"{name}-reference.pep"
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertNotEqual(reference.returncode, 0,
                                        reference.stdout + reference.stderr)
                    self.assertIn(runtime_code, reference.stderr)
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source, "--compiler", compiler)
                            self.assertNotEqual(native.returncode, 0,
                                                native.stdout + native.stderr)
                            self.assertEqual(native.returncode, reference.returncode)
                            self.assertEqual(native.stderr.strip().splitlines()[-1],
                                             runtime_code)

    def test_pep_list_sum_overflow_matches_interpreter_runtime_code(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        functions = {
            definition.split("(", 1)[0].removeprefix("fn "): definition
            for definition in library.strip().split("\n\n")
        }
        source_text = (
            functions["list_int_sum"] + "\n"
            "fn main() -> Int { return list_int_sum([9223372036854775807, 1]) }\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            source = pathlib.Path(temp) / "sum_overflow.pep"
            reference_source = pathlib.Path(temp) / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertNotEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertIn("PEP_RUNTIME_OVERFLOW", reference.stderr)
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    native = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertNotEqual(native.returncode, 0, native.stdout + native.stderr)
                    self.assertEqual(native.returncode, reference.returncode)
                    self.assertEqual(native.stderr.strip().splitlines()[-1],
                                     "PEP_RUNTIME_OVERFLOW")

    def test_pep_list_negative_sum_overflow_matches_interpreter_runtime_code(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        functions = {
            definition.split("(", 1)[0].removeprefix("fn "): definition
            for definition in library.strip().split("\n\n")
        }
        source_text = (
            functions["list_int_sum_negative"] + "\n"
            "fn main() -> Int { return list_int_sum_negative([-9223372036854775807, -2]) }\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            source = pathlib.Path(temp) / "negative_sum_overflow.pep"
            reference_source = pathlib.Path(temp) / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertNotEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertIn("PEP_RUNTIME_OVERFLOW", reference.stderr)
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    native = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertNotEqual(native.returncode, 0, native.stdout + native.stderr)
                    self.assertEqual(native.returncode, reference.returncode)
                    self.assertEqual(native.stderr.strip().splitlines()[-1],
                                     "PEP_RUNTIME_OVERFLOW")

    def test_pep_list_product_overflow_matches_interpreter_runtime_code(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        functions = {
            definition.split("(", 1)[0].removeprefix("fn "): definition
            for definition in library.strip().split("\n\n")
        }
        source_text = (
            functions["list_int_product"] + "\n"
            "fn main() -> Int { return list_int_product([9223372036854775807, 2]) }\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            source = pathlib.Path(temp) / "product_overflow.pep"
            reference_source = pathlib.Path(temp) / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertNotEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertIn("PEP_RUNTIME_OVERFLOW", reference.stderr)
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    native = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertNotEqual(native.returncode, 0, native.stdout + native.stderr)
                    self.assertEqual(native.returncode, reference.returncode)
                    self.assertEqual(native.stderr.strip().splitlines()[-1],
                                     "PEP_RUNTIME_OVERFLOW")

    def test_for_in_conditionals_selectively_update_accumulator(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var total = 0\n"
            "  for item in [-3, 0, 2, 5] {\n"
            "    if item == 0 {\n"
            "      total = total + 10\n"
            "      total = total + 1\n"
            "    } else {\n"
            "      if item == 2 {\n"
            "        total = total + 20\n"
            "        total = total + 2\n"
            "      } else { total = total + item }\n"
            "    }\n"
            "  }\n"
            "  return total\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "conditional-for-in.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "35\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    generated_c = folder / f"conditional-for-in-{compiler.stem}.c"
                    result = self.invoke("run-c23", source, "--compiler", compiler,
                                         "--emit-c", generated_c)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)
                    c_source = generated_c.read_text(encoding="utf-8")
                    self.assertIn("if (!!(", c_source)
            unsupported_source = (
                "fn main() -> Int {\n"
                "  var total = 0\n"
                "  for item in [1] {\n"
                "    if item == 0 { let ignored = item } else { total = total + 3 }\n"
                "  }\n"
                "  return total\n"
                "}\n"
            )
            unsupported = folder / "unsupported-loop-statement.pep"
            unsupported.write_text(unsupported_source, encoding="utf-8", newline="\n")
            rejected = self.invoke("run-c23", unsupported, "--compiler", CLANG)
            self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)
            self.assertIn("Pep C23 unsupported:", rejected.stderr)

    def test_while_conditionals_update_loop_state(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "fn main() -> Int {\n"
            "  var index = 0\n"
            "  var total = 0\n"
            "  while index != 4 {\n"
            "    if index == 2 { total = total + 10 } else { total = total + index }\n"
            "    index = index + 1\n"
            "  }\n"
            "  return total\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "conditional-while.pep"
            reference_source = folder / "reference.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "14\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    generated_c = folder / f"conditional-while-{compiler.stem}.c"
                    result = self.invoke("run-c23", source, "--compiler", compiler,
                                         "--emit-c", generated_c)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)
                    c_source = generated_c.read_text(encoding="utf-8")
                    self.assertGreaterEqual(c_source.count("!!("), 2)

    def test_pep_written_last_index_of_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_last_index_of(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[4, 2, 4]", 4, 2),
            ("[4, 2, 4]", 2, 1),
            ("[-2, 0, -2]", -2, 2),
            ("[4, 2, 4]", 7, -1),
            ("[]", 0, -1),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, needle, expected) in enumerate(cases):
                with self.subTest(values=values, needle=needle):
                    source = folder / f"last_index_of_{index}.pep"
                    source_text = (
                        helper
                        + f"\nfn main() -> Int {{\n"
                        + f"  return list_int_last_index_of({values}, {needle})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"last_index_of_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_bool_first_or_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_bool_first_or(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[true, false]", "false", 42),
            ("[false, true]", "true", 0),
            ("[]", "true", 42),
            ("[]", "false", 0),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, fallback, expected) in enumerate(cases):
                with self.subTest(values=values, fallback=fallback):
                    source = folder / f"bool_first_or_{index}.pep"
                    source_text = (
                        helper
                        + f"\nfn main() -> Int {{\n"
                        + f"  return if list_bool_first_or({values}, {fallback}) {{ 42 }} else {{ 0 }}\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"bool_first_or_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_last_or_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_last_or(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[8, 2, 9]", 3, 9),
            ("[-2, 4]", 10, 4),
            ("[5]", 42, 5),
            ("[]", 42, 42),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, fallback, expected) in enumerate(cases):
                with self.subTest(values=values, fallback=fallback):
                    source = folder / f"last_or_{index}.pep"
                    source_text = (
                        helper
                        + f"\nfn main() -> Int {{\n"
                        + f"  return list_int_last_or({values}, {fallback})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"last_or_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_first_or_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_first_or(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[8, 2]", 3, 8),
            ("[-2, 4]", 10, -2),
            ("[]", 42, 42),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, fallback, expected) in enumerate(cases):
                with self.subTest(values=values, fallback=fallback):
                    source = folder / f"first_or_{index}.pep"
                    source_text = (
                        helper
                        + f"\nfn main() -> Int {{\n"
                        + f"  return list_int_first_or({values}, {fallback})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"first_or_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_index_of_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_index_of(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[4, 2, 4]", 4, 0),
            ("[4, 2, 4]", 2, 1),
            ("[-2, 0]", -2, 0),
            ("[4, 2, 4]", 7, -1),
            ("[]", 0, -1),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, needle, expected) in enumerate(cases):
                with self.subTest(values=values, needle=needle):
                    source = folder / f"index_of_{index}.pep"
                    source_text = (
                        helper
                        + f"\nfn main() -> Int {{\n"
                        + f"  return list_int_index_of({values}, {needle})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"index_of_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_min_or_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_min_or(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[8, 2, 5]", 3, 2),
            ("[-2, 4, -2]", 10, -2),
            ("[7]", -100, 7),
            ("[]", 42, 42),
            ("[]", -42, -42),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, fallback, expected) in enumerate(cases):
                with self.subTest(values=values, fallback=fallback):
                    source = folder / f"min_or_{index}.pep"
                    source_text = (
                        helper
                        + f"\nfn main() -> Int {{\n"
                        + f"  return list_int_min_or({values}, {fallback})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"min_or_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_max_or_helper_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_max_or(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[8, 2, 5]", 3, 8),
            ("[-2, 4, -2]", -10, 4),
            ("[7]", 100, 7),
            ("[]", 42, 42),
            ("[]", -42, -42),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, fallback, expected) in enumerate(cases):
                with self.subTest(values=values, fallback=fallback):
                    source = folder / f"max_or_{index}.pep"
                    source_text = (
                        helper
                        + f"\nfn main() -> Int {{\n"
                        + f"  return list_int_max_or({values}, {fallback})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"max_or_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_count_not_equal_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_count_not_equal(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[1, 2, 3, 2]", 2, 2),
            ("[-1, 0, 1]", 0, 2),
            ("[4, 4]", 4, 0),
            ("[4, 4]", 7, 2),
            ("[]", 0, 0),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, expected_value, expected_count) in enumerate(cases):
                with self.subTest(values=values, expected_value=expected_value):
                    source = folder / f"count_not_equal_{index}.pep"
                    source_text = (
                        helper
                        + f"\nfn main() -> Int {{\n"
                        + f"  return list_int_count_not_equal({values}, {expected_value})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"count_not_equal_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected_count) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_loop_bodies_can_return_early(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        cases = (
            ("for-in",
             "fn main() -> Int {\n"
             "  var total = 0\n"
             "  for item in [2, 3, 8] {\n"
             "    if item == 3 { return total + item } else { total = total + item }\n"
             "  }\n"
             "  return total\n"
             "}\n",
             "5\n"),
            ("while",
             "fn main() -> Int {\n"
             "  var index = 0\n"
             "  while index != 10 {\n"
             "    if index == 4 { return index + 38 } else { index = index + 1 }\n"
             "  }\n"
             "  return -1\n"
             "}\n",
             "42\n"),
            ("while-direct-return",
             "fn main() -> Int {\n"
             "  var index = 6\n"
             "  while index != 10 { return index }\n"
             "  return -1\n"
             "}\n",
             "6\n"),
            ("for-in-direct-return",
             "fn main() -> Int {\n"
             "  for item in [2, 3, 8] { return item }\n"
             "  return -1\n"
             "}\n",
             "2\n"),
            ("for-in-multiple-returns",
             "fn main() -> Int {\n"
             "  for item in [2] {\n"
             "    if item == 2 { return item } else { return item + 1 }\n"
             "  }\n"
             "  return -1\n"
             "}\n",
             "2\n"),
        )
        for label, source_text, expected in cases:
            with self.subTest(loop=label):
                with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
                    folder = pathlib.Path(temp)
                    source = folder / f"early-return-{label}.pep"
                    reference_source = folder / "reference.pep"
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, expected)
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            generated_c = folder / f"early-return-{label}-{compiler.stem}.c"
                            native = self.invoke("run-c23", source, "--compiler", compiler,
                                                 "--emit-c", generated_c)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)
                            c_source = generated_c.read_text(encoding="utf-8")
                            self.assertIn("pep_leave();", c_source)
                            if label == "for-in-multiple-returns":
                                self.assertEqual(c_source.count("pep_result_"), 4)

    def test_pep_written_count_between_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_count_between(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[1, 2, 3, 2]", 2, 4, 3),
            ("[-4, -1, 0, 2, 5]", -1, 2, 3),
            ("[3, 3, 3]", 3, 3, 3),
            ("[1, 2, 3]", 5, 1, 0),
            ("[]", -10, 10, 0),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, lower, upper, expected) in enumerate(cases):
                with self.subTest(values=values, lower=lower, upper=upper):
                    source = folder / f"count_between_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_int_count_between({values}, {lower}, {upper})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"count_between_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

            unsupported = folder / "four_parameter.pep"
            unsupported.write_text(
                "fn sum_four(first: Int, second: Int, third: Int, fourth: Int) -> Int {\n"
                "  return first + second + third + fourth\n"
                "}\n"
                "fn main() -> Int { return sum_four(1, 2, 3, 4) }\n",
                encoding="utf-8", newline="\n")
            rejected = self.invoke("run-c23", unsupported, "--compiler", CLANG)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("Pep C23 functions require supported scalar parameters and results",
                          rejected.stdout + rejected.stderr)

    def test_pep_written_sum_between_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_sum_between(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[1, 2, 3, 2]", 2, 4, 7),
            ("[-4, -1, 0, 2, 5]", -1, 2, 1),
            ("[3, 3, 3]", 3, 3, 9),
            ("[1, 2, 3]", 5, 1, 0),
            ("[]", -10, 10, 0),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, lower, upper, expected) in enumerate(cases):
                with self.subTest(values=values, lower=lower, upper=upper):
                    source = folder / f"sum_between_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_int_sum_between({values}, {lower}, {upper})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"sum_between_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_sum_outside_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_sum_outside(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[1, 2, 3, 2]", 2, 4, 1),
            ("[-4, -1, 0, 2, 5]", -1, 2, 1),
            ("[3, 3, 3]", 3, 3, 0),
            ("[1, 2, 3]", 5, 1, 6),
            ("[]", -10, 10, 0),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, lower, upper, expected) in enumerate(cases):
                with self.subTest(values=values, lower=lower, upper=upper):
                    source = folder / f"sum_outside_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_int_sum_outside({values}, {lower}, {upper})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"sum_outside_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_bool_longest_run_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_bool_longest_run(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[]", 0),
            ("[true]", 1),
            ("[false, false, false]", 3),
            ("[true, false, false, true]", 2),
            ("[false, true, false, true]", 1),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, expected) in enumerate(cases):
                with self.subTest(values=values):
                    source = folder / f"bool_longest_run_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_bool_longest_run({values})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"bool_longest_run_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_bool_longest_true_run_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_bool_longest_true_run(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[]", 0),
            ("[false, false]", 0),
            ("[true]", 1),
            ("[true, true, false, true]", 2),
            ("[false, true, true, true, false]", 3),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, expected) in enumerate(cases):
                with self.subTest(values=values):
                    source = folder / f"bool_longest_true_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_bool_longest_true_run({values})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"bool_longest_true_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_bool_count_runs_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_bool_count_runs(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[]", 0),
            ("[true]", 1),
            ("[false, false, false]", 1),
            ("[true, false, false, true, true]", 3),
            ("[false, true, false, true]", 4),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, expected) in enumerate(cases):
                with self.subTest(values=values):
                    source = folder / f"bool_count_runs_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_bool_count_runs({values})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"bool_count_runs_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_longest_run_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_longest_run(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[]", 0),
            ("[7]", 1),
            ("[1, 1, 1, 1]", 4),
            ("[1, 2, 2, 1, 1, 3]", 2),
            ("[-2, -2, 0, -2]", 2),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, expected) in enumerate(cases):
                with self.subTest(values=values):
                    source = folder / f"longest_run_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_int_longest_run({values})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"longest_run_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_count_falls_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_count_falls(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[]", 0),
            ("[9]", 0),
            ("[4, 3, 2, 1]", 3),
            ("[5, 5, 5]", 0),
            ("[-3, -1, -2, 4, 0, 1]", 2),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, expected) in enumerate(cases):
                with self.subTest(values=values):
                    source = folder / f"count_falls_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_int_count_falls({values})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"count_falls_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_non_decreasing_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_is_non_decreasing(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[]", True),
            ("[4]", True),
            ("[-2, -2, 0, 3]", True),
            ("[1, 3, 2, 4]", False),
            ("[5, 4, 3]", False),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, expected) in enumerate(cases):
                with self.subTest(values=values):
                    source = folder / f"non_decreasing_{index}.pep"
                    condition = (
                        f"list_int_is_non_decreasing({values})"
                        if expected else f"!list_int_is_non_decreasing({values})"
                    )
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return if {condition} {{ 42 }} else {{ 0 }}\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"non_decreasing_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, "42" + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_count_rises_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_count_rises(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[]", 0),
            ("[9]", 0),
            ("[1, 2, 3, 4]", 3),
            ("[5, 5, 5]", 0),
            ("[-3, -1, -2, 4, 0, 1]", 3),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, expected) in enumerate(cases):
                with self.subTest(values=values):
                    source = folder / f"count_rises_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_int_count_rises({values})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"count_rises_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_adjacent_equal_pairs_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_count_adjacent_equal_pairs(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[]", 0),
            ("[9]", 0),
            ("[1, 1, 1, 1]", 3),
            ("[1, 2, 2, 1, 1, 3]", 2),
            ("[-2, -2, 0, -2]", 1),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, expected) in enumerate(cases):
                with self.subTest(values=values):
                    source = folder / f"adjacent_equal_pairs_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_int_count_adjacent_equal_pairs({values})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"adjacent_equal_pairs_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_count_runs_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_count_runs(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[]", 0),
            ("[7]", 1),
            ("[1, 1, 1, 1]", 1),
            ("[1, 2, 2, 1, 1, 3]", 4),
            ("[-2, -2, 0, -2]", 3),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, expected) in enumerate(cases):
                with self.subTest(values=values):
                    source = folder / f"count_runs_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_int_count_runs({values})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"count_runs_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_sum_at_most_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_sum_at_most(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[1, 2, 3, 2]", 2, 5),
            ("[-4, -1, 0, 2, 5]", -1, -5),
            ("[3, 3, 3]", 3, 9),
            ("[1, 2, 3]", 0, 0),
            ("[]", 10, 0),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, upper, expected) in enumerate(cases):
                with self.subTest(values=values, upper=upper):
                    source = folder / f"sum_at_most_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_int_sum_at_most({values}, {upper})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"sum_at_most_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_pep_written_count_outside_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        library = (ROOT / "stdlib" / "collections.pep").read_text(encoding="utf-8")
        start = library.index("fn list_int_count_outside(")
        end = library.index("\n}\n", start) + 3
        helper = library[start:end]
        cases = (
            ("[1, 2, 3, 2]", 2, 4, 1),
            ("[-4, -1, 0, 2, 5]", -1, 2, 2),
            ("[3, 3, 3]", 3, 3, 0),
            ("[1, 2, 3]", 5, 1, 3),
            ("[]", -10, 10, 0),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for index, (values, lower, upper, expected) in enumerate(cases):
                with self.subTest(values=values, lower=lower, upper=upper):
                    source = folder / f"count_outside_{index}.pep"
                    source_text = (
                        helper
                        + "\nfn main() -> Int {\n"
                        + f"  return list_int_count_outside({values}, {lower}, {upper})\n"
                        + "}\n")
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"count_outside_ref_{index}.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n",
                        encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0,
                                     reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, str(expected) + chr(10))
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            native = self.invoke("run-c23", source,
                                                 "--compiler", compiler)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)

    def test_typed_empty_mutable_lists_use_zero_length_runtime_descriptors(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        cases = (
            ("Int",
             "fn count(values: List[Int]) -> Int {\n"
             "  var total = 0\n"
             "  for item in values { total = total + item }\n"
             "  return total\n"
             "}\n"
             "fn main() -> Int {\n"
             "  var values: List[Int] = []\n"
             "  return if contains(values, 9) || count(values) != 0 { 0 } else { 42 }\n"
             "}\n"),
            ("Bool",
             "fn count(values: List[Bool]) -> Int {\n"
             "  var total = 0\n"
             "  for item in values { total = total + if item { 1 } else { 0 } }\n"
             "  return total\n"
             "}\n"
             "fn main() -> Int {\n"
             "  var values: List[Bool] = []\n"
             "  return if contains(values, true) || count(values) != 0 { 0 } else { 42 }\n"
             "}\n"),
        )
        for element_type, source_text in cases:
            with self.subTest(element_type=element_type):
                with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
                    folder = pathlib.Path(temp)
                    source = folder / "typed-empty-mutable.pep"
                    reference_source = folder / "reference.pep"
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source.write_text(source_text + "say(int_text(main()))\n",
                                                encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, "42\n")
                    for compiler in (CLANG, GCC):
                        with self.subTest(compiler=compiler.name):
                            result = self.invoke("run-c23", source, "--compiler", compiler)
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                            self.assertEqual(result.stdout, reference.stdout)
