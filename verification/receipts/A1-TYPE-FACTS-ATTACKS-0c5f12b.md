# A1 slice-4a type-facts producer attacked at `0c5f12b` — all nine fail-closed claims hold, and the STALE1 host repair generalises to a new tool function

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slice 2: cross-chunk bindings/declaration closure, stale/foreign-revision facts, incorrect fact reuse) · **Evidence label:** `TESTED`
**Target:** `codex/p1-checker-cost-fix` @ **`0c5f12b`**, pinned worktree `D:\Projects\wt-a3-a1-0c5f12b` (clean, untouched)
**Instrument:** `verification/probes/a1_type_facts_attacks.py` (new)

## Why this target

`0c5f12b` adds `chunk_type_declarations(parsed) -> List[ResolvedTypeDecl]` — cross-chunk resolved
field-type facts — with explicit guards (matching `semantic_snapshot`, `parsed.done`,
`status == "complete"`, `tree_is_valid`). That is exactly the guard class that failed open in STALE1, so
it is attacked rather than trusted.

## Result — `SUMMARY cases=9 claim_falsified=0`

| case | claim | measured at `0c5f12b` |
|---|---|---|
| **T0** | control: matching pair yields facts | **non-empty** — `['Box', 'Point']` (without this the rest would prove nothing) |
| **T1** | crossed revision yields no facts | **refused by the host** — `PEP_STALE_REVISION`, "Tool arguments derive from a different source revision than the semantic target" |
| **T2** | foreign document yields no facts | **refused** — `PEP_DOCUMENT_NOT_FOUND` |
| **T3** | `done = false` yields no facts | **empty** (the producer's own guard) |
| **T4** | `status = "partial"` yields no facts | **empty** |
| **T5** | tampered tree (child of node 0 given itself as parent) yields no facts | **empty** (`tree_is_valid` catches it) |
| **T6** | duplicate type name keeps the first declaration | **exactly one** `Dup`, span `0` = the first declaration |
| **T7** | no primitive name returned as a record declaration | **none** |
| **T8** | every fact carries the target document and revision | **all match** (`doc-3` on both facts) |

Two things worth stating plainly:

1. **The STALE1 repair generalises.** T1 shows the crossed pair being refused at the *host* before the
   new function runs. The fix A1 landed in `ba4b057` is not special-cased to `pep-c23-checker`; a newly
   added tool function inherits it. That is the difference between fixing a symptom and fixing a class.
2. **The producer's internal guards are real, not decorative.** T3–T5 pass arguments with a *valid*
   document/revision pair (so the host has no reason to refuse) but doctored `done`, `status` and node
   structure; each produces an empty fact list. The guards fire where they claim to.

## Attacks that found nothing, and the ones that found my own mistakes

First run of this probe reported T3, T4 and T5 as `LEAKED`, and T6 as a span mismatch. Both were **my**
harness defects, caught before anything was recorded:

- after `declarations()` was refactored to return `{"state", "code", "facts"}`, T3–T5 still tested
  `not declarations(...)` — truthiness of a non-empty **dict**, which is always false, so every "leak"
  was an artefact. An isolated discriminator (does the tool use the argument or an authoritative
  re-parse?) proved the tool uses the argument: empty `nodes` → 0 facts, `done=false` → 0 facts.
- T6 compared a transport **Int** (encoded as `Str`) against a Python `int`, so a correct first-span
  result read as a mismatch.

Each mutation now asserts that it actually applied (a mutation that silently does nothing would turn a
guard test into a duplicate of the control), and `declarations()` reports `refused` distinctly from
`ok`-with-empty rather than raising — a host refusal is fail-closed behaviour, not a harness error.

## Honest scope

- Nine claims, one pin, one pass. This is not a proof of the producer's correctness, and it does not test
  emitter consumption of these facts (that is A2's/combined-tree ground).
- `T1`/`T2` measure the *host* guard, not the function's own return value; the function's own
  document/revision check is therefore not independently exercised in this receipt (it is shadowed).
- No frozen gate was executed; this is not acceptance evidence.

## Reproduce

```powershell
python verification\probes\a1_type_facts_attacks.py D:\Projects\wt-a3-a1-0c5f12b   # exit 0
```

## Next action

Reported to A1 on #16. If slice 4b/5 lands, this probe is the regression set for the facts producer; the
frozen Full remains gated on a pushed combined successor of `8396b63` and on the 66-node row.
