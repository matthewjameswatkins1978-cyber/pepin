"""Agent 3 K1c: same-target forged CARRIED bindings on the typed-bound pooled path.

K1b showed callee-signature forgeries split (param admitted; result/arity refused).
The typed-bound amendment carries BINDING facts across statement groups through
`contract.BindingPool`, so the same question must be asked of carried facts:
does a retyped carried binding, with honest same-target stamps, get refused where
it is USED? Two cases on utf8_check (group 1 consumes carried `first: Int`):

- F1: retype the USED binding (`first` Int -> Str) -> must refuse (record code).
- F2: retype an UNUSED-in-group-1 binding (`source`) -> documents vacuity control:
  admission here proves nothing about enforcement; only F1 discriminates.

Hand-supplied facts, not executable attacks (no such program exists for a seed
oracle). Exit 0 = probe ran to verdicts (printed); the verdicts themselves are
evidence, recorded in the receipt, never relabeled.
Usage: python pooled_forgery_k1c.py <worktree-at-typed-bound-sha>
"""
import copy
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import pep_chunk_contract as contract
from tests import test_chained_bindings as chained


def retype(fact, to_type):
    fields = {f["name"]: f for f in fact["fields"]}
    fields["typeName"]["value"]["value"] = to_type
    for sub in fields["typeShape"]["value"]["fields"]:
        if sub["name"] == "name":
            sub["value"]["value"] = to_type


def main():
    chained.ChainedBindingTests.setUpClass()
    t = chained.ChainedBindingTests("test_utf8_check_is_fully_covered_by_chained_units")
    pool = contract.BindingPool(t.sem["document"], t.sem["revision"])
    chunk0, term0 = t.statement_chunk("utf8_check", 0)
    report0, codes0 = t.invoke("utf8_check", chunk0, term0, pool.facts())
    print("group0 honest:", report0["status"]["value"] if report0 else None, codes0)
    pool.add(report0["bindings"]["value"])

    chunk1, term1 = t.statement_chunk("utf8_check", 1)
    control, control_codes = t.invoke("utf8_check", chunk1, term1, pool.facts())
    print("group1 CONTROL:", control["status"]["value"] if control else None,
          control_codes[:3])

    forged_first = copy.deepcopy(pool.facts())
    n_first = 0
    for fact in forged_first:
        names = {f["name"]: f["value"].get("value") for f in fact["fields"]}
        if names.get("name") == "first":
            retype(fact, "Str")
            n_first += 1
    result_f, codes_f = t.invoke("utf8_check", chunk1, term1, forged_first)
    print(f"F1 forged USED binding `first` Int->Str (n={n_first}):",
          result_f["status"]["value"] if result_f else None,
          (codes_f[:3] if codes_f else codes_f))

    forged_source = copy.deepcopy(pool.facts())
    n_source = 0
    for fact in forged_source:
        names = {f["name"]: f["value"].get("value") for f in fact["fields"]}
        if names.get("name") == "source":
            retype(fact, "Int")
            n_source += 1
    result_s, codes_s = t.invoke("utf8_check", chunk1, term1, forged_source)
    print(f"F2 forged UNUSED-in-group-1 binding `source` (n={n_source}, vacuity control):",
          result_s["status"]["value"] if result_s else None,
          (codes_s[:3] if codes_s else codes_s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
