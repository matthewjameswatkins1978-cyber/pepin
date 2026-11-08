# GATE BOOT-A3-168 — the A13 defect is now mechanical, and it caught a false green in my own suite

**A ninth gate tracks the A13 assignment-target defect against the real product path. Adding it exposed a false PASS in my own
gate wiring: bound to the pinned A2 worktree the gate reported success, because that tree has no `pep_sectional.py` at all and the
defect cannot exist there.**

Seed blob `f8f476198f`. Fixtures: `a13-assign-target-reduced.pep` (31 lines) and its one-line control.

## The gate

```
A13 assignment-target defect    FAIL   … checker calls valid. Owning fix: pep_checker_a13.pep L1933 / A1
```

It builds the 31-line reducer and its control through `build-c23 --sectional` and requires:

- the **reducer** must not raise `PEP_A13_TYPE_UNSUPPORTED` — it does today, so the gate fails;
- the **control** must not raise it either — it passes today, which proves the gate can tell a checker fix from a checker break.

A gate that only checked the reducer would go green the day someone broke the checker entirely. The control is what makes a green
meaningful.

## The false green, and what caused it

My first wiring bound the gate to the A2 pin through the suite's `envmap`:

```
A13 assignment-target defect    PASS      A13 GATE: PASS - reducer accepted, control accepted
```

That is wrong. `D:\Projects\wt-a3-dbea` (`e07e278`) **has no `pep_sectional.py`** — it predates the sectional driver — so
`build-c23 --sectional` there never enters the bound-chunk path where the defect lives. Both fixtures "passed" because neither was
measured.

Two fixes:

1. **The gate refuses to measure a tree without the path.** If the root lacks `pep_sectional.py`, or that file contains no
   `bound-chunk`, it prints `CANNOT RUN` and exits **3** rather than reporting a pass it cannot support.
2. **Exit 3 is now a SKIP in the runner, never a pass.** Previously only a missing script skipped; any non-zero exit was a FAIL, so
   3 would have been misreported as a failure instead. "Cannot run here" is neither.

The gate also now reads `PEPIN_CA_ROOT` from the **ambient** environment rather than from the suite's `a1`/`a2` roots, because
binding it to a pinned worktree is what produced the false green.

## The suite now

```
A4 oracle replay (13 pins)      PASS
A4 normative boundary (17)      PASS
A1 semantic oracle (23)         PASS
A1 sectional merge (11 probes)  PASS
A2 DIVERGENCE-2 (16)            PASS
M-1 gate calibration            PASS
Seed vs emitted differential    PASS
Compiler A contract (14 cases)  FAIL    7/14 match PEP0_SUBSET.md
A13 assignment-target defect    FAIL    pep_checker_a13.pep L1933

9 gate(s) ran, 2 failed, 0 skipped — A3 GATES: 2 FAILING
```

Two failures, both real, both owned elsewhere: the contract question at A4 and the checker defect at A1. Neither is a defect in
the emitter or in A1's integration, and both gates flip to PASS without edits here once their owners act.

## Why I am comfortable leaving the suite red

A green suite that cannot see the defects the mission is actually blocked on is worse than a red one. The two red gates are the
two things standing between this campaign and a tracked compiler A.

## Limits

- The A13 gate measures whichever tree `PEPIN_CA_ROOT` names; unset, it skips. A skip is reported as a skip.
- The contract gate measures the committed fixture C from A3-159, not a tracked build.
- Neither gate is evidence about the campaign branch, which has none of this work.

REF GH #16. Related: `6728678168` (A3-167), `6728442644` (A3-162, the contract gate).