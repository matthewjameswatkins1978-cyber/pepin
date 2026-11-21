"""Strict native tests for the managed heap in isolation from generated code."""

import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tests.test_textbuf_native import run_guarded

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEAP = ROOT / "runtime" / "pep_heap"
PROBE = ROOT / "tests" / "native" / "pep_heap_probe.c"


class NativeHeapTests(unittest.TestCase):
    def run_probe(self, name):
        compiler = shutil.which(name)
        if compiler is None:
            self.skipTest(f"{name} is unavailable")
        flags = ["-std=c23", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror"]
        build = ROOT / "_build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as directory:
            path = pathlib.Path(directory)
            heap_object = path / "heap.o"
            executable = path / "heap_probe.exe"
            for command in (
                [compiler, *flags, "-Dmalloc=probe_malloc", "-Dfree=probe_free",
                 "-c", str(HEAP / "pep_heap.c"), "-o", str(heap_object)],
                [compiler, *flags, "-I", str(HEAP), str(PROBE), str(heap_object),
                 "-o", str(executable)],
                [str(executable)],
            ):
                result = run_guarded(command, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))

    def test_clang(self):
        self.run_probe("clang")

    def test_gcc(self):
        self.run_probe("gcc")
