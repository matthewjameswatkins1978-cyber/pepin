"""Strict native tests for allocation runtimes in isolation from generated code."""

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tests.test_textbuf_native import run_guarded

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _clang_rt_dir(compiler):
    """Resource lib dir carrying clang's sanitizer runtimes, else None."""
    try:
        out = subprocess.run(
            [compiler, "-print-resource-dir"], capture_output=True,
            check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    lib = pathlib.Path(out.stdout.decode().strip()) / "lib" / "windows"
    needles = ("clang_rt.asan_dynamic-x86_64.dll",)
    if lib.is_dir() and all((lib / n).is_file() for n in needles):
        return lib
    return None


class NativeMemoryTests(unittest.TestCase):
    def run_probe(self, name, source, probe, allocators=("malloc", "free")):
        compiler = shutil.which(name)
        if compiler is None:
            self.skipTest(f"{name} is unavailable")
        runtime_source = ROOT / "runtime" / source
        fixture = ROOT / "tests" / "native" / f"{probe}.c"
        flags = ["-std=c23", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
                 "-D_CRT_SECURE_NO_WARNINGS"]
        build = ROOT / "_build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as directory:
            path = pathlib.Path(directory)
            runtime_object = path / "runtime.o"
            executable = path / f"{probe}.exe"
            for command in (
                [compiler, *flags, *(f"-D{symbol}=probe_{symbol}" for symbol in allocators),
                 "-c", str(runtime_source), "-o", str(runtime_object)],
                [compiler, *flags, "-I", str(runtime_source.parent), str(fixture), str(runtime_object),
                 "-o", str(executable)],
                [str(executable)],
            ):
                result = run_guarded(command, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))

    def test_heap_clang(self):
        self.run_probe("clang", "pep_heap/pep_heap.c", "pep_heap_probe")

    def test_heap_gcc(self):
        self.run_probe("gcc", "pep_heap/pep_heap.c", "pep_heap_probe")

    def test_arena_growth_clang(self):
        self.run_probe("clang", "pep_arena/pep_arena.c", "pep_arena_growth_probe")

    def test_arena_growth_gcc(self):
        self.run_probe("gcc", "pep_arena/pep_arena.c", "pep_arena_growth_probe")

    def test_integer_append_clang(self):
        self.run_probe("clang", "pep_text/pep_textbuf.c", "pep_textbuf_integer_probe", ("realloc",))

    def test_integer_append_gcc(self):
        self.run_probe("gcc", "pep_text/pep_textbuf.c", "pep_textbuf_integer_probe", ("realloc",))

    def run_probe_sanitized(self, module, probe):
        compiler = shutil.which("clang")
        if compiler is None:
            self.skipTest("clang is unavailable")
        rtlib = _clang_rt_dir(compiler)
        if rtlib is None:
            self.skipTest("clang sanitizer runtimes unavailable")
        runtime = ROOT / "runtime" / module
        fixture = ROOT / "tests" / "native" / f"{probe}.c"
        flags = ["-std=c23", "-O2", "-Wall", "-Wextra", "-Wpedantic",
                 "-Werror", "-fsanitize=address,undefined",
                 "-fno-omit-frame-pointer", "-g"]
        env = dict(os.environ)
        env["PATH"] = str(rtlib) + os.pathsep + env.get("PATH", "")
        build = ROOT / "_build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as directory:
            path = pathlib.Path(directory)
            runtime_object = path / f"{module}.o"
            executable = path / f"{probe}.exe"
            for command in (
                [compiler, *flags, "-Dmalloc=probe_malloc",
                 "-Dfree=probe_free",
                 "-c", str(runtime / f"{module}.c"),
                 "-o", str(runtime_object)],
                [compiler, *flags, "-I", str(runtime),
                 str(fixture), str(runtime_object),
                 "-o", str(executable)],
                [str(executable)],
            ):
                result = run_guarded(command, timeout=120, env=env)
                self.assertEqual(result.returncode, 0,
                                 result.stderr.decode(errors="replace"))

    def test_heap_asan_ubsan(self):
        self.run_probe_sanitized("pep_heap", "pep_heap_probe")

    def test_arena_asan_ubsan(self):
        self.run_probe_sanitized("pep_arena", "pep_arena_growth_probe")
