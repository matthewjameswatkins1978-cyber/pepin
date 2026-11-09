# FINDING BOOT-A3-198 — the loop budget is about four units, and scan_value needs thirteen

**Measuring branches and calls together gives a boundary rather than two thresholds. Roughly: each conditional costs one unit, each
pair of calls costs one unit, and about four units fit. `scan_value`'s loop spends about thirteen.**

Seed blob `f8f476198f`. A4 `1f98045d` source, annotations, driver patch, A3-184's 20-function BASE dependency set, `scan_value`'s
88-node prologue, loop body of N trivial `if`s and M `skip_ws` calls plus one increment.

## The grid

| | 0 calls | 2 calls | 4 calls | 6 calls |
|---|---|---|---|---|
| **0 ifs** | (empty loop refused) | ok | ok | ok |
| **1 ifs** | ok | ok | ok | **STEP** |
| **2 ifs** | ok | ok | **STEP** | STEP |
| **3 ifs** | ok | **STEP** | STEP | STEP |
| **4 ifs** | **STEP** | STEP | STEP | STEP |

The diagonal is clean: **a conditional costs about what two calls cost**, and the boundary sits at roughly four units.

- 3 ifs + 0 calls = 3 units → ok; 4 ifs = 4 units → STEP
- 2 ifs + 2 calls = 3 units → ok; 2 ifs + 4 calls = 4 units → STEP
- 1 if + 4 calls = 3 units → ok; 1 if + 6 calls = 4 units → STEP

## What scan_value spends

Roughly **10 conditionals and 7 calls** in its loop ≈ 10 + 3.5 ≈ **13 units** against a budget of about **4**.

So the loop needs to do roughly **a third** of its current work per iteration. That is not a tweak to branch structure or to call
placement; it is a different decomposition, or it is not supportable.

This supersedes A3-190's "about 3 conditionals fit" and A3-197's "six calls fit" as separate statements — they were the same boundary
seen along two axes.

## What it says about the three options

| option | reading of the grid |
|---|---|
| reduce both axes in the loop | needs 13 → 4, a 3× cut in the loop's whole workload |
| split into sequential passes | each pass must itself fit in ~4 units; a pass that loops and calls may or may not |
| **narrow the contract (A3-176)** | needs none of this; measured at 9 of 10 runbook sections |

The grid makes the first option's size explicit rather than a matter of opinion. That is its value: not that the fix is impossible,
but that anyone choosing it now knows it is a threefold reduction of the loop's work, not a rewrite of its shape.

## Trust in this result

Every cell used the same dependency set, valid Pep, a real function's prologue, and varied exactly two parameters. No cross-run
comparison, no synthetic stand-in, no truncation. The one odd cell — 0 ifs, 0 calls — is an empty loop body being refused for a
different reason, not a measurement of the budget, and is marked as such rather than counted.

## Limits

- Uniform costs assumed: `skip_ws` for calls, `qi + k <= n` for branches. Different callees or condition shapes may cost differently,
  and `scan_value` uses `byte_at` four times in one `||` chain whose short-circuiting I cannot price from outside.
- Prologue held fixed at `scan_value`'s 88 nodes; a different prologue shifts the boundary (A3-189).
- "About four units" is a fitted reading of nine cells, not a stated constant of the compiler.
- One revision, sectional path only.

REF GH #16. Unifies `6729513467` (A3-190) and `6729673976` (A3-197).