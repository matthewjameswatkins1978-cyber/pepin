"""Exercise generated C23 roots and reclamation against real checked Pep."""

import json
import pathlib
import re
import shutil
import tempfile
import unittest

from pep_c23_direct import C23Emitter, run_pep_cmd
from tests.test_textbuf_native import CLANG_FLAGS, run_guarded


ROOT = pathlib.Path(__file__).resolve().parents[1]
MONITOR = ROOT / "tests" / "native" / "pep_native_heap_monitor.c"

TRANSIENT = """\
fn make(n: Int) -> List[Str] { return [int_text(n)] }
var i = 0
while i < 1600 {
    let dead = make(i)
    i = i + length(dead)
}
say(int_text(i))
"""

GRAPH = """\
type Tree = Leaf(Str) | Branch(List[Tree])
type Bundle { tree: Tree, label: Str }
fn make(n: Int) -> List[Str] { return [int_text(n)] }
fn first(a: List[Str], b: List[Str]) -> Str {
    if length(b) > 0 { return a[0] }
    return "missing"
}
fn read(tree: Tree) -> Str {
    return match tree {
        Leaf(text) => first([text], make(900))
        Branch(kids) => read(kids[0])
    }
}
fn ignored() -> Str {
    say("inactive")
    return int_text(0)
}
fn from_match(branch: Tree, values: List[Str], index: Int) -> Str {
    return match branch {
        Leaf(_) => first([values[index]], make(901))
        Branch(_) => "unexpected branch"
    }
}
fn walk(trees: List[Tree]) -> Str {
    var count = 0
    for tree in trees {
        let noise = make(count)
        count = count + length(noise)
        if count == 1 { continue }
        if count == 2 { break }
        return ignored()
    }
    return read(trees[0])
}
var bundle = Bundle {
    tree: Branch([Leaf(int_text(42))]),
    label: int_text(7)
}
say(first(make(11), make(22)))
let alias = bundle
bundle = Bundle { tree: Leaf(int_text(5)), label: int_text(9) }
let selected = if true { walk([alias.tree, bundle.tree]) } else { ignored() }
say(selected)
say(bundle.label)
say(alias.label)
say(from_match(bundle.tree, make(23), 0))
"""

BOUNDS = """\
fn first() -> Int {
    let values = [int_text(7)]
    say(values[0])
    return [21][9]
}
fn later() -> Int {
    say("out of order")
    return 21
}
say(int_text(first() + later()))
"""

OOM = """\
say("before failure")
let live = [int_text(7)]
say(int_text(length(live)))
"""


class C23ManagedMemoryTests(unittest.TestCase):
    def setUp(self):
        build = ROOT / "_build"
        build.mkdir(exist_ok=True)
        directory = tempfile.TemporaryDirectory(dir=build)
        self.addCleanup(directory.cleanup)
        self.work = pathlib.Path(directory.name)

    def emit(self, source):
        pep_file = self.work / "program.pep"
        pep_file.write_text(source, encoding="utf-8")
        code, output, error = run_pep_cmd("check", str(pep_file), "--json")
        self.assertEqual(code, 0, error or output)
        c_file = pep_file.with_suffix(".c")
        c_file.write_text(C23Emitter(json.loads(output)).generate_c23(), encoding="utf-8")
        return c_file, run_pep_cmd("run", str(pep_file))

    def compilers(self):
        compilers = [compiler for name in ("clang", "gcc") if (compiler := shutil.which(name))]
        if not compilers:
            self.skipTest("Clang and GCC are unavailable")
        return compilers

    def run_native(self, compiler, c_file, *, stress=False, fail_at=None):
        flags = [*CLANG_FLAGS, "-O2"]
        native_object = c_file.with_suffix(".o")
        exe = c_file.with_suffix(".exe")
        overrides = ["-Dmain=pep_test_program", "-Dmalloc=probe_malloc", "-Dfree=probe_free"]
        if stress:
            overrides.append("-DPEP_GC_STRESS=1")
        fault = [f"-DPEP_PROBE_FAIL_AT={fail_at}"] if fail_at is not None else []
        for command in (
            [compiler, *flags, *overrides, "-c", str(c_file), "-o", str(native_object)],
            [compiler, *flags, *fault, str(native_object), str(MONITOR), "-o", str(exe)],
        ):
            result = run_guarded(command, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
        result = run_guarded([str(exe)], text=True, timeout=60)
        *diagnostics, stats = result.stderr.splitlines()
        match = re.fullmatch(r"heap live=(\d+) peak=(\d+) calls=(\d+)", stats)
        self.assertIsNotNone(match, result.stderr)
        live, peak, calls = map(int, match.groups())
        self.assertEqual(live, 0, result.stderr)
        return result.returncode, result.stdout, "\n".join(diagnostics), peak, calls

    def test_transient_collections_have_bounded_backing(self):
        c_file, seed = self.emit(TRANSIENT)
        self.assertEqual(seed, (0, "1600\n", ""))
        for compiler in self.compilers():
            for stress in (False, True):
                with self.subTest(compiler=compiler, stress=stress):
                    code, output, error, peak, calls = self.run_native(compiler, c_file, stress=stress)
                    self.assertEqual((code, output, error), seed)
                    self.assertEqual(calls, 3201)
                    self.assertLessEqual(peak, 512 if stress else 65536)

    def test_exact_roots_for_globals_aggregates_calls_and_control_flow(self):
        c_file, seed = self.emit(GRAPH)
        self.assertEqual(seed, (0, "11\n42\n9\n7\n23\n", ""))
        for compiler in self.compilers():
            with self.subTest(compiler=compiler):
                code, output, error, _, _ = self.run_native(compiler, c_file, stress=True)
                self.assertEqual((code, output, error), seed)

    def test_error_paths_release_memory_and_preserve_effect_order(self):
        c_file, seed = self.emit(BOUNDS)
        self.assertNotEqual(seed[0], 0)
        self.assertEqual(seed[1], "7\n")
        self.assertIn("PEP_RUNTIME_INDEX_BOUNDS", seed[2])
        for compiler in self.compilers():
            with self.subTest(compiler=compiler):
                code, output, error, _, _ = self.run_native(compiler, c_file, stress=True)
                self.assertEqual((code, output), seed[:2])
                self.assertIn("PEP_RUNTIME_INDEX_BOUNDS", error)

    def test_allocation_failure_releases_preserved_roots(self):
        c_file, seed = self.emit(OOM)
        self.assertEqual(seed, (0, "before failure\n1\n", ""))
        for compiler in self.compilers():
            with self.subTest(compiler=compiler):
                code, output, error, _, calls = self.run_native(compiler, c_file, fail_at=3)
                self.assertEqual((code, output), (1, "before failure\n"))
                self.assertIn("PEP_RUNTIME_ALLOC_FAILURE: String allocation failed", error)
                self.assertEqual(calls, 4)
