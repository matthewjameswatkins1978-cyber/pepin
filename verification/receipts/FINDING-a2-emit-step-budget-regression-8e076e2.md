# FINDING — A2 emitter delta `7bfb819..8e076e2` introduces an emit-step-budget regression (milestone-level)

**Severity: high.** Previously-green native tests fail at the **emit
stage** (`PEP_RUNTIME_STEP_LIMIT`) after A2's newest push — including
the real-lexer classifier slice (the packet's "already native-verified"
milestone) and a core a14 depth-guard test. Builder-owned files
untouched; this receipt is the only artifact.

## Attribution chain (all states measured this turn, sequential runs)

| state | a14 | classifier | nested module (new) |
|---|---|---|---|
| A1 `d83ac67` clean (its own emitter) | **2 known only** | **1/1 OK** | n/a |
| A2 `7bfb819` own (**baseline before the push**) | **2 known** (their variant) | n/a | n/a |
| A2 `8e076e2` own (this push) | **3 — depth test NEW** | n/a | **1 error** (deterministic) |
| cross: A1 `f7efa23` + A2 `8e076e2` emitter | **depth FAIL** | **5 errors** | n/a |
| full combined: A1 `d83ac67` + A2 `8e076e2` emitter | **3 failures** | **5 errors** | **6 errors** |
| *previous round* `f7efa23` + `7bfb819` emitter | 2 known | 1/1 | n/a |

**Regression window = exactly A2 `7bfb819..8e076e2`** (emitter +110
lines: loop byte-locals/conditionals, ordered conditionals). It
reproduces with A1's *previous* checker and on A2's *own* branch with
their own bundled checker — **the emitter delta alone is sufficient**;
A1's `d83ac67` chunk change is exonerated (clean green).

## Failing mode: emit-stage step budget on cheap programs

Every new failure is `PEP_RUNTIME_STEP_LIMIT` inside `emit checked
source` (checker completes: parse 3 / typecheck 3 / cache 0), on
programs that emitted cheaply one round ago:

| failing test | program | position (mapped into emitter source) |
|---|---|---|
| `test_recursive_native_calls_enforce_pep_depth` | `countdown(510)` guarded recursion | `8144:42` → emitter line **~3241**/3263 (tail of `emit_c23_checked`) |
| `test_real_lexer_ascii_classifiers…` (5 byte subtests) | classifier closure | emit-stage step limit (same code) |
| `test_lucy_ascii_continue_composes_real_lexer_helpers` (5 subtests) | `ascii_letter(b) \|\| ascii_digit(b)` | `4912:8` → emitter line **9** |
| `test_recursive_union_list_loop_sums_multiple_leaves…` | union list loop sum | `7582:67` → emitter line **~2679** |

Step budget is executed-step count (host `tool_step_budget`), not
document size — so the new emitter's traversal is consuming materially
more steps for these shapes (likely a new per-node iteration in the
loop/conditional machinery). Exact hotspot is builder territory; the
fact and window are established here.

## Why the builders' own receipts didn't catch it

- A2's slice note reports "focused regression passed 1/1" — the full
  modules were not run at this tip: their own `test_a14_c23` went
  **2 → 3 failures** at `8e076e2`, and their own new module has a
  deterministic error (`union-loop-sums`).
- The classifier slice and `ascii_continue` test **do not exist on
  A2's branch** (A1-line tests), so only the integration state exposes
  those.
- `ascii_continue` is *skip-guarded* on A2's branch with the message
  `'Pep-written checker exceeds its fixed budget on this real-lexer
  closure'` — A1's checker now clears that wall, the test unskips, and
  what fires underneath is the **emitter's** budget. The skip message
  names the wrong stage for the post-integration reality (the
  budget-masking pattern the report lane has now documented repeatedly).

## What is NOT affected (verified this round)

- A1 `d83ac67` clean: a13+nested **93/93**, a14 2-known, classifier 1/1
  — A1's line is green; their `f7efa23` claims stand (109/109 last
  round).
- Combined `str_contains`: **14/14 OK** (SourceBytes tests still green
  with the new emitter).
- The two long-known a14 failures (recursion contract, length/st-type
  exemplar) are unchanged and separate from this regression.

## Methodology notes (honesty)

- Sequential runs are authoritative: parallel pep.ps1 batches produced
  transient extra errors (4→1, 9→6 observed); every number above is
  from a settled sequential run, and both headline tests were
  additionally reproduced as single-test runs.
- A2's branch note "no native C compilation/execution under the hold" is
  stale framing: #22 cleared native execution; all runs here executed
  natively with Defender on, no exclusions.

## Suggested builder action (owner's call)

1. Before the next push: run full `tests.test_a14_c23` on the A2
   branch — it fails 3, not 2.
2. Profile emit-step consumption of the new loop/conditional lowering on
   the four shapes above; the budget (host 100k) is unchanged, the cost
   is new.
3. Re-check the `ascii_continue` skip guard's stage message before the
   next integration.
