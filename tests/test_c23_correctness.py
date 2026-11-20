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
