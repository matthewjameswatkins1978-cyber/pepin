import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
NATIVE_ORDER = [
    ("expression", "checked_add_value_result"),
    ("record", "record_field_sum_result"),
    ("list_original", "list_sum_original_result"),
    ("list_extended", "list_sum_extended_result"),
    ("factorial", "recursive_factorial_result"),
    ("sum_to", "while_for_sum_result"),
]


def run(command, env=None):
    return subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False, env=env)


def interpreter_values():
    result = run(["pwsh", "-NoProfile", "-File", str(REPO / "pep.ps1"), "run", str(ROOT / "shared_semantics.pep")])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Pep interpreter failed")
    return [int(line) for line in result.stdout.splitlines()]


def native_values(compiler):
    executable = REPO / "_build" / "c23-feasibility" / compiler / "pep_c23_probe.exe"
    result = run([str(executable)])
    if result.returncode != 0:
        raise RuntimeError(f"{compiler} native proof failed: {result.returncode}")
    values = {}
    for line in result.stdout.splitlines():
        if line.startswith("OBS|"):
            _, key, value = line.split("|", 2)
            values[key] = value
    return values


def comparison(compiler):
    interpreted = interpreter_values()
    native = native_values(compiler)
    rows = []
    for index, (name, native_key) in enumerate(NATIVE_ORDER):
        native_value = int(native[native_key])
        interpreted_value = interpreted[index]
        rows.append({"name": name, "interpreter": interpreted_value, "native": native_value, "equal": interpreted_value == native_value})
    return {"compiler": compiler, "rows": rows, "equal": all(row["equal"] for row in rows)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", choices=("clang", "gcc"), action="append")
    args = parser.parse_args()
    compilers = args.compiler or ["clang", "gcc"]
    documents = [comparison(compiler) for compiler in compilers]
    print(json.dumps({"comparisons": documents, "equal": all(item["equal"] for item in documents)}, separators=(",", ":"), sort_keys=True))
    return 0 if all(item["equal"] for item in documents) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
