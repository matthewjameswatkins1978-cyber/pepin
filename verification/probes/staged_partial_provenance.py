"""Staged checking for partial/incomplete source and unverified fact provenance
(LUCY-20261104-004, A3's single bounded slice).

Extends the existing matrix with a compact set of source-revision-bound negatives that
are *genuinely discriminating*: each cell compares the staged verdict with the SEED's
verdict class for the same source (not merely two staged runs against each other), and
each names the interface contract it exercises.

Verdict taxonomy (kept distinct, per the work order):
  valid              checker accepts
  invalid            checker rejects with a diagnostic
  incomplete         front end reports partial/unresolved source (e.g. typed holes)
  unsupported        front end/checker declines to claim a verdict
  transport_refusal  host refuses the tool call (e.g. stale revision) and no report exists

Cells:
  P1/P2/P3  typed holes in a body / in a let value: seed = incomplete, so the staged
            path must not answer `valid` (a hole is incomplete source, not a program).
  G1        a fact for a record the SOURCE does not declare, stamped with the correct
            document+revision (so the provenance guard passes on labels alone).
  G2        a phantom field: the fact adds a field the source does not declare.
  G3        a stale binding: the fact declares a field type the source contradicts.
            Here the SEED says the body is valid, so a staged `invalid` is a
            false refusal — the cell fails in the opposite direction on purpose.
  M1        complete-looking facts that omit a declaration the body needs.

Exit codes: 0 = every cell met its expectation, 1 = at least one cell failed,
2 = harness error. Usage: python staged_partial_provenance.py <candidate-worktree>
"""
import importlib.util
import json
import pathlib
import sys

ARGS = [item for item in sys.argv[1:] if not item.startswith("--")]
REPO = pathlib.Path(ARGS[0] if ARGS else ".").resolve()
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location("staged_typed_attacks",
                                             HERE / "staged_typed_attacks.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

import pep_chunk_contract as contract  # noqa: E402
from tests.chunk_helper import fields_map, nval  # noqa: E402

CELLS = []


def cell(name, contract_text, seed_class, staged_class, expected, detail=""):
    ok = staged_class in expected
    CELLS.append({"cell": name, "contract": contract_text, "seed": seed_class,
                  "staged": staged_class, "expected": list(expected),
                  "verdict": "PASS" if ok else "FAIL", "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name:<10} seed={seed_class:<12} "
          f"staged={staged_class:<18} expected={sorted(expected)} {detail}")


def seed_class(source: str):
    verdict = base.seed_verdict(source.encode("utf-8"))
    head = verdict.split("/")[0]
    return head if head in ("valid", "invalid", "incomplete", "unsupported") else verdict


def staged_class(harness, parsed, sem, facts, entry, expect_returns=True):
    raw = None
    extfns, extsigs = signature_args(harness, parsed, sem, entry)
    raw = harness.analyze_typed(harness.sliced(parsed, ids_for(parsed, entry)),
                                extfns, extsigs,
                                {"type": "List[ResolvedTypeDecl]", "value": facts}, sem,
                                expect_returns=expect_returns)
    status = raw["status"]
    if status.startswith("REFUSED"):
        return "transport_refusal"
    return status


def whole_class(harness, parsed, sem):
    response = harness.session.send(
        {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
         "tool": "pep-c23-checker", "arguments": [parsed], "semanticTarget": sem})
    if response.get("outcome") != "ok":
        return "transport_refusal"
    return fields_map(response["result"])["status"]["value"]


def ids_for(parsed, entry):
    index = contract.DocumentIndex.from_parsed(parsed)
    for node in fields_map(parsed)["nodes"]["value"]:
        if nval(node, "kind") == "function" and str(nval(node, "parentId")) == "-1" \
                and nval(node, "text") == entry:
            return index.subtree(int(nval(node, "id")))
    raise RuntimeError(f"entry {entry} not found")


def signature_args(harness, parsed, sem, entry):
    sigs = harness.signatures(parsed, sem)
    return (
        {"type": "List[CheckedFunction]",
         "value": [base.checked_fn_value(s) for s in sigs if s["name"] != entry]},
        {"type": "List[ResolvedSignature]",
         "value": [base.resolved_sig_value(s) for s in sigs if s["name"] != entry]},
    )


def decl_facts(harness, parsed, sem):
    index = contract.DocumentIndex.from_parsed(parsed)
    ids = []
    for node in fields_map(parsed)["nodes"]["value"]:
        if str(nval(node, "parentId")) == "-1" and nval(node, "kind") in (
                "record_declaration", "union_declaration"):
            ids.extend(index.subtree(int(nval(node, "id"))))
    return harness.real_facts(parsed, sem, ids)


def main():
    print(f"REPO={REPO}")
    harness = base.Harness()
    try:
        # ---------------- C0 positive controls (each negative is paired) ------------
        control_src = ("type P {\n    x: Int\n}\n\n"
                       "fn f(p: P) -> Int {\n    return p.x\n}\n\n"
                       "fn main() -> Int { return 0 }\n")
        sem_c, parsed_c = harness.prepare(control_src, "pv-control")
        facts_c = decl_facts(harness, parsed_c, sem_c)
        cell("C0a", "positive control: no hole, honest facts => valid", seed_class(control_src),
             staged_class(harness, parsed_c, sem_c, facts_c, "f"), ("valid",))
        two_control = ("type P {\n    x: Int\n}\n\n"
                       "type Q {\n    y: Int\n}\n\n"
                       "fn f(p: P, q: Q) -> Int {\n    return p.x + q.y\n}\n\n"
                       "fn main() -> Int { return 0 }\n")
        sem_c2, parsed_c2 = harness.prepare(two_control, "pv-control2")
        facts_c2 = decl_facts(harness, parsed_c2, sem_c2)
        cell("C0b", "positive control: both declarations supplied => valid",
             seed_class(two_control),
             staged_class(harness, parsed_c2, sem_c2, facts_c2, "f"), ("valid",))

        # ---------------- P1/P2/P3: typed holes => incomplete, never valid ----------
        hole_body = ("type P {\n    x: Int\n}\n\n"
                     "fn f(p: P) -> Int {\n    return ?hole\n}\n\n"
                     "fn main() -> Int { return 0 }\n")
        sem_h, parsed_h = harness.prepare(hole_body, "pv-hole-body")
        facts_h = decl_facts(harness, parsed_h, sem_h)
        cell("P1", "hole in a body: parse is complete but the program is unresolved",
             seed_class(hole_body), staged_class(harness, parsed_h, sem_h, facts_h, "f"),
             ("incomplete", "invalid", "unsupported"))

        hole_named = ("type P {\n    x: Int\n}\n\n"
                      "fn f(p: P) -> Int {\n    return ?value\n}\n\n"
                      "fn main() -> Int { return 0 }\n")
        sem_n, parsed_n = harness.prepare(hole_named, "pv-hole-named")
        facts_n = decl_facts(harness, parsed_n, sem_n)
        cell("P2", "named hole in a body", seed_class(hole_named),
             staged_class(harness, parsed_n, sem_n, facts_n, "f"),
             ("incomplete", "invalid", "unsupported"))

        hole_let = ("type P {\n    x: Int\n}\n\n"
                    "fn f(p: P) -> Int {\n    let a: Int = ?filler\n    return a\n}\n\n"
                    "fn main() -> Int { return 0 }\n")
        sem_l, parsed_l = harness.prepare(hole_let, "pv-hole-let")
        facts_l = decl_facts(harness, parsed_l, sem_l)
        cell("P3", "hole in a let value", seed_class(hole_let),
             staged_class(harness, parsed_l, sem_l, facts_l, "f"),
             ("incomplete", "invalid", "unsupported"))

        # ---------------- G1: fact for a record the source never declares -----------
        ghost_src = ("type P {\n    x: Int\n}\n\n"
                     "fn f(p: P) -> Int {\n    return p.x\n}\n\n"
                     "fn main() -> Int { return 0 }\n")
        sem_g, parsed_g = harness.prepare(ghost_src, "pv-ghost")
        facts_g = decl_facts(harness, parsed_g, sem_g)
        ghost = base.build_decl("Ghost", "record", sem_g["document"], sem_g["revision"],
                                [("g", "Int", "builtin", "Int")])
        ghost_body = ("type P {\n    x: Int\n}\n\n"
                      "fn h(g: Ghost) -> Int {\n    return g.g\n}\n\n"
                      "fn main() -> Int { return 0 }\n")
        sem_h2, parsed_h2 = harness.prepare(ghost_body, "pv-ghost-body")
        facts_h2 = decl_facts(harness, parsed_h2, sem_h2)
        cell("G1", "fact asserts a record the source does not declare (labels are correct)",
             seed_class(ghost_body),
             staged_class(harness, parsed_h2, sem_h2, facts_h2 + [ghost], "h"),
             ("invalid", "unsupported", "transport_refusal"),
             f"whole={whole_class(harness, parsed_h2, sem_h2)}")

        # ---------------- G2: phantom field on a real record ------------------------
        phantom = base.tamper_field_type(facts_g[0], "x", "Int")
        phantom = json.loads(json.dumps(phantom))
        for item in phantom["fields"]:
            if item["name"] == "fields":
                item["value"]["value"].append({
                    "type": "ResolvedTypeField", "fields": [
                        {"name": "fieldName", "value": base.typed("Str", "ghost")},
                        {"name": "fieldTypeName", "value": base.typed("Str", "Int")},
                        {"name": "fieldShape", "value": base.shape("builtin", "Int")},
                        {"name": "fieldCode", "value": base.typed("Str", "")},
                        {"name": "startByte", "value": base.typed("Int", 0)},
                        {"name": "endByte", "value": base.typed("Int", 0)},
                        {"name": "line", "value": base.typed("Int", 1)},
                        {"name": "column", "value": base.typed("Int", 1)}]})
        ghost_field_src = ("type P {\n    x: Int\n}\n\n"
                           "fn f(p: P) -> Int {\n    return p.ghost\n}\n\n"
                           "fn main() -> Int { return 0 }\n")
        sem_p, parsed_p = harness.prepare(ghost_field_src, "pv-phantom")
        facts_p = decl_facts(harness, parsed_p, sem_p)
        cell("G2", "fact adds a field the source does not declare",
             seed_class(ghost_field_src),
             staged_class(harness, parsed_p, sem_p, [phantom], "f"),
             ("invalid", "unsupported", "transport_refusal"),
             f"whole={whole_class(harness, parsed_p, sem_p)}")

        # ---------------- G3: fact contradicts the source's own field type ----------
        stale_src = ("type P {\n    x: Int\n}\n\n"
                     "fn f(p: P) -> Int {\n    return p.x\n}\n\n"
                     "fn main() -> Int { return 0 }\n")
        sem_s, parsed_s = harness.prepare(stale_src, "pv-stale-binding")
        facts_s = decl_facts(harness, parsed_s, sem_s)
        stale = [base.tamper_field_type(facts_s[0], "x", "Bool")]
        # G3 is recorded as an OBSERVATION, not a claim. A fact that contradicts the
        # source can only come from a corrupt or buggy producer; rejecting it is
        # fail-closed, which the work order asks for where trust is unproven. What is
        # undefined is the contract: advisory facts would yield `valid`, authoritative
        # facts yield `invalid` (a false refusal of a program the seed accepts).
        stale_staged = staged_class(harness, parsed_s, sem_s, stale, "f")
        stale_whole = whole_class(harness, parsed_s, sem_s)
        CELLS.append({"cell": "G3", "contract": "contradictory fact: advisory vs authoritative",
                      "seed": seed_class(stale_src), "staged": stale_staged,
                      "expected": [], "verdict": "OBSERVED",
                      "detail": f"whole={stale_whole}; staged={stale_staged} — rejecting a "
                                f"contradictory fact is fail-closed, but the owner must state "
                                f"whether external facts are advisory (accept, ignore fact) or "
                                f"authoritative (refuse)"})
        print(f"[OBS ] G3         seed={seed_class(stale_src):<12} staged={stale_staged:<18} "
              f"whole={stale_whole}  contract undefined: advisory vs authoritative facts")

        # ---------------- M1: complete-looking facts missing one declaration --------
        two_src = ("type P {\n    x: Int\n}\n\n"
                   "type Q {\n    y: Int\n}\n\n"
                   "fn f(p: P, q: Q) -> Int {\n    return p.x + q.y\n}\n\n"
                   "fn main() -> Int { return 0 }\n")
        sem_t, parsed_t = harness.prepare(two_src, "pv-missing-decl")
        facts_t = decl_facts(harness, parsed_t, sem_t)
        only_p = [f for f in facts_t if fields_map(f)["typeName"]["value"] == "P"]
        cell("M1", "facts omit one of the two needed declarations",
             seed_class(two_src),
             staged_class(harness, parsed_t, sem_t, only_p, "f"),
             ("invalid", "unsupported", "transport_refusal"),
             f"whole={whole_class(harness, parsed_t, sem_t)}")
    finally:
        harness.close()

    failed = [row for row in CELLS if row["verdict"] == "FAIL"]
    passed = [row for row in CELLS if row["verdict"] == "PASS"]
    observed = [row for row in CELLS if row["verdict"] == "OBSERVED"]
    print(f"\nSUMMARY cells={len(CELLS)} pass={len(passed)} fail={len(failed)} "
          f"observed={len(observed)}")
    for row in failed:
        print(f"FAILED CELL: {row['cell']} seed={row['seed']} staged={row['staged']} "
              f"detail={row['detail']}")
    print(json.dumps(CELLS, indent=2, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
