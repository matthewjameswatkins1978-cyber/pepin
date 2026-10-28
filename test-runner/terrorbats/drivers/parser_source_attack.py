"""Source-handling and scaling attacks on the parser cursor protocol.

Four questions a chunked-parser repair must answer without cheating:

1. CRLF equivalence — does a Windows-encoded copy of the same program produce the
   same node structure, with byte extents shifted *exactly* by the number of extra
   carriage returns before each line? (The repository has already been bitten by
   CRLF silently moving pinned spans.)
2. UTF-8 honesty — are extents byte offsets rather than character offsets, so a
   multibyte literal still yields a decodable slice?
3. Invalid-input truthfulness — does malformed input end in `invalid` with an
   error code, instead of completing and handing back a plausible tree?
4. Growth — as compositions grow, do step counts scale sanely and does any single
   step approach the 100,000-step per-invocation budget?

Reuses the harness from `parser_cursor_attack` (registration recipe, typed value
helpers, cursor walk) rather than re-implementing it.

Each attack prints `ATTACK <name> | expect=… | observed=… | HOLD|VIOLATED`.
Exit codes: 0 all held, 1 any violation, 2 harness could not run.
"""
import pathlib
import sys

DRIVERS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(DRIVERS))

import parser_cursor_attack as harness  # noqa: E402  (shared harness, read-only use)

a12 = harness.a12

BASE_LINES = [
    "fn alpha(x: Int) -> Int { return x + 1 }",
    "fn beta(y: Int) -> Int { return alpha(y) }",
    "fn main() -> Int { return beta(41) }",
    "say(int_text(beta(41)))",
]

INVALID_SOURCES = [
    ("missing_else", "fn f() -> Int { if true { return 1 } }"),
    ("unterminated_brace", "fn f() -> Int { return 1"),
    ("garbage_character", "fn f() -> Int { return 1 % 2 }"),
    ("truncated_union", "type X = A(Int) |"),
]


def nodes_of(walk_result):
    return [harness.normalise(node) for node in walk_result["nodes"]]


def prepare(session):
    """Open the bundle and register the three parser tools (no budget changes)."""
    room = session.send({"schemaVersion": 3, "op": "open",
                        "name": "tb-parser-bundle",
                        "source": harness.LEXER.read_text(encoding="utf-8") + "\n"
                                  + harness.PARSER.read_text(encoding="utf-8"),
                        "metadataOnly": True})
    if room.get("outcome") != "ok" or room.get("status") != "valid":
        raise RuntimeError("bundle open failed: %s" % str(room)[:300])
    tool_document, tool_revision = room["document"], room["revision"]
    empty = session.send({"schemaVersion": 3, "op": "open_bytes",
                          "name": "empty", "bytes": []})
    empty_doc, empty_rev = empty["document"], empty["revision"]
    semantic = (empty_doc, empty_rev)
    harness.register(session, "tb-parser-start", "parser_start", [],
                     a12.parser_cursor_value(empty_doc, empty_rev),
                     tool_document, tool_revision, semantic)
    finished = a12.parser_cursor_value(empty_doc, empty_rev, done=True,
                                       lex_done=True, lex_stage="done")
    harness.register(session, "tb-parser-step", "parser_step", [finished],
                     a12.parser_chunk_value(empty_doc, empty_rev, finished),
                     tool_document, tool_revision, semantic)
    return tool_document, tool_revision


def main():
    harness.BUILD.mkdir(parents=True, exist_ok=True)
    session = harness.Session()
    violations = 0
    try:
        prepare(session)

        # ---- 1. CRLF equivalence ----------------------------------------
        lf_source = "\n".join(BASE_LINES) + "\n"
        crlf_source = "\r\n".join(BASE_LINES) + "\r\n"
        lf_doc, lf_rev = harness.open_source(session, "tb-lf", lf_source)
        crlf_doc, crlf_rev = harness.open_source(session, "tb-crlf", crlf_source)
        lf = harness.walk(session, lf_doc, lf_rev)
        crlf = harness.walk(session, crlf_doc, crlf_rev)
        if "error" in lf or "error" in crlf:
            print("HARNESS-ERROR CRLF walk failed: %s / %s" % (
                str(lf.get("error"))[:200], str(crlf.get("error"))[:200]))
            return 2
        lf_nodes, crlf_nodes = nodes_of(lf), nodes_of(crlf)
        problems = []
        if len(lf_nodes) != len(crlf_nodes):
            problems.append("node counts differ: %d vs %d" % (len(lf_nodes), len(crlf_nodes)))
        else:
            for left, right in zip(lf_nodes, crlf_nodes):
                if left.get("kind") != right.get("kind") or left.get("text") != right.get("text"):
                    problems.append("structure differs at id %s" % left.get("id"))
                    break
                if left.get("line") != right.get("line") \
                        or left.get("column") != right.get("column"):
                    problems.append("line/column differ at id %s: %s vs %s" % (
                        left.get("id"),
                        (left.get("line"), left.get("column")),
                        (right.get("line"), right.get("column"))))
                    break
                expected_shift = (left.get("line") or 1) - 1
                actual_shift = right.get("startByte") - left.get("startByte")
                if actual_shift != expected_shift:
                    problems.append("id %s shifts %d bytes, expected %d (one CR per prior line)" % (
                        left.get("id"), actual_shift, expected_shift))
                    break
        ok = not problems
        harness.report("crlf-span-equivalence",
                       "same nodes; extents shift by exactly one byte per prior line",
                       "lf=%d crlf=%d problems=%d" % (
                           len(lf_nodes), len(crlf_nodes), len(problems)), ok, problems[:2])
        violations += 0 if ok else 1

        # ---- 2. UTF-8 byte extents --------------------------------------
        unicode_source = 'fn main() -> Unit { return say("héllo ☃") }\n'
        uni_doc, uni_rev = harness.open_source(session, "tb-unicode", unicode_source)
        uni = harness.walk(session, uni_doc, uni_rev)
        if "error" in uni:
            print("HARNESS-ERROR unicode walk failed: %s" % str(uni["error"])[:300])
            return 2
        raw = unicode_source.encode("utf-8")
        literal_nodes = [harness.normalise(node) for node in uni["nodes"]
                         if harness.normalise(node).get("kind") in ("string", "str", "literal")]
        problems, checked = [], 0
        for node in literal_nodes:
            start, end = node.get("startByte"), node.get("endByte")
            if start is None or end is None:
                continue
            checked += 1
            if end > len(raw):
                problems.append("extent %s..%s beyond %d bytes" % (start, end, len(raw)))
                continue
            try:
                slice_text = raw[start:end].decode("utf-8")
            except UnicodeDecodeError as exc:
                problems.append("extent %s..%s is not a UTF-8 boundary: %s" % (start, end, exc))
                continue
            if "☃" in slice_text or "héllo" in slice_text:
                continue
            problems.append("slice %r does not contain the literal" % slice_text[:40])
        ok = checked > 0 and not problems
        harness.report("utf8-byte-extents",
                       "a multibyte literal yields a decodable byte slice",
                       "nodes=%d literal_nodes=%d checked=%d problems=%d byte_len=%d" % (
                           len(uni["nodes"]), len(literal_nodes), checked,
                           len(problems), len(raw)), ok,
                       problems[:2] if problems else ("no literal node found" if checked == 0 else ""))
        violations += 0 if ok else 1

        # ---- 3. invalid input must not complete --------------------------
        problems = []
        observed = []
        for name, source in INVALID_SOURCES:
            doc, rev = harness.open_source(session, "tb-%s" % name, source)
            result = harness.walk(session, doc, rev)
            if "error" in result:
                problems.append("%s: walk failed %s" % (name, str(result["error"])[:80]))
                continue
            final = result["final"] or {}
            observed.append("%s=%s/%s" % (name, final.get("status"), final.get("code")))
            if final.get("status") == "complete":
                problems.append("%s reported complete" % name)
            if not final.get("code"):
                problems.append("%s reported no error code" % name)
        ok = not problems
        harness.report("invalid-input-truthfulness",
                       "every malformed source ends non-complete with an error code",
                       "; ".join(observed), ok, problems[:3])
        violations += 0 if ok else 1

        # ---- 4. growth scaling ------------------------------------------
        measurements, problems = [], []
        for count in (1, 2, 3, 4):
            lines = ["fn f%d(x: Int) -> Int { return x + %d }" % (i, i) for i in range(count)]
            lines.append("fn main() -> Int { return f0(1) }")
            source = "\n".join(lines) + "\n"
            doc, rev = harness.open_source(session, "tb-grow-%d" % count, source)
            result = harness.walk(session, doc, rev)
            if "error" in result:
                problems.append("count=%d walk failed" % count)
                continue
            final = result["final"] or {}
            measurements.append((count, result["steps"], len(result["nodes"]),
                                 result["budget_hit"], final.get("status")))
            if result["budget_hit"]:
                problems.append("count=%d hit the step budget" % count)
            if final.get("status") != "complete":
                problems.append("count=%d did not complete (%s)" % (count, final.get("status")))
        steps = [row[1] for row in measurements]
        monotonic = all(after >= before for before, after in zip(steps, steps[1:])) if steps else False
        if not monotonic:
            problems.append("step counts are not monotonic: %s" % steps)
        ok = bool(measurements) and not problems
        harness.report("growth-scaling",
                       "growing compositions complete without hitting the budget",
                       "count/steps/nodes=%s" % ", ".join(
                           "%d/%d/%d" % (c, s, n) for c, s, n, _b, _st in measurements),
                       ok, problems[:3])
        violations += 0 if ok else 1

        print("SUMMARY attacks=4 violated=%d" % violations)
    finally:
        session.close()
    return 0 if violations == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
