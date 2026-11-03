"""Native sanitizer gate for emitted C23.

Every other native test compiles with -Werror and compares behaviour with the
interpreter, but behaviour can be right while memory use is wrong. The emitter now
generates arena-backed allocation helpers (list prepend/reverse) and pointer-carrying
string/list descriptors, so the generated C is checked under Clang's AddressSanitizer
and UndefinedBehaviorSanitizer as well.

Windows note: the Clang ASan runtime is a DLL beside the compiler's resource directory
and must be on PATH, otherwise the executable fails to load. Both sanitizers are skipped
rather than reported as failures when that runtime is unavailable, and GCC sanitizers are
not attempted because this MinGW installation cannot find -lasan.
"""

import os
import pathlib
import subprocess
import tempfile
import unittest

from pep_c23 import emit

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
ARENA = ROOT / "runtime" / "pep_arena" / "pep_arena.c"
ARENA_INCLUDE = ROOT / "runtime" / "pep_arena"
CLANG = pathlib.Path(r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe")

PROGRAMS = {
    # Kept small on purpose: the checker and the emitter both bound node count, so a
    # sanitizer fixture that trips a step budget would test nothing.
    "arena-list-updates": (
        "fn main() -> Int {\n"
        "  var parts: List[Str] = []\n"
        "  var guard = 0\n"
        "  while guard <= 0 {\n"
        "    parts = prepend(parts, \"a\")\n"
        "    parts = prepend(parts, \"b\")\n"
        "    parts = reverse(parts)\n"
        "    guard = guard + 1\n"
        "  }\n"
        "  return length(parts)\n"
        "}\n", 2),
    "record-and-literals": (
        "type Point { x: Int y: Int }\n"
        "type Box { point: Point name: Str }\n"
        "fn main() -> Int {\n"
        "  let box = Box { point: Point { x: 19, y: 23 }, name: \"a\\nb\" }\n"
        "  return box.point.x + box.point.y\n"
        "}\n", 42),
    "int-list-reverse": (
        "fn main() -> Int {\n"
        "  var xs: List[Int] = [1, 2]\n"
        "  var guard = 0\n"
        "  while guard <= 0 {\n"
        "    xs = reverse(xs)\n"
        "    guard = guard + 1\n"
        "  }\n"
        "  return length(xs)\n"
        "}\n", 2),
}


def sanitizer_runtime_dir():
    """Directory holding the Clang sanitizer runtimes, or None.

    On Windows these are DLLs beside the compiler's resource directory, and the
    executable will not load without them on PATH.
    """
    roots = []
    result = subprocess.run([str(CLANG), "--print-runtime-dir"], text=True,
                            capture_output=True, check=False)
    if result.stdout.strip():
        roots.append(pathlib.Path(result.stdout.strip()))
    roots.append(CLANG.parent.parent / "lib" / "clang")
    for root in roots:
        if not root.is_dir():
            continue
        for dll in sorted(root.rglob("clang_rt.asan_dynamic-x86_64.dll")):
            return dll.parent
    return None


@unittest.skipUnless(CLANG.is_file(), "Clang is required for the sanitizer gate")
class PepC23SanitizerTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(PEP), *map(str, args)],
            cwd=ROOT, text=True, capture_output=True, check=False)

    def run_sanitized(self, source_text, expected, sanitizer):
        with tempfile.TemporaryDirectory(dir=ROOT / "_build") as temp_dir:
            directory = pathlib.Path(temp_dir)
            reference = directory / "reference.pep"
            reference.write_text(source_text + "say(int_text(main()))\n",
                                 encoding="utf-8", newline="\n")
            interpreted = self.invoke("run", reference)
            self.assertEqual(interpreted.returncode, 0,
                             interpreted.stdout + interpreted.stderr)
            self.assertEqual(interpreted.stdout, f"{expected}\n")

            c_path = directory / "generated.c"
            c_path.write_text(emit(source_text.encode("utf-8")), encoding="utf-8", newline="\n")
            executable = directory / "sanitized.exe"
            built = subprocess.run(
                [str(CLANG), "-std=c23", "-g", "-O1", f"-fsanitize={sanitizer}",
                 f"-I{ARENA_INCLUDE}", str(c_path), str(ARENA), "-o", str(executable)],
                cwd=ROOT, text=True, capture_output=True, check=False)
            if built.returncode != 0:
                self.skipTest(f"{sanitizer} build unavailable: "
                              + (built.stdout + built.stderr)[-200:])

            environment = dict(os.environ)
            runtime = sanitizer_runtime_dir()
            if runtime is not None:
                environment["PATH"] = str(runtime) + os.pathsep + environment.get("PATH", "")
            ran = subprocess.run([str(executable)], cwd=ROOT, text=True,
                                 capture_output=True, check=False, env=environment)
            if ran.returncode == -1073741515 or ran.returncode == 3221225781:
                self.skipTest(f"{sanitizer} runtime DLL not loadable on this host")
            self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
            self.assertEqual(ran.stdout, interpreted.stdout)
            self.assertNotIn("AddressSanitizer", ran.stderr)
            self.assertNotIn("runtime error", ran.stderr)

    def test_arena_list_updates_are_clean_under_asan(self):
        source, expected = PROGRAMS["arena-list-updates"]
        self.run_sanitized(source, expected, "address")

    def test_arena_list_updates_are_clean_under_ubsan(self):
        source, expected = PROGRAMS["arena-list-updates"]
        self.run_sanitized(source, expected, "undefined")

    def test_records_and_escaped_literals_are_clean_under_asan(self):
        source, expected = PROGRAMS["record-and-literals"]
        self.run_sanitized(source, expected, "address")

    def test_int_list_reverse_is_clean_under_ubsan(self):
        source, expected = PROGRAMS["int-list-reverse"]
        self.run_sanitized(source, expected, "undefined")


if __name__ == "__main__":
    unittest.main()
