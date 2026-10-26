"""Deterministic bounded JSONL session histories and sequence reduction."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random
from typing import Any, Callable, Iterable


def _revision(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class SessionHistory:
    history_id: str
    seed: int
    index: int
    source: str
    filled: str
    requests: tuple[Any, ...]
    expected_codes: tuple[tuple[int, str], ...]


def generate_histories(seed: int, count: int) -> tuple[SessionHistory, ...]:
    if count < 0 or count > 100:
        raise ValueError("count must be between 0 and 100")
    rng = random.Random(seed ^ 0xC0FFEE)
    histories: list[SessionHistory] = []
    for index in range(count):
        hole = "answer" + str(rng.randrange(1000))
        value = rng.randint(2, 9)
        source = f"fn double(n: Int) -> Int {{ return ?{hole} }}\n"
        filled = source.replace("?" + hole, f"n * {value}")
        source_raw = source.encode("utf-8")
        filled_raw = filled.encode("utf-8")
        source_revision = _revision(source_raw)
        filled_revision = _revision(filled_raw)
        start = source.index("?" + hole)
        requests: tuple[Any, ...] = (
            {"schemaVersion": 3, "op": "open", "source": source},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": source_revision},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": source_revision},
            {"schemaVersion": 3, "op": "metrics"},
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1",
             "expected_revision": source_revision, "start_byte": start,
             "end_byte": start + len("?" + hole), "replacement": f"n * {value}"},
            # This is intentionally stale after the preceding successful edit.
            {"schemaVersion": 3, "op": "apply_edit", "document": "doc-1",
             "expected_revision": source_revision, "start_byte": 0, "end_byte": 0,
             "replacement": " "},
            {"schemaVersion": 3, "op": "query", "document": "doc-1", "revision": filled_revision},
            "{not json}",
            {"schemaVersion": 3, "op": "open", "source": "say(\"recovered\")\n"},
        )
        histories.append(SessionHistory(
            f"history-{seed}-{index:04d}", seed, index, source, filled, requests,
            ((5, "PEP_STALE_REVISION"), (7, "PEP_SESSION_MALFORMED_JSON"))))
    return tuple(histories)


def validate_history(result: dict[str, Any], history: SessionHistory,
                     normalized: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    """Validate only public session invariants; return a structured oracle."""
    responses = result.get("responses", [])
    if (result.get("status") != "completed" or result.get("returncode") != 0 or
            len(responses) != len(history.requests) or
            any(not isinstance(item, dict) for item in responses)):
        return {"classification": "infrastructure-failure",
                "detail": "session history did not return one JSON object per request",
                "responseCount": len(responses), "expectedCount": len(history.requests)}
    if normalized(responses[1]) != normalized(responses[2]):
        return {"classification": "confirmed-bug", "detail": "same-revision query changed semantic result"}
    metrics = responses[3].get("metrics")
    cache_hits = metrics.get("cache_hits") if isinstance(metrics, dict) else None
    if not isinstance(cache_hits, int) or cache_hits < 2:
        return {"classification": "confirmed-bug", "detail": "same-revision query did not report cache reuse",
                "response": responses[3]}
    for index, expected_code in history.expected_codes:
        response = responses[index]
        error = response.get("error") if isinstance(response, dict) else None
        actual_code = error.get("code") if isinstance(error, dict) else None
        if actual_code != expected_code:
            return {"classification": "confirmed-bug", "detail": "session history returned the wrong error contract",
                    "index": index, "expectedCode": expected_code, "actualCode": actual_code,
                    "response": response}
    if responses[8].get("status") != "valid":
        return {"classification": "confirmed-bug", "detail": "session did not recover after malformed JSON",
                "response": responses[8]}
    return {"classification": "missing-test", "detail": "bounded session history invariants preserved"}


def reduce_history(items: Iterable[Any], still_fails: Callable[[tuple[Any, ...]], bool],
                   budget: int = 80) -> tuple[tuple[Any, ...], int]:
    """Deterministic ddmin for request sequences with an explicit bound."""
    current = tuple(items)
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
