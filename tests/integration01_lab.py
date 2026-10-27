"""Integration-readiness harness for the accepted A12 boundary.

The harness deliberately stops at verified syntax.  A13 and C23 are represented
by manifest facts and contract tests, never by guessed semantic or native data.
"""

from __future__ import annotations

import argparse
import ast
import functools
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if __package__ in {None, ""}:
    sys.path.insert(0, str(ROOT))

from tests import performance03_lab as performance


MANIFEST = ROOT / "docs" / "integration" / "PEP-INTEGRATION-01-MANIFEST.json"
MATRIX = ROOT / "docs" / "integration" / "PEP-INTEGRATION-01-MATRIX.json"
CONTRACT = ROOT / "docs" / "integration" / "PEP-INTEGRATION-01-CONTRACT.json"


class IntegrationError(AssertionError):
    pass


EXPECTED_FIXTURES = {
    "minimal-smoke": {"status": "complete", "targetStatus": "valid"},
    "record-nontrivial": {"status": "complete", "targetStatus": "valid"},
    "utf8-crlf": {"status": "complete", "targetStatus": "valid"},
    "invalid-syntax": {"status": "invalid", "targetStatus": "invalid",
                        "diagnostic": {"code": "PEP_UNEXPECTED_CHARACTER", "start": 26,
                                       "end": 27, "line": 1, "column": 27}},
    "incomplete": {"status": "incomplete", "targetStatus": "invalid",
                    "diagnostic": {"code": "PEP_PARSE_EXPECTED", "start": 32,
                                   "end": 32, "line": 1, "column": 33}},
}


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def load_matrix() -> dict[str, Any]:
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    required_sections = {"syntaxInputFromA12", "a13FactsRequiredBeforeCheckerConsumer",
                         "a14FactsRequiredBeforeNativeEmitter", "mustRejectOrDefer", "limits"}
    if not required_sections.issubset(contract):
        raise IntegrationError("integration contract is missing an authority boundary")
    if "stableSemanticId" not in contract["a13FactsRequiredBeforeCheckerConsumer"]:
        raise IntegrationError("A13 contract does not require checker-owned semantic identity")
    if "syntaxIdUsedAsSemanticId" not in contract["mustRejectOrDefer"]:
        raise IntegrationError("integration contract allows syntax IDs to escape as semantics")
    if contract["limits"] != {"sourceBytes": 65536, "toolStepBudget": 100000,
                               "messageBytes": 1048576,
                               "policy": "no integration stage raises or bypasses existing limits"}:
        raise IntegrationError("integration contract limits drifted")
    return contract


def validate_matrix(matrix: dict[str, Any] | None = None) -> dict[str, Any]:
    matrix = matrix or load_matrix()
    cases = matrix.get("cases", [])
    ids = [case.get("id") for case in cases]
    if not cases or any(not case.get("expected") for case in cases) or len(ids) != len(set(ids)):
        raise IntegrationError("integration matrix has missing expectations or duplicate IDs")
    required = {"valid-minimal", "invalid-syntax", "incomplete-source", "wrong-source-revision",
                "forged-continuation", "missing-chunk", "wrong-parent-role", "wrong-type-identity", "unresolved-binding",
                "unsupported-native-feature", "runtime-overflow", "resource-exhaustion", "utf8-crlf",
                "failure-recovery"}
    if not required.issubset(set(ids)):
        raise IntegrationError("integration matrix is missing a required boundary")
    return matrix


def validate_manifest(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = manifest or load_manifest()
    if manifest["baseline"] != "4e497bf192b33e76cb0fdf59bfc30e9b3ef3127f":
        raise IntegrationError("manifest baseline drifted")
    if manifest["limits"] != {
        "sourceBytes": 65536, "toolStepBudget": 100000, "messageBytes": 1048576,
        "policy": "preserve existing limits; no integration harness may raise or bypass them",
    }:
        raise IntegrationError("manifest resource limits drifted")
    names = {entry["name"] for entry in manifest["inputs"]}
    if names != {"A11 lexer", "A12 parser", "Conformance R1", "Performance 03 adapter", "C23 Artifact-05", "A13 checker"}:
        raise IntegrationError("manifest dependency set is incomplete")
    a13 = next(entry for entry in manifest["inputs"] if entry["name"] == "A13 checker")
    if a13["status"] != "missing-accepted-input" or a13["sha"] is not None:
        raise IntegrationError("unaccepted A13 was promoted")
    for entry in manifest["inputs"]:
        if entry["status"] != "missing-accepted-input" and len(entry["sha"]) != 40:
            raise IntegrationError(f"invalid pinned SHA for {entry['name']}")
    return manifest


def verify_a12_checkout() -> dict[str, Any]:
    """Prove the disposable checkout identity instead of trusting a constant."""
    if not (performance.A12_ROOT / ".git").exists() and not (performance.A12_ROOT / "HEAD").exists():
        raise IntegrationError(f"A12 disposable checkout is missing: {performance.A12_ROOT}")
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=performance.A12_ROOT,
                              capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain"], cwd=performance.A12_ROOT,
                                capture_output=True, text=True, timeout=10, check=True).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise IntegrationError(f"could not verify A12 checkout: {exc}") from exc
    if head != performance.A12_SHA:
        raise IntegrationError(f"A12 checkout HEAD {head} != accepted {performance.A12_SHA}")
    if status.strip():
        raise IntegrationError(f"A12 disposable checkout is not clean: {status!r}")
    return {"path": str(performance.A12_ROOT), "head": head, "clean": True}


@functools.lru_cache(maxsize=1)
def _accepted_a12_oracle() -> dict[str, Any]:
    """Load only the accepted A12 test oracle functions from the pinned checkout."""
    source_path = performance.A12_ROOT / "tests" / "test_a12.py"
    if not source_path.exists():
        raise IntegrationError(f"accepted A12 oracle is missing: {source_path}")
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    wanted = {"fields", "scalar", "span", "pep_topology_nodes", "ocaml_tree_nodes",
              "valid_tree_topology", "topology_matches"}
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in body} != wanted:
        raise IntegrationError("accepted A12 oracle functions are incomplete")
    namespace: dict[str, Any] = {}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(source_path), "exec"), namespace)
    return namespace


def _wire_oracle_nodes(nodes: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    def span_value(node: dict[str, Any]) -> tuple[int, int, int, int] | None:
        span = node.get("span")
        if span is None:
            return None
        return (span["start"], span["end"], span["line"], span["column"])

    return [(node["id"], node["parentId"], node["childIndex"], node["role"],
             node["kind"], node["value"], span_value(node)) for node in nodes]


def _diagnostic_fields(diagnostic: dict[str, Any]) -> dict[str, Any]:
    span = diagnostic.get("span") or {}
    start = span.get("start") or {}
    return {"code": diagnostic.get("code"), "start": start.get("offset"),
            "end": span.get("endOffset"), "line": start.get("line"),
            "column": start.get("column")}


def _span_check(nodes: list[dict[str, Any]], source_bytes: int) -> None:
    for node in nodes:
        span = node.get("span")
        if span is None:
            continue
        if not (0 <= span["start"] <= span["end"] <= source_bytes):
            raise IntegrationError(f"span out of source bounds: {node}")


def verify_measurement(name: str, source: str | bytes, measurement: performance.ParserMeasurement,
                       *, expected_status: str | None = None,
                       expected_diagnostic: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = source if isinstance(source, bytes) else source.encode("utf-8")
    expected_revision = performance.revision(raw)
    if measurement.source_revision != expected_revision:
        raise IntegrationError(f"{name}: source revision mismatch")
    if expected_status is not None and measurement.status != expected_status:
        raise IntegrationError(f"{name}: expected parser status {expected_status}, got {measurement.status}")
    expected_target_status = "valid" if expected_status == "complete" else "invalid"
    if expected_status is not None and measurement.target_status != expected_target_status:
        raise IntegrationError(f"{name}: expected source status {expected_target_status}, got {measurement.target_status}")
    if measurement.status == "complete":
        performance.topology_check(measurement.nodes)
        _span_check(measurement.nodes, len(raw))
        if measurement.node_count != measurement.ast_node_count:
            raise IntegrationError(f"{name}: independent OCaml count mismatch")
        oracle = _accepted_a12_oracle()
        actual = _wire_oracle_nodes(measurement.nodes)
        expected = oracle["ocaml_tree_nodes"](measurement.target_ast)
        if not oracle["topology_matches"](actual, expected):
            for index, pair in enumerate(zip(actual, expected)):
                if pair[0] != pair[1]:
                    raise IntegrationError(f"{name}: independent AST mismatch at node {index}: {pair[0]!r} != {pair[1]!r}")
            raise IntegrationError(f"{name}: independent AST length mismatch {len(actual)} != {len(expected)}")
        if measurement.target_diagnostics:
            raise IntegrationError(f"{name}: complete source has diagnostics")
    elif expected_diagnostic is not None:
        actual_diagnostics = [_diagnostic_fields(item) for item in measurement.target_diagnostics]
        if not actual_diagnostics or actual_diagnostics[0] != expected_diagnostic:
            raise IntegrationError(f"{name}: diagnostic mismatch {actual_diagnostics!r} != {[expected_diagnostic]!r}")
        parser_diagnostic = {"code": measurement.parser_error_code, "start": measurement.parser_error_start,
                             "end": measurement.parser_error_end, "line": measurement.parser_error_line,
                             "column": measurement.parser_error_column}
        if parser_diagnostic != expected_diagnostic:
            raise IntegrationError(f"{name}: parser diagnostic mismatch {parser_diagnostic!r} != {expected_diagnostic!r}")
    return {
        "name": name, "status": measurement.status, "sourceBytes": len(raw),
        "sourceRevision": measurement.source_revision, "nodes": measurement.node_count,
        "calls": measurement.calls, "requestBytes": measurement.request_bytes,
        "responseBytes": measurement.response_bytes, "maxRequestBytes": measurement.max_request_bytes,
        "maxResponseBytes": measurement.max_response_bytes,
        "diagnostic": ([_diagnostic_fields(item) for item in measurement.target_diagnostics]
                        if measurement.target_diagnostics else None),
    }


def run_a12_boundary(parse_fn: Any = None) -> dict[str, Any]:
    """Run minimal, nontrivial, incomplete and stable-identity A12 checks."""
    smoke_source = "1 + 2 * 3 - 4"
    nontrivial_source = (
        "type Point { x: Int, y: Int }\n"
        "fn main() -> Int { let point = Point { x: 1, y: 2 }; return point.x }"
    )
    incomplete_source = "fn main() -> Int { return (1 + 2"
    invalid_source = "fn main() -> Int { return @ }"
    unicode_crlf_source = b'fn text() -> Str {\r\n  return "caf\xc3\xa9"\r\n}'
    parse = parse_fn or performance.parse_source
    smoke_first = parse(smoke_source)
    smoke_second = parse(smoke_source)
    if smoke_first.nodes != smoke_second.nodes:
        raise IntegrationError("smoke AST is not complete and stable")
    expected_smoke_kinds = ["expression_statement", "binary", "binary", "integer", "binary", "integer", "integer", "integer"]
    if [node["kind"] for node in smoke_first.nodes] != expected_smoke_kinds:
        raise IntegrationError("smoke AST kind sequence differs from independent expected syntax")
    rows = [verify_measurement("minimal-smoke", smoke_source, smoke_first,
                               expected_status=EXPECTED_FIXTURES["minimal-smoke"]["status"])]
    rows.append(verify_measurement("record-nontrivial", nontrivial_source, parse(nontrivial_source),
                                   expected_status=EXPECTED_FIXTURES["record-nontrivial"]["status"]))
    invalid = parse(invalid_source)
    rows.append(verify_measurement("invalid-syntax", invalid_source, invalid,
                                   expected_status=EXPECTED_FIXTURES["invalid-syntax"]["status"],
                                   expected_diagnostic=EXPECTED_FIXTURES["invalid-syntax"]["diagnostic"]))
    incomplete = parse(incomplete_source)
    rows.append(verify_measurement("incomplete", incomplete_source, incomplete,
                                   expected_status=EXPECTED_FIXTURES["incomplete"]["status"],
                                   expected_diagnostic=EXPECTED_FIXTURES["incomplete"]["diagnostic"]))
    rows.append(verify_measurement("utf8-crlf", unicode_crlf_source, parse(unicode_crlf_source),
                                   expected_status=EXPECTED_FIXTURES["utf8-crlf"]["status"]))
    return {"boundary": "A12-verified-syntax", "a12Sha": performance.A12_SHA,
            "independentOracle": "accepted OCaml AST plus local count/topology/span checks",
            "rows": rows}


def run_source_limit() -> dict[str, Any]:
    session = performance.JsonlSession(performance.A12_ROOT)
    try:
        response, timing = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "integration-limit",
                                         "bytes": [0] * (performance.MAX_SOURCE_BYTES + 1)})
        code = response.get("error", {}).get("code")
        if response.get("outcome") != "error" or code != "PEP_SOURCE_BYTE_LIMIT":
            raise IntegrationError(f"source-limit boundary changed: {response}")
        return {"status": "expected-rejection", "code": code,
                "requestBytes": timing["requestBytes"], "responseBytes": timing["responseBytes"]}
    finally:
        session.close()


def run_real() -> dict[str, Any]:
    manifest = validate_manifest()
    matrix = validate_matrix()
    contract = validate_contract()
    checkout = verify_a12_checkout()
    result = run_a12_boundary()
    result["manifest"] = {"mission": manifest["mission"], "inputs": len(manifest["inputs"]),
                           "sourceBytes": manifest["limits"]["sourceBytes"]}
    result["matrix"] = {"cases": len(matrix["cases"]), "oracleRule": matrix["oracleRule"]}
    result["contract"] = {"a12Inputs": len(contract["syntaxInputFromA12"]),
                           "a13RequiredFacts": len(contract["a13FactsRequiredBeforeCheckerConsumer"]),
                           "a14RequiredFacts": len(contract["a14FactsRequiredBeforeNativeEmitter"]),
                           "limitsPreserved": True}
    result["a12Checkout"] = checkout
    result["resourceBoundary"] = run_source_limit()
    result["a13"] = {"status": "not-executed", "reason": "no accepted A13 semantic contract or branch"}
    result["c23"] = {"status": "experimental-only", "sha": "ff0ad3fe513419a2317cc0e9616e1c5ce13f3701",
                      "reason": "Artifact-05 is not A14 and is not composed into this executable path"}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Pepin Integration 01 A12 boundary gate")
    parser.add_argument("--real-a12", action="store_true")
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "_build" / "integration01" / "receipt.json")
    args = parser.parse_args()
    if not args.real_a12:
        parser.error("--real-a12 is required")
    result = run_real()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"boundary": result["boundary"], "rows": len(result["rows"]),
                      "resourceBoundary": result["resourceBoundary"]["code"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
