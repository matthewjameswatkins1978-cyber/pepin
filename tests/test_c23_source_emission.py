import pathlib
import subprocess
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]


class C23RecordSourceEmissionTests(unittest.TestCase):
    def test_scalar_record_construction_binding_projection_and_reference(self):
        source = (
            "type Point { x: Int, y: Int }\n"
            "fn main() -> Int {\n"
            "  let point = Point { y: 23, x: 19 }\n"
            "  return point.x + point.y\n"
            "}\n"
        )
        generated = emit(source.encode("utf-8"))
        self.assertIn("typedef struct { int64_t pep_field_0; int64_t pep_field_1; } pep_record_", generated)
        self.assertIn("= (pep_record_", generated)
        self.assertIn(".pep_field_1 = 23, .pep_field_0 = 19", generated)
        self.assertIn("pep_local_", generated)
        self.assertIn(".pep_field_0", generated)
        self.assertIn(".pep_field_1", generated)

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            reference_source = pathlib.Path(temp) / "record-reference.pep"
            reference_source.write_text(
                source + "say(int_text(main()))\n",
                encoding="utf-8",
                newline="\n",
            )
            reference = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "run", str(reference_source)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
        self.assertEqual(reference.stdout, "42\n")
    def test_records_pass_through_and_return_from_helpers(self):
        source = (
            "type Point { x: Int, y: Int }\n"
            "fn make_point() -> Point { return Point { x: 19, y: 23 } }\n"
            "fn relay(point: Point) -> Point { return point }\n"
            "fn total(point: Point) -> Int { return point.x + point.y }\n"
            "fn main() -> Int {\n"
            "  let point = relay(make_point())\n"
            "  return total(point)\n"
            "}\n"
        )
        generated = emit(source.encode("utf-8"))
        self.assertIn("pep_record_0 pep_fn_", generated)
        self.assertIn("pep_record_0 pep_arg_", generated)
        self.assertIn("pep_record_0 pep_result =", generated)
        self.assertIn("= (pep_record_0){ .pep_field_0 = 19, .pep_field_1 = 23 }", generated)
        self.assertIn("pep_fn_", generated)

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            reference_source = pathlib.Path(temp) / "record-helper-reference.pep"
            reference_source.write_text(source + "say(int_text(main()))\n", encoding="utf-8", newline="\n")
            reference = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "run", str(reference_source)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
        self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
        self.assertEqual(reference.stdout, "42\n")

    def test_c_record_names_are_mangled_and_forward_types_precede_prototypes(self):
        source = (
            "fn make() -> int { return int { x: 42 } }\n"
            "type int { x: Int }\n"
            "fn int() -> Int { return 0 }\n"
            "type _Point { x: Int }\n"
            "type FILE { x: Int }\n"
            "type NULL { x: Int }\n"
            "fn main() -> Int { let point = make(); return point.x }\n"
        )
        generated = emit(source.encode("utf-8"))
        self.assertEqual(generated.count("typedef struct {"), 4)
        self.assertIn("typedef struct { int64_t pep_field_0; } pep_record_", generated)
        self.assertNotIn("} int;", generated)
        self.assertNotIn("} _Point;", generated)
        self.assertNotIn("} FILE;", generated)
        self.assertNotIn("} NULL;", generated)
        self.assertLess(generated.index("typedef struct {"), generated.index("pep_fn_"))

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            reference_source = pathlib.Path(temp) / "record-name-reference.pep"
            reference_source.write_text(source + "say(int_text(main()))\n", encoding="utf-8", newline="\n")
            reference = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "run", str(reference_source)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
        self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
        self.assertEqual(reference.stdout, "42\n")

    def test_record_payload_union_passes_helpers_and_matches(self):
        source = (
            "type AstSpan { start: Int, end: Int }\n"
            "type Maybe = None() | Some(AstSpan)\n"
            "fn relay(value: Maybe) -> Maybe { return value }\n"
            "fn main() -> Int {\n"
            "  let wrapped = relay(Some(AstSpan { start: 7, end: 23 }))\n"
            "  return match wrapped {\n"
            "    None() => 0\n"
            "    Some(span) => span.end\n"
            "  }\n"
            "}\n"
        )
        generated = emit(source.encode("utf-8"))
        self.assertIn("pep_record_0 field_0; } payload_1", generated)
        self.assertIn(".tag = 1, .payload.payload_1 = { .field_0 = (pep_record_0)", generated)
        self.assertIn(".payload.payload_1.field_0.pep_field_1", generated)
        self.assertIn(".tag == 0", generated)
        self.assertIn(".tag == 1", generated)
        self.assertIn("PEP_RUNTIME_INVALID_UNION", generated)

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            reference_source = pathlib.Path(temp) / "union-record-reference.pep"
            reference_source.write_text(source + "say(int_text(main()))\n", encoding="utf-8", newline="\n")
            reference = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "run", str(reference_source)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
        self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
        self.assertEqual(reference.stdout, "23\n")

    def test_record_and_scalar_union_variants_are_constructed(self):
        source = (
            "type Point { x: Int }\n"
            "type Mixed = Wrapped(Point) | Number(Int)\n"
            "fn main() -> Int {\n"
            "  let recordValue = Wrapped(Point { x: 23 })\n"
            "  let numberValue = Number(7)\n"
            "  return 0\n"
            "}\n"
        )
        generated = emit(source.encode("utf-8"))
        self.assertIn("pep_record_0 field_0; } payload_0; struct { int64_t field_0; } payload_1;", generated)
        self.assertIn(".tag = 0, .payload.payload_0 = { .field_0 = (pep_record_0)", generated)
        self.assertIn(".tag = 1, .payload.payload_1 = { .field_0 = 7", generated)

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            reference_source = pathlib.Path(temp) / "union-constructors-reference.pep"
            reference_source.write_text(source + "say(int_text(main()))\n", encoding="utf-8", newline="\n")
            reference = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "run", str(reference_source)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
        self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
        self.assertEqual(reference.stdout, "0\n")

    def test_two_payload_union_matches_scalar_and_record_fields(self):
        source = (
            "type S { a: Int, b: Int }\n"
            "type V = E() | I(Int, S)\n"

            "fn main() -> Int {\n"
            "  let node = I(19, S { a: 3, b: 23 })\n"
            "  return match node {\n"
            "    E() => 0\n"
            "    I(number, span) => span.b\n"
            "  }\n"
            "}\n"
        )
        generated = emit(source.encode("utf-8"))
        self.assertIn("int64_t field_0; pep_record_0 field_1; } payload_1;", generated)
        self.assertIn(".payload.payload_1 = { .field_0 = 19, .field_1 = (pep_record_0)", generated)
        self.assertIn(".payload.payload_1.field_1.pep_field_1", generated)

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp:
            reference_source = pathlib.Path(temp) / "ast-integer-reference.pep"
            reference_source.write_text(source + "say(int_text(main()))\n", encoding="utf-8", newline="\n")
            reference = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "run", str(reference_source)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
        self.assertEqual(reference.returncode, 0, reference.stdout + reference.stderr)
        self.assertEqual(reference.stdout, "23\n")

    def test_bare_identifier_pattern_is_not_nullary_constructor(self):
        source = (
            "type Maybe = None() | Some(Int)\n"
            "fn main() -> Int {\n"
            "  let value = None()\n"
            "  return match value { None => 7 }\n"
            "}\n"
        )
        with self.assertRaisesRegex(ValueError, "bare identifiers are bindings"):
            emit(source.encode("utf-8"))

    def test_non_exhaustive_union_match_fails_closed(self):
        source = (
            "type Maybe = None() | Some(Int)\n"
            "fn main() -> Int {\n"
            "  let value = None()\n"
            "  return match value { None() => 0 }\n"
            "}\n"
        )
        with self.assertRaisesRegex((RuntimeError, ValueError), "exhaustive|constructor|valid Pep checker report"):
            emit(source.encode("utf-8"))
    def test_recursive_union_payload_fails_closed(self):
        source = "type Chain = End() | Link(Chain)\nfn main() -> Int { return 0 }\n"
        with self.assertRaisesRegex(ValueError, "unsupported layout"):
            emit(source.encode("utf-8"))

    def test_unsupported_union_payload_type_fails_closed(self):
        source = "type Maybe = None() | Some(Bool)\nfn main() -> Int { return 0 }\n"
        with self.assertRaisesRegex(ValueError, "unsupported layout"):
            emit(source.encode("utf-8"))
    def test_nested_record_layout_fails_closed(self):
        source = (
            "type Point { x: Int }\n"
            "type Box { point: Point }\n"
            "fn main() -> Int { return 0 }\n"
        )
        with self.assertRaisesRegex(ValueError, "record layout supports"):
            emit(source.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
