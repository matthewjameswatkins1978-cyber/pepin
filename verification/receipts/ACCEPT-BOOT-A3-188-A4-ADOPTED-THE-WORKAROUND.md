# ACCEPT BOOT-A3-188 — A4 adopted the A3-183 workaround and it clears the A13 defect in their own source

**A4's `8025f7c8` ("annotate bare-name var inits with Int") applies the diagnosis from A3-183 to their branch. Verified through the
real product path: the A13 rejection is gone and the build advances one function to the blocker A3-186 predicted.**

Seed blob `f8f476198f`. A4 `8025f7c8`, `compiler_a.pep` blob `30363b0e`, 1,535 lines, 34 functions, **19 annotated declarations**.

## The verification

```
$ python pep_c23.py build-c23 …/compiler_a.pep --sectional …
Pep C23 unsupported: Pep C23 sectional check failed in scan_value: ['PEP_RUNTIME_STEP_LIMIT']

A13 present: False
```

Before their commit, the same build stopped at **`scan_name` with `PEP_A13_TYPE_UNSUPPORTED`** (A3-163). Now it passes `scan_name`
and stops at **`scan_value` with the step limit**.

That is exactly the sequence A3-183 and A3-184 predicted: annotations clear the A13 rejection, and the next wall is `scan_value`.

## Two things worth noting about their implementation

**They annotated 19 declarations, not my 107.** My probe applied `Int` to every bare-name initialiser because it could not know the
real types (A3-183's caveat). A4 annotated deliberately, which is what I asked for. The build reaching the step limit — rather than
reporting `PEP_TYPE_MISMATCH` — means the annotations the checker reached are type-correct.

**The fix is in their lane, by them.** I did not touch their file. The lane separation held: I produced a diagnosis and a caveated
probe, they produced the change.

## What this settles

**A3-183's root cause is confirmed by an independent implementer.** The claim was that a `var` initialised from a bare mutable
local records no type, and that an explicit annotation fixes it. A4's commit is a 19-line application of that claim and it works on
their real source, not on a fixture.

**A3-169's "no workaround transfers" is now doubly superseded** — not only was there a workaround, the owning agent has used it.

## What remains between A4 and a buildable source

1. **`scan_value`** — `PEP_RUNTIME_STEP_LIMIT`, over budget before its loop starts (A3-186), cost distributed rather than localised
   (A3-187).
2. **`names_equal`** — refused for two fallible operands, blocking `match_tail` (A3-184).
3. Whatever sits behind those two: `match_varlet_body` and `is_unsupported_prog` could not be measured independently.

Then, for M-1 on a tracked tree, the four A3-159 fixes still have to land — A1's driver recipe is in hand, and the epilogue.

## Limits

- One verification of one commit; I did not run the full runbook because the build does not complete.
- I did not inspect the 19 annotations individually to confirm each type is right — I infer correctness from the build advancing past
  the check rather than reporting `PEP_TYPE_MISMATCH`, which is weaker than reading them.
- Isolated only in the sense that it is A4's source in a disposable worktree with A1's driver patch; not a 34-function merged build.

REF GH #16. Confirms `6729170885` (A3-183). Supersedes `6728763855` (A3-169) on workaround availability.