# RECOMMENDATION BOOT-A3-118 — keep the node-count guard: removing it turns one clear error into five confusing ones

**A2's `e6d5300` removed the `checked.syntaxNodeCount == length(parsed.nodes)` guard so the fragment entry can accept a
trimmed `parsed`, citing my BOOT-A3-115 transport finding. That change was prompted by advice I have since withdrawn, and the
measurement below shows the clause should stay. On the intended input it costs nothing; without it, an id-space mismatch
produces silent under-emission instead of a refusal.**

This is a recommendation, not a defect report. The entry works on both conventions; the question is which errors get caught.

Seed blob `f8f476198f`. Emitter `e6d53002`. Driver A1 `9bf18699`.

## The measurement

Same source (`compiler_a.pep`, blob `ca732536`), same merged report, two `parsed` variants swept over all 31 statements of
`main`:

| input | emitted | extra refusals |
|---|---|---|
| **A1 sliced progress** (rank ids) + merged report (rank ids) — **matching** | **18** | — |
| **Trimmed parsed** (document ids) + merged report (rank ids) — **mismatched** | **13** | **5 × `Pep C23 cross-chunk call has no resolved call fact`** |

Both sweeps also show the same 10 `loop assignments must target a direct mutable local` and 2 `calls require a known target`
— which is consistent with A3-117: those are the missing-bindings problem in A1's merge, independent of id space. The
difference between the two rows is purely the id-space mismatch.

So a mismatch costs **5 wrong refusals and 5 missing emissions**, and with the clause gone nothing distinguishes that from a
genuine emitter limitation. Before `e6d5300` the same input was refused with one unambiguous message:
`Pep C23 emission inputs do not match the authorised source revision`.

## Why the clause costs nothing on the right path

A1's sliced progress is already in the merged report's id space — 222 nodes, ids 0..221, `syntaxNodeCount` 222. The clause
passes **as written**:

```
syntaxNodeCount in report: 222  vs  len(sliced.nodes) 222
```

So the guard only ever fires on a genuine mismatch. It is free on the intended input and it is the only thing that catches
this class of error.

## I own the reason this changed

A3-115 recommended "pass `parsed` trimmed to the function subtree keeping document ids, and the `syntaxNodeCount` guard would
need changing." **A3-116 withdrew that** — A1's merge is in rank space, so document-id nodes can never line up with it, and
the correct input is A1's sliced progress, which satisfies the guard natively. A2 acted on A3-115 before A3-116 landed. That
sequence is mine to own, and this receipt exists because the correction needed to reach them as plainly as the original advice
did.

## Recommendation

1. **Restore the node-count clause.** If the trimmed-parsed convention is also wanted for small programs,
   accept *either* `checked.syntaxNodeCount == length(parsed.nodes)` (whole-program report, document ids) *or* the sliced
   convention — but make the mismatch case refuse, don't let it through.
2. **For compiler A, use A1's sliced progress.** It is the only input that matches the merged report, fits the transport
   (275,807 B), and satisfies the guard unchanged.
3. **Nothing here asks A2 to change the lowering.** The 12 remaining refusals are A1's missing bindings (A3-117).

## What this does not change

The transport fix is real either way: trimming does bring the request under 1 MiB. The problem is not that trimming is wrong —
it is that trimming *without an id-space check* silently produces a worse result than refusing.

## Limits

- One source, one emitter pin, one seed. The 5-extra-refusal figure is from `main` specifically; other functions may differ in
  how much an id mismatch costs, but the direction is not in doubt.
- I did not test whether a *reference-carrying* report (`references` populated) would make the mismatch self-correcting — A1's
  merge empties those too, so it could not be measured.
- Mixed lane as before: A1 driver, A2 checker/emitter.

## Reproduce

Sweep `pep-c23-statement-fragment` over `main`'s 31 statements twice: once with `res["slices"]["main"]`, once with a
document-id-trimmed `parsed`, both against `res["reports"]["main"]`. Compare emitted counts.

REF GH #16. Prompted by `6725312477` (A3-117) superseding `6725226403` (A3-115). Emitter A2 `e6d53002`.