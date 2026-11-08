# ACCEPT BOOT-A3-090 — A1 closed 4 of 5 identity channels; the 5th is a stated boundary. And my instrument was wrong, not their code.

**Verdict: A1's `9bf18699` closes four of the five identity channels I reported in A3-080, and the remaining one is an
explicitly documented design boundary I accept. My probe now reports 11/11 clean. Along the way I found that my own
"valid control" was emitting an invalid record type, so what first looked like a regression was my bug.**

## A1's fixes, verified

`7e1ba66` "close A3-080 identity channels — entry agreement, ascending-unique cids, call anchoring" plus `9bf1869`
"dup-refusal sigs shape [] (A3-082 note 1)". Re-running my probe at `9bf18699`:

| A3-080 finding | at `07f1da86` | at `9bf18699` |
|---|---|---|
| entry name twice, different `semanticId`s | adopted (1 fact) | **refused** — `entry fact disagreement across groups` |
| call fact naming an absent callee | adopted | **refused** — `call to unknown function fact` |
| duplicate ids inside one group | adopted | **refused** — `group ids not ascending-unique` |
| unsorted chunk ids (remap mismatch) | mis-attributed | **refused** — `group ids not ascending-unique` |
| single-group self-consistent entry fact | adopted | adopted — **by design, see below** |
| A1's six fail-closed channels + valid control | pass | **pass** |

`11 probes, 0 disagreeing with the fail-closed expectation.`

The unsorted-cids fix is the one with teeth: the old code sorted the ids for `g2s` while `sliced()` numbered them in given
order, so a fact could land on a different node than the one it described. That is now refused before remapping, which
removes the hazard instead of documenting it.

## The remaining channel is a boundary, not a gap

A1's own comment states it: *"Single-group fully-consistent forgery is definitionally valid input and stays the emitter's
catch."* That is correct. If one group is internally consistent — its entry fact and its call anchors agree — the merge has
no second opinion to compare against, and refusing would mean refusing every legitimate single-group function. The defence
that remains is the emitter resolving `calleeId` against its function facts, which is where a forged id should fail.

I have reclassified that probe from OPEN to **accepted-by-design** so it tracks the decision rather than flagging forever.
I did **not** test the emitter's side of that boundary; bounded, not closed, is the honest description.

## Note 1 from A3-082 also closed

Verified at runtime, not by reading the diff:

```
failures = [('main', 'duplicate-function', ['PEP_DUPLICATE_FUNCTION'])]
sigs     = []
sigs is a list: True
```

`check_program` now returns `"sigs": []` on the duplicate refusal path instead of `None`, so every return shape carries a
list. A1's comment credits the note. `_duplicate_top_level_functions` still returns `[]` for a single `main`.

## My instrument was wrong — recorded because it matters

On first re-run the **valid control refused** with `call to unknown function fact`. My initial reading was that A1's
anchoring check had broken the happy path. It had not. The real record type is:

```
type ResolvedCall { callerId: Int, calleeId: Int, syntaxId: Int, startByte: Int, endByte: Int }
                                      (tests/pep_checker_a13.pep:4)
```

My `_call` helper emitted **only** `syntaxId` — not a valid `ResolvedCall` at all. A1's check correctly refused a call with
no `callerId`/`calleeId`. The instrument was wrong.

Two corrections, both now in the probe:

1. `_call` emits all five fields with realistic ids.
2. The control must supply non-entry function facts through `all_fn_facts`, because `merge_reports` copies **only the entry**
   function fact from group reports — every other function comes from the whole-file signature list. That is consistent with
   the docstring and is now written down in the probe so the next reader does not repeat my mistake.

This is the third instrument defect I have found and fixed in this lane (the others: a probe scoring a mis-attribution as
PASS, and a self-test stub crashing instead of testing stdout). Reporting them is the point — a verifier that quietly
corrects itself without saying so teaches the author nothing about their own instruments.

## Limits

- Probes are unit-level calls to `merge_reports` and `check_program` with constructed facts. They prove the refusals fire on
  the shapes I built; they do not prove end-to-end sectional emission on real compiler-A slices, which is A1's driver to
  demonstrate.
- The accepted-by-design channel is bounded by the emitter, and I have not exercised that bound.
- `239`/`9bf18699` is a moving lane; any further commit requires a re-run.

## Reproduce

```
PEPIN_SECTIONAL_ROOT=<worktree at 9bf18699> python verification/probes/sectional_negatives_080.py
```

REF GH #16, parent reports `6724326324` (A3-080) and `6724356386` (A3-082). Fixes by A1; independent re-verification by A3.