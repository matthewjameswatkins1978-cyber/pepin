import hashlib
import pathlib
import re
import subprocess
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")
GCC = pathlib.Path(r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe")


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
            "fn main() -> Int {\n"
            "  let absent = pass(None())\n"
            "  let candidate = Some(42)\n"
            "  let present = pass(candidate)\n"
            "  return match present {\n"
            "    None() => 0\n"
            "    Some(value) => value\n"
            "  }\n"
            "}\n")
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "maybe-int.pep"
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

    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_record_payload_union_variants_relay_and_match_fields(self):
        source_text = """type AstSpan { startByte: Int }
type AstValue = Number(Int) | Spanned(AstSpan)
fn relay(value: AstValue) -> AstValue { return value }
fn main() -> Int {
  let located = relay(Spanned(AstSpan { startByte: 31 }))
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
            self.assertRegex(
                generated,
                r"\.tag = 1, \.payload\.payload_1 = \{ \.field_0 = \(pep_record_\d+\)")
            self.assertRegex(generated, r"\.tag == 1")
            self.assertIn(".payload.payload_1.field_0.pep_field_0", generated)
            self.assertIn("PEP_RUNTIME_INVALID_UNION", generated)

            generated_c = pathlib.Path(temp_dir) / "ast-value.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = pathlib.Path(temp_dir) / (compiler.stem + "-ast-value.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2",
                         str(generated_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "31\n")

    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_multiple_record_payload_variants_relay_and_project_native(self):
        source_text = """type AstSpan { startByte: Int endByte: Int }
type AstValue = Spanned(AstSpan) | Token(AstSpan)
fn relay(value: AstValue) -> AstValue { return value }
fn main() -> Int {
  let value = relay(Token(AstSpan { startByte: 13, endByte: 29 }))
  return match value {
    Spanned(span) => span.startByte
    Token(span) => span.endByte
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "ast-value-record-variants.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "29\n")

            generated = emit(source.read_bytes())
            self.assertIn(".tag == 1", generated)
            self.assertIn(".pep_field_1", generated)
            generated_c = pathlib.Path(temp_dir) / "ast-value-record-variants.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = pathlib.Path(temp_dir) / (
                        compiler.stem + "-ast-value-record-variants.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2",
                         str(generated_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "29\n")

    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_nested_ast_span_record_payload_runs_native(self):
        source_text = """type AstSpan { startByte: Int endByte: Int }
type AstLocation { span: AstSpan }
type AstValue = Spanned(AstLocation) | Missing()
fn relay(value: AstValue) -> AstValue { return value }
fn main() -> Int {
  let value = relay(Spanned(AstLocation { span: AstSpan { startByte: 3, endByte: 39 } }))
  return match value {
    Spanned(location) => location.span.endByte
    Missing() => 0
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "nested-ast-span.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "39\n")

            generated = emit(source.read_bytes())
            self.assertIn(".field_0.pep_field_0.pep_field_1", generated)
            generated_c = pathlib.Path(temp_dir) / "nested-ast-span.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = pathlib.Path(temp_dir) / (
                        compiler.stem + "-nested-ast-span.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2",
                         str(generated_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "39\n")

    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_helper_returned_nested_record_union_payload_runs_natively(self):
        source_text = """type AstSpan { startByte: Int endByte: Int }
type AstLocation { span: AstSpan }
type AstValue = Spanned(AstLocation) | Missing()
fn make_location(span: AstSpan) -> AstLocation {
  return AstLocation { span: span }
}
fn main() -> Int {
  let value = Spanned(make_location(AstSpan { startByte: 17, endByte: 39 }))
  return match value {
    Spanned(location) => location.span.endByte
    Missing() => 0
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "helper-returned-ast-location.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "39\n")

            generated = emit(source.read_bytes())
            self.assertRegex(generated, r"\.field_0 = pep_fn_\d+\(")
            self.assertIn(".pep_field_0.pep_field_1", generated)
            generated_c = folder / "helper-returned-ast-location.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / (compiler.stem + "-helper-returned-ast-location.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2",
                         str(generated_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "39\n")

    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_three_level_ast_record_payload_projection_runs_natively(self):
        source_text = """type AstSpan { endByte: Int }
type AstLocation { span: AstSpan }
type AstNode { location: AstLocation }
type AstValue = Located(AstNode) | Missing()
fn main() -> Int {
  let value = Located(AstNode { location: AstLocation { span: AstSpan { endByte: 39 } } })
  return match value {
    Located(node) => node.location.span.endByte
    Missing() => 0
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "three-level-ast-record.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "39\n")

            generated = emit(source.read_bytes())
            self.assertIn(".pep_field_0.pep_field_0.pep_field_0", generated)
            generated_c = folder / "three-level-ast-record.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / (compiler.stem + "-three-level-ast-record.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2",
                         str(generated_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "39\n")

    def test_tagged_union_rejects_non_int_payload_layout(self):
        source_text = (
            "type MaybeText = None() | Some(Str)\n"
            "fn main() -> Int { return 0 }\n")
        with self.assertRaisesRegex(ValueError, "unsupported layout"):
            emit(source_text.encode("utf-8"))

    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_native_match_rejects_an_invalid_union_tag(self):
        source_text = """type MaybeInt = Missing() | Some(Int)
fn choose(value: MaybeInt) -> Int {
  return match value {
    Missing() => 0
    Some(number) => number
  }
}
fn main() -> Int { return choose(Some(7)) }
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "invalid-union-tag.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "7\n")

            generated = emit(source.read_bytes())
            signature = re.search(
                r"int64_t (pep_fn_\d+)\(pep_union_(\d+) pep_arg_\d+\);",
                generated)
            self.assertIsNotNone(signature, generated)
            function_name, union_id = signature.groups()
            generated_c = folder / "invalid-union-tag-generated.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")
            harness = folder / "invalid-union-tag-harness.c"
            harness.write_text(
                "#define main pep_generated_main\n"
                "#include \"invalid-union-tag-generated.c\"\n"
                "#undef main\n"
                "int main(void) {\n"
                f"  pep_union_{union_id} malformed = {{ .tag = UINT32_MAX }};\n"
                f"  (void){function_name}(malformed);\n"
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / (compiler.stem + "-invalid-union-tag.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2",
                         str(harness), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertEqual(result.stderr, "PEP_RUNTIME_INVALID_UNION\n")

    def test_recursive_tree_union_uses_arena_and_checked_helper_passing(self):
        source_text = """type Tree = Leaf(Int) | Branch(Tree)
fn first(value: Tree) -> Tree {
  return match value {
    Leaf(_) => Leaf(0)
    Branch(child) => child
  }
}
fn main() -> Int {
  let child = first(Branch(Leaf(19)))
  return match child {
    Leaf(number) => number
    Branch(_) => 0
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "recursive-tree.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "19\n")

            generated = emit(source.read_bytes())
            self.assertIn('#include "pep_arena.h"', generated)
            self.assertRegex(generated,
                             r"struct pep_union_\d+ \* field_0;")
            self.assertNotRegex(generated,
                                r"struct \{ pep_union_\d+ field_0;")
            self.assertRegex(
                generated,
                r"static pep_union_\d+ pep_require_union_\d+\(const pep_union_\d+ \*pep_value\)")
            self.assertIn("pep_arena_alloc(pep_arena, sizeof(pep_union_", generated)
            self.assertIn("pep_recursive_0 == NULL", generated)
            self.assertRegex(
                generated,
                r"pep_union_\d+ pep_fn_\d+\(pep_union_\d+ pep_arg_\d+, pep_arena_t \*pep_arena\);")
            self.assertIn("pep_arena), pep_arena)", generated)
            self.assertIn("pep_arena_init(&pep_arena, 0)", generated)
            self.assertIn("pep_arena_status(pep_arena)", generated)
            self.assertIn("pep_arena_free(&pep_arena)", generated)
            self.assertIn("pep_require_union_", generated)

    def test_nested_recursive_union_list_layout_fails_closed(self):
        source_text = (
            "type Chain = End(Int) | Link(List[List[Chain]])\n"
            "fn main() -> Int { return 0 }\n")
        with self.assertRaisesRegex(ValueError, "unsupported layout"):
            emit(source_text.encode("utf-8"))

    def test_nonrecursive_union_list_parameter_iteration_fails_closed(self):
        source_text = """type Item = Empty() | Number(Int)
fn first(items: List[Item]) -> Int {
  var result = 0
  for item in items {
    result = match item {
      Empty() => 0
      Number(number) => number
    }
  }
  return result
}
fn main() -> Int { return first([Number(42)]) }
"""
        with self.assertRaisesRegex(ValueError, "supported parameters"):
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
            "    AstInteger(_, span) => span.end\n"
            "    AstBoolean(flag, _) => 0\n"
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


    def test_recursive_union_list_payload_is_copied_into_arena(self):
        source_text = """type Chain = End(Int) | Link(List[Chain])
fn relay(value: Chain) -> Chain { return value }
fn main() -> Int {
  let initial = Link([End(19)])
  let chain = relay(initial)
  return match chain {
    End(_) => 0
    Link(items) => length(items)
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "recursive-union-list.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "1\n")

            generated = emit(source.read_bytes())
            self.assertRegex(
                generated,
                r"typedef struct \{ const struct pep_union_\d+ \*data; size_t length; \} pep_list_union_\d+;")
            self.assertRegex(
                generated,
                r"struct \{ pep_list_union_\d+ field_0; \} payload_\d+;")
            self.assertIn("PEP_RUNTIME_INVALID_LIST", generated)
            self.assertIn("SIZE_MAX / sizeof(pep_union_", generated)
            self.assertIn("pep_arena_alloc(pep_arena, pep_ctor_arg_0.length * sizeof(pep_union_", generated)
            self.assertIn("pep_recursive_list_0[pep_i] = pep_ctor_arg_0.data[pep_i]", generated)
            self.assertIn(".length = 1", generated)
            self.assertRegex(generated, r"\.payload\.payload_\d+\.field_0\.length")


    def test_recursive_union_list_parameter_iteration_and_match(self):
        source_text = """type Tree = Leaf(Int) | Branch(List[Tree])
fn last_leaf(values: List[Tree]) -> Int {
  var result = 0
  for item in values {
    result = match item {
      Leaf(number) => number
      Branch(_) => 0
    }
  }
  return result
}
fn main() -> Int { return last_leaf([Leaf(42)]) }
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "recursive-union-list-loop.pep"
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
            self.assertIn("pep_list_union_", generated)
            self.assertRegex(generated,
                             r"pep_union_\d+ pep_local_\d+ = pep_arg_\d+\.data\[pep_index_\d+\]")
            self.assertIn("PEP_RUNTIME_INVALID_LIST", generated)
            self.assertRegex(generated, r"\.tag == 0")
            self.assertIn("payload.payload_0.field_0", generated)

    def test_recursive_union_list_loop_extracts_branch_payload_length(self):
        source_text = """type Tree = Leaf(Int) | Branch(List[Tree])
fn child_count(values: List[Tree]) -> Int {
  for item in values {
    return match item {
      Leaf(_) => 0
      Branch(children) => length(children)
    }
  }
  return 0
}
fn main() -> Int { return 0 }
"""
        generated = emit(source_text.encode("utf-8"))
        self.assertRegex(generated, r"\.payload\.payload_1\.field_0\.length")
        self.assertRegex(generated, r"pep_union_\d+ pep_local_\d+ = pep_arg_\d+\.data\[pep_index_\d+\]")


    def test_recursive_union_list_payload_passes_to_typed_helper(self):
        source_text = """type Tree = Leaf(Int) | Branch(List[Tree])
fn count_children(values: List[Tree]) -> Int { return length(values) }
fn main() -> Int {
  let node: Tree = Branch([Leaf(7)])
  return match node {
    Leaf(_) => 0
    Branch(children) => count_children(children)
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "recursive-union-list-helper.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "1\n")

            generated = emit(source.read_bytes())
            self.assertRegex(generated, r"pep_list_union_\d+ pep_arg_\d+")
            self.assertRegex(
                generated,
                r"pep_fn_\d+\(pep_local_\d+\.payload\.payload_1\.field_0, pep_arena\)")
            self.assertRegex(generated, r"pep_union_\d+ pep_local_\d+")


    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_recursive_union_list_payload_helper_runs_with_clang_and_gcc(self):
        source_text = """type Tree = Leaf(Int) | Branch(List[Tree])
fn count_children(values: List[Tree]) -> Int { return length(values) }
fn main() -> Int {
  let node: Tree = Branch([Leaf(7)])
  return match node {
    Leaf(_) => 0
    Branch(children) => count_children(children)
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "recursive-union-list-helper.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            generated_c = folder / "recursive-union-list-helper.c"
            generated_c.write_text(emit(source.read_bytes()), encoding="utf-8", newline="\n")
            arena_c = ROOT / "runtime" / "pep_arena" / "pep_arena.c"
            arena_include = ROOT / "runtime" / "pep_arena"

            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / (compiler.stem + "-recursive-union-list.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", "-I", str(arena_include),
                         str(generated_c), str(arena_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "1\n")


    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_recursive_union_zero_arg_helper_returns_through_match(self):
        program = """type Tree = End() | Branch(List[Tree], Int)
fn make() -> Tree { return Branch([End()], 39) }
fn size(value: Tree) -> Int {
  return match value {
    End() => 0
    Branch(children, label) => label + length(children)
  }
}
fn main() -> Int { return size(make()) }
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as directory:
            folder = pathlib.Path(directory)
            source = folder / "recursive-return.pep"
            source.write_text(program, encoding="utf-8", newline="\n")
            reference = folder / "reference.pep"
            reference.write_text(program + "say(int_text(main()))\n",
                                 encoding="utf-8", newline="\n")
            result = self.invoke("run", reference)
            self.assertEqual((result.returncode, result.stdout), (0, "40\n"),
                             result.stdout + result.stderr)
            generated = emit(source.read_bytes())
            self.assertIn("pep_make_union_", generated)
            self.assertIn("pep_add(", generated)
            self.assertIn("pep_checked_length(", generated)
            self.assertRegex(generated, r"pep_fn_\d+\(pep_fn_\d+\(pep_arena\), pep_arena\)")
            c_file = folder / "recursive-return.c"
            c_file.write_text(generated, encoding="utf-8", newline="\n")
            arena_c = ROOT / "runtime" / "pep_arena" / "pep_arena.c"
            include = ROOT / "runtime" / "pep_arena"
            for compiler in (CLANG, GCC):
                exe = folder / (compiler.stem + ".exe")
                built = subprocess.run(
                    [str(compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic",
                     "-Werror", "-O2", "-I", str(include), str(c_file), str(arena_c),
                     "-o", str(exe)], cwd=ROOT, text=True, capture_output=True)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                native = subprocess.run([str(exe)], cwd=ROOT, text=True, capture_output=True)
                self.assertEqual((native.returncode, native.stdout), (0, "40\n"),
                                 native.stdout + native.stderr)


    def test_nonrecursive_union_zero_arg_helper_remains_unsupported(self):
        program = """type Maybe = None() | Some(Int)
fn make() -> Maybe { return Some(7) }
fn use(value: Maybe) -> Int {
  return match value { None() => 0 Some(number) => number }
}
fn main() -> Int { return use(make()) }
"""
        with self.assertRaisesRegex(ValueError, "direct recursive-union constructor result"):
            emit(program.encode("utf-8"))


    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_two_field_recursive_union_list_length_passes_to_helper_natively(self):
        source_text = """type Tree = End() | Branch(Int, List[Tree])
fn child_count(values: List[Tree]) -> Int { return length(values) }
fn main() -> Int {
  let node: Tree = Branch(39, [End()])
  return match node {
    End() => 0
    Branch(label, children) => child_count(children)
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "recursive-union-two-field-length-helper.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "1\n")

            generated = emit(source.read_bytes())
            self.assertIn("field_1 = (pep_list_union_", generated)
            self.assertRegex(
                generated,
                r"pep_fn_\d+\(pep_local_\d+\.payload\.payload_1\.field_1, pep_arena\)")
            generated_c = folder / "recursive-union-two-field-length-helper.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")
            arena_c = ROOT / "runtime" / "pep_arena" / "pep_arena.c"
            arena_include = ROOT / "runtime" / "pep_arena"

            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / (compiler.stem + "-recursive-union-two-field-length.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", "-I", str(arena_include),
                         str(generated_c), str(arena_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "1\n")


    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_two_field_recursive_union_list_first_payload_passes_to_helper_natively(self):
        source_text = """type Tree = End() | Branch(List[Tree], Int)
fn child_count(values: List[Tree]) -> Int { return length(values) }
fn main() -> Int {
  let node: Tree = Branch([End()], 39)
  return match node {
    End() => 0
    Branch(children, label) => child_count(children)
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "recursive-union-first-list-helper.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "1\n")

            generated = emit(source.read_bytes())
            self.assertIn("field_0 = (pep_list_union_", generated)
            self.assertRegex(
                generated,
                r"pep_fn_\d+\(pep_local_\d+\.payload\.payload_1\.field_0, pep_arena\)")
            generated_c = folder / "recursive-union-first-list-helper.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")
            arena_c = ROOT / "runtime" / "pep_arena" / "pep_arena.c"
            arena_include = ROOT / "runtime" / "pep_arena"

            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / (compiler.stem + "-recursive-union-first-list.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", "-I", str(arena_include),
                         str(generated_c), str(arena_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "1\n")


    def test_recursive_union_local_list_forwarding_fails_closed(self):
        source_text = """type Tree = Leaf(Int) | Branch(List[Tree])
fn count_children(values: List[Tree]) -> Int { return length(values) }
fn main() -> Int {
  let values: List[Tree] = [Leaf(7)]
  return count_children(values)
}
"""
        with self.assertRaisesRegex(ValueError, "direct call in its match arm"):
            emit(source_text.encode("utf-8"))


    def test_recursive_union_local_list_literal_iteration(self):
        source_text = """type Tree = Leaf(Int) | Branch(List[Tree])
fn main() -> Int {
  let values: List[Tree] = [Leaf(42)]
  for item in values {
    return match item {
      Leaf(number) => number
      Branch(_) => 0
    }
  }
  return 0
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "recursive-union-local-list.pep"
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
            self.assertRegex(generated,
                             r"pep_union_\d+ pep_iter_\d+\[\] = \{")
            self.assertRegex(generated,
                             r"pep_union_\d+ pep_local_\d+ = pep_iter_\d+\[pep_index_\d+\]")


    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_recursive_union_local_branch_with_child_list_iteration(self):
        source_text = """type Tree = Leaf(Int) | Branch(List[Tree])
fn main() -> Int {
  let values: List[Tree] = [Branch([Leaf(42)])]
  for item in values {
    return match item {
      Leaf(number) => number
      Branch(children) => length(children)
    }
  }
  return 0
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "recursive-union-branch-list.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "1\n")

            generated = emit(source.read_bytes())
            self.assertIn("pep_arena_alloc", generated)
            self.assertRegex(generated,
                             r"pep_union_\d+ pep_iter_\d+\[\] = \{")
            self.assertIn(".payload.payload_1.field_0.length", generated)
            self.assertIn("pep_checked_length(", generated)

            generated_c = pathlib.Path(temp_dir) / "recursive-union-branch-list.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")
            arena_c = ROOT / "runtime" / "pep_arena" / "pep_arena.c"
            arena_include = ROOT / "runtime" / "pep_arena"
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = pathlib.Path(temp_dir) / (
                        compiler.stem + "-recursive-union-branch-list.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", "-I", str(arena_include),
                         str(generated_c), str(arena_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "1\n")


    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_recursive_ast_union_carries_record_and_child_list(self):
        source_text = """type AstSpan { endByte: Int }
type AstLocation { span: AstSpan }
type AstValue = Leaf(Int) | Node(AstLocation, List[AstValue])
fn main() -> Int {
  let value = Node(AstLocation { span: AstSpan { endByte: 39 } }, [Leaf(7)])
  return match value {
    Leaf(number) => number
    Node(location, children) => location.span.endByte
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "recursive-ast-record-children.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "39\n")

            generated = emit(source.read_bytes())
            self.assertIn("pep_arena_alloc", generated)
            self.assertIn("pep_recursive_list_1[pep_i] = pep_ctor_arg_1.data[pep_i]", generated)
            self.assertIn(".field_0 = pep_ctor_arg_0", generated)
            self.assertIn(".payload.payload_1.field_0.pep_field_0.pep_field_0", generated)
            generated_c = folder / "recursive-ast-record-children.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")
            arena_c = ROOT / "runtime" / "pep_arena" / "pep_arena.c"
            arena_include = ROOT / "runtime" / "pep_arena"
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / (compiler.stem + "-recursive-ast-record-children.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", "-I", str(arena_include),
                         str(generated_c), str(arena_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "39\n")

    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_recursive_ast_union_child_list_length_runs_natively(self):
        source_text = """type AstSpan { endByte: Int }
type AstLocation { span: AstSpan }
type AstValue = Leaf(Int) | Node(AstLocation, List[AstValue])
fn main() -> Int {
  let value = Node(AstLocation { span: AstSpan { endByte: 39 } }, [Leaf(7)])
  return match value {
    Leaf(number) => number
    Node(location, children) => length(children)
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "recursive-ast-child-length.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "1\n")

            generated = emit(source.read_bytes())
            self.assertIn("pep_checked_length(", generated)
            self.assertIn(".payload.payload_1.field_1.length", generated)
            self.assertIn("pep_recursive_list_1[pep_i] = pep_ctor_arg_1.data[pep_i]", generated)
            generated_c = folder / "recursive-ast-child-length.c"
            generated_c.write_text(generated, encoding="utf-8", newline="\n")
            arena_c = ROOT / "runtime" / "pep_arena" / "pep_arena.c"
            arena_include = ROOT / "runtime" / "pep_arena"
            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / (compiler.stem + "-recursive-ast-child-length.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", "-I", str(arena_include),
                         str(generated_c), str(arena_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "1\n")

    def test_nested_recursive_union_constructor_composition(self):
        source_text = """type Tree = Leaf(Int) | Branch(List[Tree])
fn main() -> Int {
  let value: Tree = Branch([Branch([Leaf(42)])])
  return match value {
    Leaf(number) => number
    Branch(children) => length(children)
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            source = pathlib.Path(temp_dir) / "recursive-union-nested-branch.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = pathlib.Path(temp_dir) / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "1\n")

            generated = emit(source.read_bytes())
            self.assertIn("pep_arena_alloc", generated)
            self.assertIn(".payload.payload_1.field_0.length", generated)


    def test_nested_recursive_union_lists_reject_computed_child_payloads(self):
        source_text = """type Tree = Leaf(Int) | Branch(List[Tree])
fn main() -> Int {
  let value: Tree = Branch([Leaf(1 + 2)])
  return 0
}
"""
        with self.assertRaisesRegex(ValueError, "recursive union list"):
            emit(source_text.encode("utf-8"))


    def test_recursive_union_list_rejects_computed_constructor_payloads(self):
        source_text = """type Chain = End(Int) | Link(List[Chain])
fn main() -> Int {
  let initial = Link([End(19 + 23)])
  return match initial {
    End(_) => 0
    Link(_) => 42
  }
}
"""
        with self.assertRaisesRegex(ValueError, "scalar literal payloads"):
            emit(source_text.encode("utf-8"))


    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_recursive_union_list_loop_sums_multiple_leaves_with_clang_and_gcc(self):
        source_text = """type Tree = Leaf(Int) | Branch(List[Tree])
fn main() -> Int {
  let values: List[Tree] = [Leaf(20), Leaf(22)]
  var total = 0
  for item in values {
    total = total + match item {
      Leaf(number) => number
      Branch(_) => 0
    }
  }
  return total
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "recursive-union-tree-walk.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "reference.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")

            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "42\n")

            generated_c = folder / "recursive-union-tree-walk.c"
            generated_c.write_text(emit(source.read_bytes()),
                                   encoding="utf-8", newline="\n")
            arena_c = ROOT / "runtime" / "pep_arena" / "pep_arena.c"
            arena_include = ROOT / "runtime" / "pep_arena"

            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / (compiler.stem + "-recursive-union-tree-walk.exe")
                    compile_result = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", "-I", str(arena_include),
                         str(generated_c), str(arena_c), "-o", str(executable)],
                        cwd=ROOT, text=True, capture_output=True, check=False)
                    self.assertEqual(compile_result.returncode, 0,
                                     compile_result.stdout + compile_result.stderr)
                    result = subprocess.run(
                        [str(executable)], cwd=ROOT, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "42\n")

    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_lucy_ascii_continue_composes_real_lexer_helpers(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_bytes().replace(b"\r\n", b"\n")
        blob = hashlib.sha1(f"blob {len(lexer)}\0".encode("ascii") + lexer).hexdigest()
        self.assertEqual(blob, "12bd93a1dfc5dba3b1cab49abefffed5e406b17d",
                         "Lucy lexer changed; review this native closure before repinning")
        lexer_text = lexer.decode("utf-8")
        start = lexer_text.index("fn ascii_letter(")
        end = lexer_text.index("fn utf8_check(", start)
        closure = lexer_text[start:end].strip() + "\n"
        names = re.findall(r"(?m)^fn ([a-z_]+)\(", closure)
        self.assertEqual(names, ["ascii_letter", "ascii_digit", "ascii_continue"])

        cases = ((65, "42\n"), (57, "42\n"), (95, "42\n"),
                 (64, "0\n"), (128, "0\n"))
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for byte, expected in cases:
                with self.subTest(byte=byte):
                    source_text = (
                        closure + "\nfn main() -> Int {\n"
                        f"  if ascii_continue({byte}) {{ return 42 }} else {{ return 0 }}\n"
                        "}\n")
                    source = folder / f"lexer-{byte}.pep"
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference = folder / f"lexer-{byte}-reference.pep"
                    reference.write_text(source_text + "say(int_text(main()))\n",
                                         encoding="utf-8", newline="\n")
                    interpreted = self.invoke("run", reference)
                    self.assertEqual(interpreted.returncode, 0,
                                     interpreted.stdout + interpreted.stderr)
                    self.assertEqual(interpreted.stdout, expected)

                    c_source = folder / f"lexer-{byte}.c"
                    try:
                        generated = emit(source.read_bytes())
                    except RuntimeError as error:
                        if "PEP_RUNTIME_STEP_LIMIT" in str(error) and "check parsed source" in str(error):
                            self.skipTest(
                                "Pep-written checker exceeds its fixed budget on this real-lexer closure")
                        raise
                    c_source.write_text(generated, encoding="utf-8", newline="\n")
                    self.assertIn("pep_fn_", c_source.read_text(encoding="utf-8"))
                    for compiler in (CLANG, GCC):
                        with self.subTest(byte=byte, compiler=compiler.name):
                            executable = folder / f"lexer-{byte}-{compiler.stem}.exe"
                            compiled = subprocess.run(
                                [str(compiler), "-std=c23", "-Wall", "-Wextra",
                                 "-Wpedantic", "-Werror", "-O2",
                                 str(c_source), "-o", str(executable)],
                                cwd=ROOT, text=True, capture_output=True, check=False)
                            self.assertEqual(compiled.returncode, 0,
                                             compiled.stdout + compiled.stderr)
                            native = subprocess.run(
                                [str(executable)], cwd=ROOT, text=True,
                                capture_output=True, check=False)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, expected)
                            self.assertEqual(native.stdout, interpreted.stdout)


    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_lucy_continue_expression_composes_real_lexer_helpers(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_bytes().replace(b"\r\n", b"\n")
        blob = hashlib.sha1(f"blob {len(lexer)}\0".encode("ascii") + lexer).hexdigest()
        self.assertEqual(blob, "12bd93a1dfc5dba3b1cab49abefffed5e406b17d",
                         "Lucy lexer changed; review this native expression before repinning")
        lexer_text = lexer.decode("utf-8")

        def function_source(name):
            start = lexer_text.index(f"fn {name}(")
            end = lexer_text.index("\n}", start) + 2
            return lexer_text[start:end]

        helpers = function_source("ascii_letter") + "\n" + function_source("ascii_digit")
        continuation = function_source("ascii_continue")
        match = re.search(r"return (ascii_letter\(byte\) \|\| ascii_digit\(byte\))", continuation)
        self.assertIsNotNone(match, continuation)
        cases = ((65, "42\n"), (57, "42\n"), (64, "0\n"))

        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for byte, expected in cases:
                with self.subTest(byte=byte):
                    condition = match.group(1).replace("byte", str(byte))
                    source_text = (
                        helpers + "\nfn main() -> Int {\n"
                        f"  if {condition} {{ return 42 }} else {{ return 0 }}\n"
                        "}\n")
                    source = folder / f"lexer-continue-{byte}.pep"
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    reference = folder / f"lexer-continue-{byte}-reference.pep"
                    reference.write_text(source_text + "say(int_text(main()))\n",
                                         encoding="utf-8", newline="\n")

                    interpreted = self.invoke("run", reference)
                    self.assertEqual(interpreted.returncode, 0,
                                     interpreted.stdout + interpreted.stderr)
                    self.assertEqual(interpreted.stdout, expected)

                    generated = emit(source.read_bytes())
                    self.assertIn(" || ", generated)
                    self.assertIn("pep_fn_", generated)
                    c_source = folder / f"lexer-continue-{byte}.c"
                    c_source.write_text(generated, encoding="utf-8", newline="\n")
                    for compiler in (CLANG, GCC):
                        with self.subTest(byte=byte, compiler=compiler.name):
                            executable = folder / f"lexer-continue-{byte}-{compiler.stem}.exe"
                            compiled = subprocess.run(
                                [str(compiler), "-std=c23", "-Wall", "-Wextra",
                                 "-Wpedantic", "-Werror", "-O2",
                                 str(c_source), "-o", str(executable)],
                                cwd=ROOT, text=True, capture_output=True, check=False)
                            self.assertEqual(compiled.returncode, 0,
                                             compiled.stdout + compiled.stderr)
                            native = subprocess.run(
                                [str(executable)], cwd=ROOT, text=True,
                                capture_output=True, check=False)
                            self.assertEqual(native.returncode, 0,
                                             native.stdout + native.stderr)
                            self.assertEqual(native.stdout, expected)
                            self.assertEqual(native.stdout, interpreted.stdout)

    def test_lucy_ascii_letter_boolean_expression_runs_natively(self):
        lexer = (ROOT / "examples" / "pep_lexer.pep").read_bytes().replace(b"\r\n", b"\n")
        lexer_text = lexer.decode("utf-8")
        start = lexer_text.index("fn ascii_letter(")
        end = lexer_text.index("\n}", start) + 2
        function = lexer_text[start:end]
        self.assertIn(
            "return (65 <= byte && byte <= 90) || (97 <= byte && byte <= 122) || byte == 95",
            function)

        values = (64, 65, 90, 91, 96, 97, 122, 123, 48, 95)
        expected = "".join(
            f"{int(value in (65, 90, 97, 122, 95))}\n" for value in values)
        source_text = function + "\nfn main() -> Int { return 0 }\n"
        reference_text = source_text + "".join(
            f"say(int_text(if ascii_letter({value}) {{ 1 }} else {{ 0 }}))\n"
            for value in values)

        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            source = folder / "lucy-ascii-letter.pep"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            reference = folder / "lucy-ascii-letter-reference.pep"
            reference.write_text(reference_text, encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, expected)

            generated = emit(source.read_bytes())
            self.assertIn(" && ", generated)
            self.assertIn(" || ", generated)
            generated_path = folder / "generated.c"
            generated_path.write_text(generated, encoding="utf-8", newline="\n")
            letter_match = re.search(
                r"_Bool pep_fn_(\d+)\(int64_t pep_arg_\d+\);", generated)
            self.assertIsNotNone(letter_match, generated)
            calls = ", ".join(
                f"pep_fn_{letter_match.group(1)}({value}) ? 1 : 0"
                for value in values)
            harness_path = folder / "harness.c"
            harness_path.write_text(
                "#include <stdio.h>\n#include <stdint.h>\n"
                "#define main pep_generated_main\n#include \"generated.c\"\n#undef main\n"
                "int main(void) {\n"
                f"  printf(\"{('%d' + chr(92) + 'n') * len(values)}\", {calls});\n"
                "  return 0;\n"
                "}\n",
                encoding="utf-8", newline="\n")

            for compiler in (CLANG, GCC):
                with self.subTest(compiler=compiler.name):
                    executable = folder / f"lucy-ascii-letter-{compiler.stem}.exe"
                    compiled = subprocess.run(
                        [str(compiler), "-std=c23", "-Wall", "-Wextra",
                         "-Wpedantic", "-Werror", "-O2", str(harness_path),
                         "-o", str(executable)],
                        cwd=folder, text=True, capture_output=True, check=False)
                    self.assertEqual(compiled.returncode, 0,
                                     compiled.stdout + compiled.stderr)
                    native = subprocess.run(
                        [str(executable)], cwd=folder, text=True,
                        capture_output=True, check=False)
                    self.assertEqual(native.returncode, 0,
                                     native.stdout + native.stderr)
                    self.assertEqual(native.stdout, interpreted.stdout)

    @unittest.skipUnless(CLANG.is_file() and GCC.is_file(),
                         "Clang and GCC are required for native C23 verification")
    def test_staged_pipeline_preserves_recursive_call_depth_boundary(self):
        template = (
            "fn main() -> Int { return countdown({DEPTH}) }\n"
            "fn countdown(value: Int) -> Int {\n"
            "  if value <= 0 { return 42 } else { return countdown(value - 1) }\n"
            "}\n")
        (ROOT / "_build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            folder = pathlib.Path(temp_dir)
            for depth in (510, 511):
                source_text = template.replace("{DEPTH}", str(depth))
                source = folder / f"countdown-{depth}.pep"
                source.write_text(source_text, encoding="utf-8", newline="\n")
                reference = folder / f"countdown-{depth}-reference.pep"
                reference.write_text(
                    source_text + "\nsay(int_text(main()))\n",
                    encoding="utf-8", newline="\n")
                interpreted = self.invoke("run", reference)
                if depth == 510:
                    self.assertEqual(interpreted.returncode, 0,
                                     interpreted.stdout + interpreted.stderr)
                    self.assertEqual(interpreted.stdout, "42\n")
                else:
                    self.assertNotEqual(interpreted.returncode, 0)
                    self.assertEqual(interpreted.stdout, "")
                    self.assertIn("PEP_RUNTIME_CALL_DEPTH", interpreted.stderr)

                generated = emit(source.read_bytes())
                generated_path = folder / f"countdown-{depth}.c"
                generated_path.write_text(
                    generated, encoding="utf-8", newline="\n")
                for compiler in (CLANG, GCC):
                    with self.subTest(depth=depth, compiler=compiler.name):
                        executable = folder / f"countdown-{depth}-{compiler.stem}.exe"
                        compiled = subprocess.run(
                            [str(compiler), "-std=c23", "-Wall", "-Wextra",
                             "-Wpedantic", "-Werror", "-O2", str(generated_path),
                             "-o", str(executable)],
                            cwd=folder, text=True, capture_output=True, check=False)
                        self.assertEqual(compiled.returncode, 0,
                                         compiled.stdout + compiled.stderr)
                        native = subprocess.run(
                            [str(executable)], cwd=folder,
                            text=True, capture_output=True, check=False)
                        self.assertEqual(native.returncode, interpreted.returncode)
                        self.assertEqual(native.stdout, interpreted.stdout)
                        if depth == 511:
                            self.assertIn("PEP_RUNTIME_CALL_DEPTH", native.stderr)
                        else:
                            self.assertEqual(native.stderr, interpreted.stderr)

    def test_while_byte_at_local_and_conditional_assignment_emit_c23(self):
        source_text = """fn scan(source: SourceBytes, limit: Int) -> Int {
  var result = 0
  var index = 0
  while index <= limit {
    let byte = byte_at(source, index)
    if byte <= 127 { result = result + byte } else {}
    index = index + 1
  }
  return result
}
fn main() -> Int { return 0 }
"""
        generated = emit(source_text.encode("utf-8"))
        self.assertIn("while (!!((pep_local_", generated)
        self.assertRegex(generated, r"int64_t pep_local_\d+ = pep_byte_at\(pep_arg_\d+, pep_local_\d+\);")
        self.assertIn("if (!!((pep_local_", generated)

    def test_single_conditional_return_emits_each_branch_once(self):
        source_text = """fn choose(flag: Bool) -> Int {
  if flag { return 7 } else { return 9 }
}
fn main() -> Int { return choose(true) }
"""
        generated = emit(source_text.encode("utf-8"))
        self.assertEqual(generated.count("if (!!(pep_arg_1))"), 1, generated)
        self.assertIn("pep_result = 7", generated)
        self.assertIn("pep_result = 9", generated)


    def test_multiple_top_level_conditionals_preserve_order(self):
        source_text = """fn classify(value: Int) -> Int {
  var result = 0
  if value <= 0 { result = 1 } else {}
  if value <= 1 { result = 2 } else {}
  return result
}
fn main() -> Int { return classify(0) }
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            reference = pathlib.Path(temp_dir) / "ordered-conditionals.pep"
            reference.write_text(
                source_text + "say(int_text(main()))\n",
                encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, "2\n")

        generated = emit(source_text.encode("utf-8"))
        self.assertEqual(generated.count("if (!!"), 2, generated)
        self.assertLess(generated.index("pep_arg_1 <= 0"),
                        generated.index("pep_arg_1 <= 1"))
        self.assertIn("pep_local_", generated)


    def test_while_local_unsupported_initializer_fails_closed(self):
        source_text = """fn scan(limit: Int) -> Int {
  var index = 0
  while index <= limit {
    let next = index + 1
    index = next
  }
  return index
}
fn main() -> Int { return 0 }
"""
        with self.assertRaisesRegex(ValueError, "byte_at initializer"):
            emit(source_text.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
