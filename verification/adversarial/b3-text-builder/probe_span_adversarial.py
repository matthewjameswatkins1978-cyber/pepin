"""Agent 3 adversarial span probe for `stdlib/text_builder.pep` (A2 B3, pinned via argv[1]).

Matthew-assigned while waiting on A1: hunt real correctness defects in B3's text builder,
especially byte counts, embedded NUL, Unicode, malformed spans and source-context restrictions.

A2's `tests/probe_text_builder_span.py` exercises FULL IN-BOUNDS spans only, always
(start=0, finish=len(payload)). This probe attacks the UNPINNED classes and checks the
module's core invariant directly:

    reported byteCount == actual UTF-8 byte length of the joined fragments

Malformed outcomes are classified, not prejudged:
  refused            -> tool error / fail-closed refusal (SAFE: contract preserved)
  accepted-match     -> span accepted AND reported bytes == actual bytes (ROBUST)
  accepted-mismatch  -> span accepted AND reported bytes != actual bytes
                        (= DEFECT: the value proposition "the byte count is part of
                         the value" breaks; a consumer reports a wrong output width)

Target pin: pass the pinned worktree as argv[1] (e.g. D:\\Projects\\wt-a3-b3-b9a0f99).
Run from anywhere; the probe reads stdlib/text_builder.pep from the TARGET.

Exit codes: 0 = all cases classified (any classification is valid data);
            1 = a CONTROL case failed (harness/validity problem, not a finding);
            2 = harness error (never reads as a product result).

NO frozen acceptance instrument is imported, executed or modified by this probe.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record_value  # noqa: E402

STDLIB = REPO / "stdlib" / "text_builder.pep"

PROBE_FUNCTION = """
type PepA3SpanAdvProbe { status: Str, diagnostic: Str, byteCount: Int, partCount: Int, fragments: List[Str] }

fn a3_span_adv_probe(start: Int, finish: Int) -> PepA3SpanAdvProbe {
  let builder = text_builder_push_span(text_builder_new(), source_bytes(), start, finish)
  return PepA3SpanAdvProbe {
    status: "ok",
    diagnostic: "",
    byteCount: text_builder_bytes(builder),
    partCount: text_builder_part_count(builder),
    fragments: text_builder_parts(builder)
  }
}
"""

# (case, payload, start, finish, control)  -- control=True must classify accepted-match
CASES = [
    ("in-bounds-full",     "abc",    0, 3, True),   # reproduces A2's green
    ("empty-at-eof",       "abc",    3, 3, True),   # empty span at the boundary
    ("empty-mid",          "abc",    1, 1, True),   # empty span inside
    ("end-beyond-eof",     "abc",    0, 5, False),  # MALFORMED: finish > len
    ("start-beyond-eof",   "abc",    4, 6, False),  # MALFORMED: start > len
    ("negative-start",     "abc",  -1, 2, False),   # MALFORMED: negative offset
    ("mid-char-start",     "\u00e9", 1, 2, False),  # MALFORMED: split 2-byte char (right half)
    ("mid-char-end",       "\u00e9", 0, 1, False),  # MALFORMED: split 2-byte char (left half)
    ("split-plus-nul",     "é\0z",  1, 3, False),   # MALFORMED: halves é, keeps NUL
    ("nul-and-beyond",     "a\0b",   0, 6, False),  # MALFORMED: NUL payload, finish > len
    ("reversed-span",      "abc",    2, 1, False),  # MALFORMED: start > finish (doc: soft refusal)
    ("both-negative",      "abc",  -3, -1, False),  # MALFORMED: both offsets negative
    ("multibyte-full",     "é\0z",  0, 4, True),    # control: their multibyte+nul case
]


def empty_expected():
    return typed_record_value("PepA3SpanAdvProbe", [
        ("status", typed("Str", "ok")),
        ("diagnostic", typed("Str", "")),
        ("byteCount", typed("Int", "0")),
        ("partCount", typed("Int", "1")),
        ("fragments", {"type": "List[Str]", "value": [typed("Str", "")]}),
    ])


def fields_of(response):
    return {item["name"]: item["value"] for item in response["result"]["fields"]}


def main():
    module = STDLIB.read_text(encoding="utf-8") + PROBE_FUNCTION
    session = Session()
    rows = []
    try:
        opened = session.send({"schemaVersion": 3, "op": "open", "source": module,
                               "name": "a3-span-adversarial", "metadataOnly": True})
        require(opened, "outcome", "ok", "open probe module")
        require(opened, "status", "valid", "check probe module")
        document, revision = opened["document"], opened["revision"]

        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}

        registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                                   "tool": "a3-span-adv", "document": document,
                                   "revision": revision, "function": "a3_span_adv_probe"})
        require(registered, "status", "Registered", "register probe")
        # NOTE: validating an empty payload with (0,0) on an EMPTY source is the same
        # boundary shape A2 validates with; our empty_expected matches push_span on an
        # empty source only if the guard accepts (0,0) there. If validation fails, that
        # itself is data -> surfaced as exit 2 with the message (harness-level).
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                                  "tool": "a3-span-adv", "document": document, "revision": revision,
                                  "testVectors": [{"arguments": [typed("Int", 0), typed("Int", 0)],
                                                   "expect": empty_expected(),
                                                   "semanticTarget": target_spec}]})
        if validated.get("status") != "Validated":
            print(json.dumps({"harness": "validate", "response": validated}, default=str))
            return 2
        activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                                  "tool": "a3-span-adv", "document": document, "revision": revision})
        require(activated, "status", "Active", "activate probe")

        payload_targets = {}
        for name, payload, start, finish, control in CASES:
            raw = payload.encode("utf-8")
            if payload not in payload_targets:
                target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                       "name": f"p{len(payload_targets)}", "bytes": list(raw)})
                require(target, "outcome", "ok", f"open payload for {name}")
                payload_targets[payload] = ({"document": target["document"],
                                             "revision": target["revision"],
                                             "entryFunctions": []}, len(raw))
            semantic, raw_len = payload_targets[payload]
            row = {"case": name, "start": start, "finish": finish, "payloadBytes": raw_len,
                   "control": control}
            invoked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                                    "tool": "a3-span-adv",
                                    "arguments": [typed("Int", start), typed("Int", finish)],
                                    "semanticTarget": semantic})
            if invoked.get("outcome") != "ok":
                err = invoked.get("error") or {}
                row["classification"] = "refused"
                row["error"] = err.get("code") or "UNKNOWN"
                row["detail"] = str(err.get("message", ""))[:160]
            else:
                fields = fields_of(invoked)
                reported = int(fields["byteCount"]["value"])
                parts = int(fields["partCount"]["value"])
                fragments = [item["value"] for item in fields["fragments"]["value"]]
                actual = len("".join(fragments).encode("utf-8"))
                row.update({"reportedBytes": reported, "actualJoinedBytes": actual,
                            "partCount": parts,
                            "roundTrip": "".join(fragments).encode("utf-8").decode("utf-8", "replace")})
                row["classification"] = "accepted-match" if reported == actual else "accepted-mismatch"
            rows.append(row)
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    for row in rows:
        print(json.dumps(row, sort_keys=True))
    controls_ok = all(r["classification"] == "accepted-match" for r in rows if r["control"])
    mismatches = [r["case"] for r in rows if r["classification"] == "accepted-mismatch"]
    refusals = [r["case"] for r in rows if r["classification"] == "refused"]
    print(json.dumps({"SUMMARY": len(rows), "controls_ok": controls_ok,
                      "accepted_mismatch": mismatches, "refused": refusals}, sort_keys=True))
    return 0 if controls_ok else 1


if __name__ == "__main__":
    sys.exit(main())
