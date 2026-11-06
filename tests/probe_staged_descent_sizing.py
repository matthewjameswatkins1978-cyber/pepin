"""Sizing for the priced staged-descent mechanism (BOOT-A1-20261106-015).

For every lexer_step statement group: node count of the statement subtree and
per-invocation checker steps (read-only metrics counter), continued past
failures. Also make_cursor's single statement. Output drives the sub-statement
carving design with exact budget arithmetic.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from tests import test_chained_bindings as chained


def stmt_node_counts(t, name):
    counts = {}
    for pos, stmt_id in enumerate(t.index.statement_children(t.table[name])):
        counts[pos] = len(t.index.subtree(stmt_id))
    return counts


def full_map(t, name):
    counts = stmt_node_counts(t, name)
    rows = []
    for position in range(len(counts)):
        try:
            chunk, _terminal = t.statement_chunk(name, position)
            report, codes = t.invoke(name, chunk, False, [])
            steps = t.session.send({"schemaVersion": 3, "op": "metrics"}).get(
                "metrics", {}).get("last_execute_steps")
        except RuntimeError as error:
            rows.append({"position": position, "nodes": counts[position],
                         "status": "transport-refusal", "steps": None,
                         "detail": str(error)[:60]})
            continue
        status = (report["status"]["value"] if report is not None else "error")
        rows.append({"position": position, "nodes": counts[position],
                     "status": status, "steps": steps,
                     "codes": sorted(set(codes))[:2]})
    return {"statementNodeCounts": counts, "rows": rows}


def main():
    chained.ChainedBindingTests.setUpClass()
    try:
        t = chained.ChainedBindingTests(
            "test_utf8_check_is_fully_covered_by_chained_units")
        result = {}
        for name in ("lexer_step", "make_cursor"):
            result[name] = full_map(t, name)
            rows = result[name]["rows"]
            print(f"{name}:")
            for r in rows:
                if r["status"] != "valid":
                    print(f"  pos {r['position']:3d} nodes={r['nodes']:5d} "
                          f"{r['status']} steps={r['steps']} {r.get('codes', '')}")
        out = ROOT / "_build" / "staged_descent_sizing.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {out}")
    finally:
        chained.TypedChunkTeardown = None
    return 0


if __name__ == "__main__":
    sys.exit(main())
