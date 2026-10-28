"""Cursor-protocol attacks against the real Pep parser tools.

Purpose
-------
Independently challenge the `parser_start` / `parser_step` continuation protocol
that a chunked-parser repair (#20) depends on. Two questions matter, and they are
answered separately:

1. On a source both paths can handle, does the chunked assembly produce exactly
   the monolithic AST (`HOLD`/`VIOLATED` on parity)?
2. On a source the monolithic parser aborts on, does the chunked protocol still
   complete — and does it do so without hitting the budget, without accepting a
   stale cursor, and without duplicating nodes on a terminal step?

Reuse, not reinvention: bundle composition, registration order and typed value
builders come from the repository's own A12 differential module, imported
read-only; `pep_c23` supplies the monolithic `ParserProgress` builder. No test
file is modified and no budget is raised.

Each attack prints one machine-checkable line:

    ATTACK <name> | expect=<...> | observed=<...> | HOLD|VIOLATED

Exit codes: 0 all held, 1 any violation, 2 harness could not run.
"""
import json
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pep_c23                      # monolithic ParserProgress builder
import test_a12 as a12              # read-only reuse: registration recipe + builders

LEXER = REPO / "examples" / "pep_lexer.pep"
PARSER = REPO / "examples" / "pep_parser.pep"
BUILD = REPO / "_build" / "terrorbats-parser-bundle"
MAX_STEPS = 5000

# Small enough that the monolithic parser also succeeds: the parity baseline.
SMALL_SOURCE = "fn alpha(x: Int) -> Int { return x + 1 }\n"

# The composition that blocks the C23 pipeline today (#20).
BIG_SOURCE = (
    "fn int_mod(a: Int, b: Int) -> Int {\n"
    "  var x = a\n"
    "  while !(x <= b - 1) { x = x - b }\n"
    "  return x\n"
    "}\n"
    "\n"
    "fn int_gcd(a: Int, b: Int) -> Int {\n"
    "  var x = a\n"
    "  var y = b\n"
    "  while !(y == 0) {\n"
    "    let r = int_mod(x, y)\n"
    "    x = y\n"
    "    y = r\n"
    "  }\n"
    "  return x\n"
    "}\n"
    "\n"
    "fn main() -> Int { return int_gcd(48, 18) }\n"
    "say(int_text(int_gcd(48, 18)))\n"
)


class Session:
    def __init__(self):
        env = os.environ.copy()
        env.setdefault("PEPIN_OPAM_ROOT", os.environ.get("OPAMROOT", ""))
        self.proc = a12.JsonLineClient(
            ["pwsh", "-NoProfile", "-File", str(REPO / "pep.ps1"), "session", "--jsonl"],
            REPO, env)

    def send(self, request):
        return self.proc.send(request)

    def close(self):
        try:
            self.proc.close()
        except Exception:  # noqa: BLE001 - cleanup must never mask a verdict
            pass


def report(name, expect, observed, ok, detail=""):
    print("ATTACK %s | expect=%s | observed=%s | %s" % (
        name, expect, observed, "HOLD" if ok else "VIOLATED"))
    if detail:
        print("DETAIL %s | %s" % (name, str(detail)[:300].replace("\n", " ")))


def field_value(fields, name):
    for field in fields:
        if field["name"] == name:
            return field["value"]
    raise KeyError(name)


def register(session, tool, function, arguments, expected, document, revision,
             semantic):
    """Register/validate/activate against the bundle, validating on the target.

    `semantic` is what the test vector is evaluated against — the empty target,
    matching the repository's own A12 recipe. Validating against the bundle
    instead fails with PEP_TOOL_TEST_FAILED, because `parser_start` answers with
    the semantic target's identity rather than the tool document's.
    """
    registered = session.send({
        "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
        "tool": tool, "document": document, "revision": revision,
        "function": function})
    if registered.get("status") != "Registered":
        raise RuntimeError("register %s failed: %s" % (tool, registered))
    validated = session.send({
        "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
        "tool": tool, "document": document, "revision": revision,
        "testVectors": [{"arguments": arguments, "expect": expected,
                         "semanticTarget": {"document": semantic[0],
                                            "revision": semantic[1],
                                            "entryFunctions": []}}]})
    if validated.get("status") != "Validated":
        raise RuntimeError("validate %s failed: %s" % (tool, validated))
    activated = session.send({
        "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
        "tool": tool, "document": document, "revision": revision})
    if activated.get("status") != "Active":
        raise RuntimeError("activate %s failed: %s" % (tool, activated))


def invoke(session, tool, arguments, document, revision):
    return session.send({
        "schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
        "tool": tool, "arguments": arguments,
        "semanticTarget": {"document": document, "revision": revision,
                           "entryFunctions": []}})


def flat(nodes_value):
    return [dict((field["name"], field["value"]) for field in node.get("fields", []))
            for node in (nodes_value or {}).get("value", [])]


def normalise(node):
    """Scalar projection of a typed FlatAstNode, comparable across both paths.

    Comparing raw typed values compared representation wrappers as well as
    content; this reduces each node to the fields that carry meaning, so a
    mismatch is a real AST difference and not a formatting artefact.
    """
    out = {}
    for name, value in node.items():
        if name == "span":
            span = a12.span(value)
            out["startOffset"] = span.get("start", {}).get("offset")
            out["startLine"] = span.get("start", {}).get("line")
            out["startColumn"] = span.get("start", {}).get("column")
            out["endOffset"] = value.get("endOffset") if isinstance(value, dict) else None
        else:
            try:
                out[name] = a12.scalar(value)
            except (AssertionError, KeyError, TypeError, AttributeError):
                # Composite fields (List[Str] string parts) are reduced to their
                # payload, so the comparison stays content-level.
                out[name] = value.get("value") if isinstance(value, dict) else value
    return out


def compare(lhs, rhs):
    """First differing (index, left, right) between two node lists, else None."""
    for index, (left, right) in enumerate(zip(lhs, rhs)):
        if left != right:
            keys = sorted(set(left) | set(right))
            diff = {key: (left.get(key), right.get(key))
                    for key in keys if left.get(key) != right.get(key)}
            return index, diff
    if len(lhs) != len(rhs):
        return min(len(lhs), len(rhs)), {"length": (len(lhs), len(rhs))}
    return None


def open_source(session, name, source):
    opened = session.send({"schemaVersion": 3, "op": "open", "name": name,
                           "source": source})
    if opened.get("outcome") != "ok":
        raise RuntimeError("open %s failed: %s" % (name, opened))
    return opened["document"], opened["revision"]


def walk(session, document, revision):
    """Drive parser_start / parser_step to completion and capture the evidence."""
    started = invoke(session, "tb-parser-start", [], document, revision)
    if started.get("outcome") != "ok":
        return {"error": started}
    cursor = started["result"]["fields"]
    nodes, steps, statuses, budget_hit = [], 0, [], False
    final_fields = None
    trap = None
    while steps < MAX_STEPS:
        chunk = invoke(session, "tb-parser-step",
                       [{"type": "ParserCursor", "fields": cursor}], document, revision)
        if chunk.get("outcome") != "ok":
            code = str((chunk.get("error") or {}).get("code"))
            if "STEP_LIMIT" in code:
                budget_hit = True
                break
            return {"error": chunk}
        fields = chunk["result"]["fields"]
        status = a12.scalar(field_value(fields, "status"))
        done = a12.scalar(field_value(fields, "done"))
        chunk_nodes = flat(field_value(fields, "nodes"))
        statuses.append(status)
        nodes.extend(chunk_nodes)
        cursor = field_value(fields, "cursor")["fields"]
        steps += 1
        final_fields = {"status": status, "done": done,
                        "code": a12.scalar(field_value(fields, "errorCode")),
                        "nodes": len(chunk_nodes)}
        if done:
            # Tamper the revision of the finished cursor: a stale cursor must be
            # refused, and the refusal must be distinguishable from success.
            stale = [dict(field) for field in cursor]
            for field in stale:
                if field["name"] == "revision":
                    field["value"] = {"type": "Str", "value": "sha256:" + "0" * 64}
            trap = invoke(session, "tb-parser-step",
                          [{"type": "ParserCursor", "fields": stale}], document, revision)
            break
    return {"nodes": nodes, "steps": steps, "statuses": statuses,
            "budget_hit": budget_hit, "final": final_fields, "trap": trap}


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    bundle = LEXER.read_text(encoding="utf-8") + "\n" + PARSER.read_text(encoding="utf-8")
    session = Session()
    violations = 0
    try:
        room = session.send({"schemaVersion": 3, "op": "open",
                             "name": "tb-parser-bundle", "source": bundle,
                             "metadataOnly": True})
        if room.get("outcome") != "ok" or room.get("status") != "valid":
            print("HARNESS-ERROR bundle open failed: %s" % str(room)[:300])
            return 2
        tool_document, tool_revision = room["document"], room["revision"]

        empty = session.send({"schemaVersion": 3, "op": "open_bytes",
                              "name": "empty", "bytes": []})
        empty_doc, empty_rev = empty["document"], empty["revision"]
        semantic = (empty_doc, empty_rev)
        register(session, "tb-parser-start", "parser_start", [],
                 a12.parser_cursor_value(empty_doc, empty_rev), tool_document,
                 tool_revision, semantic)
        finished = a12.parser_cursor_value(empty_doc, empty_rev, done=True,
                                           lex_done=True, lex_stage="done")
        register(session, "tb-parser-step", "parser_step", [finished],
                 a12.parser_chunk_value(empty_doc, empty_rev, finished),
                 tool_document, tool_revision, semantic)
        register(session, "tb-parser-mono", "parser_parse_program", [],
                 pep_c23.parser_progress(empty_doc, empty_rev), tool_document,
                 tool_revision, semantic)

        # ---- 1. parity on a source both paths can handle -------------------
        small_doc, small_rev = open_source(session, "tb-small", SMALL_SOURCE)
        chunked = walk(session, small_doc, small_rev)
        mono = invoke(session, "tb-parser-mono", [], small_doc, small_rev)
        if "error" in chunked or mono.get("outcome") != "ok":
            print("HARNESS-ERROR small-source baseline failed: %s / %s" % (
                str(chunked.get("error"))[:200], str(mono)[:200]))
            return 2
        mono_nodes = flat(field_value(mono["result"]["fields"], "nodes"))
        mono_norm = [normalise(node) for node in mono_nodes]
        arrival_norm = [normalise(node) for node in chunked["nodes"]]
        by_id = sorted(chunked["nodes"],
                       key=lambda node: a12.scalar(node.get("id")))
        sorted_norm = [normalise(node) for node in by_id]

        # The order trap: chunks emit children before parents, so consuming them
        # in arrival order yields a misordered AST. This must be visible, because
        # a repair that skips the sort would look "complete" and be wrong.
        order_diff = compare(arrival_norm, mono_norm)
        ok = order_diff is not None and len(mono_nodes) > 0
        report("arrival-order-is-misordered",
               "arrival order differs from the monolithic AST (sort is required)",
               "equal=%s first_diff_index=%s" % (
                   order_diff is None, (order_diff or [None])[0]), ok,
               json.dumps(order_diff))
        violations += 0 if ok else 1

        # Parity once assembled the way A12 assembles: sorted by node id.
        difference = compare(sorted_norm, mono_norm)
        ok = difference is None and len(mono_nodes) > 0
        report("parity-after-id-sort", "identical node lists once sorted by id",
               "chunked=%d mono=%d equal=%s" % (
                   len(sorted_norm), len(mono_norm), difference is None), ok,
               json.dumps(difference))
        violations += 0 if ok else 1

        # ---- 2. the ceiling: monolithic must abort, chunked must complete ---
        big_doc, big_rev = open_source(session, "tb-big", BIG_SOURCE)
        big = walk(session, big_doc, big_rev)
        if "error" in big:
            print("HARNESS-ERROR big-source walk failed: %s" % str(big["error"])[:300])
            return 2
        mono_big = invoke(session, "tb-parser-mono", [], big_doc, big_rev)
        mono_code = str(((mono_big.get("error") or {}).get("code")))
        chunked_ok = (not big["budget_hit"]) and bool(big["final"]) \
            and big["final"]["status"] == "complete"
        mono_blocked = "STEP_LIMIT" in mono_code
        ok = chunked_ok and mono_blocked
        report("ceiling-uplift",
               "monolithic aborts on the budget while the cursor protocol completes",
               "mono=%s chunked_status=%s steps=%d nodes=%d budget_hit=%s" % (
                   mono_code or "ok", (big["final"] or {}).get("status"),
                   big["steps"], len(big["nodes"]), big["budget_hit"]), ok)
        violations += 0 if ok else 1

        # ---- 3. false-completion trap on the stale cursor -------------------
        trap = (big["trap"] or {}).get("result", {}).get("fields") or []
        trap_status = a12.scalar(field_value(trap, "status")) if trap else None
        trap_done = a12.scalar(field_value(trap, "done")) if trap else None
        trap_code = a12.scalar(field_value(trap, "errorCode")) if trap else None
        trap_nodes = len(flat(field_value(trap, "nodes"))) if trap else None
        ok = (trap_status == "invalid"
              and trap_code == "PEP_PARSER_CURSOR_REVISION"
              and trap_nodes == 0)
        report("false-completion-trap",
               "stale cursor -> invalid + code + zero nodes (done may be true)",
               "status=%s done=%s code=%s nodes=%s" % (
                   trap_status, trap_done, trap_code, trap_nodes), ok)
        violations += 0 if ok else 1

        # ---- 4. terminal idempotence ---------------------------------------
        final = big["final"] or {}
        ok = final.get("status") == "complete" and final.get("done") is True \
            and final.get("nodes") == 0 and final.get("code") == ""
        report("terminal-idempotence", "complete, done, empty errorCode, zero nodes",
               json.dumps(final), ok)
        violations += 0 if ok else 1

        # ---- 5. node identity ----------------------------------------------
        ids_arrival = [a12.scalar(node.get("id")) for node in big["nodes"]]
        ids = sorted(ids_arrival)
        ok = len(ids) == len(set(ids)) and ids == list(range(len(ids)))
        report("node-id-integrity",
               "after id sort: unique and contiguous from 0",
               "count=%d unique=%d contiguous=%s arrival_monotonic=%s" % (
                   len(ids), len(set(ids)), ids == list(range(len(ids))),
                   ids_arrival == sorted(ids_arrival)), ok)
        violations += 0 if ok else 1

        # ---- 6. spans inside the source ------------------------------------
        # FlatAstNode carries its extents inline as startByte/endByte. An earlier
        # version of this attack looked for a `span` object, found none, and
        # reported a vacuous HOLD across zero checked nodes — the exact failure
        # mode these Bats exist to catch, so it now requires a non-zero sample.
        source_len = len(BIG_SOURCE.encode("utf-8"))
        bad, checked, missing = [], 0, 0
        for node in big["nodes"]:
            start = node.get("startByte")
            end = node.get("endByte")
            start = a12.scalar(start) if start is not None else None
            end = a12.scalar(end) if end is not None else None
            if start is None or end is None:
                missing += 1
                continue
            checked += 1
            if start < 0 or end > source_len or end < start:
                bad.append((a12.scalar(node.get("id")), start, end))
        ok = checked > 0 and not bad
        report("span-in-bounds", "every node extent inside the source bytes",
               "nodes=%d checked=%d bad=%d missing=%d source_len=%d" % (
                   len(big["nodes"]), checked, len(bad), missing, source_len),
               ok, bad[:3] if bad else ("no extents found" if checked == 0 else ""))
        violations += 0 if ok else 1

        print("SUMMARY attacks=7 violated=%d big_steps=%d big_nodes=%d statuses=%s" % (
            violations, big["steps"], len(big["nodes"]),
            ",".join(sorted(set(big["statuses"])))))
    finally:
        session.close()
    return 0 if violations == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
