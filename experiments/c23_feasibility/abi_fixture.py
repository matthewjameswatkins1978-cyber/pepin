"""Build and execute the separately compiled C23 ABI fixture corpus."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from test_feasibility import REPO, fixture_executable, resolve_compiler


ROOT = Path(__file__).resolve().parent
BUILD_TIMEOUT_SECONDS = 45


def fields(line):
    parts = line.split("|")
    return parts[0], dict(part.split("=", 1) for part in parts[1:])


def run_fixture(name):
    build = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(ROOT / "build.ps1"), "-Compiler", name, "-Fixtures"],
        cwd=REPO,
        text=True,
        capture_output=True,
        timeout=BUILD_TIMEOUT_SECONDS,
        check=False,
    )
    if build.returncode != 0:
        raise RuntimeError(f"{name} fixture build failed: {build.stdout}{build.stderr}")
    executable = fixture_executable(name)
    proof = subprocess.run([str(executable)], cwd=REPO, text=True, capture_output=True, check=False)
    if proof.returncode != 0:
        raise RuntimeError(f"{name} fixture execution failed: {proof.stdout}{proof.stderr}")
    lines = proof.stdout.splitlines()
    if len(lines) != 3:
        raise RuntimeError(f"{name} fixture output is not the three-line ABI receipt")
    parsed = dict(fields(line) for line in lines)
    object_root = executable.parent
    objects = {
        path.name: path.stat().st_size
        for path in sorted(object_root.glob("*.o"))
    }
    return {
        "compiler": parsed["ABI"]["compiler"],
        "semantic": {key: value for key, value in parsed["ABI"].items() if key != "compiler"},
        "errors": parsed["ERRORS"],
        "layout": {key: int(value) for key, value in parsed["LAYOUT"].items()},
        "build_commands": [line.removeprefix("COMMAND|") for line in build.stdout.splitlines() if line.startswith("COMMAND|")],
        "object_bytes": objects,
        "executable_bytes": executable.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reports = [run_fixture(name) for name in ("clang", "gcc")]
    semantic_equal = reports[0]["semantic"] == reports[1]["semantic"]
    errors_equal = reports[0]["errors"] == reports[1]["errors"]
    report = {
        "schema": 1,
        "status": "passed" if semantic_equal and errors_equal else "failed",
        "source_revision": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True, capture_output=True, check=True
        ).stdout.strip(),
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "fixtures").glob("*"))
            if path.is_file()
        },
        "strict_flags": ["-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2"],
        "separate_translation_units": True,
        "semantic_equal": semantic_equal,
        "errors_equal": errors_equal,
        "layout_values_equal": reports[0]["layout"] == reports[1]["layout"],
        "compilers": reports,
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
