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

try:
    from .generator import boundary_vectors, generate_cases
except ImportError:  # Running this file directly from the repository root.
    from generator import boundary_vectors, generate_cases


ROOT = Path(__file__).resolve().parents[1]
PEP = ROOT / "pep.ps1"
OUT = ROOT / "_build" / "conformance"
SCHEMA = "pepin-conformance/v1"
DEFAULT_SEEDS = [20261026, 1101, 1201]
PROCESS_TIMEOUT = 8.0
MAX_TOOL_MESSAGE_BYTES = 1024 * 1024
FAILED_FINDING_CLASSIFICATIONS = {"confirmed-bug", "infrastructure-failure"}

RUNTIME_EXPECTED_CODES = {
    "division by zero": ("PEP_RUNTIME_DIVISION_BY_ZERO",),
    "minimum integer division": ("PEP_RUNTIME_OVERFLOW",),
    "addition overflow": ("PEP_RUNTIME_OVERFLOW",),
    "call depth": ("PEP_RUNTIME_CALL_DEPTH",),
}


def revision(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def json_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def decode_output(value: Any) -> str:
    """Return one stable text type for completed and timeout subprocess paths."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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
            "stdout": decode_output(proc.stdout), "stderr": decode_output(proc.stderr),
            "elapsedMs": round((time.perf_counter() - started) * 1000, 2),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout", "returncode": None,
            "stdout": decode_output(exc.stdout), "stderr": decode_output(exc.stderr),
            "elapsedMs": round((time.perf_counter() - started) * 1000, 2),
        }
    except OSError as exc:
        return {
            "status": "launch-error", "returncode": None, "stdout": "", "stderr": "",
            "error": {"type": type(exc).__name__, "errno": exc.errno, "message": str(exc)},
            "elapsedMs": round((time.perf_counter() - started) * 1000, 2),
        }


def response_from_stdout(stdout: str | bytes) -> dict[str, Any] | None:
    stdout = decode_output(stdout)
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
    if not isinstance(response, dict) or not response:
        return {"status": "no-response"}
    status = response.get("status")
    # File-oriented invalid JSON intentionally omits the partial AST and
    # checked tree; the session retains the parsed AST for inspection. Compare
    # the common diagnostic contract in that state.
    if status == "invalid":
        return {"status": status, "diagnostics": response.get("diagnostics", [])}
    raw_holes = response.get("holes", [])
    if not isinstance(raw_holes, list) or any(not isinstance(hole, dict) for hole in raw_holes):
        return {"status": status, "malformed": "holes"}
    holes = []
    for hole in raw_holes:
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


def check_result_contract(result: dict[str, Any], *, expected_status: str | None = None) -> tuple[bool, str]:
    """Validate the check command transport before interpreting its semantics."""
    if result.get("status") != "completed":
        return False, f"check process did not complete: {result.get('status')}"
    response = result.get("response")
    if not isinstance(response, dict):
        return False, "check completed without a JSON object response"
    status = response.get("status")
    if status not in {"valid", "invalid", "incomplete"}:
        return False, f"check returned unexpected status {status!r}"
    shape_error = response_shape_error(response)
    if shape_error:
        return False, shape_error
    expected_returncode = 0 if status == "valid" else 1
    if result.get("returncode") != expected_returncode:
        return False, f"check status {status!r} had returncode {result.get('returncode')!r}"
    if expected_status is not None and status != expected_status:
        return False, f"expected check status {expected_status!r}, got {status!r}"
    return True, "check response and exit contract are valid"


def response_shape_error(response: Any) -> str | None:
    """Return a diagnostic rather than raising on adversarial JSON shapes."""
    if not isinstance(response, dict):
        return "response is not a JSON object"
    if response.get("_malformedResponse") is not None:
        return "response contains a malformed-output marker"
    status = response.get("status")
    if status in {"invalid", "runtime_error"}:
        diagnostics = response.get("diagnostics")
        if not isinstance(diagnostics, list):
            return f"{status} response diagnostics is not a list"
        if not diagnostics:
            return f"{status} response has an empty diagnostic list"
        if any(not isinstance(item, dict) or not isinstance(item.get("code"), str) for item in diagnostics):
            return f"{status} response contains a malformed diagnostic"
    if "holes" in response and not isinstance(response.get("holes"), list):
        return "response holes field is not a list"
    return None


def transport_failure_classification(result: dict[str, Any]) -> str:
    """Separate launch/shape failures from a completed compiler contradiction."""
    if result.get("status") == "launch-error":
        return "infrastructure-failure"
    if result.get("status") == "completed":
        response = result.get("response")
        if not isinstance(response, dict) or response_shape_error(response):
            return "infrastructure-failure"
    return "confirmed-bug"


def classify_invalid_check(result: dict[str, Any]) -> dict[str, Any]:
    """Classify one invalid-program check without relying on tuple truthiness."""
    response = result.get("response")
    if isinstance(response, dict) and response.get("status") in {"valid", "incomplete"} and result.get("status") == "completed":
        return {"classification": "confirmed-bug", "detail": "Intentionally malformed or ill-typed program was accepted"}
    valid, detail = check_result_contract(result)
    if not valid:
        return {"classification": transport_failure_classification(result),
                "detail": "Invalid-program check did not satisfy its rejection contract",
                "contract": detail}
    return {"classification": "expected-rejection", "detail": "Invalid program was rejected by the check contract"}


def check_failure_signature(result: dict[str, Any]) -> dict[str, Any]:
    response = result.get("response")
    if result.get("status") != "completed":
        return {"kind": "process", "status": result.get("status")}
    if not isinstance(response, dict):
        return {"kind": "no-response", "returncode": result.get("returncode")}
    return {"kind": "rejected", "status": response.get("status"), "returncode": result.get("returncode")}


def diagnostic_codes(response: dict[str, Any] | None) -> list[str]:
    if not isinstance(response, dict):
        return []
    diagnostics = response.get("diagnostics", [])
    if not isinstance(diagnostics, list):
        return []
    return [item.get("code") for item in diagnostics
            if isinstance(item, dict) and isinstance(item.get("code"), str)]


def response_error_code(response: Any) -> str | None:
    if not isinstance(response, dict) or not isinstance(response.get("error"), dict):
        return None
    code = response["error"].get("code")
    return code if isinstance(code, str) else None


def classify_runtime_result(result: dict[str, Any], expected_codes: Iterable[str]) -> dict[str, Any]:
    """Apply the exact runtime-error oracle, including process/launcher failures."""
    expected = list(expected_codes)
    evidence = {
        "status": result.get("status"),
        "returncode": result.get("returncode"),
        "response": result.get("response"),
        "stdout": decode_output(result.get("stdout")),
        "stderr": decode_output(result.get("stderr")),
    }
    if result.get("status") == "timeout":
        return {"classification": "confirmed-bug", "outcome": "timeout", "detail": "runtime process exceeded bounded timeout", "evidence": evidence}
    if result.get("status") == "launch-error":
        return {"classification": "infrastructure-failure", "outcome": "launch-error", "detail": "runtime launcher could not start the requested process", "evidence": evidence}
    if result.get("status") != "completed":
        return {"classification": "confirmed-bug", "outcome": "process-failure", "detail": "runtime process did not complete", "evidence": evidence}
    response = result.get("response")
    actual_codes = diagnostic_codes(response)
    if result.get("returncode") == 1 and isinstance(response, dict) and response.get("status") == "runtime_error" and actual_codes == expected:
        return {"classification": "expected-rejection", "outcome": "controlled-runtime-failure", "codes": actual_codes, "evidence": evidence}
    if result.get("returncode") == 0:
        detail = "runtime failure case exited successfully"
        outcome = "unexpected-success"
    elif not isinstance(response, dict):
        detail = "runtime process failed without a Pep JSON diagnostic"
        outcome = "launcher-or-malformed-output"
    elif response.get("status") != "runtime_error":
        detail = f"runtime process returned unexpected status {response.get('status')!r}"
        outcome = "wrong-response-status"
    else:
        detail = f"runtime diagnostic codes {actual_codes!r} did not match expected {expected!r}"
        outcome = "wrong-diagnostic"
    classification = "infrastructure-failure" if outcome == "launcher-or-malformed-output" else "confirmed-bug"
    return {"classification": classification, "outcome": outcome, "detail": detail,
            "expectedCodes": expected, "actualCodes": actual_codes, "evidence": evidence}


def classify_large_response(result: dict[str, Any]) -> dict[str, Any]:
    """Require the documented cap error or verify a genuinely bounded success."""
    responses = result.get("responses", [])
    response = responses[0] if len(responses) == 1 else None
    if (result.get("status") != "completed" or result.get("returncode") != 0 or
            len(responses) != 1 or not isinstance(response, dict)):
        return {"classification": transport_failure_classification(result),
                "detail": "Large valid source did not receive one bounded session response",
                "response": response}
    if response_error_code(response) == "PEP_TOOL_MESSAGE_TOO_LARGE":
        return {"classification": "expected-rejection", "detail": "documented response cap rejected the oversized message"}
    response_bytes = len(decode_output(result.get("stdout")).encode("utf-8"))
    if (response.get("status") in {"valid", "incomplete"} and
            response_shape_error(response) is None and response_bytes <= MAX_TOOL_MESSAGE_BYTES):
        return {"classification": "missing-test", "detail": "large response completed within the documented message limit",
                "responseBytes": response_bytes}
    return {"classification": "confirmed-bug", "detail": "Large valid source returned an unrelated error or an unverified response",
            "expectedCode": "PEP_TOOL_MESSAGE_TOO_LARGE", "response": response,
            "responseBytes": response_bytes}


def analysis_pair(case_id: str, raw: bytes) -> dict[str, Any]:
    cli = cli_case(case_id, raw, "check")
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {"caseId": case_id, "kind": "cli-session", "classification": "unsupported-feature",
                "detail": "The text CLI cannot carry malformed UTF-8; open_bytes is tested separately."}
    opened = session_case([{"schemaVersion": 3, "op": "open", "source": source}])
    cli_valid, cli_detail = check_result_contract(cli)
    if not cli_valid:
        return {"caseId": case_id, "kind": "cli-session", "classification": transport_failure_classification(cli),
                "detail": cli_detail, "cliEvidence": cli}
    if (opened.get("status") != "completed" or opened.get("returncode") != 0 or
            len(opened.get("responses", [])) != 1 or not isinstance(opened["responses"][0], dict) or
            opened["responses"][0].get("status") not in {"valid", "invalid", "incomplete"} or
            response_shape_error(opened["responses"][0])):
        return {"caseId": case_id, "kind": "cli-session", "classification": transport_failure_classification(opened),
                "detail": "session open did not produce one completed JSON object response",
                "sessionEvidence": opened}
    session_response = opened["responses"][0]
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


def note_classification(stats: dict[str, Any], classification: str) -> None:
    counts = stats.setdefault("classificationCounts", {})
    counts[classification] = counts.get(classification, 0) + 1


def append_finding(findings: list[dict[str, Any]], stats: dict[str, Any], finding: dict[str, Any]) -> None:
    note_classification(stats, str(finding.get("classification", "unknown")))
    case_id = finding.get("caseId")
    if case_id:
        finding.setdefault("reproducer", {
            "caseFile": f"_build/conformance/corpus/{case_id}.pep",
            "checkCommand": f"pwsh -NoProfile -File pep.ps1 check _build/conformance/corpus/{case_id}.pep --json",
            "runCommand": f"pwsh -NoProfile -File pep.ps1 run _build/conformance/corpus/{case_id}.pep --json",
        })
    findings.append(finding)


def failed_finding_count(findings: list[dict[str, Any]]) -> int:
    return sum(1 for finding in findings if finding.get("classification") in FAILED_FINDING_CLASSIFICATIONS)


def run_generated(seed: int, count: int, findings: list[dict[str, Any]], stats: dict[str, Any]) -> None:
    for case_id, raw, expected in valid_sources(seed, count):
        stats["validGenerated"] += 1
        check = cli_case(case_id, raw, "check")
        response = check.get("response") or {}
        valid_check, check_detail = check_result_contract(check, expected_status="valid")
        if not valid_check:
            append_finding(findings, stats, {"caseId": case_id, "kind": "valid-generator", "classification": transport_failure_classification(check),
                             "detail": "Generated valid program was not accepted or check transport failed",
                             "contract": check_detail, "response": response, "evidence": check,
                             "oracle": {"kind": "check-failure", "signature": check_failure_signature(check)}})
            continue
        run = cli_case(case_id, raw, "run")
        if run["status"] == "timeout":
            append_finding(findings, stats, {"caseId": case_id, "kind": "valid-runtime", "classification": "confirmed-bug",
                             "detail": "Generated valid program exceeded bounded runtime", "timeoutSeconds": PROCESS_TIMEOUT,
                             "oracle": {"kind": "valid-output", "mode": "timeout", "expected": expected}})
        elif run["returncode"] != 0 or run["stdout"] != expected:
            append_finding(findings, stats, {"caseId": case_id, "kind": "valid-runtime", "classification": "infrastructure-failure" if run.get("status") == "launch-error" else "confirmed-bug",
                             "detail": "Generated valid program did not produce its independent expected output",
                             "expected": expected, "actual": run["stdout"], "stderr": run["stderr"],
                             "oracle": {"kind": "valid-output", "mode": "output-mismatch", "expected": expected}})
        pair = analysis_pair(case_id, raw)
        if pair["classification"] != "missing-test":
            append_finding(findings, stats, pair)
        else:
            note_classification(stats, "missing-test")
    for case_id, raw, reason in invalid_sources(seed, count):
        stats["invalidGenerated"] += 1
        check = cli_case(case_id, raw, "check")
        response = check.get("response") if isinstance(check.get("response"), dict) else {}
        invalid_outcome = classify_invalid_check(check)
        if invalid_outcome["classification"] == "expected-rejection":
            stats["expectedRejection"] += 1
            note_classification(stats, "expected-rejection")
        else:
            append_finding(findings, stats, {"caseId": case_id, "kind": "invalid-generator",
                             "classification": invalid_outcome["classification"],
                             "detail": invalid_outcome["detail"], "reason": reason,
                             "response": response, **{key: value for key, value in invalid_outcome.items() if key not in {"classification", "detail"}}})
        pair = analysis_pair(case_id, raw)
        if pair["classification"] != "missing-test":
            append_finding(findings, stats, pair)
        else:
            note_classification(stats, "missing-test")
    for case_id, raw, reason in runtime_sources(seed, count):
        stats["runtimeGenerated"] += 1
        check = cli_case(case_id, raw, "check")
        response = check.get("response") if isinstance(check.get("response"), dict) else {}
        check_ok, check_detail = check_result_contract(check, expected_status="valid")
        if not check_ok:
            if check.get("status") == "completed" and response.get("status") in {"invalid", "incomplete"}:
                append_finding(findings, stats, {"caseId": case_id, "kind": "runtime-generator", "classification": "confirmed-bug",
                                 "detail": "Intentionally valid runtime program was rejected before execution",
                                 "reason": reason, "expectedStatus": "valid", "response": response,
                                 "evidence": check})
            else:
                append_finding(findings, stats, {"caseId": case_id, "kind": "runtime-generator", "classification": transport_failure_classification(check),
                                 "detail": "Runtime check transport failed", "reason": reason,
                                 "contract": check_detail, "evidence": check})
            continue
        run = cli_case(case_id, raw, "run")
        oracle = classify_runtime_result(run, RUNTIME_EXPECTED_CODES[reason])
        if oracle["classification"] == "expected-rejection":
            stats["controlledRuntimeFailures"] += 1
            note_classification(stats, "expected-rejection")
        else:
            append_finding(findings, stats, {"caseId": case_id, "kind": "runtime-generator",
                             "classification": oracle["classification"], "detail": oracle["detail"],
                             "reason": reason, "oracle": oracle,
                             "expectedCodes": list(RUNTIME_EXPECTED_CODES[reason])})


def run_grammar_generated(seed: int, count: int, depth: int,
                          findings: list[dict[str, Any]], stats: dict[str, Any]) -> None:
    """Run the independent grammar-aware corpus with strict case oracles."""
    cases = generate_cases(seed, count, depth)
    for case in cases:
        stats["grammarGenerated"] += 1
        stats["grammarValid" if case.validity == "valid" else "grammarInvalid"] += 1
        check = cli_case(case.case_id, case.source, "check")
        response = check.get("response") if isinstance(check.get("response"), dict) else {}
        status = response.get("status")
        expected_returncode = 1 if case.validity == "invalid" else 0
        contract_ok = (check.get("status") == "completed" and
                       check.get("returncode") == expected_returncode)
        shape_ok = isinstance(response, dict) and response_shape_error(response) is None
        expected_status = status in case.expected_statuses
        if case.validity == "invalid":
            expected = contract_ok and shape_ok and expected_status
        else:
            expected = contract_ok and shape_ok and status == "valid"
        if not expected:
            completed_semantic_rejection = (
                check.get("status") == "completed"
                and status in {"invalid", "incomplete"}
                and shape_ok
            )
            classification = "confirmed-bug" if case.validity == "valid" and completed_semantic_rejection else transport_failure_classification(check)
            append_finding(findings, stats, {
                "caseId": case.case_id,
                "kind": "grammar-generator",
                "classification": classification,
                "detail": "Generated case did not satisfy its grammar/check oracle",
                "case": case.as_record(),
                "contract": {"expectedStatuses": list(case.expected_statuses),
                             "actualStatus": status, "returncode": check.get("returncode")},
                "response": response,
                "evidence": check,
            })
            continue
        if case.validity == "invalid":
            stats["grammarExpectedRejection"] += 1
            note_classification(stats, "expected-rejection")
            continue
        stats["grammarExpectedOutput"] += 1
        run = cli_case(case.case_id, case.source, "run")
        if run.get("status") == "launch-error":
            classification = "infrastructure-failure"
        elif run.get("status") == "timeout":
            classification = "confirmed-bug"
        elif run.get("status") != "completed" or run.get("returncode") != 0 or run.get("stdout") != case.expected_output:
            classification = "confirmed-bug"
        else:
            note_classification(stats, "missing-test")
            continue
        append_finding(findings, stats, {
            "caseId": case.case_id,
            "kind": "grammar-runtime",
            "classification": classification,
            "detail": "Generated valid program did not produce its independent expected output",
            "case": case.as_record(),
            "expected": case.expected_output,
            "actual": run.get("stdout"),
            "evidence": run,
        })


def session_invariants(findings: list[dict[str, Any]], stats: dict[str, Any]) -> None:
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
    if (result["status"] != "completed" or result.get("returncode") != 0 or
            len(responses) != len(requests) or any(not isinstance(item, dict) for item in responses)):
        append_finding(findings, stats, {"caseId": "session-invariants", "kind": "session", "classification": transport_failure_classification(result),
                         "detail": "JSONL session did not return one bounded response per request",
                         "returncode": result["returncode"], "responseCount": len(responses)})
        return
    if normalized_analysis(responses[1]) != normalized_analysis(responses[2]):
        append_finding(findings, stats, {"caseId": "session-invariants", "kind": "cache", "classification": "confirmed-bug",
                         "detail": "Repeated same-revision analysis changed its semantic result"})
    metrics = responses[3].get("metrics")
    cache_hits = metrics.get("cache_hits") if isinstance(metrics, dict) else None
    if not isinstance(cache_hits, int) or cache_hits < 2:
        append_finding(findings, stats, {"caseId": "session-invariants", "kind": "cache", "classification": "confirmed-bug",
                         "detail": "Repeated same-revision queries did not report cache hits", "response": responses[3]})
    if response_error_code(responses[5]) != "PEP_STALE_REVISION":
        append_finding(findings, stats, {"caseId": "session-invariants", "kind": "revision", "classification": "confirmed-bug",
                         "detail": "Stale edit was not rejected", "response": responses[5]})
    if response_error_code(responses[7]) != "PEP_SESSION_MALFORMED_JSON" or responses[8].get("status") != "valid":
        append_finding(findings, stats, {"caseId": "session-invariants", "kind": "recovery", "classification": "confirmed-bug",
                         "detail": "Malformed JSON did not preserve session recovery", "responses": responses[7:9]})

    invalid = session_case([
        {"schemaVersion": 3, "op": "open_bytes", "bytes": [255, 0, 1]},
        {"schemaVersion": 3, "op": "open_bytes", "bytes": [256]},
        {"schemaVersion": 3, "op": "open_bytes", "bytes": [0] * 65537},
    ])
    stats["sessionRequests"] += 3
    if invalid["status"] != "completed" or len(invalid["responses"]) != 3:
        append_finding(findings, stats, {"caseId": "session-open-bytes", "kind": "session", "classification": transport_failure_classification(invalid),
                         "detail": "open_bytes adversarial inputs did not receive bounded responses"})
    else:
        stats["malformedInputs"] += 3
        expected_codes = ["PEP_INVALID_UTF8", "PEP_SOURCE_BYTE_VALUE", "PEP_SOURCE_BYTE_LIMIT"]
        for index, expected_code in enumerate(expected_codes):
            response = invalid["responses"][index]
            if not isinstance(response, dict):
                actual_code = None
            elif response.get("status") == "invalid":
                diagnostics = response.get("diagnostics")
                first = diagnostics[0] if isinstance(diagnostics, list) and diagnostics else {}
                actual_code = first.get("code") if isinstance(first, dict) else None
            else:
                error = response.get("error")
                actual_code = error.get("code") if isinstance(error, dict) else None
            if actual_code != expected_code:
                append_finding(findings, stats, {"caseId": "session-open-bytes", "kind": "utf8" if index == 0 else "source-boundary",
                                 "classification": "confirmed-bug",
                                 "detail": f"open_bytes case {index} returned the wrong error contract",
                                 "expectedCode": expected_code, "actualCode": actual_code, "response": response})

    # A large but structurally ordinary source probes the JSONL response cap
    # without depending on A12 code. It must either return the documented
    # bounded-message rejection or complete within the cap; a hung/crashed
    # session is a real harness finding.
    large_source = ('say("x")\n' * 6000)
    write_case("session-large-response", large_source.encode("utf-8"))
    large = session_case([{"schemaVersion": 3, "op": "open", "source": large_source}], timeout=20.0)
    stats["largeResponseProbes"] += 1
    large_outcome = classify_large_response(large)
    if large_outcome["classification"] == "expected-rejection":
        stats["largeResponseLimitRejections"] += 1
        note_classification(stats, "expected-rejection")
    elif large_outcome["classification"] == "missing-test":
        stats["largeResponseSuccessfulWithinLimit"] += 1
        note_classification(stats, "missing-test")
    else:
        append_finding(findings, stats, {"caseId": "session-large-response", "kind": "transport",
                         "classification": large_outcome["classification"], **large_outcome})


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


def reduce_bytes(raw: bytes, still_fails: Callable[[bytes], bool], budget: int = 80) -> tuple[bytes, int]:
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
    return current, attempts


def replay_finding(finding: dict[str, Any], raw: bytes, case_id: str) -> bool | None:
    """Replay one finding's own failure oracle; None means unsupported reduction."""
    kind = finding.get("kind")
    if kind == "invalid-generator":
        result = cli_case(case_id + "-reduce", raw, "check")
        response = result.get("response") if isinstance(result.get("response"), dict) else {}
        return result.get("status") == "completed" and response.get("status") in {"valid", "incomplete"}
    if kind == "valid-generator":
        result = cli_case(case_id + "-reduce", raw, "check")
        oracle = finding.get("oracle", {})
        if oracle.get("kind") != "check-failure":
            return None
        return check_failure_signature(result) == oracle.get("signature")
    if kind == "valid-runtime":
        check = cli_case(case_id + "-reduce", raw, "check")
        if not check_result_contract(check, expected_status="valid")[0]:
            return False
        run = cli_case(case_id + "-reduce", raw, "run")
        oracle = finding.get("oracle", {})
        if oracle.get("kind") != "valid-output":
            return None
        if oracle.get("expected") is None:
            return None
        if oracle.get("mode") == "timeout":
            return run.get("status") == "timeout"
        return run.get("status") == "completed" and (run.get("returncode") != 0 or run.get("stdout") != oracle["expected"])
    if kind == "runtime-generator":
        check = cli_case(case_id + "-reduce", raw, "check")
        if not check_result_contract(check, expected_status="valid")[0]:
            return False
        reason = finding.get("reason")
        expected = RUNTIME_EXPECTED_CODES.get(reason)
        oracle = finding.get("oracle")
        if not expected or not isinstance(oracle, dict):
            return None
        replay = classify_runtime_result(cli_case(case_id + "-reduce", raw, "run"), expected)
        if replay.get("classification") != "confirmed-bug" or replay.get("outcome") != oracle.get("outcome"):
            return False
        if oracle.get("outcome") == "wrong-diagnostic":
            return replay.get("actualCodes") == oracle.get("actualCodes")
        return True
    if kind == "cli-session":
        return analysis_pair(case_id + "-reduce", raw).get("classification") == "confirmed-bug"
    return None


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
            finding["reduction"] = {"status": "unsupported", "reason": "original corpus input is unavailable"}
            continue
        original = path.read_bytes()
        original_reproduces = replay_finding(finding, original, case_id)
        if original_reproduces is None:
            finding["reduction"] = {"status": "unsupported", "reason": f"finding kind {finding.get('kind')!r} has no reliable oracle"}
            continue
        if original_reproduces is not True:
            finding["reduction"] = {"status": "unsupported", "reason": "original failure oracle did not reproduce"}
            continue
        minimized, attempts = reduce_bytes(original, lambda candidate: replay_finding(finding, candidate, case_id) is True)
        if replay_finding(finding, minimized, case_id) is not True:
            finding["reduction"] = {"status": "unsupported", "reason": "minimized bytes failed the original failure oracle",
                                     "attempts": attempts}
            continue
        reduced_path = OUT / "counterexamples" / f"{case_id}.pep"
        reduced_path.parent.mkdir(parents=True, exist_ok=True)
        reduced_path.write_bytes(minimized)
        finding["reducedPath"] = str(reduced_path.relative_to(ROOT))
        finding["originalBytes"] = len(original)
        finding["reducedBytes"] = len(minimized)
        finding["reducedHex"] = minimized.hex()
        finding["reduction"] = {"status": "reduced", "attempts": attempts,
                                 "budget": 80, "oracle": finding.get("kind")}
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
        ("grammarGenerated", "grammar-aware generated cases"), ("grammarValid", "grammar-aware valid cases"),
        ("grammarInvalid", "grammar-aware invalid cases"), ("grammarExpectedOutput", "grammar output checks"),
        ("grammarExpectedRejection", "grammar expected rejections"),
        ("grammarBoundaryVectors", "independent integer boundary vectors"),
        ("expectedRejection", "expected rejections"), ("controlledRuntimeFailures", "controlled runtime failures"),
        ("sessionRequests", "session requests"), ("malformedInputs", "malformed/byte-boundary inputs"),
        ("largeResponseProbes", "large-response probes"),
        ("largeResponseLimitRejections", "large-response limit rejections"),
        ("largeResponseSuccessfulWithinLimit", "large-response successful-within-limit responses"),
    ]:
        lines.append(f"| {label} | {stats.get(key, 0)} |")
    lines += ["", "## Findings", ""]
    if not findings:
        lines.append("No confirmed defects were found by this run. Passing cases are recorded as coverage, not proof of full correctness.")
    else:
        for finding in findings:
            lines.append(f"- **{finding.get('classification', 'unknown')}** `{finding.get('caseId', 'unknown')}` — {finding.get('detail', '')}")
            if finding.get("reproducer"):
                lines.append(f"  - source: `{finding['reproducer']['caseFile']}`")
                lines.append(f"  - check: `{finding['reproducer']['checkCommand']}`")
            if finding.get("reducedPath"):
                lines.append(f"  - reduced counterexample: `{finding['reducedPath']}` ({finding['reducedBytes']} bytes; hex `{finding['reducedHex']}`)")
            elif finding.get("reduction", {}).get("status") == "unsupported":
                lines.append(f"  - reduction unsupported: {finding['reduction'].get('reason', 'unspecified')}")
    lines += ["", "## Classification counts", "", "| Classification | Count |", "|---|---:|"]
    for classification, count in sorted(stats.get("classificationCounts", {}).items()):
        lines.append(f"| {classification} | {count} |")
    lines += [
        "", "## Independent checks", "",
        "- CLI `check` and JSONL `open` are compared after removing transport-only fields.",
        "- Repeated same-revision session queries must be semantically identical and expose cache hits.",
        "- A stale edit must be rejected while malformed JSON must not terminate the session.",
        "- Generated valid programs are checked and run against independently computed expected output.",
        "- Generated invalid programs must not be accepted as valid or incomplete.",
        "- Grammar-aware cases are generated from bounded constructors; valid cases require both check acceptance and exact independent output.",
        "- Grammar invalid cases accept only the documented invalid/incomplete check statuses with a valid diagnostic contract.",
        "- Integer boundary vectors use an independent signed-64-bit model; they are evidence about the model and do not replace compiler execution.",
        "- Runtime stress cases require return code 1, status `runtime_error`, and the exact expected diagnostic code; launcher errors, malformed output and timeouts are findings.",
        "- Launch failures and missing/malformed process output are classified as `infrastructure-failure` and fail the run without being misreported as Pep compiler defects.",
        "- Reduction reruns the finding-specific oracle and retains the original input when the oracle is unsupported or does not survive.",
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
        "grammarGenerated": 0, "grammarValid": 0, "grammarInvalid": 0,
        "grammarExpectedOutput": 0, "grammarExpectedRejection": 0,
        "grammarBoundaryVectors": len(boundary_vectors()),
        "sessionRequests": 0, "malformedInputs": 0, "largeResponseProbes": 0,
        "largeResponseLimitRejections": 0, "largeResponseSuccessfulWithinLimit": 0,
        "classificationCounts": {},
    }
    findings: list[dict[str, Any]] = []
    example_paths = sorted((ROOT / "examples").glob("*.pep"))
    for path in example_paths:
        raw = path.read_bytes()
        case_id = "example-" + path.stem
        stats["repositoryExamples"] += 1
        finding = analysis_pair(case_id, raw)
        if finding["classification"] != "missing-test":
            append_finding(findings, stats, finding)
        else:
            note_classification(stats, "missing-test")
    for seed in args.seeds:
        run_generated(seed, args.count, findings, stats)
        if args.grammar_count:
            run_grammar_generated(seed, args.grammar_count, args.grammar_depth, findings, stats)
    session_invariants(findings, stats)
    if args.reduce:
        reduce_findings(findings, args.reduce)
    git_revision = run_bounded(["git", "rev-parse", "HEAD"], timeout=3)
    git_branch = run_bounded(["git", "branch", "--show-current"], timeout=3)
    lab_command = [sys.executable, "conformance/harness.py", "--seeds", *map(str, args.seeds),
                   "--count", str(args.count), "--grammar-count", str(args.grammar_count),
                   "--grammar-depth", str(args.grammar_depth), "--timeout", str(args.timeout),
                   "--reduce", str(args.reduce)]
    if args.a11:
        lab_command.append("--a11")
    result = {
        "schema": SCHEMA, "revision": git_revision["stdout"].strip(),
        "branch": git_branch["stdout"].strip(), "seeds": args.seeds,
        "countPerSeed": args.count, "timeoutSeconds": args.timeout,
        "command": lab_command,
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
    parser.add_argument("--grammar-count", type=int, default=0,
                        help="bounded grammar-aware valid/invalid pairs per seed (0 disables)")
    parser.add_argument("--grammar-depth", type=int, default=2,
                        help="maximum recursive expression depth for grammar cases")
    parser.add_argument("--timeout", type=float, default=8.0, help="documented process timeout")
    parser.add_argument("--reduce", type=int, default=2, help="confirmed findings to reduce")
    parser.add_argument("--a11", action="store_true", help="run the existing bounded A11 lexer differential suite")
    parser.add_argument("--a11-timeout", type=float, default=180.0, help="timeout for inherited A11 evidence")
    args = parser.parse_args()
    if args.count < 1 or args.count > 100 or args.grammar_count < 0 or args.grammar_count > 100 or args.reduce < 0:
        parser.error("count must be 1..100, grammar-count must be 0..100 and reduce must be nonnegative")
    if args.grammar_depth < 0 or args.grammar_depth > 5:
        parser.error("grammar-depth must be 0..5")
    if args.timeout <= 0 or args.a11_timeout <= 0:
        parser.error("timeouts must be positive")
    PROCESS_TIMEOUT = args.timeout
    result = run_lab(args)
    failed_findings = failed_finding_count(result["findings"])
    print(json.dumps({"schema": SCHEMA, "stats": result["stats"],
                      "confirmedFindings": sum(1 for item in result["findings"]
                                                if item.get("classification") == "confirmed-bug"),
                      "failedFindings": failed_findings,
                      "report": str(OUT / "report.md")}, indent=2))
    return 1 if failed_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
