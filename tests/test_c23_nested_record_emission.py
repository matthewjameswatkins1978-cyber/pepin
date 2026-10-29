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


    def test_int_tagged_union_construction_helper_and_match_emit_c(self):
        source_text = (
            "type MaybeInt = None() | Some(Int)\n"
            "fn pass(value: MaybeInt) -> MaybeInt { return value }\n"
            "fn unwrap(value: MaybeInt) -> Int {\n"
            "  return match value {\n"
            "    None() => 0\n"
            "    Some(item) => item\n"
            "  }\n"
            "}\n"
            "fn main() -> Int {\n"
            "  let absent = pass(None())\n"
            "  let candidate = Some(42)\n"
            "  let present = pass(candidate)\n"
            "  return unwrap(present)\n"
            "}\n")
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "maybe-int.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\nsay(int_text(unwrap(pass(None()))))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "42\n0\n")

            generated = emit(source.read_bytes())
            self.assertRegex(
                generated,
                r"typedef struct \{ uint32_t tag; union \{ struct \{ int64_t field_0; \} payload_1; \} payload; \} pep_union_\d+;")
            self.assertRegex(
                generated,
                r"pep_union_\d+ pep_fn_\d+\(pep_union_\d+ pep_arg_\d+\);")
            self.assertRegex(generated, r"\.tag = 0")
            self.assertRegex(
                generated,
                r"\.tag = 1, \.payload\.payload_1 = \{ \.field_0 = 42 \}")
            self.assertRegex(generated, r"\.tag == 0")
            self.assertRegex(generated, r"\.tag == 1")
            self.assertRegex(generated, r"\.payload")
            self.assertIn("PEP_RUNTIME_INVALID_UNION", generated)

    def test_record_payload_union_variants_relay_and_match_fields(self):
        source_text = """type AstSpan { startByte: Int }
type AstValue = Number(Int) | Spanned(AstSpan)
fn relay(value: AstValue) -> AstValue { return value }
fn main() -> Int {
  let located = relay(Spanned(AstSpan { startByte: 31 }))
  let counted = Number(11)
  return match located {
    Number(number) => number
    Spanned(span) => span.startByte
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "ast-value.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "31\n")

            generated = emit(source.read_bytes())
            self.assertRegex(
                generated,
                r"typedef struct \{ uint32_t tag; union \{ struct \{ int64_t field_0; \} payload_0; "
                r"struct \{ pep_record_\d+ field_0; \} payload_1; \} payload; \} pep_union_\d+;")
            self.assertRegex(
                generated,
                r"pep_union_\d+ pep_fn_\d+\(pep_union_\d+ pep_arg_\d+\);")
            self.assertRegex(generated, r"\.tag = 0, \.payload\.payload_0 = \{ \.field_0 = 11 \}")
            self.assertRegex(
                generated,
                r"\.tag = 1, \.payload\.payload_1 = \{ \.field_0 = \(pep_record_\d+\)")
            self.assertRegex(generated, r"\.tag == 1")
            self.assertIn(".payload.payload_1.field_0.pep_field_0", generated)
            self.assertIn("PEP_RUNTIME_INVALID_UNION", generated)

    def test_tagged_union_rejects_non_int_payload_layout(self):
        source_text = (
            "type MaybeText = None() | Some(Str)\n"
            "fn main() -> Int { return 0 }\n")
        with self.assertRaisesRegex(ValueError, "unsupported layout"):
            emit(source_text.encode("utf-8"))

    def test_recursive_union_layout_fails_closed(self):
        source_text = (
            "type Chain = End() | Link(Chain)\n"
            "fn main() -> Int { return 0 }\n")
        with self.assertRaisesRegex(ValueError, "unsupported layout"):
            emit(source_text.encode("utf-8"))

    def test_bare_identifier_pattern_is_not_a_nullary_constructor(self):
        source_text = (
            "type MaybeInt = None() | Some(Int)\n"
            "fn unwrap(value: MaybeInt) -> Int { return match value { None => 7 } }\n"
            "fn main() -> Int { let value = None(); return unwrap(value) }\n")
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "bare-binding.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "7\n")
            with self.assertRaisesRegex(ValueError, "cover every constructor"):
                emit(source.read_bytes())

    def test_ast_integer_and_boolean_variants_with_record_payloads_emit_c(self):
        prefix = (
            "type AstSpan { end: Int }\n"
            "type AstValue = AstInteger(Int, AstSpan) | AstBoolean(Bool, AstSpan)\n"
            "fn relay(value: AstValue) -> AstValue { return value }\n"
            "fn main() -> Int { let value = relay(")
        suffix = (
            ")\n  return match value {\n"
            "    AstInteger(number, span) => span.end\n"
            "    AstBoolean(flag, span) => 0\n"
            "  }\n}\n")
        cases = (
            ("AstInteger(9, AstSpan { end: 23 })", "23\n", "payload_0", "field_0 = 9"),
            ("AstBoolean(true, AstSpan { end: 42 })", "0\n", "payload_1", "field_0 = 1"),
        )
        for index, (constructor, expected, payload, initializer) in enumerate(cases):
            with self.subTest(constructor=constructor), tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
                source_text = prefix + constructor + suffix
                source = pathlib.Path(temp_dir) / f"ast-value-{index}.pep"
                source.write_text(source_text, encoding="utf-8", newline="\n")
                reference = pathlib.Path(temp_dir) / "reference.pep"
                reference.write_text(
                    source_text + "say(int_text(main()))\n",
                    encoding="utf-8", newline="\n")

                interpreted = self.invoke("run", reference)
                self.assertEqual(interpreted.returncode, 0,
                                 interpreted.stdout + interpreted.stderr)
                self.assertEqual(interpreted.stdout, expected)

                generated = emit(source.read_bytes())
                if payload == "payload_0":
                    self.assertRegex(
                        generated,
                        r"struct \{ int64_t field_0; pep_record_\d+ field_1; \} payload_0;")
                else:
                    self.assertRegex(
                        generated,
                        r"struct \{ _Bool field_0; pep_record_\d+ field_1; \} payload_1;")
                self.assertIn(f".payload.{payload} = {{ .{initializer}", generated)
                if payload == "payload_0":
                    self.assertIn(".payload.payload_0.field_1.pep_field_0", generated)
                self.assertIn("PEP_RUNTIME_INVALID_UNION", generated)

    def test_tagged_union_more_than_two_payload_fields_fails_closed(self):
        source_text = (
            "type Many = Empty() | Full(Int, Int, Int)\n"
            "fn main() -> Int { let value = Full(1, 2, 3); return 0 }\n")
        with self.assertRaisesRegex(ValueError, "unsupported layout"):
            emit(source_text.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
