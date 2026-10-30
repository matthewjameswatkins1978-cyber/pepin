# Fix-status round 2 — A2 `7b69964` / A1 `9263ea9` (2026-10-30)

Second builder response to the emit-step-budget finding
(`edbe3b6` "Reuse function result type in loop lowering" +
`7b69964` "Skip irrelevant loop-local binding lookups"; A1 added
`7bfa690`+`9263ea9` checker scan/validation chunking). Sequential runs,
detached read-only, no builder file edited.

## Verdict: further partial recovery — small-countdown class fixed, ≥100 class and closures still over budget

| measure | `f184580` (round 1) | `7b69964` (now) |
|---|---|---|
| A2-own a14 | 4 failures | **3** — `source_backed` recovered; depth still failing |
| combined a14 (A1 `9263ea9` + A2 `7b69964`) | 4 | **3** (recursion-contract, depth, unsupported exemplar) |
| combined classifier | 5 errors | **5 errors — unchanged** |
| combined nested module | 5 errors (ascii_continue) | **5 errors — unchanged** |
| combined str_contains | 16/16 | OK |
| combined cli+driver | — | **17/17 OK** |

## New measurement: sharp emit boundary at literal 99/100

Countdown emit probe on `7b69964` (same program, one constant):

| literal | result |
|---|---|
| 0, 6, 7, 10, 20, 40, 70, **99** | **emitted** |
| **100**, 510, 511 | STEP_LIMIT at `7696:59` (same position) |
| 2000 | STEP_LIMIT at `7672:42` (different position) |

The boundary is exact at **99/100** — a value-linear cost signature
(emit work grows with the literal; the fixed budget is crossed at
exactly 100 on this shape). The classifier/`ascii_continue` closures
fail at the same stage regardless of literals (their programs contain
larger structures, not literals — same wall, different content).
Mechanism remains builder territory; the sharp threshold is the
profiling lead: something in emit scales with integer-literal magnitude
(partial evaluation / digit processing / value-driven unfolding are the
candidate shapes — the report lane's "profile the emitter" advice now
has an exact probe).

## A1 `9263ea9` (clean) — green

a14 **2 known only**, classifier **1/1**, claimed suites
a13+nested+cli **104/104**. Their declaration-scan reduction and
chunked validation land without regressions.

## State of the original finding

- Fixed so far: union-loop-sums (round 1), small-countdown /
  `source_backed` (round 2).
- Outstanding: `test_recursive_native_calls_enforce_pep_depth`
  (≥100 literals), classifier slice (5 subtests),
  `ascii_continue` (5 subtests) — all emit-stage
  `PEP_RUNTIME_STEP_LIMIT`.
- The standing suggestion (full `test_a14_c23` on the A2 branch pre-push
  is the only way their lane sees depth-class regressions; classifier
  needs the integrated state) remains unactioned but increasingly
  evidenced: their focused receipts keep passing while a14 on their own
  branch sat at 3→4→3.

Replay: corpus/`replay.py`/base untouched — **161/161** current.
Prior receipts: `FINDING-a2-emit-step-budget-regression-8e076e2.md`,
`FIX-STATUS-a2-cfa88d2-partial.md`.
