import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")
GCC = pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe")


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

    def test_run_c23_executes_native_output_for_typed_empty_mutable_list(self):
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
            source.write_text("type Point { x: Int }\n"
                              "type Located { point: Point }\n"
                              "fn main() -> Int {\n"
                              "  let located = Located { point: Point { x: 42 } }\n"
                              "  return located.point.x\n"
                              "}\n",
                              encoding="utf-8", newline="\n")
            generated = folder / "unsupported.c"
            rejected = self.invoke("run-c23", source, "--compiler", CLANG, "--emit-c", generated)
            self.assertEqual(rejected.returncode, 2, rejected.stdout + rejected.stderr)
            self.assertIn("Pep C23 unsupported:", rejected.stderr)
            self.assertFalse(generated.exists())
            source.write_text("fn main() -> Int { var values: List[Int] = []; return length(values) }\n",
                              encoding="utf-8", newline="\n")
            generated = folder / "empty-list.c"
            native = self.invoke("run-c23", source, "--compiler", CLANG, "--emit-c", generated)
            self.assertEqual(native.returncode, 0, native.stdout + native.stderr)
            self.assertEqual(native.stdout, "0\n")
            self.assertIn(".length = 0", generated.read_text(encoding="utf-8"))


    @unittest.skipUnless(GCC.is_file(), f"GCC not installed at {GCC}")
    def test_run_c23_builds_and_executes_pep_calls_with_gcc(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "sum.pep"
            source.write_text(
                "fn add(left: Int, right: Int) -> Int { return left + right }\n"
                "fn main() -> Int { return add(20, 22) }\n",
                encoding="utf-8", newline="\n")
            result = self.invoke("run-c23", source, "--compiler", GCC)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "42\n")

    def test_nested_distinct_helpers_fit_staged_compiler_pipeline(self):
        if not GCC.is_file():
            self.skipTest(f"GCC not installed at {GCC}")
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            source = pathlib.Path(temp) / "nested.pep"
            source.write_text(
                "fn negate(value: Bool) -> Bool { return !value }\n"
                "fn identity(value: Bool) -> Bool { return value }\n"
                "fn main() -> Int { return if identity(negate(false)) { 42 } else { 0 } }\n",
                encoding="utf-8", newline="\n")
            reference_source = pathlib.Path(temp) / "nested_reference.pep"
            reference_source.write_text(source.read_text(encoding="utf-8") +
                                        "say(int_text(main()))\n", encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    result = self.invoke("run-c23", source, "--compiler", compiler)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, reference.stdout)
                    self.assertEqual(result.stdout, "42\n")

    def test_scalar_record_construction_and_field_access_match_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        programs = (
            ("record-parameter-by-value",
             "type Point { x: Int y: Int }\n"
             "fn sum(point: Point) -> Int { return point.x + point.y }\n"
             "fn main() -> Int { let point = Point { y: 22, x: 20 }; return sum(point) }\n"),
            ("bool-record-field",
             "type Mark { enabled: Bool code: Int }\n"
             "fn main() -> Int { let mark = Mark { code: 42, enabled: true }; return if mark.enabled { mark.code } else { 0 } }\n"),
        )
        for case, source_text in programs:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
                    folder = pathlib.Path(temp)
                    source = folder / f"{case}.pep"
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference_source = folder / f"{case}-reference.pep"
                    reference_source.write_text(
                        source_text + "say(int_text(main()))\n", encoding="utf-8", newline="\n")
                    reference = self.invoke("run", reference_source)
                    self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
                    self.assertEqual(reference.stdout, "42\n")
                    for compiler in (CLANG, GCC):
                        with self.subTest(case=case, compiler=compiler.name):
                            generated = folder / f"{case}-{compiler.stem}.c"
                            native = self.invoke("run-c23", source, "--compiler", compiler,
                                                 "--emit-c", generated)
                            self.assertEqual(native.returncode, 0, native.stdout + native.stderr)
                            self.assertEqual(native.stdout, reference.stdout)
                            self.assertIn("typedef struct", generated.read_text(encoding="utf-8"))

    def test_record_lists_pass_by_value_and_length_match_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "type Point { x: Int y: Int }\n"
            "fn count(points: List[Point]) -> Int { return length(points) }\n"
            "fn forward(points: List[Point]) -> Int { return count(points) }\n"
            "fn main() -> Int { return forward([Point { x: 10, y: 20 }, Point { x: 12, y: 22 }]) }\n")
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "record-list-values.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source = folder / "record-list-values-reference.pep"
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "2\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    generated = folder / f"record-list-values-{compiler.stem}.c"
                    native = self.invoke("run-c23", source, "--compiler", compiler,
                                         "--emit-c", generated)
                    self.assertEqual(native.returncode, 0, native.stdout + native.stderr)
                    self.assertEqual(native.stdout, reference.stdout)
                    self.assertIn("pep_list_record_", generated.read_text(encoding="utf-8"))

    def test_record_list_for_in_matches_interpreter_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        source_text = (
            "type Point { x: Int y: Int }\n"
            "fn sum_points(points: List[Point]) -> Int {\n"
            "  var total = 0\n"
            "  for point in points { total = total + point.x + point.y }\n"
            "  return total\n"
            "}\n"
            "fn main() -> Int { return sum_points([Point { x: 10, y: 11 }, Point { x: 9, y: 12 }]) }\n")
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            folder = pathlib.Path(temp)
            source = folder / "record-list-loop.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference_source = folder / "record-list-loop-reference.pep"
            reference_source.write_text(source_text + "say(int_text(main()))\n",
                                        encoding="utf-8", newline="\n")
            reference = self.invoke("run", reference_source)
            self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
            self.assertEqual(reference.stdout, "42\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    generated = folder / f"record-list-loop-{compiler.stem}.c"
                    native = self.invoke("run-c23", source, "--compiler", compiler,
                                         "--emit-c", generated)
                    self.assertEqual(native.returncode, 0, native.stdout + native.stderr)
                    self.assertEqual(native.stdout, reference.stdout)
                    self.assertIn("pep_record_", generated.read_text(encoding="utf-8"))

    def test_c23_unsupported_programs_fail_closed_consistently_on_clang_and_gcc(self):
        if not CLANG.is_file() or not GCC.is_file():
            self.skipTest("both Clang and GCC are required for the differential native check")
        cases = (
            ("record-string-field",
             "type Label { text: Str }\n"
             "fn main() -> Int { let label = Label { text: \"hello\" }; return 42 }\n",
             "Pep C23 unsupported: Pep C23 records currently require fields of type Int or Bool",
             "valid"),
            ("record-fallible-initializer",
             "type Value { value: Int }\n"
             "fn calculate() -> Int { return 42 }\n"
             "fn main() -> Int { let value = Value { value: calculate() }; return value.value }\n",
             "Pep C23 unsupported: Pep C23 record field initializers currently require expressions without runtime failure",
             "valid"),
            ("record-list-empty-pep-checker-mismatch",
             "type Point { x: Int }\n"
             "fn count(points: List[Point]) -> Int { return length(points) }\n"
             "fn main() -> Int { return count([]) }\n",
             "Pep C23 unsupported: Pep C23 emission requires a valid Pep checker report",
             "valid"),
            ("bool-main",
             "fn main() -> Bool { return true }\n",
             "Pep C23 unsupported: Pep C23 main function must return Int",
             "valid"),
            ("unit-main",
             "fn main() -> Unit { return say(\"hello\") }\n",
             "Pep C23 unsupported: Pep C23 main function must return Int",
             "valid"),
            ("say-in-main",
             "fn main() -> Int { say(\"hello\"); return 0 }\n",
             "Pep C23 unsupported: Pep C23 functions require local bindings and supported loops followed by one return",
             "valid"),
            ("ill-typed-main",
             "fn main() -> Int { return true }\n",
             "Pep C23 unsupported: Pep C23 emission requires a valid Pep checker report",
             "invalid"),
        )
        for case, source_text, diagnostic, check_status in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
                    folder = pathlib.Path(temp)
                    source = folder / f"{case}.pep"
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    checked = self.invoke("check", source, "--json")
                    self.assertIn(f'"status":"{check_status}"', checked.stdout)
                    for compiler in (CLANG, GCC):
                        with self.subTest(case=case, compiler=compiler.name):
                            generated = folder / f"{case}-{compiler.stem}.c"
                            native = self.invoke("run-c23", source, "--compiler", compiler,
                                                 "--emit-c", generated)
                            self.assertEqual(native.returncode, 2,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, "")
                            self.assertEqual(native.stderr.strip(), diagnostic)
                            self.assertFalse(generated.exists())

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