"""Strict native tests for allocation runtimes in isolation from generated code."""

import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tests.test_textbuf_native import run_guarded

ROOT = pathlib.Path(__file__).resolve().parents[1]


class NativeMemoryTests(unittest.TestCase):
    def run_probe(self, name, module, probe):
        compiler = shutil.which(name)
        if compiler is None:
            self.skipTest(f"{name} is unavailable")
        runtime = ROOT / "runtime" / module
        fixture = ROOT / "tests" / "native" / f"{probe}.c"
        flags = ["-std=c23", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror"]
        build = ROOT / "_build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as directory:
            path = pathlib.Path(directory)
            runtime_object = path / f"{module}.o"
            executable = path / f"{probe}.exe"
            for command in (
                [compiler, *flags, "-Dmalloc=probe_malloc", "-Dfree=probe_free",
                 "-c", str(runtime / f"{module}.c"), "-o", str(runtime_object)],
                [compiler, *flags, "-I", str(runtime), str(fixture), str(runtime_object),
                 "-o", str(executable)],
                [str(executable)],
            ):
                result = run_guarded(command, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))

    def test_heap_clang(self):
        self.run_probe("clang", "pep_heap", "pep_heap_probe")

    def test_heap_gcc(self):
        self.run_probe("gcc", "pep_heap", "pep_heap_probe")

    def test_arena_growth_clang(self):
        self.run_probe("clang", "pep_arena", "pep_arena_growth_probe")

    def test_arena_growth_gcc(self):
        self.run_probe("gcc", "pep_arena", "pep_arena_growth_probe")
