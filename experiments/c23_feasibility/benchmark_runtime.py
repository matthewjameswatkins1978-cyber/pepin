import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path

from test_feasibility import executable, resolve_compiler


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
CASES = {
    "arithmetic": [(32, 1000), (256, 1000), (2048, 1000)],
    "record": [(1, 10000), (16, 10000), (64, 10000)],
    "union": [(4, 50), (16, 50), (64, 50)],
    "arena": [(8, 100), (64, 100), (256, 100)],
    "list": [(8, 100), (64, 100), (256, 100)],
    "recursive": [(4, 200), (16, 200), (64, 200)],
    "utf8": [(16, 500), (256, 500), (4096, 500)],
}


def timed_run(command):
    start = time.perf_counter_ns()
    result = subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False)
    return result, time.perf_counter_ns() - start


def parse_record(result):
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"benchmark failed with exit {result.returncode}")
    lines = [line for line in result.stdout.splitlines() if line]
    if len(lines) != 1 or not lines[0].startswith("BENCH|"):
        raise RuntimeError(f"unexpected benchmark output: {result.stdout!r}")
    fields = {}
    for field in lines[0].split("|")[1:]:
        key, value = field.split("=", 1)
        fields[key] = int(value) if key not in {"case"} else value
    return fields


def compiler_version(compiler):
    result = subprocess.run([compiler, "--version"], cwd=REPO, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "compiler version failed")
    return result.stdout.splitlines()[0]


def run_benchmark(compiler_name, compiler, trials):
    build_args = ["pwsh", "-NoProfile", "-File", str(ROOT / "build.ps1"), "-Compiler", compiler_name, "-Benchmark"]
    build_result, build_elapsed = timed_run(build_args)
    if build_result.returncode != 0:
        raise RuntimeError(build_result.stdout + build_result.stderr)
    benchmark_executable = executable(compiler_name).parent / "benchmark" / "pep_c23_benchmark.exe"
    rows = []
    for case, sizes in CASES.items():
        for size, iterations in sizes:
            command = [str(benchmark_executable), case, str(size), str(iterations)]
            warmup, _ = timed_run(command)
            parse_record(warmup)
            native_samples = []
            process_samples = []
            parsed = None
            for _ in range(trials):
                result, process_elapsed = timed_run(command)
                parsed = parse_record(result)
                native_samples.append(parsed["elapsed_ns"])
                process_samples.append(process_elapsed)
            rows.append({
                "compiler": compiler_name,
                "case": case,
                "size": size,
                "iterations": iterations,
                "operations": parsed["operations"],
                "checksum": parsed["checksum"],
                "bytes": parsed["bytes"],
                "arena_reserved_bytes": parsed["reserved"],
                "native_elapsed_ns_samples": native_samples,
                "native_elapsed_ns_median": int(statistics.median(native_samples)),
                "process_wall_ns_samples": process_samples,
                "process_wall_ns_median": int(statistics.median(process_samples)),
            })
    return {
        "compiler": compiler_name,
        "version": compiler_version(compiler),
        "strict_flags": ["-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2"],
        "compile_elapsed_ns": build_elapsed,
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", choices=("clang", "gcc"), action="append")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.trials < 2:
        parser.error("--trials must be at least 2")
    compilers = args.compiler or ["clang", "gcc"]
    reports = []
    for name in compilers:
        compiler = resolve_compiler(name)
        if compiler is None:
            raise SystemExit(f"UNAVAILABLE|{name}")
        reports.append(run_benchmark(name, compiler, args.trials))
    payload = {
        "schema": 1,
        "method": {
            "warmup_runs": 1,
            "measured_trials": args.trials,
            "native_elapsed": "C23 timespec_get wall-clock around the operation",
            "process_wall": "Python perf_counter_ns around executable invocation, including process startup",
            "memory": "arena_reserved_bytes is reserved arena capacity; bytes is the case input/output estimate, not peak RSS",
        },
        "compilers": reports,
    }
    text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
