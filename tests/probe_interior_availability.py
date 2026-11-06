"""Interior-unit availability for the hard staged-descent shapes (A1 pricing).

Measured (2026-11-06, at codex/a1-typed-bound-pipeline@6d406cd lineage):
  lexer_step pos 4/5/6/10: kind=if_statement, body_parts=0  -> bounded_units
    interiors NOT available (then/else use a different role in the flat AST);
  lexer_step pos 32: kind=while, body_parts=1 -> the single-part "interior"
    unit equals the whole statement; carving 1,033 nodes requires RECURSIVE
    descent, not one-level interiors;
  make_cursor pos 0: kind=return, body_parts=0 -> no carving possible via
    interiors; expression-level extractor required.
Consequence: the staged-descent mechanism (draft receipt BOOT-A1-20261106-012
pricing) needs a NEW roles-aware recursive carver - existing bounded_units
interiors do not engage on any of the five hard shapes. Read-only probe over
the chained harness session.
"""
import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, './tests')
from chunk_helper import nval
from tests import test_chained_bindings as chained


def main():
    chained.ChainedBindingTests.setUpClass()
    try:
        t = chained.ChainedBindingTests(
            "test_utf8_check_is_fully_covered_by_chained_units")
        result = {}
        for name, positions in (("lexer_step", [4, 5, 6, 10, 32]),
                                ("make_cursor", [0])):
            fid = t.table[name]
            statements = t.index.statement_children(fid)
            by_id = {str(nval(n, "id")): n for n in t.nodes}
            rows = []
            for pos in positions:
                stmt_id = str(statements[pos])
                kind = nval(by_id[stmt_id], "kind")
                body_parts = t.index.block_children(statements[pos])
                rows.append({"position": pos, "kind": kind,
                             "body_parts": len(body_parts),
                             "interior_units_available": len(body_parts) > 0})
            result[name] = rows
            print(name, json.dumps(rows))
        out = ROOT_OUT = __import__("pathlib").Path(".") / "_build" / \
            "interior_availability.json"
        out.write_text(json.dumps(result, indent=1), encoding="utf-8")
        print("wrote", out)
        return 0
    finally:
        chained.TypedChunkTeardown = None


if __name__ == "__main__":
    sys.exit(main())
