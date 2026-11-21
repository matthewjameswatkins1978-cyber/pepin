#!/usr/bin/env python3
"""Run native arena stress/fault injection with real GCC/Clang C23.

Optional --sanitize uses ASan+UBSan (requires host toolchain support).
This verifies the explicit-lifetime byte arena only, not tracing GC/rooting.
"""
import argparse
import pathlib
import shutil
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
ARENA = ROOT / "runtime" / "pep_arena"
EXPECTED = (
    "allocation fault injection: handle, first chunk, later growth; sticky status and cleanup OK\n"
    "overflow, invalid alignment/size, isolation and repeated free: OK\n"
    "stress: 4096 nonoverlapping aligned allocations; all bytes retained\n"
)


def run(compiler, sanitize):
    flags = ["-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2"]
    if sanitize:
        flags.extend(["-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                      "-fno-omit-frame-pointer"])
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        obj, exe = root / "arena.o", root / "arena_stress.exe"
        # Redirect allocation only in the production object. The test wrapper
        # and any other library calls use the normal allocator.
        subprocess.run([compiler, *flags, "-Dmalloc=lucy_test_malloc", "-Dfree=lucy_test_free",
                        "-c", str(ARENA / "pep_arena.c"), "-o", str(obj)], check=True, timeout=30)
        subprocess.run([compiler, *flags, "-I", str(ARENA),
                        str(ROOT / "verification" / "lucy_arena_stress.c"), str(obj),
                        "-o", str(exe)], check=True, timeout=30)
        result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
        if (result.returncode, result.stdout, result.stderr) != (0, EXPECTED, ""):
            raise RuntimeError(f"{compiler} exit={result.returncode}\n{result.stdout}\n{result.stderr}")
        print(f"{compiler}: PASS\n{result.stdout}", end="")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", action="append", help="Compiler name or path; repeat for both")
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    compilers = args.compiler or [name for name in ("gcc", "clang") if shutil.which(name)]
    if not compilers:
        parser.error("No GCC/Clang found")
    for compiler in compilers:
        run(compiler, args.sanitize)


if __name__ == "__main__":
    main()
