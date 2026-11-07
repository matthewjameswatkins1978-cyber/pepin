"""A3 BOOT-A3-036: is A1's new `shared_spine` admission rule sound?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-036-SHARED-SPINE.md @ 983dfdd,
committed before this probe existed or ran.

Target: `pep_chunk_contract.plan_ids(..., shared_spine=...)` as added by A1 `231caf1`. Before it, a
node could repeat across chunks only inside a declared *shared root* (which carries its subtree); now
a bare spine id may repeat with no subtree attached. This is the critical path of the only proposed
remedy to the capacity blocker, and A3 has not tested it.

Structure proven here: `parent-in-chunk` forces a function node into EVERY window containing any of
its descendants, so a sub-function split necessarily shares the ancestor chain — which is why the spine exists.

Read-only: A3 implements nothing in the contract, A1's code is not modified.

Run: python verification/probes/shared_spine_036.py [--json]
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

PROBE_ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOT = pathlib.Path(os.environ.get("PEPIN_GATE_ROOT") or PROBE_ROOT).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402

APP_REL = "examples/dogfood/pepin-source-scan.pep"
APP_REV = "12e143f"
APP_BLOB = "4a44dd653e949258a196d247097197d7c24c1da7"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


class Gate:
    def __init__(self):
        self.rows = []

    def row(self, name, ok, detail):
        self.rows.append({"check": name, "ok": bool(ok), "detail": detail})


def main():
    as_json = "--json" in sys.argv
    gate = Gate()
    contract = __import__("pep_chunk_contract")
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")

    app = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", f"{APP_REV}:{APP_REL}"],
                         capture_output=True, check=False).stdout
    gate.row("app:pinned", len(app) == 1159,
             f"{len(app)} B (frozen app; blob expected {APP_BLOB[:8]})")

    session = Session()
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        require(opened, "status", "valid", "check bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "validate",
                               "bytes": []})
        pic.register(session, document, revision, sample["document"], sample["revision"])
        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "spine-036",
                               "bytes": list(app)})
        require(target, "outcome", "ok", "open app")
        parsed = parse_target(session, app, target, revision)
    finally:
        session.close()

    index = contract.DocumentIndex.from_parsed(parsed)
    nodes = fm(parsed)["nodes"]["value"]
    functions = {helper.nval(n, "text"): int(helper.nval(n, "id"))
                 for n in nodes if helper.nval(n, "kind") == "function"}
    gate.row("index:functions", set(functions) == {"ascii_letter", "ascii_digit",
                                                  "ascii_continue", "main"},
             f"{sorted(functions)} ids={functions}")

    def subtree_ids(node_id):
        return sorted(int(x) for x in index.subtree(node_id))

    whole = {name: subtree_ids(nid) for name, nid in functions.items()}
    main_id = functions["main"]

    # ---- baseline: whole-function chunks (the shape A3 already gates) --------
    plan = contract.plan_ids(index, list(whole.values()))
    covered = set().union(*[set(ids) for ids in plan.chunk_ids])
    gate.row("S0:baseline-accepted", True,
             f"{len(plan.chunk_ids)} chunks, {sum(len(c) for c in plan.chunk_ids)} ids, "
             f"covers {len(covered)}/{len(index.ids)} document nodes")

    # ---- honest two-window split of main, spine = the function node ---------
    children = sorted({int(nid) for nid in index.parents
                       if index.parents[nid] == main_id})
    gate.row("S1:main-has-children", len(children) >= 2,
             f"main id={main_id} direct children={children}")
    if len(children) < 2:
        _report(gate, as_json)
        return 1
    half = len(children) // 2
    group_a, group_b = children[:half], children[half:]

    def window(group):
        ids = {main_id}
        for child in group:
            ids.update(int(x) for x in index.subtree(child))
        return sorted(ids)

    win_a, win_b = window(group_a), window(group_b)
    others = [ids for name, ids in whole.items() if name != "main"]
    chunks = others + [win_a, win_b]

    split = contract.plan_ids(index, chunks, shared_spine=[main_id])
    gate.row("S1:two-window-split-accepted", True,
             f"accepted with shared_spine=[{main_id}]; chunks={[len(c) for c in split.chunk_ids]}")

    covered = set().union(*[set(ids) for ids in split.chunk_ids])
    missing = [nid for nid in index.ids if nid not in covered]
    gate.row("S2:completeness-with-spine", not missing,
             f"covers {len(covered)}/{len(index.ids)} nodes, missing={missing[:5]}")

    counts = {}
    for ids in split.chunk_ids:
        for nid in ids:
            counts[nid] = counts.get(nid, 0) + 1
    duplicated = sorted(nid for nid, c in counts.items() if c > 1)
    gate.row("S4:only-spine-duplicates", duplicated == [main_id],
             f"nodes in >1 chunk: {duplicated} (declared spine was [{main_id}])")

    # ---- refusals preserved -------------------------------------------------
    def expect(name, code, fn):
        try:
            fn()
        except contract.ContractRefusal as refused:
            gate.row(name, getattr(refused, "code", str(refused)) == code,
                     f"{getattr(refused, 'code', refused)}: {refused}")
            return
        except Exception as error:                       # noqa: BLE001
            gate.row(name, False, f"unexpected {type(error).__name__}: {error}")
            return
        gate.row(name, False, f"ACCEPTED but expected {code}")

    def expect_any(name, fn):
        try:
            fn()
        except contract.ContractRefusal as refused:
            gate.row(name, True, f"refused with {getattr(refused, 'code', refused)}: {refused}")
            return
        except Exception as error:                       # noqa: BLE001
            gate.row(name, False, f"unexpected {type(error).__name__}: {error}")
            return
        gate.row(name, False, "ACCEPTED but expected a refusal")

    expect("S6a:undeclared-overlap-refused", "CHUNK_PLAN_OVERLAP",
           lambda: contract.plan_ids(index, others + [win_a, win_b], shared_spine=[]))
    expect("S6b:unknown-spine-refused", "CHUNK_UNKNOWN_NODE",
           lambda: contract.plan_ids(index, others + [win_a, win_b], shared_spine=[999999]))
    # A repeated id can never reach the overlap rule: the ascending-id check fires first.
    # Recorded as rule ORDERING, and the requirement is only that it refuses.
    expect_any("S6c:in-chunk-duplicate-refused",
               lambda: contract.plan_ids(index, others + [[win_a[0], win_a[0]], win_b]))
    expect("S6d:non-ascending-refused", "CHUNK_COVERAGE_MISMATCH",
           lambda: contract.plan_ids(index, others + [list(reversed(win_a)), win_b]))
    # incompleteness must be tested WITH the spine declared, otherwise overlap fires first
    unique_b = [nid for nid in win_b if nid not in win_a]
    expect("S7:incomplete-refused", "CHUNK_PLAN_INCOMPLETE",
           lambda: contract.plan_ids(index, others + [win_a, [x for x in win_b
                                                             if x != unique_b[-1]]],
                                     shared_spine=[main_id]))

    # ---- S8: the split the capacity fix actually needs — inside the loop ------
    # A top-level child split is lumpy (6 vs 39 ids) because the `while` is one child with a
    # large subtree. A real window must split inside the loop, sharing a deeper spine chain.
    biggest = max(children, key=lambda c: len(index.subtree(c)))
    big_size = len(index.subtree(biggest))
    inner = sorted({int(nid) for nid in index.parents if index.parents[nid] == biggest})
    gate.row("S8:loop-is-lumpy", big_size > 0 and len(inner) >= 2,
             f"largest child of main = {biggest} with {big_size} subtree nodes, "
             f"{len(inner)} inner children; a top-level split gave windows of "
             f"{len(win_a)} vs {len(win_b)} ids")
    if len(inner) >= 2:
        ih = len(inner) // 2
        rest = [c for c in children if c != biggest]
        def inner_window(group, include_rest):
            # window A must also carry main's OTHER children or those 9 nodes go uncovered
            ids = {main_id, biggest}
            if include_rest:
                for child in rest:
                    ids.update(int(x) for x in index.subtree(child))
            for child in group:
                ids.update(int(x) for x in index.subtree(child))
            return sorted(ids)
        iwa, iwb = inner_window(inner[:ih], True), inner_window(inner[ih:], False)
        deep = contract.plan_ids(index, others + [iwa, iwb], shared_spine=[main_id, biggest])
        counts2 = {}
        for ids in deep.chunk_ids:
            for nid in ids:
                counts2[nid] = counts2.get(nid, 0) + 1
        dupe2 = sorted(nid for nid, c in counts2.items() if c > 1)
        covered2 = set().union(*[set(ids) for ids in deep.chunk_ids])
        missing2 = [nid for nid in index.ids if nid not in covered2]
        gate.row("S8:deep-spine-accepted", not missing2 and dupe2 == [main_id, biggest],
                 f"windows={[len(iwa), len(iwb)]} covers={len(covered2)}/{len(index.ids)} "
                 f"duplicates={dupe2} expected=[{main_id}, {biggest}] missing={missing2[:3]}")

    # S5: a spine declaration must NOT excuse a missing parent inside a chunk
    without_main = [nid for nid in win_a if nid != main_id]
    expect("S5:spine-does-not-excuse-open-parent", "CHUNK_PLAN_OPEN_PARENT",
           lambda: contract.plan_ids(index, others + [without_main, win_b],
                                     shared_spine=[main_id]))

    _report(gate, as_json)
    return 0 if all(r["ok"] for r in gate.rows) else 1


def _report(gate, as_json):
    ok = all(r["ok"] for r in gate.rows)
    if as_json:
        print(json.dumps({"verdict": "SOUND" if ok else "DIVERGENCE",
                          "checks": gate.rows}, indent=2))
    else:
        for r in gate.rows:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']:<38} {r['detail']}")
        failed = [r["check"] for r in gate.rows if not r["ok"]]
        print(f"\n{len(gate.rows)} checks, {len(gate.rows) - len(failed)} passed")
        print("shared_spine admission:", "SOUND" if ok else f"DIVERGENCE {failed}")


if __name__ == "__main__":
    sys.exit(main())
