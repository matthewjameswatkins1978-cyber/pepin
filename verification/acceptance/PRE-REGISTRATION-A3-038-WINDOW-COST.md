# PRE-REGISTRATION A3-038: does a dependency-closed window actually EMIT inside the budget?

**Seat:** A3. Follows BOOT-A3-037. **Written and committed before measurement.**

## The unanswered question, and why it decides A2's next move

BOOT-A3-037 established the shape of a *checkable* window for the frozen app: **39 of `main`'s 44
nodes** (16 for the other window). BOOT-A3-032/033 established that the whole 44-node `main` exceeds
the 100k budget. Nobody has measured whether a 39-node window **emits**, and I explicitly declined to
predict a pass.

That number decides whether the window route is worth building at all:

- If a 39-node window emits comfortably → the route works and the remaining work is A2's design of how
  to assemble two partial bodies into one correct function.
- If it does not emit → the window route cannot solve capacity for this app, and A2 should spend the
  time on cheaper lowering (BOOT-A3-033's quadratic term) instead.

Either answer saves A2 from building the wrong thing.

## What will be measured, and what will NOT be claimed

For each window I will invoke `pep-c23-unit` and read `last_execute_steps`.

**A window is semantically incomplete**: it contains half of the loop body, so an emitted unit would
compute the wrong answer. **This is a COST probe only.** It is not an application, not a gate, and it
will not be compiled into a binary that is run for correctness. Any figure here is "the emitter's cost
to lower this chunk", nothing more.

## Predictions

Using BOOT-A3-033's flat fit `steps ≈ 380.75·n + 35.68·n²` (a **lower bound** for nested shapes, which
under-predicted by 17.2% at n=30):

| # | Claim | Falsified if |
|---|---|---|
| C1 | the 39-node dependency-closed window **emits** (does not trip 100k) | it refuses with `PEP_RUNTIME_STEP_LIMIT` |
| C2 | its measured steps land in **70,000–95,000** (fit ≈ 69,128, plus the known nested under-prediction) | outside that band |
| C3 | the 16-node window emits, at **below 40,000** steps (fit ≈ 15,222, generously banded) | it refuses or exceeds 40,000 |
| C4 | the 39-node window costs **materially less** than the whole 44-node `main`, which is already known to exceed 100,000 | any emission cost ≥ 100,000 |

C1 is the decision-relevant one. C2/C3 are calibration — if they miss, the fit's usefulness is further
bounded and I will say so rather than quietly re-fitting.

## Ambiguity I may hit, and how it will be reported

The emitter may refuse a window for a **capability** reason rather than the budget (it has never been
asked to lower a partial function). If so, that is recorded as the first refusal with its exact
message, and C1 is reported **NOT TESTED** for the budget question — not as a pass and not as a
budget failure. Distinguishing "too expensive" from "not supported" is the whole point.

## Method

- Frozen app `pepin-source-scan.pep` (blob `4a44dd65…`), A1 `86ff953` tree, fresh worktree, seed built
  there.
- Window construction identical to BOOT-A3-037's final form: window A = declarations + first half of the
  loop body (16 ids); window B closed = subtree half + locals' subtrees + parameter + type annotation +
  return (39 ids); both spine-closed as the plan requires.
- Steps read from `{"op":"metrics"}` immediately after each `pep-c23-unit` invocation.
- Cap unchanged. A3 proposes no cap change and implements nothing in the emitter.

## Scope guard

A3 owns only `verification/**`. No edits to A1's contract/checker, A2's emitter, or A4's app.
