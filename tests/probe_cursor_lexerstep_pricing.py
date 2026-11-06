"""Measured pricing notes for make_cursor / lexer_step (BOOT-A1-011 section 5).

One-shot read-only probe on the existing chained harness:
  1. make_cursor: count its top-level statements (predicted 1 - a single return),
     and re-run the bound group to re-record the refusal code/step state.
  2. lexer_step: take bounded_units' one-level interior unit for its largest
     statement (label statement[1].body[0]) and invoke it - the prediction is a
     transport refusal because the unit keeps all sibling statements.
No budgets changed; a refusal here is a measurement.
Usage: python tests/probe_cursor_lexerstep_pricing.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from chunk_helper import fields_map  # noqa: E402
from tests import test_chained_bindings as chained  # noqa: E402


def main():
    chained.ChainedBindingTests.setUpClass()
    t = chained.ChainedBindingTests(
        "test_utf8_check_is_fully_covered_by_chained_units")
    rows = {}
    for name in ("make_cursor", "lexer_step"):
        statements = t.index.statement_children(t.table[name])
        rows[name] = {"statements": len(statements)}
    # make_cursor: re-run its single bound group (the failure is the chunk itself)
    chunk, terminal = t.statement_chunk("make_cursor", 0)
    report, codes = t.invoke("make_cursor", chunk, terminal, [])
    rows["make_cursor"]["group0"] = (
        {"status": report["status"]["value"]}
        if report is not None else {"status": "error", "codes": codes})
    # lexer_step: bounded_units interior unit named statement[1].body[0]
    interior = None
    for label, ids, expect_returns in t.index.bounded_units(t.table["lexer_step"]):
        if label == "statement[1].body[0]":
            interior = (label, ids, expect_returns)
            break
    if interior is None:
        rows["lexer_step"]["interior"] = {"status": "no-interior-unit"}
    else:
        label, ids, expect_returns = interior
        allowed = t.index.fact_closure(ids, {s["name"] for s in t.sigs
                                             if s["name"] != "lexer_step"})
        ext = [s for s in t.sigs if s["name"] != "lexer_step"
               and s["name"] in allowed]
        from tests.chunk_helper import checked_fn_value, resolved_sig_value
        try:
            response = t.session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                 "tool": "bound-chunk",
                 "arguments": [
                     t.harness.sliced(t.parsed, ids),
                     {"type": "List[CheckedFunction]",
                      "value": [checked_fn_value(s) for s in ext] + t.host[0]},
                     {"type": "List[ResolvedSignature]",
                      "value": [resolved_sig_value(s) for s in ext] + t.host[1]},
                     {"type": "List[ResolvedTypeDecl]", "value": t.facts + t.host[2]},
                     {"type": "List[BindingFact]", "value": []},
                     {"type": "Bool", "value": expect_returns}],
                 "semanticTarget": t.sem})
            rep = fields_map(response.get("result", {}))
            rows["lexer_step"]["interior"] = {
                "status": rep.get("status", {}).get("value",
                        (response.get("error") or {}).get("code")),
                "nodes": len(ids)}
        except RuntimeError as error:
            rows["lexer_step"]["interior"] = {"status": "transport-refusal",
                                              "nodes": len(ids),
                                              "detail": str(error)[:100]}
    print(json.dumps(rows, indent=2))
    out = ROOT / "_build" / "pricing_cursor_lexerstep.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    chained.TypedChunkTeardown = chained_tear_down()
    return 0


def chained_tear_down():
    from tests import test_chunk_typed as typed_probe
    return typed_probe.TypedChunkTests.tearDownClass()


if __name__ == "__main__":
    sys.exit(main())
