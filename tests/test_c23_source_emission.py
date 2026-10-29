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
    def test_record_parameters_fail_closed_until_function_boundary_lowering(self):
        source = (
            "type Point { x: Int }\n"
            "fn get_x(point: Point) -> Int { return point.x }\n"
            "fn main() -> Int {\n"
            "  let point = Point { x: 42 }\n"
            "  return get_x(point)\n"
            "}\n"
        )
        with self.assertRaisesRegex(ValueError, "supported scalar parameters"):
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
