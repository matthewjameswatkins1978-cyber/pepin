# Reconciliation — the emit-budget finding decomposes into TWO walls on TWO invocation contracts (and a correction to my round-2 attribution)

**Round at A1 `e0d1f89` / A2 `8677492` (2026-10-30).** Sequential
runs, detached read-only, no builder file edited. This receipt both
advances and **corrects** the earlier finding — read the correction
first.

## Correction (round-2 attribution was wrong)

I characterized the countdown ≥100 failure as "value-linear **emit**
cost". Measured two-path probe on the *same trees* disproves that:

| path | countdown(99) | countdown(100) | countdown(510) |
|---|---|---|---|
| `pep_c23.py` **staged** emit (precomputed `parsed`,`checked`) — A2-own | OK | **OK** | **OK** (4,695 B of C) |
| same staged emit — combined (A1 checker + A2 emitter) | OK | **OK** | **OK** |
| **a14 harness** (`emit_c23`, `arguments: []`) — same trees | emitted | **STEP_LIMIT** | **STEP_LIMIT** |

Staged emit of `countdown(510)` succeeds on every state tested. The
countdown wall is **not** emit-only cost. The earlier position mapping
(bundle → emitter source line) showed where the *shared* budget died,
not who consumed it — I attributed the consumer incorrectly.

## Why the two lanes were both right

Source of the two entry points (`tests/pep_c23_emitter.pep`):

```pep
fn emit_c23() -> PepC23Emission {            -- a14 harness registers THIS
  let parsed = parser_parse_program()         -- parse INSIDE
  ...
  let checked = analyze_parsed(parsed)        -- full analysis INSIDE
  return emit_c23_checked(parsed, checked)    -- then emit — all in ONE 100k invocation
}
fn emit_c23_checked(parsed: ParserProgress, checked: CheckerReport) -> ...
```

- **a14 harness** registers `emit_c23` with empty arguments → parse +
  analyze + emit share **one** 100k step budget per invocation.
- **`pep_c23.py`** (both lanes) registers `emit_c23_checked` with
  precomputed `[parsed_value, checked_report]` → each stage pays in its
  own invocation; emit's invocation is emit-only.

So builders' green focused receipts (staged path) and my a14 failures
(all-in-one path) are **both correct measurements of different
contracts**. This is the root of every round of apparent disagreement.

## The finding now decomposes into two distinct walls

**Wall A — staged emit cost for large closures (the original finding;
STILL OPEN).** With A2's emitter since `8e076e2`, emit-**only** cost
exceeds 100k for the classifier closure and `ascii_letter ||
ascii_digit`: both fail on the *staged* path in the combined state
(classifier 5 errors, ascii_continue 5 errors — unchanged through
`7b69964`/`8677492`). A1's own line passes them (old emitter). This is
a genuine emitter-cost regression; A2's branch cannot see it (tests
absent or skip-guarded there).

**Wall B — a14's all-in-one headroom (reattributed).** `countdown ≥
100` fails only because parse+analyze+emit share 100k in `emit_c23`;
the shared cost crossed when A2's emit cost rose (exact 99/100 boundary
stands as a measured fact of *that* path; its internal mechanism —
what in parse/analyze scales with the literal — is unattributed and now
belongs to bisecting the three stages separately, which the staged path
makes possible). The a14 depth test (literal 510) lives on this wall;
`source_backed`'s `countdown(6)` sits below the boundary (≤99 emits on
the a14 path), which is why it recovered at `7b69964`+ and stays green.

**Practical consequence for the builders:** the a14 harness may be
measuring a legacy contract (`emit_c23`) that the staged pipeline was
built to escape — whether the harness should migrate to
`emit_c23_checked` (or the host should budget stages separately inside
`emit_c23`) is an owner decision. Wall A needs no such decision: it is
raw emitter cost and needs the fix already requested.

## Round numbers at current pins

| state | result |
|---|---|
| A1 `e0d1f89` clean | a14 **2 known**, classifier **1/1**, claimed suites **115/115** (a13 84, cli 8) — green; `PEP_TOOL_VALUE_LIMIT`→`INCONCLUSIVE` labelling lands cleanly |
| A2 `8677492` own | a14 **3** (contract, depth, exemplar; emitter unchanged since `7b69964`); nested **43 tests: new ascii_letter + staged-depth-boundary both PASS**; str 16 OK |
| combined `e0d1f89`+`8677492` | a14 **3**, classifier **5 errors**, nested **5 errors** (ascii_continue only), str OK |

A1's `e0d1f89` note explicitly adopts my finding as "an integration
blocker pending A2 repair and independent retest" — consistent with
Wall A being open.

## Flakiness note (honesty)

The A2-own nested module reported 3 errors in one full run; the same
module passed on rerun **and** in isolation. Those three are
load-sensitive flakiness, not deterministic failures — reported here so
the transient is on record and not mistaken for a regression (distinct
from, and milder than, the parallel-batch contention gotcha already
saved).

Replay: corpus/`replay.py`/base untouched — **161/161** current.
