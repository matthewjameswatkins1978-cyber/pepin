#!/usr/bin/env python3
"""
tests/test_c23_correctness.py — Regression Test Suite for Lucy's Reproduced Defects (PEP-AG-20261120-02)

Verifies resolution of the 7 independently reproduced compiler & native runtime defects:
1. Global constant access inside functions.
2. Unary negative integer expressions (-x, -5).
3. Unresolved typed holes rejected upfront (never silently compiling to zero).
4. String equality comparing contents (value semantics) rather than pointer addresses.
5. Returning a list from a function preserving contents (no stack-allocation corruption).
6. Top-level conditionals and loops executed.
7. Strict ISO C23 compilation without GNU statement expressions under -pedantic-errors.
8. Source/output path collision prevention.
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23_direct


class C23CorrectnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clang = shutil_which("clang")
        cls.gcc = shutil_which("gcc")

    def test_global_constant_access_inside_functions(self):
        """Defect 1: Global constant access inside functions must compile and run."""
        source = (
            "let GLOBAL_LIMIT: Int = 100\n"
            "fn check_limit(v: Int) -> Bool {\n"
            "  return v <= GLOBAL_LIMIT\n"
            "}\n"
            "fn main() -> Int {\n"
            "  return if check_limit(50) { 1 } else { 0 }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            pep_file = pathlib.Path(td) / "test_global.pep"
            pep_file.write_text(source, encoding="utf-8")
            code, stdout, stderr = pep_c23_direct.run_c23(pep_file)
            self.assertEqual(code, 0, stderr)
            self.assertEqual(stdout.strip(), "1")

    def test_unary_negative_integer_expressions(self):
        """Defect 2: Unary negative integer expressions (-x, -5) must generate valid C."""
        source = (
            "fn negate(x: Int) -> Int {\n"
            "  return -x\n"
            "}\n"
            "fn main() -> Int {\n"
            "  let a: Int = negate(42)\n"
            "  let b: Int = -5\n"
            "  return a + b\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            pep_file = pathlib.Path(td) / "test_neg.pep"
            pep_file.write_text(source, encoding="utf-8")
            code, stdout, stderr = pep_c23_direct.run_c23(pep_file)
            self.assertEqual(code, 0, stderr)
            self.assertEqual(stdout.strip(), "-47")

    def test_unresolved_typed_holes_rejected(self):
        """Defect 3: Unresolved typed holes must fail native compilation, never compiling to zero."""
        source = (
            "fn incomplete(x: Int) -> Int {\n"
            "  return ?hole\n"
            "}\n"
            "fn main() -> Int {\n"
            "  return incomplete(1)\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            pep_file = pathlib.Path(td) / "test_hole.pep"
            pep_file.write_text(source, encoding="utf-8")
            exe_file = pathlib.Path(td) / "test_hole.exe"
            with self.assertRaises(ValueError) as ctx:
                pep_c23_direct.build_c23(pep_file, exe_file)
            self.assertIn("typed hole", str(ctx.exception).lower())

    def test_string_equality_value_semantics(self):
        """Defect 4: String equality must compare string values, not pointer addresses."""
        source = (
            "fn test_str_eq() -> Bool {\n"
            "  let s1: Str = \"hello world\"\n"
            "  let s2: Str = \"hello world\"\n"
            "  return s1 == s2\n"
            "}\n"
            "fn test_str_neq() -> Bool {\n"
            "  let s1: Str = \"hello\"\n"
            "  let s2: Str = \"world\"\n"
            "  return s1 != s2\n"
            "}\n"
            "fn main() -> Int {\n"
            "  if test_str_eq() && test_str_neq() {\n"
            "    return 42\n"
            "  } else {\n"
            "    return 0\n"
            "  }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            pep_file = pathlib.Path(td) / "test_str.pep"
            pep_file.write_text(source, encoding="utf-8")
            code, stdout, stderr = pep_c23_direct.run_c23(pep_file)
            self.assertEqual(code, 0, stderr)
            self.assertEqual(stdout.strip(), "42")

    def test_returning_list_preserves_contents(self):
        """Defect 5: Returning a list from a function must preserve contents without stack corruption."""
        source = (
            "fn make_list() -> List[Int] {\n"
            "  return [10, 20, 30, 40, 50]\n"
            "}\n"
            "fn sum_list(xs: List[Int]) -> Int {\n"
            "  var total = 0\n"
            "  for item in xs {\n"
            "    total = total + item\n"
            "  }\n"
            "  return total\n"
            "}\n"
            "fn main() -> Int {\n"
            "  let items = make_list()\n"
            "  return sum_list(items)\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            pep_file = pathlib.Path(td) / "test_list_escape.pep"
            pep_file.write_text(source, encoding="utf-8")
            code, stdout, stderr = pep_c23_direct.run_c23(pep_file)
            self.assertEqual(code, 0, stderr)
            self.assertEqual(stdout.strip(), "150")

    def test_top_level_conditionals_and_loops(self):
        """Defect 6: Top-level conditionals and statements must be executed."""
        source = (
            "var status = 0\n"
            "if true {\n"
            "  status = status + 10\n"
            "} else {\n"
            "  status = status + 999\n"
            "}\n"
            "while status <= 14 {\n"
            "  status = status + 1\n"
            "}\n"
            "fn main() -> Int {\n"
            "  return status\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            pep_file = pathlib.Path(td) / "test_top_level.pep"
            pep_file.write_text(source, encoding="utf-8")
            code, stdout, stderr = pep_c23_direct.run_c23(pep_file)
            self.assertEqual(code, 0, stderr)
            self.assertEqual(stdout.strip(), "15")

    def test_strict_iso_c23_pedantic_compilation(self):
        """Defect 7: Pattern matching must compile with strict -pedantic-errors on Clang and GCC."""
        source = (
            "type Option = None() | Some(Int)\n"
            "fn unwrap(opt: Option, fallback: Int) -> Int {\n"
            "  return match opt {\n"
            "    Some(v) => v\n"
            "    None() => fallback\n"
            "  }\n"
            "}\n"
            "fn main() -> Int {\n"
            "  let a = unwrap(Some(100), 0)\n"
            "  let b = unwrap(None(), 23)\n"
            "  return a + b\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            pep_file = pathlib.Path(td) / "test_iso.pep"
            pep_file.write_text(source, encoding="utf-8")
            c_file = pathlib.Path(td) / "test_iso.c"
            exe_file = pathlib.Path(td) / "test_iso.exe"

            # Check with compiler check & emit C
            pep_c23_direct.build_c23(pep_file, exe_file, emit_c_path=c_file)

            for comp in filter(None, [self.clang, self.gcc]):
                comp_name = comp.name
                with self.subTest(compiler=comp_name):
                    # Strict ISO C23 flags
                    cmd = [str(comp), "-std=c23", "-pedantic-errors", "-Wall", "-Wextra", "-Werror", str(c_file), "-o", str(exe_file)]
                    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
                    self.assertEqual(res.returncode, 0, f"{comp_name} failed strict compilation:\n{res.stderr}")
                    run_res = subprocess.run([str(exe_file)], capture_output=True, text=True, encoding="utf-8")
                    self.assertEqual(run_res.stdout.strip(), "123")

    def test_native_string_bytes_match_interpreter(self):
        source = (
            'fn echo(value: Str) -> Str { return value }\n'
            'say(echo("caf\u00e9 \U0001f680"))\n'
            'say("a\\0b")\n'
            'say(if "a\\0b" != "a\\0c" { "different" } else { "wrong" })\n'
            'say(if "a\\0b" == "a\\0b" { "equal" } else { "wrong" })\n'
            'say(if "" == "" { int_text(-123) } else { "wrong" })\n'
        )
        with tempfile.TemporaryDirectory() as folder:
            pep_file = pathlib.Path(folder) / "strings.pep"
            pep_file.write_text(source, encoding="utf-8")
            reference = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"), "run", str(pep_file)],
                capture_output=True,
            )
            self.assertEqual(reference.returncode, 0, reference.stderr)
            expected = "caf\u00e9 \U0001f680\na\0b\ndifferent\nequal\n-123\n".encode("utf-8")
            self.assertEqual(reference.stdout.replace(b"\r\n", b"\n"), expected)

            c_file = pep_file.with_suffix(".c")
            executable = pep_file.with_suffix(".exe")
            pep_c23_direct.build_c23(pep_file, executable, emit_c_path=c_file)
            for compiler in filter(None, [self.clang, self.gcc]):
                with self.subTest(compiler=compiler.name):
                    compiled = subprocess.run(
                        [str(compiler), "-std=c23", "-pedantic-errors", "-Wall", "-Wextra",
                         "-Werror", str(c_file), "-o", str(executable)],
                        capture_output=True,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    native = subprocess.run([str(executable)], capture_output=True)
                    self.assertEqual(native.returncode, 0, native.stderr)
                    self.assertEqual(native.stdout.replace(b"\r\n", b"\n"), expected)

    def test_native_string_list_operations_match_interpreter(self):
        source = (
            'fn words() -> List[Str] { return ["caf\u00e9", "a\\0b"] }\n'
            'let empty: List[Str] = []\n'
            'let original = words()\n'
            'let changed = prepend(append(original, int_text(42)), "\U0001f680")\n'
            'for word in reverse(changed) { say(word) }\n'
            'say(int_text(length(original)))\n'
            'say(int_text(length(empty)))\n'
            'say(if contains(changed, "a\\0b") { "found" } else { "wrong" })\n'
            'say(if contains(changed, "a\\0c") || contains(empty, "") { "wrong" } else { "missing" })\n'
        )
        with tempfile.TemporaryDirectory() as folder:
            pep_file = pathlib.Path(folder) / "string_lists.pep"
            pep_file.write_text(source, encoding="utf-8")
            reference = pep_c23_direct.run_pep_cmd("run", str(pep_file))
            expected = "42\na\0b\ncaf\u00e9\n\U0001f680\n2\n0\nfound\nmissing\n"
            self.assertEqual(reference, (0, expected, ""))
            for compiler in filter(None, [self.clang, self.gcc]):
                with self.subTest(compiler=compiler.name):
                    native = pep_c23_direct.run_c23(pep_file, compiler)
                    self.assertEqual(native, reference)

    def assert_native_order_parity(self, source, stdout, stderr=""):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder)
            pep_file = path / "order.pep"
            pep_file.write_text(source, encoding="utf-8")
            reference = pep_c23_direct.run_pep_cmd("run", str(pep_file))
            expected = (1 if stderr else 0, stdout, stderr)
            # The interpreter prefixes runtime errors with the source line and column.
            reference_error = reference[2].split(" ", 1)[1] if stderr else reference[2]
            self.assertEqual((*reference[:2], reference_error), expected)

            c_file = path / "order.c"
            executable = path / "order.exe"
            pep_c23_direct.build_c23(pep_file, executable, emit_c_path=c_file)
            for compiler in filter(None, [self.clang, self.gcc]):
                for optimization in ("-O0", "-O2", "-O3"):
                    with self.subTest(compiler=compiler.name, optimization=optimization):
                        compiled = subprocess.run(
                            [str(compiler), "-std=c23", "-pedantic-errors", "-Wall", "-Wextra",
                             "-Werror", optimization, str(c_file), "-o", str(executable)],
                            capture_output=True, text=True, encoding="utf-8",
                        )
                        self.assertEqual(compiled.returncode, 0, compiled.stderr)
                        native = subprocess.run(
                            [str(executable)], capture_output=True, text=True, encoding="utf-8"
                        )
                        self.assertEqual((native.returncode, native.stdout, native.stderr), expected)

    def test_native_order_for_calls_and_eager_operands(self):
        self.assert_native_order_parity(
            """type Pair { left: Int, right: Int }
type Values = Both(Int, Int) | Neither()
fn mark(n: Int) -> Int {
    say(int_text(n))
    return n
}
fn subtract(a: Int, b: Int) -> Int { return a - b }
say(int_text(subtract(mark(1), mark(2))))
say(int_text(mark(3) + subtract(mark(4), mark(5))))
say(if mark(6) <= mark(7) { "less" } else { "wrong" })
let pair = Pair { right: mark(8), left: mark(9) }
say(int_text(pair.left))
let chosen = match Both(mark(10), mark(11)) {
    Both(first, second) => subtract(mark(first + 2), mark(second + 2))
    Neither() => mark(99)
}
say(int_text(chosen))
let items = [mark(14), mark(15)]
for item in items { say(int_text(item + 100)) }
""",
            "1\n2\n-1\n3\n4\n5\n2\n6\n7\nless\n8\n9\n9\n10\n11\n12\n13\n-1\n14\n15\n114\n115\n",
        )

    def test_native_order_snapshots_mutable_global_before_later_operand(self):
        self.assert_native_order_parity(
            """var state = 1
fn change() -> Int {
    state = 8
    return 2
}
say(int_text(state + change()))
say(int_text(state))
state = 9
fn read_state() -> Int { return state }
say(int_text(read_state()))
""",
            "3\n8\n9\n",
        )

    def test_native_rejects_uninitialized_global_access_in_interpreter_order(self):
        for statement, message in (
            ("return later", "Checked binding is missing at runtime"),
            ("later = rhs()\n    return 0", "Checked assignment target is missing at runtime"),
        ):
            with self.subTest(statement=statement):
                self.assert_native_order_parity(
                    f"""let first = touch()
var later = 42
fn rhs() -> Int {{
    say("rhs")
    return 7
}}
fn touch() -> Int {{
    {statement}
}}
say(int_text(first))
""",
                    "rhs\n" if statement.startswith("later") else "",
                    f"PEP_RUNTIME_UNRESOLVED_BINDING: {message}\n",
                )

    def test_native_order_preserves_lazy_evaluation(self):
        self.assert_native_order_parity(
            """type Choice = Selected(Int) | Skipped()
fn flag(n: Int, result: Bool) -> Bool {
    say(int_text(n))
    return result
}
fn never() -> Int { return 1 / 0 }
say(if flag(1, false) && flag(99, true) { int_text(never()) } else { "and" })
say(if flag(2, true) || flag(99, false) { "or" } else { int_text(never()) })
say(if flag(3, true) && flag(4, true) { "both" } else { int_text(never()) })
let value = match Selected(5) {
    Skipped() => never()
    Selected(n) => if flag(n, false) { never() } else { n + 1 }
}
say(int_text(value))
var count = 7
while flag(count, count <= 8) {
    count = count + 1
}
""",
            "1\nand\n2\nor\n3\n4\nboth\n5\n6\n7\n8\n9\n",
        )

    def test_native_order_stops_at_first_runtime_failure(self):
        preamble = """fn left() -> Int {
    say("left")
    return 1 / 0
}
fn right() -> Int {
    say("right")
    return 9223372036854775807 + 1
}
fn subtract(a: Int, b: Int) -> Int { return a - b }
"""
        for expression in ("subtract(left(), right())", "left() + right()"):
            with self.subTest(expression=expression):
                self.assert_native_order_parity(
                    preamble + f"say(int_text({expression}))\n",
                    "left\n", "PEP_RUNTIME_DIVISION_BY_ZERO: Division by zero\n",
                )

    def test_native_rejects_unsupported_checked_value_type_before_writing_c(self):
        with tempfile.TemporaryDirectory() as folder:
            pep_file = pathlib.Path(folder) / "unsupported.pep"
            pep_file.write_text('let xs: List[Unit] = [say("done")]\n', encoding="utf-8")
            self.assertEqual(pep_c23_direct.run_pep_cmd("run", str(pep_file)), (0, "done\n", ""))
            executable = pep_file.with_suffix(".exe")
            with self.assertRaisesRegex(ValueError, "Unsupported C23 list element type: Unit"):
                pep_c23_direct.build_c23(pep_file, executable)
            self.assertFalse(executable.with_suffix(".c").exists())
            self.assertFalse(executable.exists())

    def test_native_lists_store_nested_and_nominal_values(self):
        self.assert_native_order_parity(
            """type Item { value: Int }
type Tree { children: List[Tree], value: Int }
fn items() -> List[Item] {
    return [Item { value: 19 }]
}
fn tree_sum(tree: Tree) -> Int {
    var total = tree.value
    for child in tree.children { total = total + tree_sum(child) }
    return total
}
let original = [items()]
let groups = reverse(prepend(append(original, [Item { value: 23 }]), []))
var total = 0
for list in groups {
    for item in list { total = total + item.value }
}
say(int_text(total))
say(int_text(length(original)))
let leaf = Tree { children: [], value: 2 }
let root = Tree { children: [leaf], value: 40 }
say(int_text(tree_sum(root)))
""",
            "42\n1\n42\n",
        )

    def test_file_modules_check_and_execute_the_same_program(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / "std").mkdir()
            ops = root / "std" / "ops.pep"
            ops.write_text("pub fn increment(n: Int) -> Int { return n + 1 }\n", encoding="utf-8")
            (root / "std" / "scale.pep").write_text(
                "import std.ops\n"
                "fn helper(n: Int) -> Int { return ops.increment(n) }\n"
                "pub fn twice(n: Int) -> Int { return helper(n) * 2 }\n", encoding="utf-8"
            )
            entry = root / "main.pep"
            entry.write_text("import std.scale as math\nsay(int_text(math.twice(20)))\n", encoding="utf-8")
            status, output, error = pep_c23_direct.run_pep_cmd("check", str(entry), "--json")
            self.assertEqual(status, 0, error or output)
            checked = json.loads(output)
            graph = checked["moduleGraph"]
            self.assertEqual(graph["entry"], "main.pep")
            self.assertEqual([f["document"] for f in graph["files"]],
                             ["std/ops.pep", "std/scale.pep", "main.pep"])
            self.assertEqual([ex["name"] for ex in graph["files"][1]["exports"]], ["twice"])
            from pep_semantic_map import SemanticMap

            semantic = SemanticMap(entry)
            self.assertEqual(semantic.module_graph, graph)
            context = semantic.get_context_packet("std/scale.pep::twice")
            self.assertEqual(context["implementation"], "fn twice(n: Int) -> Int { return helper(n) * 2 }")
            self.assertEqual(context["moduleRevision"], graph["revision"])
            self.assertEqual(context["sourceHash"], graph["files"][1]["revision"])
            self.assertIn("error", semantic.get_context_packet("std/scale.pep::helper"))
            self.assertFalse(semantic.verify_lane({})["laneValid"])
            self.assertEqual(semantic.apply_repair({})["status"], "UNSUPPORTED_MODULE_REPAIR")
            self.assertEqual(pep_c23_direct.run_pep_cmd("run", str(entry)), (0, "42\n", ""))
            for compiler in filter(None, [self.clang, self.gcc]):
                with self.subTest(compiler=compiler.name):
                    self.assertEqual(pep_c23_direct.run_c23(entry, compiler), (0, "42\n", ""))
            ops.write_text("pub fn increment(n: Int) -> Int { return n + 2 }\n", encoding="utf-8")
            status, new_output, error = pep_c23_direct.run_pep_cmd("check", str(entry), "--json")
            self.assertEqual(status, 0, error or new_output)
            self.assertNotEqual(json.loads(new_output)["moduleGraph"]["revision"], graph["revision"])
            self.assertIn("std/ops.pep", semantic.get_context_packet("std/scale.pep::twice")["error"])

    def test_file_module_boundaries_fail_with_source_identity(self):
        cases = (
            ("say(int_text(lib.secret()))", "fn secret() -> Int { return 42 }\n",
             "PEP_MODULE_PRIVATE", "main.pep"),
            ("say(int_text(lib.entry()))", "pub fn entry() -> Int { return outside() }\n",
             "PEP_UNKNOWN_FUNCTION", "lib.pep"),
            ("say(int_text(lib.entry()))", "pub fn entry() -> Int { return hidden }\n",
             "PEP_UNKNOWN_VARIABLE", "lib.pep"),
            ("say(int_text(lib.fun()))", "import main\npub fn fun() -> Int { return 0 }\n",
             "PEP_MODULE_CYCLE", "lib.pep"),
            ("say(int_text(lib.fun()))", "say(\"unexpected\")\n",
             "PEP_MODULE_INITIALIZER", "lib.pep"),
        )
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            entry = root / "main.pep"
            lib = root / "lib.pep"
            for expression, dependency, code, source in cases:
                with self.subTest(code=code):
                    entry.write_text("import lib\nlet hidden = 9\n"
                                     "fn outside() -> Int { return 8 }\n" + expression + "\n",
                                     encoding="utf-8")
                    lib.write_text(dependency, encoding="utf-8")
                    status, output, stderr = pep_c23_direct.run_pep_cmd("check", str(entry), "--json")
                    self.assertNotEqual(status, 0, output or stderr)
                    diagnostics = json.loads(output)["diagnostics"]
                    self.assertIn((code, source), [(d["code"], d["span"].get("document"))
                                                  for d in diagnostics])

    def test_imported_private_nominal_types_stay_local(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            entry = root / "main.pep"
            entry.write_text(
                "import alpha\nimport beta\n"
                "type EntryOnly { unrelated: Int }\n"
                "say(int_text(alpha.value() + beta.value()))\n", encoding="utf-8"
            )
            source = """type Payload { number: Int }
type Choice = Keep(Payload) | Empty()
fn evaluate(choice: Choice) -> Int {
    return match choice {
        Keep(payload) => payload.number
        Empty() => 0
    }
}
pub fn value() -> Int {
    let payload: Payload = Payload { number: NUMBER }
    return evaluate(Keep(payload))
}
"""
            for module, number in (("alpha", 19), ("beta", 23)):
                (root / f"{module}.pep").write_text(
                    source.replace("NUMBER", str(number)), encoding="utf-8"
                )
            self.assertEqual(pep_c23_direct.run_pep_cmd("run", str(entry)), (0, "42\n", ""))
            for compiler in filter(None, [self.clang, self.gcc]):
                with self.subTest(compiler=compiler.name):
                    self.assertEqual(pep_c23_direct.run_c23(entry, compiler), (0, "42\n", ""))

            alpha = root / "alpha.pep"
            for function, code in (
                ("pub fn value() -> Payload { return Payload { number: 1 } }",
                 "PEP_MODULE_TYPE_UNSUPPORTED"),
                ("pub fn value() -> Int { return (EntryOnly { unrelated: 1 }).unrelated }",
                 "PEP_UNKNOWN_TYPE"),
            ):
                with self.subTest(code=code):
                    alpha.write_text("type Payload { number: Int }\n" + function + "\n", encoding="utf-8")
                    status, output, stderr = pep_c23_direct.run_pep_cmd("check", str(entry), "--json")
                    self.assertNotEqual(status, 0, output or stderr)
                    diagnostic = json.loads(output)["diagnostics"][0]
                    self.assertEqual((diagnostic["code"], diagnostic["span"]["document"]), (code, "alpha.pep"))

    def test_opaque_nominal_type_crosses_modules_through_public_functions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            module = """pub type Counter { value: Int }
pub type Reading = Available(Int) | Missing()
pub fn make(value: Int) -> Counter { return Counter { value: value } }
pub fn read(counter: Counter) -> Reading { return Available(counter.value) }
pub fn unwrap(reading: Reading) -> Int {
    return match reading { Available(n) => n Missing() => 0 }
}
"""
            for name in ("alpha", "beta"):
                (root / f"{name}.pep").write_text(module, encoding="utf-8")
            entry = root / "main.pep"
            imports = "import alpha as counter\nimport beta\n"
            entry.write_text(imports
                             + "let value: counter.Counter = counter.make(42)\n"
                             + "let reading: counter.Reading = counter.read(value)\n"
                             + "say(int_text(counter.unwrap(reading)))\n", encoding="utf-8")
            status, output, stderr = pep_c23_direct.run_pep_cmd("check", str(entry), "--json")
            self.assertEqual(status, 0, output or stderr)
            graph = json.loads(output)["moduleGraph"]
            types = graph["files"][0]["typeExports"]
            self.assertEqual([(t["name"], t["opaque"]) for t in types],
                             [("Counter", True), ("Reading", True)])
            self.assertTrue(all(set(t) == {"name", "symbol", "opaque"} for t in types))
            reference = pep_c23_direct.run_pep_cmd("run", str(entry))
            self.assertEqual(reference, (0, "42\n", ""))
            for compiler in filter(None, [self.clang, self.gcc]):
                with self.subTest(compiler=compiler.name):
                    self.assertEqual(pep_c23_direct.run_c23(entry, compiler), reference)
            for statement, code in (
                ("say(int_text(counter.make(1).value))", "PEP_MODULE_OPAQUE_FIELD"),
                ("let value: counter.Counter = beta.make(1)", "PEP_TYPE_MISMATCH"),
                ("let reading = counter.Available(1)", "PEP_MODULE_UNKNOWN_EXPORT"),
                ("let value: counter.Unexported = counter.make(1)", "PEP_MODULE_UNKNOWN_TYPE_EXPORT"),
            ):
                with self.subTest(code=code):
                    entry.write_text(imports + statement + "\n", encoding="utf-8")
                    status, output, stderr = pep_c23_direct.run_pep_cmd("check", str(entry), "--json")
                    self.assertNotEqual(status, 0, output or stderr)
                    diagnostic = json.loads(output)["diagnostics"][0]
                    self.assertEqual((diagnostic["code"], diagnostic["span"]["document"]), (code, "main.pep"))

    def test_native_nominal_layout_orders_by_value_dependencies(self):
        self.assert_native_order_parity(
            """type Batch { item: Choice, empty: Empty }
type Empty {}
type Choice = Taken(Payload) | Absent()
type Payload { number: Int }
let batch = Batch { item: Taken(Payload { number: 42 }), empty: Empty {} }
let result = match batch.item {
    Taken(payload) => payload.number
    Absent() => 0
}
say(int_text(result))
""",
            "42\n",
        )

    def test_native_recursive_nominal_layout_is_explicitly_unsupported(self):
        with tempfile.TemporaryDirectory() as folder:
            pep_file = pathlib.Path(folder) / "tree.pep"
            pep_file.write_text("type Tree = Leaf(Int) | Branch(Tree)\n", encoding="utf-8")
            self.assertEqual(pep_c23_direct.run_pep_cmd("run", str(pep_file)), (0, "", ""))
            output = pep_file.with_suffix(".exe")
            with self.assertRaisesRegex(ValueError, "Unsupported recursive by-value C23 layout: Tree"):
                pep_c23_direct.build_c23(pep_file, output)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix(".c").exists())

    def test_path_collision_prevention(self):
        """Collision Prevention: Source, output executable, and emitted C file paths must be distinct."""
        with tempfile.TemporaryDirectory() as td:
            pep_file = pathlib.Path(td) / "prog.pep"
            pep_file.write_text("fn main() -> Int { return 0 }\n", encoding="utf-8")

            # Source equals output
            with self.assertRaises(ValueError) as ctx1:
                pep_c23_direct.build_c23(pep_file, pep_file)
            self.assertIn("collide", str(ctx1.exception))

            # Source equals emitted C
            with self.assertRaises(ValueError) as ctx2:
                pep_c23_direct.build_c23(pep_file, pathlib.Path(td) / "prog.exe", emit_c_path=pep_file)
            self.assertIn("collide", str(ctx2.exception))


def shutil_which(name: str) -> Optional[pathlib.Path]:
    import shutil
    res = shutil.which(name)
    return pathlib.Path(res) if res else None


if __name__ == "__main__":
    unittest.main()
