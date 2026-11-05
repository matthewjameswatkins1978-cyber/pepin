# Decision note: does Road 1 need the monolithic 66-node checker row green?

Written 2026-11-05 by A1 (sole integrator seat) under PEP-FINISH-20261105-A1, "NEXT /
ARCHITECTURE". Measurement only: no checker change, no cap change, no frozen-test change,
no acceptance claimed. The decision is Matthew's; this note supplies evidence and one
question precise enough to answer.

## The question, stated once

Road 1 acceptance currently carries a red row: a whole-program check of the 66-node
`recpad-6` fixture exceeds the unchanged 100,000-step tool budget. Every real compiler
module is checked by **chunking** instead. Is a documented, independently verified
*staged* route sufficient to call compiler-source checking done for Road 1, with the
monolithic row remaining a documented red — or must the monolithic 66-node row itself go
green first?

## What is actually measured (all at `codex/p1-checker-cost-fix@3ff3bf1` unless stated)

1. **The red row is a cost boundary, not a semantic refusal.** Every fixture in the
   boundary suite is seed-valid; the failure is always `PEP_RUNTIME_STEP_LIMIT`.
2. **Monolithic cost is quantified.** Check steps across the frozen ladder are
   11,711 / 27,260 / 45,553 / 67,150 / 92,051 for 11 / 22 / 33 / 44 / 55 nodes, and
   100,001 (limit) at 66 nodes, expiring inside `record_declaration`. Least squares over
   the five valid points: `steps ≈ 13.1n² + 962n` — roughly 57k quadratic and 63k linear
   at n=66 (`docs/CHECKER_COST_SCOPING.md`, K2 section; reproduce with
   `python tests/probe_checker_phase_cost.py`).
3. **No single local fix reaches compiler scale.** Removing the whole quadratic term
   alone moves the ceiling to ≈104 nodes; removing the whole linear term alone to ≈87
   nodes. Independent ablation evidence already shows the cost is distributed across the
   scan family, not hoistable in one function. Pep has no indexed access, so an in-language
   index is itself O(n) per probe.
4. **Staged checking is real and bounded by the same budget.** On the real lexer, the
   pinned ledger reports five of ten top-level functions valid
   (`ascii_letter` 24, `ascii_digit` 12, `ascii_continue` 10, `advance_position` 33,
   `make_token` 55 nodes), four still step-limited (`utf8_check` 268, `make_cursor` 103,
   `make_progress` 125, `lexer_start` 59), and one transport-limited (`lexer_step`,
   1,513 nodes). `tests/test_lexer_chunk_ledger.py` passes at this head.
5. **A real 86-node closure checks monolithically** (`T5` = LexToken / LexCursor /
   LexProgress) at 65,181 steps — so the ceiling is shape-dependent, not a universal node
   cutoff.
6. **Trust boundary is scoped, not solved.** Stamps give target consistency (foreign /
   stale / omitted refuse); content authenticity is a trusted-producer assumption. The
   honest host is a pure transcription, so same-target forgery requires hand-constructed
   facts or a lying producer tool.

## What the red row does and does not tell us

It does **not** say the checker is unsound, nor that compiler source is uncheckable — the
lexer's own type closure checks at 86 nodes. It does say that *one invocation over an
arbitrary whole module* is unavailable at this cost model, i.e. the staged route is not an
optimisation of the monolithic route; it is the only currently available route for
compiler-scale state.

It also does **not** yet show the staged route covering a whole compiler module: five of
ten lexer functions are checked, and four of the remaining five fail for cost, one for
transport. So "staged covers compiler source" is half-true today and should not be claimed
as complete.

## Two candidate acceptance policies

**Policy A — monolithic row is part of acceptance.** Road 1 is not accepted until a
whole-program 66-node check is green under unchanged caps. Consequence: acceptance is
gated on a cost-model change of the kind already shown insufficient locally (a cross-layer
host-indexed node access, or staged-then-fused passes). This is a real engineering project,
not a slice, and it must be designed deliberately rather than discovered.

**Policy B — staged route is the acceptance route; the monolithic row stays documented
red.** Road 1 accepts compiler-source checking when (i) every top-level function of the
target module is checked in a chunk under unchanged caps, (ii) chunk facts are
revision-bound and ingress-refused when stale/foreign, and (iii) the uncovered set is
published with a named falsifier. Consequence: today's honest verdict is **NOT MET**, because
four hot lexer functions still fail for cost; Policy B changes what counts, not what is
true.

The distinction that matters: Policy B does not accept current state. It makes the remaining
blocker narrower and testable — "make `lexer_start`, `make_cursor`, `make_progress`,
`utf8_check` check in bounded chunks" instead of "raise an unbounded whole-module ceiling".

## Cheapest falsifier for each policy's premise

- Against Policy A being *necessary*: exhibit one real compiler module fully checked by the
  staged route with unchanged caps, all top-level functions, published uncovered set empty.
  If that exists, the monolithic row is a diagnostic, not an acceptance gate.
- Against Policy B being *sufficient*: exhibit a soundness property that only whole-program
  checking provides — e.g. a cross-function defect that staged chunks admit while the whole
  program refuses with the same seed oracle. None is published today; the laundering probes
  show the opposite shape (whole-program INVALID can become chunk VALID through forged
  facts), which is a trust-boundary issue, not an argument for monolithic checking.

## Question for Matthew (one decision, two parts)

1. For Road 1, is compiler-source checking satisfied by a **staged** route with a published
   uncovered set and revision-bound facts (Policy B), or does acceptance require the
   **monolithic** 66-node row green (Policy A)?
2. If Policy B: is the interim acceptance bar "uncovered set empty for the target module"
   (currently false: 4 hot lexer functions) — or "uncovered set published and each entry has
   a named falsifier" (currently true)?

No recommendation is smuggled into this note beyond that: under Policy B the current state is
still NOT accepted, and the next engineering target is per-function chunk checkability for
the four hot lexer functions, not a raised ceiling.
