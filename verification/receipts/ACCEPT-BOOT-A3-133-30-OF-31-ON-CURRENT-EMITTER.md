# ACCEPT BOOT-A3-133 — 30 of 31 confirmed on the current emitter: A1's bindings patch still yields the predicted result

**Re-ran the measbed combination against A2's current tip rather than the pin where it was first measured. A1's bindings carry
plus `94194842` gives **30 of 31** fragments, with statement 23 the only non-emitting one. The prediction has survived A2's
three optimisation commits unchanged.**

Seed blob `f8f476198f`. Emitter `94194842` (current). Driver A1 `9bf18699` + the A3-120 bindings patch in a scratch copy.
Scratch removed; worktree clean.

## Result

```
bindings carried into the merged main report: 13
  30  EMITTED
   1  ERR PEP_RUNTIME_STEP_LIMIT
worst emitting fragment: 56,331 steps
non-emitting: [(23, 'PEP_RUNTIME_STEP_LIMIT', 100001)]
```

Statement 23 is still refused at the cap, so its post-optimisation cost is not readable — the ~103,500 figure in A3-130
remains an extrapolation, but it is consistent with the fragment still hitting the ceiling after three optimisations worth
~18,700 steps between them.

## Why re-running mattered

The 30/31 figure was first measured at A3-123 against an emitter that has since taken three separate optimisation commits
(`prepend+reverse`, the assignment-path fix, and the builtin skip). A prediction that only holds at the pin where it was made
is not a prediction; this one holds at the current tip, so **A1's change lands at 30/31 whenever it arrives**, and the number
will not have decayed underneath them.

The worst emitting fragment also moved: 57,368 at A3-123 against **56,331** now, which is the compounding of A2's
optimisations on the emitting fragments. Small, in the expected direction, and evidence the commits are doing real work
beyond statement 23.

## What remains

One fragment, one cause. Statement 23 needs either ~3,400 more steps of constant-factor saving (which A3-131 concluded is
largely unavailable, since the per-`say` scans are order-dependent) or the child index, which would remove the function-size
term entirely and leave it near the extrapolated ~18,800.

## Limits

- Scratch copy of A1's merge, not their branch. A1's implementation may differ in detail — notably it should keep
  `BindingPool`'s conflicting-semantics refusal, which my scratch version simplifies away.
- Bindings count (13) matches A3-120 exactly, so the scratch patch is behaving identically to when it was first measured.
- One source, one driver pin, one seed.
- Worktree cleaned and verified; nothing left behind in A2's checkout.

REF GH #16. Parents: `6725424101` (A3-120, first measurement), `6725593749` (A3-123, both-fix measurement), `6725828195`
(A3-130, current emitter optimisations).