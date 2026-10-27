import argparse
import json
import os
import subprocess
import sys
import tempfile
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
FAILURE_CASES = [
    {
        "name": "add_overflow",
        "native_key": "add_overflow",
        "native_status": "overflow",
        "semantic": "integer_overflow",
        "pep_source": "say(int_text(9223372036854775807 + 1))\n",
        "pep_code": "PEP_RUNTIME_OVERFLOW",
    },
    {
        "name": "division_by_zero",
        "native_key": "division_by_zero",
        "native_status": "division_by_zero",
        "semantic": "division_by_zero",
        "pep_source": "say(int_text(8 / 0))\n",
        "pep_code": "PEP_RUNTIME_DIVISION_BY_ZERO",
    },
    {
        "name": "recursive_depth_limit",
        "native_key": "recursive_union_depth_limit",
        "native_status": "depth",
        "semantic": "call_depth_limit",
        "pep_source": (
            "fn f(n: Int) -> Int {\n"
            "    if n == 0 { return 0 } else { return f(n - 1) }\n"
            "}\n"
            "say(int_text(f(1000)))\n"
        ),
        "pep_code": "PEP_RUNTIME_CALL_DEPTH",
    },
]
NATIVE_ONLY_FAILURES = [
    {"name": "invalid_variant", "native_key": "recursive_union_reject_invalid_tag"},
    {"name": "malformed_utf8", "native_key": "utf8_reject_overlong"},
    {"name": "allocator_failure", "native_key": "list_allocator_failure"},
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


def interpreter_failure(source):
    build_root = REPO / "_build"
    build_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=build_root) as directory:
        path = Path(directory) / "failure_case.pep"
        path.write_text(source, encoding="utf-8")
        result = run([
            "pwsh", "-NoProfile", "-File", str(REPO / "pep.ps1"),
            "run", str(path), "--json",
        ])
    if result.returncode == 0:
        raise RuntimeError("Pep failure case unexpectedly succeeded")
    try:
        payload = json.loads(result.stdout)
        return payload["status"], payload["diagnostics"][0]["code"]
    except (KeyError, IndexError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Pep failure case did not produce a diagnostic: {result.stdout!r}") from error


def failure_comparison(compiler, native):
    rows = []
    for case in FAILURE_CASES:
        native_status = native[case["native_key"]]
        interpreter_status, interpreter_code = interpreter_failure(case["pep_source"])
        equal = (
            native_status == case["native_status"]
            and interpreter_status == "runtime_error"
            and interpreter_code == case["pep_code"]
        )
        rows.append({
            "name": case["name"],
            "semantic": case["semantic"],
            "comparable": True,
            "interpreter": {"status": interpreter_status, "code": interpreter_code},
            "native": {"status": native_status},
            "equal": equal,
        })
    for case in NATIVE_ONLY_FAILURES:
        rows.append({
            "name": case["name"],
            "comparable": False,
            "interpreter": {"status": "not_representable"},
            "native": {"status": native[case["native_key"]]},
            "equal": None,
        })
    return rows


def comparison(compiler):
    interpreted = interpreter_values()
    native = native_values(compiler)
    rows = []
    for index, (name, native_key) in enumerate(NATIVE_ORDER):
        native_value = int(native[native_key])
        interpreted_value = interpreted[index]
        rows.append({"name": name, "interpreter": interpreted_value, "native": native_value, "equal": interpreted_value == native_value})
    failure_rows = failure_comparison(compiler, native)
    comparable_failures = [row for row in failure_rows if row["comparable"]]
    return {
        "compiler": compiler,
        "rows": rows,
        "failures": failure_rows,
        "counterexamples": [row for row in comparable_failures if not row["equal"]],
        "equal": all(row["equal"] for row in rows + comparable_failures),
    }


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
