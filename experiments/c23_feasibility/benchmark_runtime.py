import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

from test_feasibility import executable, resolve_compiler


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PROCESS_TIMEOUT_SECONDS = 15
BUILD_TIMEOUT_SECONDS = 45
MAX_TRIALS = 20
INT64_MAX = (1 << 63) - 1
INT64_MIN = -(1 << 63)
CASES = {
    "arithmetic": [(32, 1000), (256, 1000), (2048, 1000)],
    "record": [(1, 10000), (16, 10000), (64, 10000)],
    "union": [(4, 50), (16, 50), (64, 50)],
    "arena": [(8, 100), (64, 100), (256, 100)],
    "list": [(8, 100), (64, 100), (256, 100)],
    "recursive": [(4, 200), (16, 200), (64, 200)],
    "utf8": [(16, 500), (256, 500), (4096, 500)],
}
SOURCE_FILES = (
    "c23_runtime.h",
    "c23_runtime.c",
    "c23_benchmark.c",
    "build.ps1",
)


class BenchmarkFailure(RuntimeError):
    def __init__(self, message, **context):
        super().__init__(message)
        self.context = context

    def __str__(self):
        return json.dumps(
            {"status": "failed", "message": self.args[0], **self.context},
            separators=(",", ":"),
            sort_keys=True,
        )


def timed_run(command, timeout_seconds=PROCESS_TIMEOUT_SECONDS):
    start = time.perf_counter_ns()
    try:
        result = subprocess.run(
            command,
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        def tail(value):
            if isinstance(value, bytes):
                value = value.decode(errors="replace")
            return (value or "")[-512:]

        raise BenchmarkFailure(
            "process timeout",
            command=[str(part) for part in command],
            timeout_seconds=timeout_seconds,
            stdout=tail(error.stdout),
            stderr=tail(error.stderr),
        ) from error
    return result, time.perf_counter_ns() - start


def parse_record(result, context=None):
    context = {} if context is None else dict(context)
    if result.returncode != 0:
        raise BenchmarkFailure(
            "unexpected process exit",
            exit_code=result.returncode,
            stderr=result.stderr[-512:],
            **context,
        )
    lines = [line for line in result.stdout.splitlines() if line]
    if len(lines) != 1 or not lines[0].startswith("BENCH|"):
        raise BenchmarkFailure("malformed benchmark output", stdout=result.stdout[-512:], **context)
    fields = {}
    try:
        for field in lines[0].split("|")[1:]:
            key, value = field.split("=", 1)
            fields[key] = int(value) if key not in {"case", "clock"} else value
    except (TypeError, ValueError) as error:
        raise BenchmarkFailure("malformed benchmark field", stdout=lines[0], **context) from error
    return fields


def expected_case(case, size, iterations):
    operations = size * iterations
    if case == "arithmetic":
        per_iteration = sum(index % 97 for index in range(size))
        checksum = per_iteration * iterations
    elif case == "record":
        checksum = 42 * size * iterations
    elif case in {"union", "recursive"}:
        checksum = size * iterations
    elif case == "arena":
        checksum = (size * (size - 1) // 2) * iterations
    elif case == "list":
        checksum = (sum(index % 97 for index in range(size)) + 7) * iterations
    elif case == "utf8":
        checksum = size * iterations
    else:
        raise BenchmarkFailure("unknown expected benchmark case", case=case)
    if not INT64_MIN <= checksum <= INT64_MAX:
        raise BenchmarkFailure("independent expected value exceeds Pep Int", case=case, checksum=checksum)
    return {"case": case, "size": size, "iterations": iterations, "operations": operations, "checksum": checksum}


def validate_record(record, expected, compiler, phase, trial):
    context = {
        "compiler": compiler,
        "case": expected["case"],
        "size": expected["size"],
        "iterations": expected["iterations"],
        "phase": phase,
        "trial": trial,
    }
    required = ("case", "size", "iterations", "operations", "checksum", "bytes", "reserved", "elapsed_ns", "clock")
    missing = [key for key in required if key not in record]
    if missing:
        raise BenchmarkFailure("missing benchmark field", missing=missing, **context)
    for key in expected:
        if record[key] != expected[key]:
            raise BenchmarkFailure(
                "benchmark observable mismatch",
                field=key,
                expected=expected[key],
                observed=record[key],
                **context,
            )
    if record["elapsed_ns"] < 0 or record["clock"] not in {"qpc", "timespec_get_utc"}:
        raise BenchmarkFailure("invalid benchmark clock result", observed_clock=record["clock"], **context)
    return record


def validate_cross_compiler(reports):
    if len(reports) < 2:
        return
    by_key = {}
    for report in reports:
        for row in report["rows"]:
            key = (row["case"], row["size"], row["iterations"])
            by_key.setdefault(key, []).append((report["compiler"], row))
    for key, observations in by_key.items():
        checksums = {tuple(item[1]["observed_checksums"]) for item in observations}
        if len(checksums) != 1:
            raise BenchmarkFailure(
                "cross-compiler checksum disagreement",
                case=key[0],
                size=key[1],
                iterations=key[2],
                observations={compiler: row["observed_checksums"] for compiler, row in observations},
            )


def compiler_version(compiler):
    result, _ = timed_run([compiler, "--version"], timeout_seconds=PROCESS_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise BenchmarkFailure("compiler version failed", compiler=compiler, exit_code=result.returncode)
    return result.stdout.splitlines()[0]


def source_identity():
    revision_result, _ = timed_run(["git", "rev-parse", "HEAD"], timeout_seconds=5)
    if revision_result.returncode != 0:
        raise BenchmarkFailure("source revision unavailable", stderr=revision_result.stderr[-512:])
    return {
        "revision": revision_result.stdout.strip(),
        "files_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in SOURCE_FILES
        },
    }


def run_benchmark(compiler_name, compiler, trials):
    build_args = ["pwsh", "-NoProfile", "-File", str(ROOT / "build.ps1"), "-Compiler", compiler_name, "-Benchmark"]
    build_result, build_elapsed = timed_run(build_args, timeout_seconds=BUILD_TIMEOUT_SECONDS)
    if build_result.returncode != 0:
        raise BenchmarkFailure(
            "benchmark build failed",
            compiler=compiler_name,
            exit_code=build_result.returncode,
            stdout=build_result.stdout[-1024:],
            stderr=build_result.stderr[-1024:],
        )
    build_commands = [line.removeprefix("COMMAND|") for line in build_result.stdout.splitlines() if line.startswith("COMMAND|")]
    benchmark_executable = executable(compiler_name).parent / "benchmark" / "pep_c23_benchmark.exe"
    rows = []
    for case, sizes in CASES.items():
        for size, iterations in sizes:
            expected = expected_case(case, size, iterations)
            command = [str(benchmark_executable), case, str(size), str(iterations)]
            context = {"compiler": compiler_name, "case": case, "size": size, "iterations": iterations}
            warmup_result, _ = timed_run(command)
            warmup = validate_record(parse_record(warmup_result, {**context, "phase": "warmup", "trial": None}), expected, compiler_name, "warmup", None)
            observed_checksums = []
            native_samples = []
            process_samples = []
            parsed = None
            for trial in range(1, trials + 1):
                result, process_elapsed = timed_run(command)
                parsed = validate_record(parse_record(result, {**context, "phase": "trial", "trial": trial}), expected, compiler_name, "trial", trial)
                observed_checksums.append(parsed["checksum"])
                native_samples.append(parsed["elapsed_ns"])
                process_samples.append(process_elapsed)
            rows.append({
                **context,
                "operations": expected["operations"],
                "expected_checksum": expected["checksum"],
                "warmup_checksum": warmup["checksum"],
                "observed_checksums": observed_checksums,
                "checksum": parsed["checksum"],
                "bytes": parsed["bytes"],
                "arena_reserved_bytes": parsed["reserved"],
                "clock": parsed["clock"],
                "native_elapsed_ns_samples": native_samples,
                "native_elapsed_ns_median": int(statistics.median(native_samples)),
                "process_wall_ns_samples": process_samples,
                "process_wall_ns_median": int(statistics.median(process_samples)),
                "validation": "passed",
            })
    return {
        "compiler": compiler_name,
        "version": compiler_version(compiler),
        "strict_flags": ["-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2"],
        "build_commands": build_commands,
        "compile_elapsed_ns": build_elapsed,
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", choices=("clang", "gcc"), action="append")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.trials < 2 or args.trials > MAX_TRIALS:
        parser.error(f"--trials must be between 2 and {MAX_TRIALS}")
    compilers = args.compiler or ["clang", "gcc"]
    reports = []
    for name in compilers:
        compiler = resolve_compiler(name)
        if compiler is None:
            raise SystemExit(f"UNAVAILABLE|{name}")
        reports.append(run_benchmark(name, compiler, args.trials))
    validate_cross_compiler(reports)
    identity = source_identity()
    payload = {
        "schema": 2,
        "status": "passed",
        "source": identity,
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
        },
        "method": {
            "warmup_runs": 1,
            "measured_trials": args.trials,
            "max_trials": MAX_TRIALS,
            "process_timeout_seconds": PROCESS_TIMEOUT_SECONDS,
            "build_timeout_seconds": BUILD_TIMEOUT_SECONDS,
            "native_elapsed": "monotonic QueryPerformanceCounter on Windows; timespec_get(TIME_UTC) fallback elsewhere",
            "process_wall": "Python perf_counter_ns around executable invocation, including process startup",
            "memory": "arena_reserved_bytes is reserved arena capacity; bytes is the case input/output estimate, not peak RSS",
            "oracle": "independent Python expected checksums and operation counts; every warmup and trial validated",
            "cross_compiler": "all observed checksum sequences must agree when multiple compilers are selected",
        },
        "compilers": reports,
        "validation": "passed",
    }
    text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BenchmarkFailure as error:
        print(f"BENCHMARK_FAILURE|{error}", file=sys.stderr)
        raise SystemExit(1)
