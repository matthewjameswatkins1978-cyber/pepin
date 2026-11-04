"""Staged-checker metamorphic/differential matrix (LUCY-20261104-002 slice 2).

Deterministic and bounded: a fixed case list crossed with fixed metamorphic
relations. No search, no generated fuzzing — every cell is enumerated, so the same
inputs produce the same matrix on every run and every pin.

Reuse: this probe imports the harness, typed-record builders and seed oracle from
`staged_typed_attacks.py` (same directory) instead of standing up a second harness.
Infrastructure is the project's own: `pep_c23` session/tool transport plus
`tests/chunk_helper` conversions.

Relations (each a claim; a cell is PASS/FAIL/SKIP):
  R1 whole baseline              record the seed and whole-path verdict for the case.
  R2 declaration-order invariance  reordering independent TOP-LEVEL declarations must not
                                   change the whole-path verdict, and the chunked body
                                   verdict must stay equal to it.
  R3 chunk-boundary invariance     splitting the same statements at different boundaries
                                   must not change the terminal-group verdict.
  R4 fact-order invariance         reversing the trusted fact list must not change the
                                   chunked verdict. (Known to FAIL on duplicate
                                   declarations — that is the counterexample under test.)
  R5 missing-fact closure          dropping the facts a body needs must not leave it valid.
  R6 foreign-fact closure          adding a fact stamped with another revision must not
                                   leave the body valid (expect PEP_STALE_REVISION report).

Exit codes: 0 = every applicable cell passed, 1 = at least one cell failed,
2 = harness error. A failing R4 cell is the documented defect, not a probe error.
Usage: python staged_metamorphic_matrix.py <candidate-worktree> [--json PATH]
"""
import importlib.util
import json
import pathlib
import sys

ARGS = [item for item in sys.argv[1:] if not item.startswith("--")]
REPO = pathlib.Path(ARGS[0] if ARGS else ".").resolve()
JSON_OUT = None
if "--json" in sys.argv:
    JSON_OUT = pathlib.Path(sys.argv[sys.argv.index("--json") + 1])
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location("staged_typed_attacks",
                                             HERE / "staged_typed_attacks.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

import pep_chunk_contract as contract  # noqa: E402
from tests.chunk_helper import fields_map, nval  # noqa: E402

MATRIX = []


def cell(case, relation, verdict, detail=""):
    MATRIX.append({"case": case, "relation": relation, "verdict": verdict,
                   "detail": detail})
    print(f"[{verdict:4}] {case:<22} {relation:<28} {detail}")


def whole_status(harness, parsed, sem):
    response = harness.session.send(
        {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
         "tool": "pep-c23-checker", "arguments": [parsed], "semanticTarget": sem})
    if response.get("outcome") != "ok":
        return f"REFUSED:{(response.get('error') or {}).get('code')}"
    return fields_map(response["result"])["status"]["value"]


def body_ids(parsed, entry):
    index = contract.DocumentIndex.from_parsed(parsed)
    for node in fields_map(parsed)["nodes"]["value"]:
        if nval(node, "kind") == "function" and str(nval(node, "parentId")) == "-1" \
                and nval(node, "text") == entry:
            return index.subtree(int(nval(node, "id")))
    raise RuntimeError(f"entry {entry} not found")


def decl_roots(parsed):
    index = contract.DocumentIndex.from_parsed(parsed)
    ids = []
    for node in fields_map(parsed)["nodes"]["value"]:
        if str(nval(node, "parentId")) == "-1" and nval(node, "kind") in (
                "record_declaration", "union_declaration"):
            ids.extend(index.subtree(int(nval(node, "id"))))
    return ids


def facts_for(harness, parsed, sem):
    return harness.real_facts(parsed, sem, decl_roots(parsed))


def signature_args(harness, parsed, sem, entry):
    sigs = harness.signatures(parsed, sem)
    return (
        {"type": "List[CheckedFunction]",
         "value": [base.checked_fn_value(s) for s in sigs if s["name"] != entry]},
        {"type": "List[ResolvedSignature]",
         "value": [base.resolved_sig_value(s) for s in sigs if s["name"] != entry]},
    )


def run_body(harness, parsed, sem, facts, entry, expect_returns=True):
    extfns, extsigs = signature_args(harness, parsed, sem, entry)
    return harness.analyze_typed(
        harness.sliced(parsed, body_ids(parsed, entry)), extfns, extsigs,
        {"type": "List[ResolvedTypeDecl]", "value": facts}, sem,
        expect_returns=expect_returns)["status"]


def group_ids(parsed, entry, indexes):
    index = contract.DocumentIndex.from_parsed(parsed)
    nodes = fields_map(parsed)["nodes"]["value"]
    root_id = None
    for node in nodes:
        if nval(node, "kind") == "function" and str(nval(node, "parentId")) == "-1" \
                and nval(node, "text") == entry:
            root_id = str(nval(node, "id"))
    keep = {int(root_id)}
    for node in nodes:
        if str(nval(node, "parentId")) == root_id and \
                nval(node, "role") in ("parameter", "return_type"):
            keep.update(index.subtree(int(nval(node, "id"))))
    statements = [node for node in nodes
                  if str(nval(node, "parentId")) == root_id
                  and nval(node, "role") == "statement"]
    for i in indexes:
        keep.update(index.subtree(int(nval(statements[i], "id"))))
    return sorted(keep)


def run_group(harness, parsed, sem, facts, entry, indexes):
    extfns, extsigs = signature_args(harness, parsed, sem, entry)
    return harness.analyze_typed(
        harness.sliced(parsed, group_ids(parsed, entry, indexes)), extfns, extsigs,
        {"type": "List[ResolvedTypeDecl]", "value": facts}, sem,
        expect_returns=False)["status"]


# ---------------------------------------------------------------- cases
CASE_VALID_USE = ("type P {\n    x: Int\n}\n\n"
                  "fn f(p: P) -> Int {\n    return p.x\n}\n\n"
                  "fn main() -> Int { return 0 }\n")

CASE_VALID_SWAP = ("type Q {\n    y: Int\n}\n\n"
                   "type P {\n    x: Int\n}\n\n"
                   "fn f(p: P) -> Int {\n    return p.x\n}\n\n"
                   "fn main() -> Int { return 0 }\n")

CASE_DUP_DECL = ("type D {\n    a: Int\n}\n"
                 "type D {\n    b: Int\n}\n"
                 "fn f(d: D) -> Int {\n    return d.a\n}\n")

CASE_DUP_LET = ("type P {\n    x: Int\n}\n\n"
                "fn f(p: P) -> Int {\n    let a = p.x\n    let a = 1\n"
                "    return a\n}\n\n"
                "fn main() -> Int { return 0 }\n")

CASE_UNKNOWN_FIELD_TYPE = ("type Bad {\n    n: Nope\n}\n\n"
                           "fn main() -> Int { return 0 }\n")

CASE_THREE_STATEMENTS = ("type P {\n    x: Int\n}\n\n"
                         "fn g(p: P) -> Int {\n    let v = p.x\n    let w = v + 1\n"
                         "    return w\n}\n\n"
                         "fn main() -> Int { return 0 }\n")


def main():
    print(f"REPO={REPO}")
    harness = base.Harness()
    try:
        # ---- C1 valid record use: baseline, fact order, missing/foreign facts ----
        sem, parsed = harness.prepare(CASE_VALID_USE, "mx-valid")
        facts = facts_for(harness, parsed, sem)
        whole = whole_status(harness, parsed, sem)
        seed = base.seed_verdict(CASE_VALID_USE.encode("utf-8"))
        cell("valid_use", "R1 whole baseline", "PASS" if whole == "valid" else "FAIL",
             f"whole={whole} seed={seed}")
        body = run_body(harness, parsed, sem, facts, "f")
        cell("valid_use", "R1 chunk agrees with whole",
             "PASS" if body == whole else "FAIL", f"chunk={body} whole={whole}")

        reversed_facts = list(reversed(facts))
        body_rev = run_body(harness, parsed, sem, reversed_facts, "f")
        cell("valid_use", "R4 fact-order invariance",
             "PASS" if body_rev == body else "FAIL", f"{body} -> {body_rev}")

        dropped = [f for f in facts
                   if fields_map(f)["typeName"]["value"] != "P"]
        body_drop = run_body(harness, parsed, sem, dropped, "f")
        cell("valid_use", "R5 missing-fact closure",
             "PASS" if body_drop != "valid" else "FAIL", f"without P facts -> {body_drop}")

        foreign = base.build_decl("Foreign", "record", sem["document"],
                                  "rev-not-this-one", [("z", "Int", "builtin", "Int")])
        body_foreign = run_body(harness, parsed, sem, facts + [foreign], "f")
        cell("valid_use", "R6 foreign-fact closure",
             "PASS" if body_foreign != "valid" else "FAIL",
             f"with foreign fact -> {body_foreign}")

        # ---- C2 declaration-order invariance (whole path) ----
        sem_s, parsed_s = harness.prepare(CASE_VALID_SWAP, "mx-swap")
        facts_s = facts_for(harness, parsed_s, sem_s)
        whole_s = whole_status(harness, parsed_s, sem_s)
        body_s = run_body(harness, parsed_s, sem_s, facts_s, "f")
        cell("decl_order", "R2 declaration-order invariance",
             "PASS" if whole_s == whole == body_s else "FAIL",
             f"swapped whole={whole_s} chunk={body_s} original whole={whole}")

        # ---- C3 duplicate declarations: fact order (the known defect) ----
        sem_d, parsed_d = harness.prepare(CASE_DUP_DECL, "mx-dup")
        facts_d = facts_for(harness, parsed_d, sem_d)
        whole_d = whole_status(harness, parsed_d, sem_d)
        seed_d = base.seed_verdict(CASE_DUP_DECL.encode("utf-8"))
        forward = run_body(harness, parsed_d, sem_d, facts_d, "f", expect_returns=False)
        backward = run_body(harness, parsed_d, sem_d, list(reversed(facts_d)), "f",
                            expect_returns=False)
        cell("dup_decl", "R1 whole baseline", "PASS" if whole_d != "valid" else "FAIL",
             f"whole={whole_d} seed={seed_d}")
        # Order invariance alone is too weak: both orders agreeing is worthless if both
        # disagree with the seed. The relation is (forward == reversed) AND
        # (each order agrees with the whole-path/seed verdict).
        agrees = forward == backward == whole_d
        cell("dup_decl", "R4 fact-order + seed agreement",
             "PASS" if agrees else "FAIL",
             f"forward={forward} reversed={backward} whole={whole_d} seed={seed_d}")

        # ---- C4 duplicate scope binding ----
        sem_l, parsed_l = harness.prepare(CASE_DUP_LET, "mx-duplet")
        facts_l = facts_for(harness, parsed_l, sem_l)
        whole_l = whole_status(harness, parsed_l, sem_l)
        seed_l = base.seed_verdict(CASE_DUP_LET.encode("utf-8"))
        body_l = run_body(harness, parsed_l, sem_l, facts_l, "f")
        cell("dup_let", "R1 chunk agrees with whole",
             "PASS" if body_l == whole_l else "FAIL",
             f"whole={whole_l} chunk={body_l} seed={seed_l}")

        # ---- C5 invalid program (unknown field type), body that USES the bad record ----
        CASE_BAD_USE = ("type Bad {\n    n: Nope\n}\n\n"
                        "fn f(b: Bad) -> Int {\n    return b.n\n}\n\n"
                        "fn main() -> Int { return 0 }\n")
        sem_b, parsed_b = harness.prepare(CASE_BAD_USE, "mx-bad")
        facts_b = facts_for(harness, parsed_b, sem_b)
        whole_b = whole_status(harness, parsed_b, sem_b)
        seed_b = base.seed_verdict(CASE_BAD_USE.encode("utf-8"))
        body_b = run_body(harness, parsed_b, sem_b, facts_b, "f")
        cell("invalid_program", "R1 body that uses the bad record is refused",
             "PASS" if whole_b != "valid" and body_b != "valid"
             and seed_b.startswith("invalid") else "FAIL",
             f"whole={whole_b} chunk={body_b} seed={seed_b}")

        # ---- C6 chunk-boundary invariance on a three-statement body ----
        sem_t, parsed_t = harness.prepare(CASE_THREE_STATEMENTS, "mx-split")
        facts_t = facts_for(harness, parsed_t, sem_t)
        # Two complete but differently-sliced views of the same program region: the
        # body chunk (through the function root) and the statement-group chunk. Both
        # include every statement, so both must agree; a partial group must refuse.
        body_t = run_body(harness, parsed_t, sem_t, facts_t, "g")
        group_t = run_group(harness, parsed_t, sem_t, facts_t, "g", [0, 1, 2])
        partial_t = run_group(harness, parsed_t, sem_t, facts_t, "g", [2])
        cell("chunk_boundary", "R3 boundary invariance (body vs full group)",
             "PASS" if body_t == group_t == "valid" else "FAIL",
             f"body={body_t} group[0,1,2]={group_t} partial[2]={partial_t}")
        cell("chunk_boundary", "R3 partial group refuses (dependency discipline)",
             "PASS" if partial_t != "valid" else "FAIL", f"partial[2]={partial_t}")

        # ---- C7 incomplete/unparseable source: both paths must fail closed ----
        incomplete = "fn h(x: Int) -> Int {\n    return\n"
        try:
            sem_i, parsed_i = harness.prepare(incomplete, "mx-incomplete")
            facts_i = facts_for(harness, parsed_i, sem_i)
            whole_i = whole_status(harness, parsed_i, sem_i)
            seed_i = base.seed_verdict(incomplete.encode("utf-8"))
            cell("incomplete", "R1 both paths fail closed",
                 "PASS" if whole_i != "valid" and seed_i.startswith("invalid") else "FAIL",
                 f"whole={whole_i} seed={seed_i}")
        except BaseException as error:  # noqa: BLE001 - an unparseable source is data
            seed_i = base.seed_verdict(incomplete.encode("utf-8"))
            cell("incomplete", "R1 both paths fail closed",
                 "PASS" if seed_i.startswith("invalid") else "FAIL",
                 f"parse refused before checking ({type(error).__name__}), "
                 f"seed={seed_i}")
    finally:
        harness.close()

    passed = sum(1 for row in MATRIX if row["verdict"] == "PASS")
    failed = [row for row in MATRIX if row["verdict"] == "FAIL"]
    skipped = sum(1 for row in MATRIX if row["verdict"] == "SKIP")
    if JSON_OUT:
        JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps({"repo": str(REPO), "matrix": MATRIX,
                                        "pass": passed, "fail": len(failed),
                                        "skip": skipped}, indent=2, sort_keys=True),
                            encoding="utf-8")
        print(f"json={JSON_OUT}")
    print(f"SUMMARY cells={len(MATRIX)} pass={passed} fail={len(failed)} skip={skipped}")
    for row in failed:
        print(f"FAILED CELL: {row['case']} / {row['relation']} -> {row['detail']}")
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
