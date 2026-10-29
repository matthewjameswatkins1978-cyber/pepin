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


if __name__ == "__main__":
    unittest.main()
