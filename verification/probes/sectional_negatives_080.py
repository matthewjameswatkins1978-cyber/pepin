#!/usr/bin/env python3
"""A3-S3: adversarial probes of A1's sectional merge (verification/probes).

A1's `tests/test_a1_sectional_merge_negatives.py` pins six fail-closed channels:
empty groups, foreign document, stale revision, holes, out-of-span facts, plus a
valid control. I reproduce those independently here, then probe identity channels
A1's tests do not cover, because "document and revision match" is not the same as
"this fact is the fact it claims to be".

Read-only: imports A1's module, never writes to A1's lane.

  PEPIN_SECTIONAL_ROOT=<worktree at A1 tip>   (default: repo root)
"""
import copy
import importlib.util
import os
import pathlib
import sys

ROOT = pathlib.Path(os.environ.get("PEPIN_SECTIONAL_ROOT") or
                    pathlib.Path(__file__).resolve().parents[2]).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sectional = load("pep_sectional", ROOT / "pep_sectional.py")


def _field(ftype, value):
    return {"type": ftype, "value": value}


def _report(doc="doc1", rev="7", holes=None, calls=None, etypes=None, fns=None):
    return {
        "document": _field("Str", doc),
        "revision": _field("Int", rev),
        "holes": _field("List[HoleFact]", holes or []),
        "functions": _field("List[CheckedFunction]", fns or []),
        "calls": _field("List[ResolvedCall]", calls or []),
        "expressionTypes": _field("List[ExpressionTypeFact]", etypes or []),
    }


def _call(syntax_id, caller="1", callee="1"):
    """A realistic ResolvedCall.

    CORRECTED (BOOT-A3-090): the real record is
    `type ResolvedCall { callerId: Int, calleeId: Int, syntaxId: Int, startByte: Int,
    endByte: Int }` (tests/pep_checker_a13.pep:4). My first version emitted only
    `syntaxId`, which is not a valid ResolvedCall at all - so A1's new call-anchoring
    check correctly refused it. The instrument was wrong, not the code under audit.
    """
    return {"fields": [
        {"name": "callerId", "value": {"type": "Int", "value": str(caller)}},
        {"name": "calleeId", "value": {"type": "Int", "value": str(callee)}},
        {"name": "syntaxId", "value": {"type": "Int", "value": str(syntax_id)}},
        {"name": "startByte", "value": {"type": "Int", "value": "0"}},
        {"name": "endByte", "value": {"type": "Int", "value": "1"}},
    ]}


def _fn(name, semantic_id):
    return {"fields": [
        {"name": "name", "value": {"type": "Str", "value": name}},
        {"name": "semanticId", "value": {"type": "Str", "value": semantic_id}},
    ]}


def _sliced():
    return {"type": "ParserProgress", "fields": [
        {"name": "nodes",
         "value": {"type": "List[FlatAstNode]", "value": []}}]}


def merge(groups, full, entry="main", extra=()):
    return sectional.merge_reports(_sliced(), groups, list(full), entry, list(extra))


def merged_names(report):
    fields = {f["name"]: f["value"] for f in report["fields"]}
    return [e["fields"][0]["value"]["value"]
            for e in fields["functions"]["value"]]


def merged_calls(report):
    fields = {f["name"]: f["value"] for f in report["fields"]}
    return [int(e["fields"][0]["value"]["value"])
            for e in fields["calls"]["value"]]


RESULTS = []


def probe(label, expect, run):
    """expect: 'refuse' (ValueError) or 'adopt'. Records observed behaviour."""
    try:
        out = run()
        observed, detail = "adopt", (out if isinstance(out, str) else "")
    except ValueError as error:
        observed, detail = "refuse", str(error)[:90]
    except Exception as error:  # noqa: BLE001 - any other exception is also a finding
        observed, detail = f"RAISED {type(error).__name__}", str(error)[:90]
    ok = observed == expect
    RESULTS.append((label, expect, observed, ok, detail))
    print(f"{'PASS' if ok else 'OPEN':<5} {label:<52} expect={expect:<6} got={observed:<16} {detail}")


def main():
    print(f"sectional: {ROOT / 'pep_sectional.py'}\n--- A1's six, reproduced independently ---")
    probe("empty group list", "refuse", lambda: merge([], []))
    probe("foreign document", "refuse",
          lambda: merge([([1, 2], _report(doc="doc1")), ([3, 4], _report(doc="docX"))],
                        [1, 2, 3, 4]))
    probe("stale revision", "refuse",
          lambda: merge([([1, 2], _report(rev="7")), ([3, 4], _report(rev="8"))],
                        [1, 2, 3, 4]))
    probe("hole present", "refuse",
          lambda: merge([([1], _report(holes=[{"hole": True}]))], [1]))
    probe("out-of-span call fact", "refuse",
          lambda: merge([([5], _report(calls=[_call(99)]))], [5]))
    # Realistic control: the merged function set must contain the caller and callee
    # semanticIds, because A1 anchors every call in it (BOOT-A3-080 item).
    # NOTE (BOOT-A3-090): merge_reports copies only the ENTRY function fact from the
    # group reports; every other function fact must arrive via all_fn_facts (the
    # whole-file signature list). So the callee has to be supplied there, not in the
    # group report, or its semanticId is not in the anchored set.
    probe("valid control (anchored call)", "adopt",
          lambda: (merge([([1, 2], _report(fns=[_fn("main", "1")],
                                            calls=[_call(0, caller="1", callee="2")])),
                          ([3], _report(calls=[_call(0, caller="1", callee="2")]))],
                         [1, 2, 3], extra=[_fn("helper", "2")]),
                   "ok")[1])

    print("\n--- identity channels A1's tests do not cover ---")
    # A1's stated boundary (9bf18699): a single group that is internally consistent
    # cannot be told apart from truth at merge level, so it is accepted and left to
    # the emitter. This is now an intentional boundary, not an open gap - recorded as
    # expect="adopt" so the probe tracks the decision rather than flagging it forever.
    probe("single-group self-consistent entry fact (accepted by design)", "adopt",
          lambda: merged_names_dummy(
              merge([([1], _report(fns=[_fn("main", "forged-sem")]))], [1])))
    # Two facts claiming the entry name with different ids: silent duplication?
    probe("entry name carried twice with different semanticIds", "refuse",
          lambda: merged_names_dummy(
              merge([([1], _report(fns=[_fn("main", "good")])),
                     ([2], _report(fns=[_fn("main", "evil")]))], [1, 2])))
    # A call fact naming a callee that appears nowhere in the function facts.
    probe("call fact naming an absent callee", "refuse",
          lambda: merged_calls_dummy(
              merge([([1], _report(calls=[_call(0, "ghost-function")]))], [1])))
    # Duplicate chunk ids: two chunk-local ids collapse onto one full-slice id.
    probe("duplicate ids inside one group", "refuse",
          lambda: merged_calls_dummy(
              merge([([7, 7], _report(calls=[_call(0), _call(1)]))], [7])))
    # UNREACHABLE TODAY, still a contract hazard: unsorted cids.
    # sliced() numbers nodes in the given order; merge_reports sorts them, so a
    # fact can land on a DIFFERENT node than the one it describes. Expected to be
    # fail-open like the others; the detail string states where the fact moved.
    probe("unsorted chunk ids (latent remap mismatch)", "refuse",
          lambda: remap_mismatch())

    print()
    bad = [r for r in RESULTS if not r[3]]
    print(f"{len(RESULTS)} probes, {len(bad)} disagreeing with the fail-closed expectation")
    return 0


def merged_names_dummy(report):
    names = merged_names(report)
    return f"{len(names)} fact(s): {','.join(names) or 'empty'}"


def merged_calls_dummy(report):
    return ",".join(str(c) for c in merged_calls(report)) or "empty"


def remap_mismatch():
    """Show that merge_reports renumbers by sorted order regardless of input order.

    A chunk of ids [10, 2] is numbered by sliced() as 10->0, 2->1. merge_reports
    computes ordered=sorted([10,2])=[2,10] and maps chunk-local 0 -> rank[2] = 0.
    The fact describing node 10 is therefore re-attached to node 2: silent
    mis-attribution with no refusal. Returns a string, i.e. reports fail-open.
    Reachable only if a caller passes unsorted ids; the sectional driver's groups
    path always sorts, so this is a latent hazard rather than a live bug.
    """
    report = merge([([10, 2], _report(calls=[_call(0)]))], [2, 10])
    got = merged_calls(report)
    if got == [1]:
        raise ValueError("no mis-attribution observed; chunk-local 0 stayed on node 10")
    return f"mis-attributed: chunk-local 0 (belongs to node 10) landed on full-slice rank {got}"


if __name__ == "__main__":
    sys.exit(main())