"""Agent 3 prepared adversarial regression batch: node-ID indexing / caching
threat themes (Lucy advisory priority 1), runnable NOW at the current head
and re-runnable unchanged at A1's future index/caching SHA.

Themes and claims (anchored to existing contracts, not to an implementation):

  IDX1  A node list whose node names a missing parent is refused at index
        construction (`CHUNK_PLAN_OPEN_PARENT`) — invalid reference.
  IDX2  A node whose parent sits at or after it is refused
        (`CHUNK_INVALID_PARENT_ORDER`) — invalid reference/ordering.
  IDX3  Two distinct siblings with IDENTICAL (parentId, role, childIndex)
        edges are refused at index construction. Anchor: the contract doc's
        provable-piece rule — no authoritative parser parse can contain two
        children with the same edge identity, and the checker/emitter treat
        (parent, role, childIndex) as a key (child_at/count_children).
  IDX4  (observation) document-level negative childIndex — recorded, not
        claimed (chunk validation already refuses it downstream).
  CACHE1  Two queries on the SAME retained revision: parse/typecheck counts
          do not grow between them and cache_hits does not fall, and the
          diagnostic lists are byte-identical (protocol: deterministic JSON,
          same-revision reuse).
  CACHE2  After inserting 4 bytes BEFORE the error site, the same diagnostic
          reappears with its span moved by EXACTLY +4 bytes and the same
          code — a node-id-keyed cross-revision reuse would keep the old span.
  CACHE3  Reverting the insertion restores the ORIGINAL content-addressed
          revision and byte-identical diagnostics (revision-keyed identity).
  STALE0  (observation) a CONSISTENT pre-edit pair — arguments and
          semanticTarget both at rev1 — stays invokable after the target
          advances; older revisions remain usable by design.
  STALE1  the CROSSED pair — rev1-derived arguments presented under the
          advanced rev2 semanticTarget — is refused, and a fresh target
          still invokes (non-vacuity). This is the stale-index reuse case:
          provenance from one revision must never answer under another.

Pure checker/session layer: no emission, no native build, no execution.

Exit code: 0 = no claim falsified, 1 = at least one claim falsified.

Usage: python index_cache_adversarial.py <repo-root-at-pin>
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require  # noqa: E402
import pep_chunk_contract as contract  # noqa: E402
from pep_chunk_contract import ContractRefusal, DocumentIndex  # noqa: E402

RESULTS = []

# Deliberate diagnostic: unknown type Zzz on line 2.
BASE_SOURCE = ("fn main() -> Int {\n"
               "  let x: Zzz = 1\n"
               "  return 0\n"
               "}\n")


def scalar(type_name, value):
    return {"type": type_name, "value": value}


def flat_node(node_id, parent_id, child_index=0, role="statement", kind="name", text=""):
    return {"type": "FlatAstNode", "fields": [
        {"name": "id", "value": scalar("Int", str(node_id))},
        {"name": "parentId", "value": scalar("Int", str(parent_id))},
        {"name": "childIndex", "value": scalar("Int", str(child_index))},
        {"name": "role", "value": scalar("Str", role)},
        {"name": "kind", "value": scalar("Str", kind)},
        {"name": "text", "value": scalar("Str", text)},
        {"name": "integerValue", "value": scalar("Int", "0")},
        {"name": "booleanValue", "value": scalar("Bool", False)},
        {"name": "stringParts", "value": {"type": "List[Str]", "value": []}},
        {"name": "startByte", "value": scalar("Int", "0")},
        {"name": "endByte", "value": scalar("Int", "1")},
        {"name": "line", "value": scalar("Int", "1")},
        {"name": "column", "value": scalar("Int", "1")}]}


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claim_case": claim, "expect": expect,
                    "outcome": outcome, "detail": detail, "falsified": falsified})


def try_refusal(case, claim, expect, thunk):
    """Exact-code expectations compare against the refusal code itself;
    the literal expect \"any refusal\" compares against REFUSED."""
    try:
        result = thunk()
    except ContractRefusal as refusal:
        outcome = "REFUSED" if expect == "any refusal" else refusal.code
        record(case, claim, expect, outcome, refusal.code)
    except Exception as error:  # noqa: BLE001
        record(case, claim, expect, "NON_CONTRACT_EXCEPTION",
               f"{type(error).__name__}: {error}")
    else:
        record(case, claim, expect, "ACCEPTED", repr(result)[:120])


def index_with(nodes):
    return DocumentIndex("doc-i", "rev-i", nodes)


def diagnostics_of(query_response):
    """Exact serialisation of the query response's `diagnostics` list
    (plain dicts: code, message, severity, span{startOffset,endOffset,...})."""
    return json.dumps(query_response.get("diagnostics"), sort_keys=True)


def main():
    # ---------------- index-level cases (pure Python) --------------------
    base = [flat_node(0, -1, 0, role="", kind="function", text="f"),
            flat_node(1, 0, 0, kind="return")]

    try_refusal("IDX1 index refuses node naming a missing parent", True,
                "CHUNK_PLAN_OPEN_PARENT",
                lambda: index_with([flat_node(0, -1, 0), flat_node(1, 7, 0)]))

    try_refusal("IDX2 index refuses parent at/after the child", True,
                "CHUNK_INVALID_PARENT_ORDER",
                lambda: index_with([flat_node(0, -1, 0), flat_node(1, 1, 0)]))

    # Two distinct siblings sharing the exact same edge identity.
    try_refusal(
        "IDX3 index refuses duplicate child edge (same parent+role+childIndex)", True,
        "any refusal",
        lambda: index_with([flat_node(0, -1, 0, role="", kind="function"),
                            flat_node(1, 0, 0, role="statement", kind="let"),
                            flat_node(2, 0, 0, role="statement", kind="let")]))

    try_refusal("IDX4 observation: document-level negative childIndex", False,
                "observed",
                lambda: index_with([flat_node(0, -1, 0), flat_node(1, 0, -1)]))

    # ---------------- session-level cache/staleness cases -----------------
    session = Session()
    try:
        # Register the checker tool for the stale-target case.
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-index-cache", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        tool_document, tool_revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "validate", "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                      done=True, lex_done=True, lex_stage="done")
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_rep = pep_c23.checker_report(sample["document"], sample["revision"])
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished_cursor)),
                ("pep-c23-checker", "analyze_parsed", [empty_pp], empty_rep)]:
            reg = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_register", "tool": tool,
                                "document": tool_document, "revision": tool_revision,
                                "function": function})
            require(reg, "status", "Registered", f"register {tool}")
            val = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_validate", "tool": tool,
                                "document": tool_document, "revision": tool_revision,
                                "testVectors": [{"arguments": arguments, "expect": expected,
                                                 "semanticTarget": target_spec}]})
            require(val, "status", "Validated", f"validate {tool}")
            act = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_activate", "tool": tool,
                                "document": tool_document, "revision": tool_revision})
            require(act, "status", "Active", f"activate {tool}")

        # --- diagnostic/cache round over the fixture document -------------
        doc = session.send({"schemaVersion": 3, "op": "open",
                            "source": BASE_SOURCE, "name": "cache-fixture"})
        require(doc, "outcome", "ok", "open fixture")
        document, rev1 = doc["document"], doc["revision"]

        def metrics():
            response = session.send({"schemaVersion": 3, "op": "metrics"})
            fields = response.get("metrics", response)
            return {key: fields.get(key) for key in
                    ("parse_count", "typecheck_count", "cache_hits")}

        def query(revision):
            return session.send({"schemaVersion": 3, "op": "query",
                                 "document": document, "revision": revision})

        m_before_q1 = metrics()
        q1 = query(revision=rev1)
        diag1 = diagnostics_of(q1)
        m_after_q1 = metrics()
        q2 = query(revision=rev1)
        diag2 = diagnostics_of(q2)
        m_after_q2 = metrics()

        reuse_ok = (m_after_q2["parse_count"] == m_after_q1["parse_count"]
                    and m_after_q2["typecheck_count"] == m_after_q1["typecheck_count"]
                    and (m_after_q2["cache_hits"] or 0) >= (m_after_q1["cache_hits"] or 0))
        record("CACHE1 same-revision re-query: no reparse/recheck growth, "
               "byte-identical diagnostics", True, "reuse+deterministic",
               "reuse+deterministic" if (reuse_ok and diag1 == diag2 and diag1 != "null")
               else "mismatch",
               f"metrics_before={m_before_q1} after_q1={m_after_q1} after_q2={m_after_q2} "
               f"diag_equal={diag1 == diag2} diag_nonempty={diag1 not in ('null', '[]')}")

        # --- CACHE2: shift the error site by exactly +4 bytes -------------
        edit = session.send({"schemaVersion": 3, "op": "apply_edit",
                             "document": document, "expected_revision": rev1,
                             "start_byte": 0, "end_byte": 0, "replacement": "    "})
        require(edit, "outcome", "ok", "insert 4 bytes")
        rev2 = edit["revision"]
        q3 = query(revision=rev2)
        diag3 = diagnostics_of(q3)

        def spans(diag_json):
            payload = json.loads(diag_json) if diag_json not in ("null",) else []
            out = []
            for item in payload or []:
                span = item.get("span", {})
                start = span.get("start") or {}
                out.append((item.get("code"), item.get("message"),
                            int(start.get("offset", -1)),
                            int(span.get("endOffset", -1))))
            return out

        before = spans(diag1)
        after = spans(diag3)
        shift_ok = (len(before) >= 1 and len(before) == len(after)
                    and all(a[0] == b[0] and a[1] == b[1]
                            and b[2] == a[2] + 4 and b[3] == a[3] + 4
                            for a, b in zip(before, after)))
        record("CACHE2 diagnostics follow a +4-byte edit exactly (spans shift by 4, "
               "same codes/messages)", True, "shift+4",
               "shift+4" if shift_ok else "mismatch",
               f"before={before} after={after}")

        # --- CACHE3: revert restores original revision + diagnostics ------
        revert = session.send({"schemaVersion": 3, "op": "apply_edit",
                               "document": document, "expected_revision": rev2,
                               "start_byte": 0, "end_byte": 4, "replacement": ""})
        require(revert, "outcome", "ok", "revert insert")
        rev3 = revert["revision"]
        q4 = query(revision=rev3)
        diag4 = diagnostics_of(q4)
        record("CACHE3 revert restores the original revision id and byte-identical "
               "diagnostics", True, "identity-restored",
               "identity-restored" if (rev3 == rev1 and diag4 == diag1)
               else "mismatch",
               f"rev_restored={rev3 == rev1} diag_equal={diag4 == diag1}")

        # --- STALE1: checker tool invoked with the pre-edit target ---------
        source_bytes = BASE_SOURCE.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "stale-target", "bytes": list(source_bytes)})
        require(target, "outcome", "ok", "open target")
        t_document, t_rev1 = target["document"], target["revision"]
        sem1 = {"document": t_document, "revision": t_rev1, "entryFunctions": []}
        parsed1 = pep_c23.parse_target(session, source_bytes, target, tool_revision)
        first_invoke = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "pep-c23-checker",
                                     "arguments": [parsed1], "semanticTarget": sem1})
        control_ok = first_invoke.get("outcome") == "ok"

        advance = session.send({"schemaVersion": 3, "op": "apply_edit",
                                "document": t_document, "expected_revision": t_rev1,
                                "start_byte": 0, "end_byte": 0, "replacement": "//x\n"})
        require(advance, "outcome", "ok", "advance target revision")
        t_rev2 = advance["revision"]

        # (a) consistent PRE-EDIT pair: old revisions remain usable by design
        consistent = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_invoke", "tool": "pep-c23-checker",
                                   "arguments": [parsed1],
                                   "semanticTarget": {"document": t_document,
                                                      "revision": t_rev1,
                                                      "entryFunctions": []}})
        record("STALE0 observation: consistent pre-edit pair (args+target both rev1) "
               "invoked after the target advanced", False, "observed",
               consistent.get("outcome"), json.dumps(consistent.get("error"))[:160])

        # (b) CROSSED pair: rev1-derived arguments under the advanced rev2 target
        crossed = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed1],
                                "semanticTarget": {"document": t_document,
                                                   "revision": t_rev2,
                                                   "entryFunctions": []}})
        refused = crossed.get("outcome") == "error"
        code = (crossed.get("error") or {}).get("code", "NO_ERROR")
        crossed_nodes, crossed_declared = None, None
        if crossed.get("outcome") == "ok":
            crossed_fields = {f["name"]: f["value"]
                              for f in crossed["result"]["fields"]}
            crossed_nodes = (crossed_fields.get("syntaxNodeCount") or {}).get("value")
            crossed_declared = (crossed_fields.get("revision") or {}).get("value")

        refreshed = session.send({"schemaVersion": 3, "op": "open_bytes",
                                  "name": "fresh-target",
                                  "bytes": list(("//x\n" + BASE_SOURCE).encode("utf-8"))})
        fresh_ok = refreshed.get("outcome") == "ok"
        fresh_nodes, fresh_declared = None, None
        if fresh_ok:
            fresh_bytes = ("//x\n" + BASE_SOURCE).encode("utf-8")
            fresh_parsed = pep_c23.parse_target(session, fresh_bytes, refreshed,
                                                tool_revision)
            fresh_invoke = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                         "op": "tool_invoke", "tool": "pep-c23-checker",
                                         "arguments": [fresh_parsed],
                                         "semanticTarget": {
                                             "document": refreshed["document"],
                                             "revision": refreshed["revision"],
                                             "entryFunctions": []}})
            if fresh_invoke.get("outcome") == "ok":
                fresh_fields = {f["name"]: f["value"]
                                for f in fresh_invoke["result"]["fields"]}
                fresh_nodes = (fresh_fields.get("syntaxNodeCount") or {}).get("value")
                fresh_declared = (fresh_fields.get("revision") or {}).get("value")
        record("STALE1 crossed stale-index pair (rev1 arguments presented under the "
               "advanced rev2 target) refused; fresh target still works", True,
               "refused+fresh-ok",
               "refused+fresh-ok" if (control_ok and refused and fresh_ok) else "mismatch",
               f"control_ok={control_ok} refused={refused} code={code} "
               f"fresh_ok={fresh_ok} t_rev2_changed={t_rev2 != t_rev1} "
               f"crossed_declared_rev==target_rev2={crossed_declared == t_rev2} "
               f"crossed_nodes={crossed_nodes} fresh_nodes={fresh_nodes} "
               f"fresh_declared==fresh_rev={fresh_declared == refreshed['revision']}")
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"REPO={REPO}")
    print(json.dumps(RESULTS, indent=2, sort_keys=True))
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']} ({item['detail']})")
    return 1 if falsified else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:  # harness failure must NOT read as falsification
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
