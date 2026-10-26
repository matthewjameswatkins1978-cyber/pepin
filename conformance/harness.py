#!/usr/bin/env python3
"""Bounded, deterministic black-box conformance lab for Pepin.

The harness deliberately drives only the public PowerShell CLI and JSONL
session.  It owns its generated corpus and result schema, while the existing
repository tests remain a separate evidence source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
OUT = ROOT / "_build" / "conformance"
SCHEMA = "pepin-conformance/v1"
DEFAULT_SEEDS = [20261026, 1101, 1201]
PROCESS_TIMEOUT = 8.0


def revision(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def json_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def run_bounded(args: list[str], *, cwd: Path = ROOT, input_text: str | None = None,
                timeout: float = 8.0) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            args, cwd=cwd, input=input_text, text=True, capture_output=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
        return {
            "status": "completed", "returncode": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr,
            "elapsedMs": round((time.perf_counter() - started) * 1000, 2),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout", "returncode": None,
            "stdout": (exc.stdout or ""), "stderr": (exc.stderr or ""),
            "elapsedMs": round((time.perf_counter() - started) * 1000, 2),
        }


def response_from_stdout(stdout: str) -> dict[str, Any] | None:
    for line in reversed([line for line in stdout.splitlines() if line.strip()]):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def write_case(case_id: str, raw: bytes) -> Path:
    path = OUT / "corpus" / f"{case_id}.pep"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def cli_case(case_id: str, raw: bytes, command: str = "check") -> dict[str, Any]:
    path = write_case(case_id, raw)
    result = run_bounded([
        "pwsh", "-NoProfile", "-File", str(PEP), command, str(path), "--json"
    ], timeout=PROCESS_TIMEOUT)
    result["response"] = response_from_stdout(result["stdout"])
    result["caseId"] = case_id
    result["command"] = command
    return result


def session_case(requests: list[Any], timeout: float | None = None) -> dict[str, Any]:
    payload = "\n".join(
        item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
        for item in requests
    ) + "\n"
    result = run_bounded([
        "pwsh", "-NoProfile", "-File", str(PEP), "session", "--jsonl"
    ], input_text=payload, timeout=timeout if timeout is not None else PROCESS_TIMEOUT + 4)
    responses = []
    for line in result["stdout"].splitlines():
        try:
            responses.append(json.loads(line))
        except json.JSONDecodeError:
            responses.append({"_malformedResponse": line})
    result["responses"] = responses
    result["requestCount"] = len(requests)
    return result


def normalized_analysis(response: dict[str, Any] | None) -> dict[str, Any]:
    if not response:
        return {"status": "no-response"}
    status = response.get("status")
    # File-oriented invalid JSON intentionally omits the partial AST and
    # checked tree; the session retains the parsed AST for inspection. Compare
    # the common diagnostic contract in that state.
    if status == "invalid":
        return {"status": status, "diagnostics": response.get("diagnostics", [])}
    holes = []
    for hole in response.get("holes", []):
        normalized = dict(hole)
        # Session identities are revision-bound objects; the file CLI uses a
        # compact string for the same named-hole identity.
        identity = normalized.pop("identity", None)
        if "name" not in normalized and isinstance(identity, str):
            normalized["name"] = identity
        holes.append(normalized)
    return {
        "status": status,
        "ast": response.get("ast"),
        "typedTree": response.get("typedTree"),
        "holes": holes,
        "diagnostics": response.get("diagnostics", []),
    }


def analysis_pair(case_id: str, raw: bytes) -> dict[str, Any]:
    cli = cli_case(case_id, raw, "check")
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {"caseId": case_id, "kind": "cli-session", "classification": "unsupported-feature",
                "detail": "The text CLI cannot carry malformed UTF-8; open_bytes is tested separately."}
    opened = session_case([{"schemaVersion": 3, "op": "open", "source": source}])
    session_response = opened["responses"][0] if opened["responses"] else None
    left = normalized_analysis(cli.get("response"))
    right = normalized_analysis(session_response)
    if left == right:
        classification = "missing-test"
        detail = "CLI check and session open agree"
    else:
        classification = "confirmed-bug"
        detail = "CLI check and session open disagree on normalized semantic result"
    return {
        "caseId": case_id, "kind": "cli-session", "classification": classification,
        "detail": detail, "cli": left, "session": right,
        "cliReturncode": cli["returncode"], "sessionReturncode": opened["returncode"],
        "elapsedMs": {"cli": cli["elapsedMs"], "session": opened["elapsedMs"]},
    }


def valid_sources(seed: int, count: int) -> Iterable[tuple[str, bytes, str | None]]:
    rng = random.Random(seed)
    for index in range(count):
        family = index % 7
        a = rng.randint(-20, 20)
        b = rng.randint(1, 20)
        if family == 0:
            source = f'say(int_text({a} + {b} * 2))\n'
            expected = str(a + b * 2) + "\n"
        elif family == 1:
            values = [rng.randint(-5, 9) for _ in range(3)]
            source = (
                f"let values: List[Int] = [{', '.join(map(str, values))}]\n"
                "say(int_text(length(values)))\n"
                f"say(int_text(if contains(values, {values[1]}) && !(length(values) == 0) {{ 1 }} else {{ 0 }}))\n"
            )
            expected = "3\n1\n"
        elif family == 2:
            source = (
                "fn shadow(value: Int) -> Int {\n"
                "    let inner: Int = value + 1\n"
                "    { let inner: Int = inner + 1; return inner }\n"
                "}\n"
                f"say(int_text(shadow({a})))\n"
            )
            expected = str(a + 2) + "\n"
        elif family == 3:
            n = rng.randint(0, 6)
            expected_value = 1
            for value in range(2, n + 1):
                expected_value *= value
            source = (
                "fn fact(n: Int) -> Int {\n"
                "    return if n <= 1 { 1 } else { n * fact(n - 1) }\n"
                "}\n"
                f"say(int_text(fact({n})))\n"
            )
            expected = str(expected_value) + "\n"
        elif family == 4:
            source = (
                "type Point { x: Int y: Int }\n"
                "fn sum(point: Point) -> Int { return point.x + point.y }\n"
                f"say(int_text(sum(Point {{ x: {a}, y: {b} }})))\n"
            )
            expected = str(a + b) + "\n"
        elif family == 5:
            source = (
                "type Expr = Number(Int) | Add(Expr, Expr)\n"
                "fn evaluate(expr: Expr) -> Int {\n"
                "    return match expr { Number(n) => n Add(left, right) => evaluate(left) + evaluate(right) }\n"
                "}\n"
                f"say(int_text(evaluate(Add(Number({a}), Number({b})))))\n"
            )
            expected = str(a + b) + "\n"
        else:
            n = rng.randint(1, 5)
            source = (
                "fn count_down(start: Int) -> Int {\n"
                "    var current = start\n"
                "    while current != 0 { current = current - 1 }\n"
                "    return current\n"
                "}\n"
                f"say(int_text(count_down({n})))\n"
            )
            expected = "0\n"
        yield f"valid-{seed}-{index:04d}", source.encode("utf-8"), expected


def invalid_sources(seed: int, count: int) -> Iterable[tuple[str, bytes, str]]:
    rng = random.Random(seed ^ 0x5A17)
    templates = [
        ('let value: Int = "wrong"\n', "type mismatch"),
        ('say(missing_name)\n', "unknown name"),
        ('say("unterminated)\n', "unterminated string"),
        ('fn f(value: Int) -> Int { return value\n', "missing delimiter"),
        ('fn f(value: Int) -> Int { return value + }\n', "incomplete expression"),
        ('fn f() -> Int { return g() }\n', "unknown function"),
        ('let values = []\nsay(int_text(length(values)))\n', "unconstrained empty list"),
        ('fn f() -> Int { return 9223372036854775808 }\n', "integer overflow"),
        ('fn f(value: Int) -> Int { return value }\nsay(int_text(f("bad")))\n', "wrong argument"),
        ('type Point { x: Int }\nlet p = Point { x: 1, x: 2 }\n', "duplicate field"),
    ]
    for index in range(count):
        source, reason = templates[index % len(templates)]
        if index >= len(templates):
            source = source.replace("1", str(rng.randint(2, 9)), 1)
        yield f"invalid-{seed}-{index:04d}", source.encode("utf-8"), reason


def runtime_sources(seed: int, count: int) -> Iterable[tuple[str, bytes, str]]:
    cases = [
        ('say(int_text(1 / 0))\n', "division by zero"),
        ('say(int_text((-9223372036854775807 - 1) / -1))\n', "minimum integer division"),
        ('say(int_text(9223372036854775807 + 1))\n', "addition overflow"),
        ('fn loop() -> Int { return loop() }\nsay(int_text(loop()))\n', "call depth"),
    ]
    for index in range(count):
        source, reason = cases[index % len(cases)]
        yield f"runtime-{seed}-{index:04d}", source.encode("utf-8"), reason


def run_generated(seed: int, count: int, findings: list[dict[str, Any]], stats: dict[str, int]) -> None:
    for case_id, raw, expected in valid_sources(seed, count):
        stats["validGenerated"] += 1
        check = cli_case(case_id, raw, "check")
        response = check.get("response") or {}
        if response.get("status") != "valid":
            findings.append({"caseId": case_id, "kind": "valid-generator", "classification": "confirmed-bug",
                             "detail": "Generated valid program was not accepted", "response": response})
            continue
        run = cli_case(case_id, raw, "run")
        if run["status"] == "timeout":
            findings.append({"caseId": case_id, "kind": "valid-runtime", "classification": "confirmed-bug",
                             "detail": "Generated valid program exceeded bounded runtime", "timeoutSeconds": 8})
        elif run["returncode"] != 0 or run["stdout"] != expected:
            findings.append({"caseId": case_id, "kind": "valid-runtime", "classification": "confirmed-bug",
                             "detail": "Generated valid program did not produce its independent expected output",
                             "expected": expected, "actual": run["stdout"], "stderr": run["stderr"]})
        findings.append(analysis_pair(case_id, raw))
    for case_id, raw, reason in invalid_sources(seed, count):
        stats["invalidGenerated"] += 1
        check = cli_case(case_id, raw, "check")
        response = check.get("response") or {}
        if response.get("status") in ("valid", "incomplete"):
            findings.append({"caseId": case_id, "kind": "invalid-generator", "classification": "confirmed-bug",
                             "detail": "Intentionally malformed or ill-typed program was accepted",
                             "reason": reason, "response": response})
        else:
            stats["expectedRejection"] += 1
        findings.append(analysis_pair(case_id, raw))
    for case_id, raw, reason in runtime_sources(seed, count):
        stats["runtimeGenerated"] += 1
        check = cli_case(case_id, raw, "check")
        run = cli_case(case_id, raw, "run")
        response = check.get("response") or {}
        if response.get("status") != "valid":
            findings.append({"caseId": case_id, "kind": "runtime-generator", "classification": "missing-test",
                             "detail": "Runtime stress source was rejected before execution", "reason": reason,
                             "response": response})
        elif run["status"] == "timeout":
            findings.append({"caseId": case_id, "kind": "runtime-generator", "classification": "confirmed-bug",
                             "detail": "Runtime stress source exceeded bounded process timeout", "reason": reason})
        elif run["returncode"] == 0:
            findings.append({"caseId": case_id, "kind": "runtime-generator", "classification": "confirmed-bug",
                             "detail": "Runtime failure case exited successfully", "reason": reason,
                             "stdout": run["stdout"]})
        else:
            stats["controlledRuntimeFailures"] += 1


def session_invariants(findings: list[dict[str, Any]], stats: dict[str, int]) -> None:
    source = "fn double(n: Int) -> Int { return ?calculation }\n"
    rev = revision(source.encode())
    filled = source.replace("?calculation", "n * 2")
    filled_rev = revision(filled.encode())
    requests = [
        {"schemaVersion": 3, "op": "open", "source": source},
        {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": rev},
        {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": rev},
        {"schemaVersion": 3, "op": "metrics"},
        {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1", "expected_revision": rev,
         "start_byte": source.index("?calculation"), "end_byte": source.index("?calculation") + len("?calculation"),
         "replacement": "n * 2"},
        {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1", "expected_revision": rev,
         "start_byte": 0, "end_byte": 0, "replacement": " "},
        {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": filled_rev},
        "{not json}",
        {"schemaVersion": 3, "op": "open", "source": "say(\"recovered\")\n"},
    ]
    result = session_case(requests)
    stats["sessionRequests"] += len(requests)
    responses = result["responses"]
    if result["status"] != "completed" or len(responses) != len(requests):
        findings.append({"caseId": "session-invariants", "kind": "session", "classification": "confirmed-bug",
                         "detail": "JSONL session did not return one bounded response per request",
                         "returncode": result["returncode"], "responseCount": len(responses)})
        return
    if normalized_analysis(responses[1]) != normalized_analysis(responses[2]):
        findings.append({"caseId": "session-invariants", "kind": "cache", "classification": "confirmed-bug",
                         "detail": "Repeated same-revision analysis changed its semantic result"})
    if responses[3].get("metrics", {}).get("cache_hits", 0) < 2:
        findings.append({"caseId": "session-invariants", "kind": "cache", "classification": "confirmed-bug",
                         "detail": "Repeated same-revision queries did not report cache hits", "response": responses[3]})
    if responses[5].get("error", {}).get("code") != "PEP_STALE_REVISION":
        findings.append({"caseId": "session-invariants", "kind": "revision", "classification": "confirmed-bug",
                         "detail": "Stale edit was not rejected", "response": responses[5]})
    if responses[7].get("error", {}).get("code") != "PEP_SESSION_MALFORMED_JSON" or responses[8].get("status") != "valid":
        findings.append({"caseId": "session-invariants", "kind": "recovery", "classification": "confirmed-bug",
                         "detail": "Malformed JSON did not preserve session recovery", "responses": responses[7:9]})

    invalid = session_case([
        {"schemaVersion": 3, "op": "open_bytes", "bytes": [255, 0, 1]},
        {"schemaVersion": 3, "op": "open_bytes", "bytes": [256]},
        {"schemaVersion": 3, "op": "open_bytes", "bytes": [0] * 65537},
    ])
    stats["sessionRequests"] += 3
    if invalid["status"] != "completed" or len(invalid["responses"]) != 3:
        findings.append({"caseId": "session-open-bytes", "kind": "session", "classification": "confirmed-bug",
                         "detail": "open_bytes adversarial inputs did not receive bounded responses"})
    else:
        stats["malformedInputs"] += 3
        if invalid["responses"][0].get("status") != "invalid":
            findings.append({"caseId": "session-open-bytes", "kind": "utf8", "classification": "confirmed-bug",
                             "detail": "Malformed UTF-8 was not reported as invalid", "response": invalid["responses"][0]})

    # A large but structurally ordinary source probes the JSONL response cap
    # without depending on A12 code. It must either return the documented
    # bounded-message rejection or complete within the cap; a hung/crashed
    # session is a real harness finding.
    large_source = ('say("x")\n' * 6000)
    large = session_case([{"schemaVersion": 3, "op": "open", "source": large_source}], timeout=20.0)
    stats["largeResponseProbes"] += 1
    large_response = large["responses"][0] if large["responses"] else {}
    if large["status"] != "completed" or len(large["responses"]) != 1:
        findings.append({"caseId": "session-large-response", "kind": "transport", "classification": "confirmed-bug",
                         "detail": "Large valid source did not receive one bounded session response",
                         "returncode": large["returncode"], "status": large["status"]})
    elif large_response.get("error", {}).get("code") == "PEP_TOOL_MESSAGE_TOO_LARGE":
        stats["largeResponseLimitRejections"] += 1
    else:
        findings.append({"caseId": "session-large-response", "kind": "transport", "classification": "missing-test",
                         "detail": "Large valid source completed without the response-limit rejection",
                         "responseBytes": len(large["stdout"].encode("utf-8"))})


def inherited_a11_evidence(timeout: float) -> dict[str, Any]:
    """Run the repository's existing A11 differential suite as labelled evidence."""
    result = run_bounded([sys.executable, "-m", "unittest", "tests.test_a11", "-v"], timeout=timeout)
    output = result["stdout"] + result["stderr"]
    marker = "Ran "
    tests_run = None
    if marker in output:
        try:
            tests_run = int(output.split(marker, 1)[1].split(" tests", 1)[0])
        except (ValueError, IndexError):
            pass
    return {
        "status": "passed" if result["status"] == "completed" and result["returncode"] == 0 else result["status"],
        "returncode": result["returncode"], "tests": tests_run,
        "elapsedMs": result["elapsedMs"], "outputTail": output[-4000:],
    }


def reduce_bytes(raw: bytes, still_fails: Callable[[bytes], bool], budget: int = 80) -> bytes:
    """Deterministic ddmin over bytes; every predicate call is externally bounded."""
    current = raw
    granularity = 2
    attempts = 0
    while len(current) >= 2 and attempts < budget:
        chunk = max(1, (len(current) + granularity - 1) // granularity)
        changed = False
        start = 0
        while start < len(current) and attempts < budget:
            candidate = current[:start] + current[min(len(current), start + chunk):]
            attempts += 1
            if candidate != current and still_fails(candidate):
                current = candidate
                granularity = max(2, granularity - 1)
                changed = True
                break
            start += chunk
        if not changed:
            if granularity >= len(current):
                break
            granularity = min(len(current), granularity * 2)
    return current


def reduce_findings(findings: list[dict[str, Any]], max_cases: int) -> None:
    reduced = 0
    for finding in findings:
        if reduced >= max_cases or finding.get("classification") != "confirmed-bug":
            continue
        case_id = finding.get("caseId")
        if not case_id:
            continue
        path = OUT / "corpus" / f"{case_id}.pep"
        if not path.exists():
            continue
        original = path.read_bytes()
        def fails(candidate: bytes) -> bool:
            result = cli_case(case_id + "-reduce", candidate, "check")
            response = result.get("response") or {}
            return response.get("status") == "valid" if finding.get("kind") == "invalid-generator" else result["status"] == "timeout"
        minimized = reduce_bytes(original, fails)
        reduced_path = OUT / "counterexamples" / f"{case_id}.pep"
        reduced_path.parent.mkdir(parents=True, exist_ok=True)
        reduced_path.write_bytes(minimized)
        finding["reducedPath"] = str(reduced_path.relative_to(ROOT))
        finding["originalBytes"] = len(original)
        finding["reducedBytes"] = len(minimized)
        finding["reducedHex"] = minimized.hex()
        reduced += 1


def report_text(result: dict[str, Any]) -> str:
    stats = result["stats"]
    findings = result["findings"]
    lines = [
        "# Pepin conformance laboratory report",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Repository revision: `{result['revision']}`",
        f"- Branch: `{result['branch']}`",
        f"- Seeds: `{', '.join(map(str, result['seeds']))}`",
        f"- Bounded per-process timeout: `{result['timeoutSeconds']}s`",
        "",
        "## Corpus and execution counts",
        "",
        "| Measure | Count |",
        "|---|---:|",
    ]
    for key, label in [
        ("repositoryExamples", "repository examples"), ("validGenerated", "generated valid programs"),
        ("invalidGenerated", "generated invalid programs"), ("runtimeGenerated", "runtime stress programs"),
        ("expectedRejection", "expected rejections"), ("controlledRuntimeFailures", "controlled runtime failures"),
        ("sessionRequests", "session requests"), ("malformedInputs", "malformed/byte-boundary inputs"),
        ("largeResponseProbes", "large-response probes"),
        ("largeResponseLimitRejections", "large-response limit rejections"),
    ]:
        lines.append(f"| {label} | {stats.get(key, 0)} |")
    lines += ["", "## Findings", ""]
    if not findings:
        lines.append("No confirmed defects were found by this run. Passing cases are recorded as coverage, not proof of full correctness.")
    else:
        for finding in findings:
            lines.append(f"- **{finding.get('classification', 'unknown')}** `{finding.get('caseId', 'unknown')}` — {finding.get('detail', '')}")
            if finding.get("reducedPath"):
                lines.append(f"  - reduced counterexample: `{finding['reducedPath']}` ({finding['reducedBytes']} bytes; hex `{finding['reducedHex']}`)")
    lines += [
        "", "## Independent checks", "",
        "- CLI `check` and JSONL `open` are compared after removing transport-only fields.",
        "- Repeated same-revision session queries must be semantically identical and expose cache hits.",
        "- A stale edit must be rejected while malformed JSON must not terminate the session.",
        "- Generated valid programs are checked and run against independently computed expected output.",
        "- Generated invalid programs must not be accepted as valid or incomplete.",
        "- Existing A11 OCaml-vs-Pep lexer tests are separate evidence and are not counted as fresh lab cases.",
        f"- Inherited A11 differential evidence: `{result['inheritedA11']['status'] if result.get('inheritedA11') else 'not requested'}`"
        + (f" ({result['inheritedA11'].get('tests')} tests)" if result.get('inheritedA11') and result['inheritedA11'].get('tests') else ""),
        "", "## Limitations", "",
        "- The harness does not claim an independent semantic implementation; shared parser/checker assumptions remain possible.",
        "- The text CLI cannot represent malformed UTF-8, so byte-level malformed input is exercised only through `open_bytes`.",
        "- Timeout findings are process-level observations; they are not complexity proofs.",
        "- `missing-test` means the case passed the current oracle checks and is retained as reusable coverage, not that the feature is fully specified.",
    ]
    return "\n".join(lines) + "\n"


def run_lab(args: argparse.Namespace) -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    stats = {
        "repositoryExamples": 0, "validGenerated": 0, "invalidGenerated": 0,
        "runtimeGenerated": 0, "expectedRejection": 0, "controlledRuntimeFailures": 0,
        "sessionRequests": 0, "malformedInputs": 0, "largeResponseProbes": 0,
        "largeResponseLimitRejections": 0,
    }
    findings: list[dict[str, Any]] = []
    example_paths = sorted((ROOT / "examples").glob("*.pep"))
    for path in example_paths:
        raw = path.read_bytes()
        case_id = "example-" + path.stem
        stats["repositoryExamples"] += 1
        findings.append(analysis_pair(case_id, raw))
    for seed in args.seeds:
        run_generated(seed, args.count, findings, stats)
    session_invariants(findings, stats)
    if args.reduce:
        reduce_findings(findings, args.reduce)
    git_revision = run_bounded(["git", "rev-parse", "HEAD"], timeout=3)
    git_branch = run_bounded(["git", "branch", "--show-current"], timeout=3)
    result = {
        "schema": SCHEMA, "revision": git_revision["stdout"].strip(),
        "branch": git_branch["stdout"].strip(), "seeds": args.seeds,
        "countPerSeed": args.count, "timeoutSeconds": args.timeout,
        "stats": stats, "findings": findings,
        "inheritedA11": inherited_a11_evidence(args.a11_timeout) if args.a11 else None,
    }
    (OUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "report.md").write_text(report_text(result), encoding="utf-8")
    return result


def main() -> int:
    global PROCESS_TIMEOUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--count", type=int, default=4, help="cases per generated family and seed")
    parser.add_argument("--timeout", type=float, default=8.0, help="documented process timeout")
    parser.add_argument("--reduce", type=int, default=2, help="confirmed findings to reduce")
    parser.add_argument("--a11", action="store_true", help="run the existing bounded A11 lexer differential suite")
    parser.add_argument("--a11-timeout", type=float, default=180.0, help="timeout for inherited A11 evidence")
    args = parser.parse_args()
    if args.count < 1 or args.count > 100 or args.reduce < 0:
        parser.error("count must be 1..100 and reduce must be nonnegative")
    if args.timeout <= 0 or args.a11_timeout <= 0:
        parser.error("timeouts must be positive")
    PROCESS_TIMEOUT = args.timeout
    result = run_lab(args)
    print(json.dumps({"schema": SCHEMA, "stats": result["stats"],
                      "confirmedFindings": sum(1 for item in result["findings"]
                                                if item.get("classification") == "confirmed-bug"),
                      "report": str(OUT / "report.md")}, indent=2))
    return 1 if any(item.get("classification") == "confirmed-bug" for item in result["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
