"""PEP-PERFORMANCE-02 measurement foundations.

This module is deliberately test-only.  It reuses the accepted R2 session
harness for real A11 runs, and keeps future parser/checker/emitter experiments
as labelled local fixtures.  None of the experimental representations are
used by the Pep compiler or by the JSONL protocol.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests import benchmark_runtime_transport as base


CLOCK_SOURCE = "python.time.perf_counter_ns"
LAB_SCHEMA_VERSION = 1
DEFAULT_MAX_TRIALS = 20
DEFAULT_MAX_BYTES = 65_536
TOOL_STEP_BUDGET = 100_000
TOOL_MESSAGE_BUDGET = 1_048_576


def elapsed_ms(start_ns: int, end_ns: int | None = None) -> float:
    return round(((time.perf_counter_ns() if end_ns is None else end_ns) - start_ns) / 1_000_000, 4)


def measured(call: Callable[[], Any]) -> tuple[Any, float]:
    started = time.perf_counter_ns()
    value = call()
    return value, elapsed_ms(started)


@dataclass(frozen=True)
class ProfileTotals:
    """Internal profile totals; these are elapsed wall-clock timestamps."""

    calls: int
    decode_ms: float
    grant_ms: float
    execute_ms: float
    encode_ms: float
    response_ms: float
    steps: int
    value_nodes: int
    encoded_result_bytes: int

    @property
    def internal_ms(self) -> float:
        return round(
            self.decode_ms + self.grant_ms + self.execute_ms + self.encode_ms + self.response_ms,
            4,
        )


def profile_totals(rows: Iterable[dict[str, Any]]) -> ProfileTotals:
    rows = list(rows)
    return ProfileTotals(
        calls=len(rows),
        decode_ms=round(sum(int(row.get("decodeCpuUs", 0)) for row in rows) / 1000, 4),
        grant_ms=round(sum(int(row.get("grantCpuUs", 0)) for row in rows) / 1000, 4),
        execute_ms=round(sum(int(row.get("executeCpuUs", 0)) for row in rows) / 1000, 4),
        encode_ms=round(sum(int(row.get("encodeCpuUs", 0)) for row in rows) / 1000, 4),
        response_ms=round(sum(int(row.get("responseCpuUs", 0)) for row in rows) / 1000, 4),
        steps=sum(int(row.get("steps", 0)) for row in rows),
        value_nodes=sum(int(row.get("resultValueNodes", 0)) for row in rows),
        encoded_result_bytes=sum(int(row.get("encodedResultBytes", 0)) for row in rows),
    )


def source_acquisition(raw: bytes) -> dict[str, Any]:
    """Measure the host-side source snapshot preparation, not Pep execution."""

    started = time.perf_counter_ns()
    decoded = raw.decode("utf-8")
    source_revision = base.revision(raw)
    digest = hashlib.sha256(raw).hexdigest()
    return {
        "clockSource": CLOCK_SOURCE,
        "bytes": len(raw),
        "utf8Valid": True,
        "revision": source_revision,
        "sha256": digest,
        "elapsedMs": elapsed_ms(started),
        "decodedCodepoints": len(decoded),
    }


def stage_accounting(
    *,
    source: dict[str, Any],
    result: dict[str, Any],
    metrics: dict[str, Any],
    profiles: list[dict[str, Any]],
    process: dict[str, Any],
    trial: int,
) -> dict[str, Any]:
    """Create a non-double-counting view of one end-to-end A11 trial.

    Host request/response timings and internal profile timings overlap during
    the response wait.  The report therefore exposes both ledgers and never
    subtracts them as if they were disjoint CPU intervals.
    """

    internal = profile_totals(profiles)
    requests = metrics["requests"]
    return {
        "schemaVersion": LAB_SCHEMA_VERSION,
        "kind": "a11-stage-profile",
        "clockSource": CLOCK_SOURCE,
        "trial": trial,
        "source": source,
        "result": {"tokens": len(result.get("tokens", [])), "error": result.get("error")},
        "process": process,
        "requests": {
            "calls": int(requests["count"]),
            "requestBytes": int(requests["requestBytes"]),
            "responseBytes": int(requests["responseBytes"]),
            "requestEncodeMs": float(requests["requestEncodeMs"]),
            "writeMs": float(requests["writeMs"]),
            "responseWaitMs": float(requests["readMs"]),
            "hostJsonDecodeMs": float(requests["parseMs"]),
            "hostMeasuredTotalMs": float(requests["totalMs"]),
        },
        "internalProfile": {
            "calls": internal.calls,
            "clockMeaning": "elapsed wall time from Unix.gettimeofday in isolated profile executable",
            "decodeMs": internal.decode_ms,
            "revisionGrantMs": internal.grant_ms,
            "interpreterAndTypedConstructionMs": internal.execute_ms,
            "resultEncodingMs": internal.encode_ms,
            "responseFormattingMs": internal.response_ms,
            "profileTotalMs": internal.internal_ms,
            "steps": internal.steps,
            "valueNodes": internal.value_nodes,
            "encodedResultBytes": internal.encoded_result_bytes,
        },
        "attribution": {
            "sourceAcquisitionMeasuredSeparately": True,
            "processStartupIncludedInProcess.spawnMs": True,
            "firstResponseReadIncludesReadiness": True,
            "internalAndHostLedgersOverlap": True,
            "typedConstructionIsNotSeparatelyIsolated": True,
        },
    }


def run_a11_stage_profile(
    *,
    mode: str = "direct",
    trials: int = 1,
    timeout_s: float = 30.0,
    startup_timeout_s: float = 10.0,
    cleanup_timeout_s: float = 2.0,
) -> list[dict[str, Any]]:
    """Run the real A11 lexer through the accepted R2 session route."""

    if not 1 <= trials <= DEFAULT_MAX_TRIALS:
        raise ValueError(f"trials must be between 1 and {DEFAULT_MAX_TRIALS}")
    raw = base.LEXER.read_bytes()
    source = source_acquisition(raw)
    source_text = raw.decode("utf-8")
    rows: list[dict[str, Any]] = []
    for trial in range(1, trials + 1):
        result, metrics, profiles, process = base.run_lexer(
            mode,
            source_text,
            raw,
            profile=(mode == "direct"),
            timeout_s=timeout_s,
            startup_timeout_s=startup_timeout_s,
            cleanup_timeout_s=cleanup_timeout_s,
        )
        rows.append(stage_accounting(
            source=source,
            result=result,
            metrics=metrics,
            profiles=profiles,
            process=process,
            trial=trial,
        ))
    return rows


def provisional_a12_measurement(
    *,
    candidate_sha: str,
    source_bytes: int,
    nodes: int,
    continuations: int,
    request_bytes: int,
    response_bytes: int,
    max_request_bytes: int,
    max_response_bytes: int,
) -> dict[str, Any]:
    """Normalize evidence from a disposable A12 checkout without promoting it."""

    return {
        "kind": "a12-provisional-parser-measurement",
        "authority": "provisional-disposable-checkout",
        "candidateSha": candidate_sha,
        "sourceBytes": source_bytes,
        "nodes": nodes,
        "continuations": continuations,
        "requestBytes": request_bytes,
        "responseBytes": response_bytes,
        "maxRequestBytes": max_request_bytes,
        "maxResponseBytes": max_response_bytes,
        "sourceCapUnchanged": True,
        "protocolChanged": False,
        "clockSource": "candidate test_a12.py time.perf_counter (reported as elapsed wall time)",
    }


def estimate_batch_width(
    *,
    target_width: int,
    remaining_units: int,
    remaining_steps: int,
    remaining_bytes: int,
    estimated_steps_per_unit: int,
    estimated_bytes_per_unit: int,
    safety: float = 0.8,
    hard_max: int = 256,
) -> int:
    """Conservative test-only estimator using only observed/public counters."""

    if not 0 < safety <= 1:
        raise ValueError("safety must be in (0, 1]")
    if min(target_width, remaining_units, remaining_steps, remaining_bytes) <= 0:
        return 1
    step_budget = int(remaining_steps * safety) // max(1, estimated_steps_per_unit)
    byte_budget = int(remaining_bytes * safety) // max(1, estimated_bytes_per_unit)
    return max(1, min(target_width, hard_max, remaining_units, step_budget, byte_budget))


@dataclass
class FeedbackBatcher:
    """Bounded scheduler model; it never commits a failed batch."""

    target_width: int = 256
    min_width: int = 1
    max_width: int = 256
    safety: float = 0.8
    width: int = 32

    def __post_init__(self) -> None:
        if not 1 <= self.min_width <= self.max_width:
            raise ValueError("invalid feedback width bounds")
        if not 0 < self.safety <= 1:
            raise ValueError("safety must be in (0, 1]")
        self.width = max(self.min_width, min(self.max_width, self.width))

    def propose(self, remaining_units: int, remaining_steps: int, remaining_bytes: int, estimate_steps: int, estimate_bytes: int) -> int:
        bounded = estimate_batch_width(
            target_width=min(self.target_width, self.width),
            remaining_units=remaining_units,
            remaining_steps=remaining_steps,
            remaining_bytes=remaining_bytes,
            estimated_steps_per_unit=estimate_steps,
            estimated_bytes_per_unit=estimate_bytes,
            safety=self.safety,
            hard_max=self.max_width,
        )
        return max(self.min_width, bounded)

    def observe(self, *, requested_units: int, actual_steps: int, actual_bytes: int, success: bool) -> None:
        if requested_units <= 0:
            raise ValueError("requested_units must be positive")
        if not success:
            # The failed batch is not committed; only the next proposal changes.
            self.width = max(self.min_width, min(self.width // 2, requested_units // 2 or 1))
            return
        steps_per_unit = max(1, actual_steps // requested_units)
        bytes_per_unit = max(1, actual_bytes // requested_units)
        if steps_per_unit * requested_units <= int(TOOL_STEP_BUDGET * self.safety) and actual_bytes <= int(TOOL_MESSAGE_BUDGET * self.safety):
            self.width = min(self.max_width, max(self.width + 1, self.width * 2))
        else:
            self.width = max(self.min_width, min(self.width, requested_units))


def simulate_batch_strategy(
    *,
    strategy: str,
    units: int,
    steps_per_unit: int,
    bytes_per_unit: int,
    target_width: int = 256,
    optimistic: bool = False,
) -> dict[str, Any]:
    """Simulate fixed, estimated and feedback scheduling at unchanged budgets."""

    if strategy not in {"fixed", "estimated", "feedback"}:
        raise ValueError("unknown batching strategy")
    remaining = units
    committed = 0
    batches: list[dict[str, Any]] = []
    feedback = FeedbackBatcher(target_width=target_width, width=min(32, target_width))
    while remaining:
        if strategy == "fixed":
            width = min(target_width, remaining)
        elif strategy == "estimated":
            estimated_steps = steps_per_unit if not optimistic else max(1, steps_per_unit // 4)
            estimated_bytes = bytes_per_unit if not optimistic else max(1, bytes_per_unit // 4)
            width = estimate_batch_width(
                target_width=target_width, remaining_units=remaining,
                remaining_steps=TOOL_STEP_BUDGET, remaining_bytes=TOOL_MESSAGE_BUDGET,
                estimated_steps_per_unit=estimated_steps, estimated_bytes_per_unit=estimated_bytes,
            )
        else:
            width = feedback.propose(remaining, TOOL_STEP_BUDGET, TOOL_MESSAGE_BUDGET, steps_per_unit, bytes_per_unit)
        actual_steps = width * steps_per_unit
        actual_bytes = width * bytes_per_unit
        success = actual_steps <= TOOL_STEP_BUDGET and actual_bytes <= TOOL_MESSAGE_BUDGET
        row = {"requestedUnits": width, "actualSteps": actual_steps, "actualBytes": actual_bytes, "outcome": "success" if success else "bounded-failure"}
        batches.append(row)
        if not success:
            if strategy == "feedback":
                feedback.observe(requested_units=width, actual_steps=actual_steps, actual_bytes=actual_bytes, success=False)
                if feedback.width == width:
                    break
                continue
            break
        committed += width
        remaining -= width
        if strategy == "feedback":
            feedback.observe(requested_units=width, actual_steps=actual_steps, actual_bytes=actual_bytes, success=True)
    return {
        "strategy": strategy,
        "units": units,
        "stepsPerUnit": steps_per_unit,
        "bytesPerUnit": bytes_per_unit,
        "optimisticEstimator": optimistic,
        "committedUnits": committed,
        "complete": committed == units,
        "batches": batches,
    }


def transport_scaling(counts: Iterable[int] = (8, 32, 128, 256)) -> list[dict[str, Any]]:
    rows = []
    for count in counts:
        fixture = synthetic_checked_ast_fixture(count)
        rows.extend(measure_representations(fixture))
    return rows


def _timed_send(client: base.SessionClient, request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], float]:
    started = time.perf_counter_ns()
    response, timing = client.send(request)
    return response, timing, elapsed_ms(started)


def run_session_lifecycle(
    *,
    count: int = 8,
    repeated_invokes: int = 4,
    cold_trials: int = 2,
    timeout_s: float = 30.0,
    startup_timeout_s: float = 10.0,
    cleanup_timeout_s: float = 2.0,
) -> dict[str, Any]:
    """Measure cold setup versus same-session reuse on the real typed tool."""

    if min(count, repeated_invokes, cold_trials) < 1:
        raise ValueError("lifecycle counts must be positive")
    source, expected = base.typed_result_source(count)
    cold = []
    for _ in range(cold_trials):
        row = base.run_typed_result(
            "direct", count, timeout_s=timeout_s,
            startup_timeout_s=startup_timeout_s, cleanup_timeout_s=cleanup_timeout_s,
        )
        cold.append(row)

    client = base.SessionClient(
        "direct", timeout_s=timeout_s, startup_timeout_s=startup_timeout_s,
        cleanup_timeout_s=cleanup_timeout_s,
    )
    try:
        setup_rows: list[dict[str, Any]] = []
        opened, timing, open_ms = _timed_send(client, {"schemaVersion": 3, "op": "open", "name": "lifecycle", "source": source})
        setup_rows.append(timing)
        document, source_revision = opened["document"], opened["revision"]
        for request in [
            base.tool_request("tool_register", tool="lifecycle-tool", document=document, revision=source_revision, function="build"),
            base.tool_request("tool_validate", tool="lifecycle-tool", document=document, revision=source_revision,
                              testVectors=[{"arguments": [], "expect": expected}]),
            base.tool_request("tool_activate", tool="lifecycle-tool", document=document, revision=source_revision),
        ]:
            response, row, _ = _timed_send(client, request)
            setup_rows.append(row)
            if response.get("status") not in {"Registered", "Validated", "Active"}:
                raise AssertionError(f"lifecycle setup failed: {response}")
        invoke_rows = []
        for _ in range(repeated_invokes):
            response, timing, elapsed = _timed_send(client, base.tool_request("tool_invoke", tool="lifecycle-tool", arguments=[]))
            if response.get("outcome") != "ok" or response.get("result") != expected:
                raise AssertionError("same-session result changed")
            invoke_rows.append({"wire": timing, "elapsedMs": elapsed})
        edit, _, edit_ms = _timed_send(client, {
            "schemaVersion": 3, "op": "apply_edit", "document": document,
            "expected_revision": source_revision, "start_byte": 0, "end_byte": 0,
            "replacement": " ",
        })
        stale, _, stale_ms = _timed_send(client, {
            "schemaVersion": 3, "op": "apply_edit", "document": document,
            "expected_revision": source_revision, "start_byte": 0, "end_byte": 0,
            "replacement": " ",
        })
        stderr = client.close()
        return {
            "kind": "session-lifecycle",
            "clockSource": CLOCK_SOURCE,
            "count": count,
            "coldTrials": cold,
            "coldMedianSetupMs": statistics.median(row["setup"]["totalMs"] for row in cold),
            "coldMedianInvokeMs": statistics.median(row["response"]["totalMs"] for row in cold),
            "warmSession": {
                "spawnMs": client.spawn_ms,
                "readyMs": client.ready_ms,
                "openMs": open_ms,
                "setupMs": sum(float(row["totalMs"]) for row in setup_rows),
                "invokeRows": invoke_rows,
                "invokeMedianMs": statistics.median(row["elapsedMs"] for row in invoke_rows),
                "peakMemory": base.peak_memory(client.samples),
            },
            "revisionLifecycle": {
                "editOutcome": edit.get("outcome"),
                "editElapsedMs": edit_ms,
                "staleOutcome": stale.get("outcome"),
                "staleCode": stale.get("error", {}).get("code"),
                "staleRejected": stale.get("outcome") == "error",
                "staleElapsedMs": stale_ms,
                "oldRevision": source_revision,
                "newRevision": edit.get("revision"),
            },
            "stderrProfileRecords": len(base.parse_profile(stderr)),
        }
    except BaseException:
        client.close()
        raise


def architecture_comparison(
    *,
    a11_calls: int,
    a11_response_bytes: int,
    a12_calls: int,
    a12_response_bytes: int,
    compact_ratio: float,
) -> list[dict[str, Any]]:
    """Compare pipeline shapes without creating a host-state implementation."""

    return [
        {
            "model": "separated-tools",
            "measuredEvidence": "A11/A12 independent session routes",
            "roundTrips": a11_calls + a12_calls,
            "responseBytes": a11_response_bytes + a12_response_bytes,
            "trustComplexity": "low",
            "debuggability": "high",
            "status": "measured-components-only",
        },
        {
            "model": "composed-Pep-invocation",
            "measuredEvidence": "A12 one-invocation lexer-to-parser boundary plus A11 profile",
            "roundTrips": a12_calls,
            "responseBytes": a12_response_bytes,
            "trustComplexity": "low",
            "debuggability": "medium",
            "status": "supported-direction; checker/emitter not implemented",
        },
        {
            "model": "hybrid-retained-state",
            "measuredEvidence": "compact fixture ratio only; host state is design-only",
            "roundTrips": a12_calls,
            "responseBytes": int(a12_response_bytes * compact_ratio),
            "trustComplexity": "high",
            "debuggability": "low",
            "status": "design-only; no production host state",
        },
    ]


def median_stage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot summarize an empty stage profile")
    request_keys = (
        "requestBytes", "responseBytes", "requestEncodeMs", "writeMs",
        "responseWaitMs", "hostJsonDecodeMs", "hostMeasuredTotalMs",
    )
    internal_keys = (
        "decodeMs", "revisionGrantMs", "interpreterAndTypedConstructionMs",
        "resultEncodingMs", "responseFormattingMs", "profileTotalMs",
        "steps", "valueNodes", "encodedResultBytes",
    )
    return {
        "trials": len(rows),
        "sourceBytes": rows[0]["source"]["bytes"],
        "tokens": rows[0]["result"]["tokens"],
        "requests": {key: statistics.median(row["requests"][key] for row in rows) for key in request_keys},
        "internalProfile": {key: statistics.median(row["internalProfile"][key] for row in rows) for key in internal_keys},
        "process": {
            "spawnMsMedian": statistics.median(row["process"]["spawnMs"] for row in rows),
            "readyMsMedian": statistics.median(
                row["process"]["readyMs"] for row in rows if row["process"]["readyMs"] is not None
            ),
        },
        "clockSource": rows[0]["clockSource"],
    }


def synthetic_checked_ast_fixture(count: int, revision: str = "sha256:synthetic") -> dict[str, Any]:
    if count < 1:
        raise ValueError("fixture count must be positive")
    nodes = []
    for index in range(count):
        parent = None if index == 0 else (index - 1) // 2
        nodes.append({
            "id": index,
            "parentId": parent,
            "childIndex": 0 if parent is None else index - (parent * 2 + 1),
            "role": "root" if parent is None else "body",
            "kind": "Call" if index % 3 == 0 else "IntLiteral",
            "type": "Unit" if index % 3 == 0 else "Int",
            "startByte": index * 3,
            "endByte": index * 3 + 2,
            "revision": revision,
            "value": str(index) if index % 3 else "int_text",
            "diagnostic": None,
        })
    return {"schemaVersion": 1, "kind": "synthetic-checked-ast", "revision": revision, "nodes": nodes}


def synthetic_c23_emission_fixture(count: int) -> dict[str, Any]:
    if count < 1:
        raise ValueError("fixture count must be positive")
    lines = [
        {"line": index, "text": f"static const int64_t pep_value_{index} = {index};"}
        for index in range(count)
    ]
    return {"schemaVersion": 1, "kind": "synthetic-c23-emission", "lines": lines}


def _typed_ast_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    nodes = [
        base.typed_record("AstNode", [
            (key, base.typed("Int", str(value)) if isinstance(value, int) else base.typed("Str", "" if value is None else str(value)))
            for key, value in node.items()
        ])
        for node in fixture["nodes"]
    ]
    return base.typed_record("CheckedAst", [
        ("revision", base.typed("Str", fixture["revision"])),
        ("nodes", base.typed_list("AstNode", nodes)),
    ])


def representation_variants(fixture: dict[str, Any]) -> dict[str, Callable[[], tuple[bytes, Callable[[bytes], dict[str, Any]]]]]:
    """Return local-only encoders and decoders for the same logical AST."""

    nodes = fixture["nodes"]
    flat = {"schemaVersion": 1, "kind": fixture["kind"], "revision": fixture["revision"], "nodes": nodes}
    strings: dict[str, int] = {}
    for node in nodes:
        for key in ("role", "kind", "type", "revision", "value"):
            value = node[key]
            if value not in strings:
                strings[value] = len(strings)
    string_table = [value for value, _ in sorted(strings.items(), key=lambda pair: pair[1])]
    compact_rows = [
        [node["id"], -1 if node["parentId"] is None else node["parentId"], node["childIndex"],
         strings[node["role"]], strings[node["kind"]], strings[node["type"]],
         node["startByte"], node["endByte"], strings[node["revision"]], strings[node["value"]],
         node["diagnostic"]]
        for node in nodes
    ]
    compact = {"v": 1, "r": fixture["revision"], "s": string_table, "n": compact_rows}

    def dumps(value: Any) -> bytes:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def decode_flat(payload: bytes) -> dict[str, Any]:
        return json.loads(payload)

    def decode_typed(payload: bytes) -> dict[str, Any]:
        value = json.loads(payload)
        fields = base.record_fields(value)
        decoded_nodes = []
        for typed_node in fields["nodes"]["value"]:
            node = {}
            for key, field in base.record_fields(typed_node).items():
                raw = field["value"]
                if key == "parentId" and raw == "":
                    raw = None
                elif key in {"id", "parentId", "childIndex", "startByte", "endByte"}:
                    raw = int(raw)
                elif key == "diagnostic" and raw == "":
                    raw = None
                node[key] = raw
            decoded_nodes.append(node)
        return {"schemaVersion": 1, "kind": "synthetic-checked-ast", "revision": fields["revision"]["value"], "nodes": decoded_nodes}

    def decode_compact(payload: bytes) -> dict[str, Any]:
        value = json.loads(payload)
        table = value["s"]
        decoded_nodes = []
        for row in value["n"]:
            decoded_nodes.append({
                "id": row[0], "parentId": None if row[1] < 0 else row[1], "childIndex": row[2],
                "role": table[row[3]], "kind": table[row[4]], "type": table[row[5]],
                "startByte": row[6], "endByte": row[7], "revision": table[row[8]],
                "value": table[row[9]], "diagnostic": row[10],
            })
        return {"schemaVersion": 1, "kind": "synthetic-checked-ast", "revision": value["r"], "nodes": decoded_nodes}

    return {
        "existing-typed-json": lambda: (dumps(_typed_ast_fixture(fixture)), decode_typed),
        "flat-node-array": lambda: (dumps(flat), decode_flat),
        "compact-interned-array": lambda: (dumps(compact), decode_compact),
    }


def canonical_fixture(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def measure_representations(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    expected = canonical_fixture(fixture)
    rows = []
    for name, factory in representation_variants(fixture).items():
        started = time.perf_counter_ns()
        payload, decoder = factory()
        encode_ms = elapsed_ms(started)
        decoded, decode_ms = measured(lambda: decoder(payload))
        if canonical_fixture(decoded) != expected:
            raise AssertionError(f"representation {name} changed the logical fixture")
        rows.append({
            "representation": name,
            "fixtureKind": fixture["kind"],
            "logicalBytes": len(canonical_fixture(fixture).encode("utf-8")),
            "jsonBytes": len(payload),
            "encodeMs": encode_ms,
            "decodeMs": decode_ms,
            "nodes": len(fixture["nodes"]),
            "clockSource": CLOCK_SOURCE,
        })
    return rows


def cursor_variants(document: str = "target", source_revision: str = "sha256:cursor") -> dict[str, dict[str, Any]]:
    full = base.cursor_value(document, source_revision, "scan")
    fields = base.record_fields(full)
    minimal = {
        "schemaVersion": 1,
        "document": fields["document"]["value"],
        "revision": fields["revision"]["value"],
        "status": fields["status"]["value"],
        "stage": fields["stage"]["value"],
        "state": {
            key: value["value"] for key, value in fields.items()
            if key not in {"document", "revision", "status", "stage"}
        },
    }
    # Design-only: the registry is local to this function and is not an
    # authenticated continuation mechanism or a production host-state change.
    opaque = {"schemaVersion": 1, "document": document, "revision": source_revision, "handle": "local:cursor-0"}
    return {"full-existing-typed": full, "minimal-logical": minimal, "opaque-design-only": opaque}


def cursor_size_rows(document: str = "target", source_revision: str = "sha256:cursor") -> list[dict[str, Any]]:
    rows = []
    for name, value in cursor_variants(document, source_revision).items():
        payload, encode_ms = measured(lambda value=value: json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        decoded, decode_ms = measured(lambda: json.loads(payload))
        if name == "full-existing-typed":
            decoded_fields = base.record_fields(decoded)
            decoded_document = decoded_fields["document"]["value"]
            decoded_revision = decoded_fields["revision"]["value"]
        else:
            decoded_document = decoded.get("document")
            decoded_revision = decoded.get("revision")
        rows.append({
            "representation": name,
            "jsonBytes": len(payload),
            "encodeMs": encode_ms,
            "decodeMs": decode_ms,
            "revisionPreserved": decoded_revision == source_revision,
            "documentPreserved": decoded_document == document,
            "clockSource": CLOCK_SOURCE,
        })
    return rows


def assert_mutation_rejected(fixture: dict[str, Any], mutation: Callable[[dict[str, Any]], None]) -> None:
    mutated = json.loads(json.dumps(fixture))
    mutation(mutated)
    if canonical_fixture(mutated) == canonical_fixture(fixture):
        raise AssertionError("mutation did not change fixture")
    if mutated["revision"] != fixture["revision"]:
        return
    for expected, actual in zip(fixture["nodes"], mutated["nodes"]):
        if expected != actual:
            return
    raise AssertionError("topology mutation was not detectable")


def self_test() -> dict[str, Any]:
    fixture = synthetic_checked_ast_fixture(8)
    representation_rows = measure_representations(fixture)
    cursor_rows = cursor_size_rows()
    assert_mutation_rejected(fixture, lambda value: value["nodes"][3].__setitem__("parentId", 0))
    assert_mutation_rejected(fixture, lambda value: value["nodes"][4].__setitem__("startByte", 999))
    return {
        "kind": "performance02-self-test",
        "schemaVersion": LAB_SCHEMA_VERSION,
        "clockSource": CLOCK_SOURCE,
        "representations": representation_rows,
        "cursorRows": cursor_rows,
        "syntheticStages": [
            synthetic_checked_ast_fixture(2)["kind"],
            synthetic_c23_emission_fixture(2)["kind"],
        ],
        "negativeControls": ["parentId", "sourceSpan"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--a11", action="store_true", help="run real A11 stage profiles")
    parser.add_argument("--mode", default="direct", choices=("direct", "powershell"))
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--request-timeout-s", type=float, default=30.0)
    parser.add_argument("--startup-timeout-s", type=float, default=10.0)
    parser.add_argument("--cleanup-timeout-s", type=float, default=2.0)
    parser.add_argument("--max-source-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--transport-sizes", action="store_true", help="measure local AST representation scaling")
    parser.add_argument("--batch-sim", action="store_true", help="emit bounded fixed/estimated/feedback simulations")
    parser.add_argument("--lifecycle", action="store_true", help="measure cold and warm real-session lifecycle")
    parser.add_argument("--architecture", action="store_true", help="emit separated/composed/hybrid architecture comparison")
    parser.add_argument("--lifecycle-count", type=int, default=8)
    parser.add_argument("--lifecycle-invokes", type=int, default=4)
    parser.add_argument("--lifecycle-cold-trials", type=int, default=2)
    args = parser.parse_args(argv)
    if args.trials < 1 or args.trials > DEFAULT_MAX_TRIALS:
        parser.error(f"--trials must be between 1 and {DEFAULT_MAX_TRIALS}")
    if args.max_source_bytes <= 0:
        parser.error("--max-source-bytes must be positive")
    emitted = False
    if args.self_test or not any((args.a11, args.transport_sizes, args.batch_sim, args.lifecycle, args.architecture)):
        print(json.dumps(self_test(), ensure_ascii=False, separators=(",", ":")))
        emitted = True
    if args.transport_sizes:
        print(json.dumps({"kind": "transport-scaling", "rows": transport_scaling()}, ensure_ascii=False, separators=(",", ":")))
        emitted = True
    if args.batch_sim:
        scenarios = []
        for density, steps, bytes_per_unit in (("identifier", 120, 180), ("punctuation", 900, 220), ("nested", 2200, 640)):
            for strategy in ("fixed", "estimated", "feedback"):
                scenarios.append({"density": density, "result": simulate_batch_strategy(
                    strategy=strategy, units=1024, steps_per_unit=steps, bytes_per_unit=bytes_per_unit,
                )})
            scenarios.append({"density": density, "result": simulate_batch_strategy(
                strategy="estimated", units=1024, steps_per_unit=steps, bytes_per_unit=bytes_per_unit, optimistic=True,
            )})
        print(json.dumps({"kind": "batch-simulation", "budgets": {"steps": TOOL_STEP_BUDGET, "messageBytes": TOOL_MESSAGE_BUDGET}, "scenarios": scenarios}, ensure_ascii=False, separators=(",", ":")))
        emitted = True
    if args.lifecycle:
        if min(args.lifecycle_count, args.lifecycle_invokes, args.lifecycle_cold_trials) < 1:
            parser.error("lifecycle counts must be positive")
        base.ensure_build()
        print(json.dumps(run_session_lifecycle(
            count=args.lifecycle_count,
            repeated_invokes=args.lifecycle_invokes,
            cold_trials=args.lifecycle_cold_trials,
            timeout_s=args.request_timeout_s,
            startup_timeout_s=args.startup_timeout_s,
            cleanup_timeout_s=args.cleanup_timeout_s,
        ), ensure_ascii=False, separators=(",", ":")))
        emitted = True
    if args.architecture:
        print(json.dumps({
            "kind": "architecture-comparison",
            "clockSource": CLOCK_SOURCE,
            "models": architecture_comparison(
                a11_calls=1216, a11_response_bytes=4114973,
                a12_calls=567, a12_response_bytes=6100090,
                compact_ratio=0.25,
            ),
            "inputs": {"a11": "one-trial direct profile", "a12": "accepted disposable checkout evidence", "compactRatio": 0.25},
        }, ensure_ascii=False, separators=(",", ":")))
        emitted = True
    if args.a11:
        raw = base.LEXER.read_bytes()
        if len(raw) > args.max_source_bytes:
            print(json.dumps({"kind": "benchmark-error", "error": "source-cap", "bytes": len(raw)}))
            return 2
        base.ensure_build()
        rows = run_a11_stage_profile(
            mode=args.mode,
            trials=args.trials,
            timeout_s=args.request_timeout_s,
            startup_timeout_s=args.startup_timeout_s,
            cleanup_timeout_s=args.cleanup_timeout_s,
        )
        print(json.dumps({"kind": "a11-stage-profile-summary", "summary": median_stage(rows), "trials": rows}, ensure_ascii=False, separators=(",", ":")))
        emitted = True
    return 0 if emitted else 2


if __name__ == "__main__":
    sys.exit(main())
