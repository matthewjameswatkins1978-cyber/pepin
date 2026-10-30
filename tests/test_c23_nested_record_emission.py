import pathlib
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

    def test_tagged_union_rejects_non_int_payload_layout(self):
        source_text = (
            "type MaybeText = None() | Some(Str)\n"
            "fn main() -> Int { return 0 }\n")
        with self.assertRaisesRegex(ValueError, "unsupported layout"):
            emit(source_text.encode("utf-8"))

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


if __name__ == "__main__":
    unittest.main()
