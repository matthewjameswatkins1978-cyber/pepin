import pathlib
import subprocess
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"


class PepC23NestedRecordEmissionTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
            cwd=ROOT, text=True, capture_output=True, check=False)

    def test_nested_record_construction_and_projection_emit_c(self):
        source_text = (
            "type Point { x: Int y: Int }\n"
            "type Box { point: Point }\n"
            "fn main() -> Int {\n"
            "  let box = Box { point: Point { x: 19, y: 23 } }\n"
            "  return box.point.x + box.point.y\n"
            "}\n")
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "nested-record.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")

            reference_source = pathlib.Path(temp_dir) / "nested-record-reference.pep"
            reference_source.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference_source)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "42\n")

            generated = emit(source.read_bytes())
            self.assertRegex(generated,
                             r"typedef struct \{ int64_t pep_field_0; int64_t pep_field_1; \} pep_record_\d+;")
            self.assertRegex(generated,
                             r"typedef struct \{ pep_record_\d+ pep_field_0; \} pep_record_\d+;")
            self.assertIn(".pep_field_0 = (pep_record_", generated)
            self.assertIn(".pep_field_0.pep_field_0", generated)
            self.assertIn(".pep_field_0.pep_field_1", generated)

    def test_forward_nested_record_declaration_fails_closed(self):
        source_text = (
            "type Box { point: Point }\n"
            "type Point { x: Int }\n"
            "fn main() -> Int { return 0 }\n")
        with self.assertRaisesRegex(ValueError, "preceding record declaration"):
            emit(source_text.encode("utf-8"))

    def test_nested_record_argument_is_lowered_by_value(self):
        source_text = (
            "type Point { x: Int y: Int }\n"
            "type Box { point: Point }\n"
            "fn sum(box: Box) -> Int { return box.point.x + box.point.y }\n"
            "fn main() -> Int {\n"
            "  let box = Box { point: Point { x: 19, y: 23 } }\n"
            "  return sum(box)\n"
            "}\n")
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "nested-record-argument.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "42\n")

            generated = emit(source.read_bytes())
            self.assertRegex(generated, r"pep_record_\d+ pep_arg_\d+")
            self.assertRegex(generated, r"pep_fn_\d+\(pep_local_\d+\)")
            self.assertIn(".pep_field_0.pep_field_0", generated)
            self.assertIn(".pep_field_0.pep_field_1", generated)


    def test_nested_record_return_and_projection_emit_c(self):
        source_text = (
            "type Point { x: Int y: Int }\n"
            "type Box { point: Point }\n"
            "fn make_box() -> Box {\n"
            "  return Box { point: Point { x: 19, y: 23 } }\n"
            "}\n"
            "fn relay(box: Box) -> Box { return box }\n"
            "fn main() -> Int {\n"
            "  let original = make_box()\n"
            "  let box = relay(original)\n"
            "  return box.point.x + 23\n"
            "}\n")
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "nested-record-return.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "42\n")

            generated = emit(source.read_bytes())
            self.assertRegex(
                generated,
                r"pep_record_\d+ pep_fn_\d+\(void\);")
            self.assertRegex(
                generated,
                r"pep_record_\d+ pep_fn_\d+\(pep_record_\d+ pep_arg_\d+\);")
            self.assertRegex(
                generated,
                r"pep_record_\d+ pep_result = pep_arg_\d+")
            self.assertRegex(
                generated,
                r"pep_record_\d+ pep_result = \(pep_record_\d+\)")
            self.assertRegex(generated, r"pep_record_\d+ pep_local_\d+ = pep_fn_\d+\(\)")
            self.assertIn(".pep_field_0.pep_field_0", generated)
            self.assertIn(".pep_field_1 = 23", generated)


if __name__ == "__main__":
    unittest.main()
