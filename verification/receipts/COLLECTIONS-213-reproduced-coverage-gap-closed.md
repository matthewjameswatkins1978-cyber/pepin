# Coverage gap closed + headline reproduction — `test_c23_collections` (129 tests / 213 failures) (2026-10-30)

## The gap

A2's branch carries **`tests/test_c23_collections.py` (129 test
methods)** and `stdlib/collections.pep` — a module absent from A1's
line and therefore **never run in this lane before**: my "all modules"
baselines (rounds 9/23) used the A1-branch set (15 files; A2-branch
set = that minus {textbuf, driver_validation, classifier} plus
{collections, str_contains, nested_record}). Every prior A2-own run
covered str_contains/cli/nested only.

## Independent run at current pin A2 `26be4be`

| metric | my run | report claim |
|---|---|---|
| tests | 129 | (same module) |
| duration | 3,002 s | — |
| **failures** | **213** | **213** ✓ exact |
| code histogram | **182 × `PEP_RUNTIME_STEP_LIMIT`** | "all budget or unsupported" |
| remainder | 213 − 182 = **31** | **"31 unsupported cases"** ✓ exact |

**Both headline numbers reproduce independently** (213 total, 31
non-budget). The top-ranked code by a wide margin is the step limit —
consistent with the budget characterization; I did not individually
re-enumerate the 31 (their per-helper attribution — 16 to
`bool_true_majority`, family B unmapped — was read and is consistent
with my Wall A/B accounting: budget walls vs construct refusals, zero
wrong-value codes among the dominant groups).

## What this changes

1. **Coverage claim qualified:** "all modules at current pins" now
   holds for BOTH branch sets — A1-branch 15 modules (272/3, turn 23)
   plus A2-branch's extra `test_c23_collections` (213 failures, this
   turn) and the already-covered str/nested modules.
2. The report's collections work (impact measurement, two-rules
   split, family-B gap) is now **double-sourced at the totals level**;
   their family-B minimal-repro hunt remains open — my four loop/accum
   probes all EMIT (4,998/4,805/4,752/4,619 B), so plain loop
   accumulation is NOT family B's trigger; the trigger hides in the
   actual helper bodies (`stdlib/collections.pep`), which I located
   for the next probe round.

Blocker map unchanged (Wall A, Wall B, design trigger). Replay
**163/163**.
