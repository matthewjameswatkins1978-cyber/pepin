#!/usr/bin/env python3
"""Bounded native/interpreter runner for the isolated Artifact-05 lab."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from artifact_lab import FixtureError, generate

STRICT_FLAGS = ["-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2"]
KNOWN = {
    "clang": [r"C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe"],
    "gcc": [r"C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe"],
}
ARTIFACT_RE = re.compile(r"^ARTIFACT\|fixture=([^|]+)\|status=(success|runtime_error)\|(value|error)=(.*)$")


def _decode_stream(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _check_timeout(timeout: float) -> None:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a finite positive number")


@dataclass(frozen=True)
class ProcessResult:
    state: str
    code: int | None
    stdout: str
    stderr: str
    timed_out: bool

    @property
    def output(self) -> str:
        return (self.stdout + self.stderr).strip()

    def __iter__(self):
        """Keep the small four-value API used by the existing lab callers."""
        yield self.state
        yield self.code
        yield self.output
        yield self.timed_out


def discover_compiler(name: str, environ: dict[str, str] | None = None, which: Any = shutil.which) -> str | None:
    environ = os.environ if environ is None else environ
    override = environ.get("PEP_C23_CLANG" if name == "clang" else "PEP_C23_GCC")
    candidates = [override] if override else []
    candidates += [which(name)]
    candidates += KNOWN[name]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    return None


def command_text(command: list[str]) -> str:
    return " ".join('"' + part + '"' if " " in part else part for part in command)


def parse_artifact_output(output: str, fixture_id: str) -> dict[str, Any]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    rows = [ARTIFACT_RE.match(line) for line in lines]
    if len(rows) != 1 or rows[0] is None or rows[0].group(1) != fixture_id:
        raise ValueError("missing or ambiguous ARTIFACT receipt")
    row = rows[0]
    status, field, value = row.group(2), row.group(3), row.group(4)
    return {"status": status, field: value}


def expected_value(expected: dict[str, Any]) -> str | None:
    if expected["status"] == "runtime_error":
        return None
    value = expected["value"]
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "unit"
    return str(value)


def run_process(command: list[str], timeout: float, cwd: Path) -> ProcessResult:
    _check_timeout(timeout)
    try:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=False, timeout=timeout, check=False)
        return ProcessResult("completed", completed.returncode, _decode_stream(completed.stdout), _decode_stream(completed.stderr), False)
    except subprocess.TimeoutExpired as exc:
        return ProcessResult("timeout", None, _decode_stream(exc.stdout), _decode_stream(exc.stderr), True)
    except OSError as exc:
        return ProcessResult("failed", None, "", str(exc), False)


def compiler_version(path: str, timeout: float, cwd: Path) -> dict[str, Any]:
    result = run_process([path, "--version"], timeout, cwd)
    state, code, output, _ = result
    if state != "completed" or code != 0:
        return {"status": "unavailable", "state": state, "exit": code, "output": output}
    if not result.stdout.strip():
        return {"status": "failed", "state": state, "exit": code, "output": output, "reason": "version_empty"}
    return {"status": "ok", "version": result.stdout.splitlines()[0], "output": output}


def compare_interpreter(manifest: dict[str, Any], root: Path, build: Path, timeout: float) -> dict[str, Any]:
    pep = build / (manifest["fixture_id"].replace(".", "_") + ".pep")
    pep.write_text(manifest["pep_source"], encoding="utf-8", newline="\n")
    command = ["pwsh", "-NoProfile", "-File", str(root / "pep.ps1"), "run", str(pep)]
    result = run_process(command, timeout, root)
    state, code, output, timed_out = result
    expected = manifest["expected"]
    if timed_out:
        return {"status": "timeout", "command": command_text(command), "match": False}
    if expected["status"] == "success":
        actual_text = output.rstrip("\r\n")
        actual = actual_text.encode("utf-8").hex() if expected.get("value_encoding") == "utf8_hex" else actual_text
        match = code == 0 and actual == expected_value(expected)
        return {"status": "success" if match else "mismatch", "exit": code, "output": output, "match": match}
    marker = "PEP_RUNTIME_" + str(expected["error"]).upper()
    match = code != 0 and marker in output
    return {"status": "runtime_error" if match else "mismatch", "exit": code, "output": output, "match": match}


def run_fixture(manifest_path: Path, compiler: str | None, compiler_name: str, root: Path, runtime: Path, build: Path, timeout: float, compare: bool) -> dict[str, Any]:
    fixture_id = manifest_path.stem
    receipt: dict[str, Any] = {"fixture": fixture_id, "compiler": compiler_name, "flags": STRICT_FLAGS, "timeout_seconds": timeout}
    try:
        source_path = build / (manifest_path.stem + ".c")
        generated = generate(manifest_path, source_path)
        receipt["generated"] = generated
    except FixtureError as exc:
        receipt.update({"status": "invalid_manifest", "error": exc.as_dict()})
        return receipt
    if compiler is None:
        receipt.update({"status": "unavailable", "reason": "compiler_not_found"})
        return receipt
    exe = build / f"{compiler_name}_{manifest_path.stem}.exe"
    command = [compiler, *STRICT_FLAGS, "-I", str(runtime.parent), str(source_path), str(runtime), "-o", str(exe)]
    identity = compiler_version(compiler, timeout, root)
    receipt["compiler_version"] = identity
    if identity["status"] != "ok":
        receipt["status"] = "compiler_identity_failed"
        return receipt
    compile_result = run_process(command, timeout, root)
    state, code, output, timed_out = compile_result
    receipt.update({"compile": {"state": state, "exit": code, "command": command_text(command), "stdout": compile_result.stdout, "stderr": compile_result.stderr, "diagnostics": output}, "compiler_version": identity})
    if timed_out:
        receipt["status"] = "compile_timeout"
        return receipt
    if code != 0:
        receipt["status"] = "compile_failed"
        return receipt
    execute_result = run_process([str(exe)], timeout, root)
    run_state, run_code, run_output, run_timed_out = execute_result
    receipt["execute"] = {"state": run_state, "exit": run_code, "stdout": execute_result.stdout, "stderr": execute_result.stderr, "output": run_output, "timeout": run_timed_out}
    if run_timed_out:
        receipt["status"] = "execute_timeout"
        return receipt
    try:
        actual = parse_artifact_output(execute_result.stdout, json.loads(manifest_path.read_text(encoding="utf-8"))["fixture_id"])
        expected = json.loads(manifest_path.read_text(encoding="utf-8"))["expected"]
        if expected["status"] == "success":
            match = run_code == 0 and actual == {"status": "success", "value": expected_value(expected)}
        else:
            match = run_code == 2 and actual == {"status": "runtime_error", "error": expected["error"]}
        receipt["native_observation"] = actual
        receipt["native_match"] = match
        receipt["status"] = "passed" if match else "native_mismatch"
    except (ValueError, json.JSONDecodeError, KeyError) as exc:
        receipt.update({"status": "invalid_native_receipt", "error": str(exc)})
    if compare and receipt["status"] == "passed":
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        receipt["interpreter"] = compare_interpreter(manifest, root, build, timeout)
        if not receipt["interpreter"]["match"]:
            receipt["status"] = "interpreter_mismatch"
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-dir", type=Path, default=Path(__file__).parent / "fixtures")
    parser.add_argument("--build-dir", type=Path, default=Path("_build/c23-artifact-05/native"))
    parser.add_argument("--runtime", type=Path, default=Path("experiments/c23_feasibility/c23_runtime.c"))
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--no-interpreter", action="store_true")
    args = parser.parse_args(argv)
    root = Path.cwd()
    build = args.build_dir if args.build_dir.is_absolute() else root / args.build_dir
    runtime = args.runtime if args.runtime.is_absolute() else root / args.runtime
    build.mkdir(parents=True, exist_ok=True)
    compilers = {name: discover_compiler(name) for name in ("clang", "gcc")}
    rows = []
    for name, path in compilers.items():
        for manifest in sorted(args.manifest_dir.glob("*.json")):
            rows.append(run_fixture(manifest, path, name, root, runtime, build, args.timeout, not args.no_interpreter))
    print(json.dumps({"generator": "pep-c23-artifact-05.1", "strict_flags": STRICT_FLAGS, "compilers": compilers, "receipts": rows}, sort_keys=True, indent=2))
    if not rows or any(row["status"] != "passed" for row in rows):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
