"""Full bound-chain cost map for lexer_step (36 statements) and make_cursor.

Unlike chain()/pipeline probes, does NOT stop at the first failing unit: every
top-level statement group is invoked with an empty pool, so the complete
pass/fail/step map is recorded for the priced staged-descent mechanism
(A1 receipt BOOT-A1-20261106-012/013 pricing section). Read-only measurement.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from tests import test_chained_bindings as chained


def full_map(t, name):
    rows = []
    statements = t.index.statement_children(t.table[name])
    for position in range(len(statements)):
        try:
            chunk, _terminal = t.statement_chunk(name, position)
            report, codes = t.invoke(name, chunk, False, [])
        except RuntimeError as error:
            rows.append({"position": position, "status": "transport-refusal",
                         "detail": str(error)[:80]})
            continue
        if report is not None and report["status"]["value"] == "valid" and not codes:
            rows.append({"position": position, "status": "valid"})
        else:
            status = report["status"]["value"] if report else "error"
            rows.append({"position": position, "status": status,
                         "codes": sorted(set(codes))[:2]})
    return rows


def main():
    chained.ChainedBindingTests.setUpClass()
    try:
        t = chained.ChainedBindingTests(
            "test_utf8_check_is_fully_covered_by_chained_units")
        result = {}
        for name in ("lexer_step", "make_cursor"):
            rows = full_map(t, name)
            valid = sum(1 for r in rows if r["status"] == "valid")
            result[name] = {"statements": len(rows), "valid": valid,
                            "failing": [r for r in rows if r["status"] != "valid"]}
            print(f"{name}: {valid}/{len(rows)} statement groups valid; "
                  f"failing positions: "
                  f"{[r['position'] for r in result[name]['failing']]}")
        out = ROOT / "_build" / "lexerstep_fullmap.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {out}")
    finally:
        chained.TypedChunkTeardown = None
    return 0


if __name__ == "__main__":
    sys.exit(main())
