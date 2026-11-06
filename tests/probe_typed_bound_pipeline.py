"""A1 typed-bound pipeline trial: does chained statement-group checking close
the hot lexer functions in the canonical staged pipeline?

Read-only measurement on the existing checker machinery (slice-4b/4c lineage).
Per target function, in order:
  1. body-only TYPED chunk (`analyze_chunk_typed`) scoped via `fact_closure`
     (the production pattern per the landscape pins) with host facts where the
     body needs `semantic_snapshot` — if valid, the function is COVERED
     without decomposition;
  2. otherwise the BOUND statement-group chain (`analyze_chunk_typed_bound`,
     the `bound-chunk` tool) with `contract.BindingPool` scoped/same-revision
     carried facts — COVERED only if every top-level statement group checks
     `valid` with zero diagnostics and the group count equals the statement
     count (totality);
  3. per-invocation steps via the READ-ONLY `metrics.last_execute_steps`
     counter (3ff3bf1 commitments), transport refusals recorded as
     measurements, never crashes.

Budgets unchanged; no source, no diagnostics, no caps touched. Usage:
  python tests/probe_typed_bound_pipeline.py [--out _build/typed_bound.json]
"""
import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import pep_chunk_contract as contract
from chunk_helper import fields_map
from tests import test_chunk_typed as typed_probe
from tests import test_chained_bindings as chained

TARGETS = ["lexer_start", "make_progress", "make_cursor", "utf8_check", "lexer_step"]


def metrics_steps(session):
    return session.send({"schemaVersion": 3, "op": "metrics"}).get(
        "metrics", {}).get("last_execute_steps")


def body_only(harness, raw, name, host_names, scope=True):
    try:
        status, diags = harness.check_body_with_facts(
            raw, "pipeline-" + name, name, host_builtin_names=host_names,
            scope_facts=scope, allow_error=True, expect_returns=True)
    except AssertionError as error:
        return {"status": "harness-assert", "detail": str(error)[:120], "steps": None}
    except RuntimeError as error:
        # The 1 MiB per-message cap binding is a measurement, not a crash.
        return {"status": "transport-refusal", "detail": str(error)[:100], "steps": None}
    return {"status": status, "diagnostics": len(diags),
            "steps": metrics_steps(harness.session) if harness.session else None}


def chain(t, name):
    pool = contract.BindingPool(t.sem["document"], t.sem["revision"])
    statements = t.index.statement_children(t.table[name])
    total = len(statements)
    groups, accepted, first_fail = [], 0, None
    for position in range(total):
        chunk, terminal = t.statement_chunk(name, position)
        try:
            report, codes = t.invoke(name, chunk, terminal, pool.facts())
        except RuntimeError as error:
            groups.append({"position": position, "status": "transport-refusal",
                           "detail": str(error)[:100]})
            first_fail = first_fail if first_fail is not None else position
            break
        steps = metrics_steps(t.session)
        if report is not None and report["status"]["value"] == "valid" and not codes:
            accepted += 1
            pool.add(report["bindings"]["value"])
            groups.append({"position": position, "status": "valid", "steps": steps,
                           "bindings_carried": len(pool.facts())})
        else:
            status = report["status"]["value"] if report else "error"
            groups.append({"position": position, "status": status,
                           "codes": sorted(set(codes))[:3], "steps": steps})
            first_fail = first_fail if first_fail is not None else position
            break
    covered = accepted == total and first_fail is None
    return {"statements": total, "accepted": accepted, "covered": covered,
            "first_fail": first_fail, "groups": groups}


def main():
    argv = sys.argv[1:]
    out_path = ROOT / "_build" / "typed_bound.json"
    if "--out" in argv:
        i = argv.index("--out")
        out_path = pathlib.Path(argv[i + 1])

    chained.ChainedBindingTests.setUpClass()
    t = chained.ChainedBindingTests(
        "test_utf8_check_is_fully_covered_by_chained_units")
    t.setUpClass() if False else None  # classmethod handles shared state
    harness = t.harness
    raw = t.raw
    rows = {}
    for name in TARGETS:
        host_names = ("semantic_snapshot",) if name in ("lexer_start",) else ()
        row = {"body_typed_scope": body_only(harness, raw, name, host_names, True),
               "body_typed_unscope": body_only(harness, raw, name, host_names, False)}
        if (row["body_typed_scope"].get("status") == "valid"
                or row["body_typed_unscope"].get("status") == "valid"):
            row["verdict"] = "COVERED-CHUNK (body-only typed chunk)"
            row["chain"] = None
        else:
            row["chain"] = chain(t, name)
            row["verdict"] = ("COVERED-BOUND (statement groups, bindings carried)"
                              if row["chain"]["covered"]
                              else f"NOT-COVERED (first fail at group {row['chain']['first_fail']})")
        rows[name] = row
        print(f"{name:14s} {row['verdict']}")

    result = {"targets": targets_from(rows), "rows": rows}
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    chained.TypedChunkTeardown = typed_probe.TypedChunkTests.tearDownClass()
    print(f"wrote {out_path}")
    return 0


def targets_from(rows):
    return list(rows.keys())


if __name__ == "__main__":
    sys.exit(main())
