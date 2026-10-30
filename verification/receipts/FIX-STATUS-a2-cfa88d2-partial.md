# Fix-status addendum — A2's `cfa88d2` response to the emit-step-budget finding

**Verdict: partial fix, regression net-worse.** Follow-up round at
A1 `e603e79` / A2 `f184580` (2026-10-30, sequential runs, detached
read-only worktrees, no builder file edited).

## What the builder's fix did (verified true)

- `cfa88d2` "Reduce repeated recursive union list analysis":
  `test_recursive_union_list_loop_sums_multiple_leaves_with_clang_and_gcc`
  — **FIXED** (nested-module errors 6 → 5). Their slice evidence
  ("structural suite 41 tests passed with five existing step-limit
  skips", "recursive-list native test returns 42") reproduces on their
  branch.
- Technique visible in the delta: single-scan variant lookup replacing
  two full scans, validation loops skipped for iterated local recursive
  union lists, hoisted return-type lookup, plus a new fail-closed guard
  (`conditional-return specialization does not lower loops`).

## What it did NOT fix (still emit-stage `PEP_RUNTIME_STEP_LIMIT`)

| test | state at `f184580` |
|---|---|
| `test_recursive_native_calls_enforce_pep_depth` | **still FAIL** — on A2's own branch *and* combined |
| classifier slice (5 byte subtests, combined) | **still 5 errors** |
| `test_lucy_ascii_continue_composes_real_lexer_helpers` (5 subtests, combined) | **still 5 errors** (union-loop fixed, this not) |

## What got WORSE — new measurement, literal matrix

Emit probe across countdown literals on both A2 heads (same program
shape, one constant differing):

| program | `8e076e2` | `f184580` |
|---|---|---|
| `countdown(0/1/6/7)` | **emitted** | **STEP_LIMIT** (`7667:18`) |
| `countdown(510/511)` | STEP_LIMIT (`7670:5`) | STEP_LIMIT (`7637:43`) |

At `8e076e2` only large literals failed (which is why A2's own a14 was
3, not 4: `source_backed` contains `countdown(6)` and passed). At
`f184580` **the whole countdown class fails**, so `test_generated_c23_executes_source_backed_programs_under_clang_and_gcc`
— a core execution test — **newly breaks**:

- A2 own branch a14: baseline **2** (`7bfb819`) → **3** (`8e076e2`) →
  **4** (`f184580`)
- combined (A1 `e603e79` + A2 `f184580`): a14 **4** + classifier **5
  errors** + nested **5 errors** (str_contains 16/16 OK)

## Full state table this round

| state | result |
|---|---|
| A1 `e603e79` clean | a14 **2 known only**, classifier **1/1**, a13+nested+cli+driver **112/112** (a13 80→82, cli 6→7, all green) — A1 green; their budget-`INCONCLUSIVE` labelling lands without breaking the harness |
| A2 `f184580` own | a14 **4**; nested 41 pass + 5 skip (ascii_continue guard on-branch); str 16 tests pass |
| combined `e603e79` + `f184580` | a14 **4**, classifier **5 errors**, nested **5 errors**, str **16/16 OK** |

## Bottom line for the builders

1. The union-list dedup worked for its target; the countdown/
   classifier/ascii_continue emit-step class is **untouched and now
   broader** (value-independent: fails from literal 0 upward).
2. Because the countdown class widened, their own a14 lost
   `test_generated_c23_executes_source_backed…` — running full
   `test_a14_c23` on the A2 branch before push would have caught all of
   this (my original suggestion, still unactioned).
3. The failure moved from "large-literal dependent" to "all countdown
   shapes", which actually *simplifies* profiling: any countdown emit
   reproduces it in ~2s (`fn main() -> Int { return countdown(0) }`
   with the trivial base case is the cheapest reproducer).

Prior receipt: `FINDING-a2-emit-step-budget-regression-8e076e2.md`.
Replay inputs still unchanged — 161/161 current.
