#!/usr/bin/env python3
"""Small bounded size/startup baseline for generated artifacts; not a compiler benchmark."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from artifact_lab import generate
from run_artifacts import STRICT_FLAGS, _check_timeout, compiler_version, discover_compiler, expected_value, parse_artifact_output, run_process


def command_text(command: list[str]) -> str:
    return " ".join('"' + item + '"' if " " in item else item for item in command)


def verify_execution(executable: Path, fixture_id: str, expected: dict, root: Path, timeout: float, phase: str, index: int) -> dict:
    command = [str(executable)]
    started = time.perf_counter_ns()
    result = run_process(command, timeout, root)
    elapsed_ns = time.perf_counter_ns() - started
    record = {
        "phase": phase,
        "index": index,
        "command": command_text(command),
        "state": result.state,
        "exit": result.code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "output": result.output,
        "timeout": result.timed_out,
        "elapsed_ns": elapsed_ns,
        "match": False,
    }
    if result.timed_out:
        record["error"] = "timeout"
        return record
    try:
        actual = parse_artifact_output(result.stdout, fixture_id)
    except ValueError as exc:
        record["error"] = str(exc)
        return record
    record["observation"] = actual
    if expected["status"] == "success":
        record["match"] = result.code == 0 and actual == {"status": "success", "value": expected_value(expected)}
    else:
        record["match"] = result.code == 2 and actual == {"status": "runtime_error", "error": expected["error"]}
    if not record["match"]:
        record["error"] = "unexpected_exit_or_observation"
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", type=Path, default=Path("_build/c23-artifact-05/performance.json"))
    args = parser.parse_args(argv)
    if not 1 <= args.trials <= 20 or not 0 <= args.warmups <= 5:
        raise SystemExit("trials must be 1..20 and warmups 0..5")
    try:
        _check_timeout(args.timeout)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    root = Path.cwd()
    fixture_dir = Path(__file__).parent / "fixtures"
    build = root / "_build/c23-artifact-05/performance"
    build.mkdir(parents=True, exist_ok=True)
    runtime = root / "experiments/c23_feasibility/c23_runtime.c"
    include = runtime.parent
    rows = []
    for compiler_name in ("clang", "gcc"):
        compiler = discover_compiler(compiler_name)
        for manifest_path in sorted(fixture_dir.glob("*.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            source = build / (compiler_name + "_" + manifest_path.stem + ".c")
            generated = generate(manifest_path, source)
            row = {"compiler": compiler_name, "fixture": manifest["fixture_id"], "source_sha256": generated["sha256"], "source_bytes": source.stat().st_size, "warmups": args.warmups, "trials": args.trials}
            if compiler is None:
                row["status"] = "unavailable"
                rows.append(row)
                continue
            artifact_obj = build / (compiler_name + "_" + manifest_path.stem + ".o")
            runtime_obj = build / (compiler_name + "_runtime.o")
            executable = build / (compiler_name + "_" + manifest_path.stem + ".exe")
            compile_command = [compiler, *STRICT_FLAGS, "-I", str(include), "-c", str(source), "-o", str(artifact_obj)]
            runtime_command = [compiler, *STRICT_FLAGS, "-I", str(include), "-c", str(runtime), "-o", str(runtime_obj)]
            link_command = [compiler, *STRICT_FLAGS, str(artifact_obj), str(runtime_obj), "-o", str(executable)]
            identity = compiler_version(compiler, args.timeout, root)
            row["compiler_version"] = identity
            if identity["status"] != "ok":
                row["status"] = "compiler_identity_failed"
                rows.append(row)
                continue
            failed = None
            for command in (compile_command, runtime_command, link_command):
                result = run_process(command, args.timeout, root)
                if result.state != "completed":
                    failed = {"status": "timeout", "command": command_text(command), "stdout": result.stdout, "stderr": result.stderr, "diagnostics": result.output}
                    break
                if result.code != 0:
                    failed = {"status": "failed", "command": command_text(command), "exit": result.code, "stdout": result.stdout, "stderr": result.stderr, "diagnostics": result.output}
                    break
            if failed:
                row.update(failed)
                rows.append(row)
                continue
            runs = []
            expected = manifest["expected"]
            for index in range(args.warmups):
                runs.append(verify_execution(executable, manifest["fixture_id"], expected, root, args.timeout, "warmup", index))
            for index in range(args.trials):
                runs.append(verify_execution(executable, manifest["fixture_id"], expected, root, args.timeout, "trial", index))
            trials = [record for record in runs if record["phase"] == "trial"]
            samples = [record["elapsed_ns"] for record in trials]
            matches = bool(runs) and all(record["match"] for record in runs)
            row.update({"status": "passed" if matches else "mismatch", "object_bytes": artifact_obj.stat().st_size, "runtime_object_bytes": runtime_obj.stat().st_size, "executable_bytes": executable.stat().st_size, "compile_command": command_text(compile_command), "runtime_command": command_text(runtime_command), "link_command": command_text(link_command), "exit": trials[-1]["exit"], "output": trials[-1]["output"], "runs": runs, "samples_ns": samples, "min_ns": min(samples), "max_ns": max(samples), "mean_ns": sum(samples) // len(samples), "source_sha256_runtime": hashlib.sha256(runtime.read_bytes()).hexdigest()})
            rows.append(row)
    report = {"schema": 2, "generator_version": "pep-c23-artifact-05.1", "strict_flags": STRICT_FLAGS, "receipt_policy": "stdout must contain exactly one ARTIFACT receipt; stderr is recorded but not parsed; every warmup and trial must match", "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "passed" if rows and all(row["status"] == "passed" for row in rows) else "failed", "rows": len(rows), "output": str(args.output)}, sort_keys=True))
    return 0 if rows and all(row["status"] == "passed" for row in rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
