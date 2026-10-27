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
    hole_name: str
    expected_document: str
    original_revision: str
    filled_revision: str
    recovery_source: str
    recovery_revision: str


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
        recovery_source = 'say("recovered")\n'
        recovery_revision = _revision(recovery_source.encode("utf-8"))
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
            ((5, "PEP_STALE_REVISION"), (7, "PEP_SESSION_MALFORMED_JSON")),
            hole, "doc-1", source_revision, filled_revision,
            recovery_source, recovery_revision))
    return tuple(histories)


def _failure(signature: str, detail: str, **evidence: Any) -> dict[str, Any]:
    return {"classification": "confirmed-bug", "failureSignature": signature,
            "detail": detail, **evidence}


def _infrastructure(signature: str, detail: str, **evidence: Any) -> dict[str, Any]:
    return {"classification": "infrastructure-failure", "failureSignature": signature,
            "detail": detail, **evidence}


def _error_code(response: Any) -> str | None:
    if not isinstance(response, dict) or not isinstance(response.get("error"), dict):
        return None
    code = response["error"].get("code")
    return code if isinstance(code, str) else None


def _request_op(request: Any) -> str | None:
    if isinstance(request, str):
        return None
    return request.get("op") if isinstance(request, dict) else None


def _find_request(requests: tuple[Any, ...], predicate: Callable[[Any], bool]) -> int | None:
    for index, request in enumerate(requests):
        if predicate(request):
            return index
    return None


def _valid_result(response: Any, operation: str, document: str | None = None,
                 revision: str | None = None, status: str | None = None) -> bool:
    if not isinstance(response, dict) or response.get("outcome") != "ok" or response.get("operation") != operation:
        return False
    if document is not None and response.get("document") != document:
        return False
    if revision is not None and response.get("revision") != revision:
        return False
    if status is not None and response.get("status") != status:
        return False
    return isinstance(response.get("typedTree"), dict) and isinstance(response.get("holes"), list)


def _locate_roles(history: SessionHistory, requests: tuple[Any, ...]) -> dict[str, int | None]:
    original = history.original_revision
    filled = history.filled_revision
    roles = {
        "initial_open": _find_request(requests, lambda item: isinstance(item, dict) and
                                       item.get("op") == "open" and item.get("source") == history.source),
        "original_query_first": _find_request(requests, lambda item: isinstance(item, dict) and
                                               item.get("op") == "query" and item.get("revision") == original),
        "original_query_second": None,
        "metrics": _find_request(requests, lambda item: isinstance(item, dict) and item.get("op") == "metrics"),
        "edit": _find_request(requests, lambda item: isinstance(item, dict) and item.get("op") == "apply_edit" and
                               item.get("expected_revision") == original and
                               item.get("start_byte") == history.source.index("?" + history.hole_name) and
                               item.get("end_byte", item.get("start_byte")) > item.get("start_byte")),
        "stale": None,
        "filled_query": _find_request(requests, lambda item: isinstance(item, dict) and
                                       item.get("op") == "query" and item.get("revision") == filled),
        "malformed": _find_request(requests, lambda item: isinstance(item, str)),
        "recovery": _find_request(requests, lambda item: isinstance(item, dict) and
                                   item.get("op") == "open" and item.get("source") == history.recovery_source),
    }
    original_queries = [index for index, item in enumerate(requests)
                        if isinstance(item, dict) and item.get("op") == "query" and
                        item.get("revision") == original]
    roles["original_query_first"] = original_queries[0] if original_queries else None
    roles["original_query_second"] = original_queries[1] if len(original_queries) > 1 else None
    edits = [index for index, item in enumerate(requests)
             if isinstance(item, dict) and item.get("op") == "apply_edit" and
             item.get("expected_revision") == original]
    roles["edit"] = edits[0] if edits else None
    roles["stale"] = edits[1] if len(edits) > 1 else None
    return roles


def _validate_focused(result: dict[str, Any], history: SessionHistory,
                      normalized: Callable[[dict[str, Any]], Any],
                      requests: tuple[Any, ...], signature: str) -> dict[str, Any]:
    responses = result.get("responses", [])
    roles = _locate_roles(history, requests)
    if result.get("status") != "completed" or result.get("returncode") != 0 or len(responses) != len(requests):
        return _infrastructure(signature, "focused session replay did not complete with one response per request")
    if signature == "stale-error-mismatch":
        required = (roles["initial_open"], roles["edit"], roles["stale"])
        if any(index is None for index in required):
            return _infrastructure("reduction-prerequisite-missing", "stale-write prerequisites were removed")
        initial = responses[required[0]]
        edit = responses[required[1]]
        stale = responses[required[2]]
        if not _valid_result(initial, "open", history.expected_document, history.original_revision, "incomplete"):
            return _infrastructure("reduction-prerequisite-missing", "initial open prerequisite changed")
        if not _valid_result(edit, "apply_edit", history.expected_document, history.filled_revision, "valid"):
            return _infrastructure("reduction-prerequisite-missing", "successful edit prerequisite changed")
        if _error_code(stale) == "PEP_STALE_REVISION":
            return {"classification": "missing-test", "failureSignature": "history-preserved",
                    "detail": "focused replay no longer reproduces the stale-error mismatch"}
        return _failure("stale-error-mismatch", "stale edit returned the wrong error", response=stale,
                        actualCode=_error_code(stale), expectedCode="PEP_STALE_REVISION")
    return _infrastructure("reduction-unsupported", "focused replay does not support this signature")


def validate_history(result: dict[str, Any], history: SessionHistory,
                     normalized: Callable[[dict[str, Any]], Any],
                     requests: Iterable[Any] | None = None,
                     focus_signature: str | None = None) -> dict[str, Any]:
    """Validate all consequential state transitions in a public session history."""
    request_sequence = tuple(history.requests if requests is None else requests)
    if focus_signature is not None:
        return _validate_focused(result, history, normalized, request_sequence, focus_signature)
    responses = result.get("responses", [])
    if (result.get("status") != "completed" or result.get("returncode") != 0 or
            len(responses) != len(request_sequence) or
            any(not isinstance(item, dict) for item in responses)):
        return _infrastructure("session-transport", "session history did not return one JSON object per request",
                               responseCount=len(responses), expectedCount=len(request_sequence))
    if request_sequence != history.requests:
        return _infrastructure("session-shape", "full history validator requires the declared request sequence")
    initial = responses[0]
    if not _valid_result(initial, "open", status="incomplete"):
        return _failure("initial-open-shape", "initial open did not establish the documented incomplete result",
                        response=initial)
    document = initial.get("document")
    original_revision = initial.get("revision")
    if not isinstance(document, str) or not document:
        return _failure("initial-open-identity", "initial open did not return a document identity", response=initial)
    if document != history.expected_document or original_revision != history.original_revision:
        return _failure("initial-open-revision", "initial open returned the wrong document or revision",
                        expectedDocument=history.expected_document, actualDocument=document,
                        expectedRevision=history.original_revision, actualRevision=original_revision)
    if not initial.get("holes") or not any(isinstance(hole, dict) and hole.get("name") == history.hole_name
                                            for hole in initial["holes"]):
        return _failure("initial-open-hole", "initial open did not expose the expected named hole", response=initial)
    original_queries = responses[1:3]
    for response in original_queries:
        if not _valid_result(response, "query", document, history.original_revision, "incomplete"):
            return _failure("original-query-shape", "original-revision query did not return the expected incomplete shape",
                            response=response)
        if not any(isinstance(hole, dict) and hole.get("name") == history.hole_name
                   for hole in response["holes"]):
            return _failure("original-query-hole", "original-revision query lost the expected hole", response=response)
    if normalized(original_queries[0]) != normalized(original_queries[1]):
        return _failure("repeated-query-difference", "same-revision queries changed semantic result")
    metrics = responses[3].get("metrics")
    cache_hits = metrics.get("cache_hits") if isinstance(metrics, dict) else None
    if not isinstance(metrics, dict) or not isinstance(cache_hits, int) or cache_hits < 2:
        return _failure("cache-reuse-missing", "same-revision queries did not report cache reuse", response=responses[3])
    edit = responses[4]
    if not _valid_result(edit, "apply_edit", document, history.filled_revision, "valid"):
        return _failure("edit-failed", "first edit did not succeed with the expected valid result", response=edit)
    if edit.get("revision") == history.original_revision:
        return _failure("edit-revision-mismatch", "successful edit returned the original revision", response=edit)
    if edit.get("revision") != history.filled_revision:
        return _failure("edit-revision-mismatch", "successful edit returned an unrelated revision",
                        expectedRevision=history.filled_revision, actualRevision=edit.get("revision"))
    if edit.get("document") != document:
        return _failure("edit-document-mismatch", "successful edit changed document identity", response=edit)
    if edit.get("holes"):
        return _failure("edit-hole-remains", "successful edit still reports the original hole", response=edit)
    stale = responses[5]
    if not isinstance(stale, dict) or stale.get("outcome") != "error" or stale.get("operation") != "apply_edit":
        return _failure("stale-edit-accepted", "stale edit was not rejected as an apply_edit error", response=stale)
    if stale.get("document") != document or stale.get("currentRevision") != history.filled_revision:
        return _failure("stale-state-mismatch", "stale rejection did not preserve the current document state", response=stale)
    if _error_code(stale) != "PEP_STALE_REVISION":
        return _failure("stale-error-mismatch", "stale edit returned the wrong error", response=stale,
                        expectedCode="PEP_STALE_REVISION", actualCode=_error_code(stale))
    current = responses[6]
    if not _valid_result(current, "query", document, history.filled_revision, "valid"):
        return _failure("current-query-mismatch", "current-revision query did not return the filled valid result",
                        response=current)
    if current.get("holes"):
        return _failure("current-query-hole", "current-revision query still reports a hole", response=current)
    malformed = responses[7]
    if malformed.get("outcome") != "error" or _error_code(malformed) != "PEP_SESSION_MALFORMED_JSON":
        return _failure("malformed-json-recovery-failed", "malformed JSON did not return its exact transport error",
                        response=malformed)
    recovery = responses[8]
    if not _valid_result(recovery, "open", status="valid"):
        return _failure("recovery-failed", "session did not recover with a valid subsequent open", response=recovery)
    if recovery.get("document") == document or recovery.get("revision") != history.recovery_revision:
        return _failure("recovery-identity-mismatch", "recovery open did not establish the expected new document",
                        response=recovery, expectedRevision=history.recovery_revision)
    return {"classification": "missing-test", "failureSignature": "history-preserved",
            "detail": "bounded session history invariants preserved"}


def history_record(history: SessionHistory) -> dict[str, Any]:
    return {"historyId": history.history_id, "seed": history.seed, "index": history.index,
            "source": history.source, "filled": history.filled,
            "expectedDocument": history.expected_document, "holeName": history.hole_name,
            "originalRevision": history.original_revision, "filledRevision": history.filled_revision,
            "recoverySource": history.recovery_source, "recoveryRevision": history.recovery_revision,
            "expectedCodes": [list(item) for item in history.expected_codes],
            "requests": list(history.requests)}


def history_from_record(record: dict[str, Any]) -> SessionHistory:
    return SessionHistory(record["historyId"], int(record["seed"]), int(record["index"]),
                          record["source"], record["filled"], tuple(record["requests"]),
                          tuple((int(item[0]), item[1]) for item in record["expectedCodes"]),
                          record["holeName"], record["expectedDocument"], record["originalRevision"],
                          record["filledRevision"], record["recoverySource"], record["recoveryRevision"])


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
