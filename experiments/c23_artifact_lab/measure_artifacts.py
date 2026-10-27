#!/usr/bin/env python3
"""Small bounded size/startup baseline for generated artifacts; not a compiler benchmark."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from artifact_lab import generate
from run_artifacts import STRICT_FLAGS, compiler_version, discover_compiler, expected_value, parse_artifact_output


def command_text(command: list[str]) -> str:
    return " ".join('"' + item + '"' if " " in item else item for item in command)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", type=Path, default=Path("_build/c23-artifact-05/performance.json"))
    args = parser.parse_args(argv)
    if not 1 <= args.trials <= 20 or not 0 <= args.warmups <= 5:
        raise SystemExit("trials must be 1..20 and warmups 0..5")
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
            failed = None
            for command in (compile_command, runtime_command, link_command):
                try:
                    result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=args.timeout, check=False)
                except subprocess.TimeoutExpired:
                    failed = {"status": "timeout", "command": command_text(command)}
                    break
                if result.returncode != 0:
                    failed = {"status": "failed", "command": command_text(command), "exit": result.returncode, "diagnostics": (result.stdout + result.stderr).strip()}
                    break
            if failed:
                row.update(failed)
                rows.append(row)
                continue
            samples = []
            output = ""
            exit_code = None
            for _ in range(args.warmups):
                subprocess.run([str(executable)], cwd=root, capture_output=True, text=True, timeout=args.timeout, check=False)
            for _ in range(args.trials):
                started = time.perf_counter_ns()
                result = subprocess.run([str(executable)], cwd=root, capture_output=True, text=True, timeout=args.timeout, check=False)
                samples.append(time.perf_counter_ns() - started)
                output = (result.stdout + result.stderr).strip()
                exit_code = result.returncode
            try:
                actual = parse_artifact_output(output, manifest["fixture_id"])
                expected = manifest["expected"]
                if expected["status"] == "success":
                    matches = exit_code == 0 and actual == {"status": "success", "value": expected_value(expected)}
                else:
                    matches = exit_code == 2 and actual == {"status": "runtime_error", "error": expected["error"]}
            except ValueError:
                matches = False
            row.update({"status": "passed" if matches else "mismatch", "compiler_version": compiler_version(compiler, args.timeout, root), "object_bytes": artifact_obj.stat().st_size, "runtime_object_bytes": runtime_obj.stat().st_size, "executable_bytes": executable.stat().st_size, "compile_command": command_text(compile_command), "runtime_command": command_text(runtime_command), "link_command": command_text(link_command), "exit": exit_code, "output": output, "samples_ns": samples, "min_ns": min(samples), "max_ns": max(samples), "mean_ns": sum(samples) // len(samples), "source_sha256_runtime": hashlib.sha256(runtime.read_bytes()).hexdigest()})
            rows.append(row)
    report = {"schema": 1, "generator_version": "pep-c23-artifact-05.1", "strict_flags": STRICT_FLAGS, "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "passed" if rows and all(row["status"] == "passed" for row in rows) else "failed", "rows": len(rows), "output": str(args.output)}, sort_keys=True))
    return 0 if rows and all(row["status"] == "passed" for row in rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
