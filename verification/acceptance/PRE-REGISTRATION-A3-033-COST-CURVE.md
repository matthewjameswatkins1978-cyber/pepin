# PRE-REGISTRATION A3-033: is the emitter's step cost linear or superlinear in chunk nodes?

**Seat:** A3. Campaign `LUCY-20261107-007`. Follows BOOT-A3-028.
**Written and committed before the measurement runs.**

## Why this decides something real

BOOT-A3-028 established the *levels*: a `while` alone costs 58.6–59.9k of the 100k budget, and one
extra nesting level inside it costs >41k steps. That told A2 the app is blocked on capacity. It did
**not** say what kind of fix is possible.

The two candidate worlds are very different:

- **Linear in node count.** Then the emitter's cost is inherent to the work, and the only levers are a
  smaller unit of emission or a bigger budget. Since the cap is frozen, that means structural change.
- **Superlinear in node count.** Then the cost is an artefact of *how* the emitter walks the tree —
  the visible shape `for branchStatement in nodes` inside every nested lowering suggests an
  O(nodes × body) scan — and a child-index would cut the cost for the *same* program. That is an
  algorithmic fix inside A2's own lane, no cap change and no chunk restructuring.

A2 is currently asking A1 for a chunk window. If the cost is superlinear, that ask may be solving the
wrong problem. This is worth one measured curve.

## Predictions, fixed before measurement

Family: `while !(byte_length(source) <= o) { <N flat assignments>  o = o + 1 }`, single function,
N = 4, 5, 6, 7, 8.

| # | Claim | Falsified if |
|---|---|---|
| P1 | **steps/node rises monotonically with N** within this family | any N+1 has a lower steps/node than N |
| P2 | from BOOT-A3-028, L04 (36 nodes) is 1,665 steps/node; I predict **N=6 (≈44 nodes) exceeds 1,900 steps/node** | N=6 is at or below 1,900 |
| P3 | **N=8 (52 nodes) exceeds 2,300 steps/node** — i.e. clearly superlinear | N=8 at or below 2,300 |
| P4 | A quadratic fit `steps ≈ a + b·nodes²` explains the observed points better than a linear fit `a + b·nodes` (lower residual on the points that succeed) | linear fits better |

Exact step counts come from the session `{"op":"metrics"}` `last_execute_steps` instrument, which
resets per `execute` and ticks per evaluated node — the same instrument BOOT-A3-028 used.

**I am predicting superlinearity.** If the curve is linear, that is a clean falsification and it
matters: it would tell A2 the chunk window is the right ask and stop anyone hunting an algorithmic
fix that does not exist. A falsified prediction here is worth as much as a confirmed one.

## Method and honesty boundaries

- Measured on **A1's integrated `scratch/a1-dogfood-scan@4e325e0`**, which carries A2's fixed emitter
  (blob `3f5b9582`) and the chunk tooling. Fresh detached worktree, seed built there.
- Variants are A3-authored cost probes, not language test cases; they assert nothing about meaning.
  Only `nodes`, `steps` and emitted/refused are reported.
- A row that is refused still reports its `last_execute_steps` (100,001 = tripped the budget), which
  is a **lower bound**, not a measurement of what it would have cost. Refused rows are excluded from
  the fit and marked as bounds.
- **Correlation is not mechanism.** If the curve is superlinear I may *infer* that the per-level
  node scan is responsible; I will not claim to have proven it, because I am not instrumenting A2's
  code. The inference will be labelled as an inference.
- The cap is unchanged. A3 proposes no cap change and does not implement the emitter fix.

## Scope guard

A3 owns only `verification/**`. No edits to A4's app, A1's checker/host, A2's emitter/runtime, frozen
gates, budgets, `CURRENT`, manifest, master or release labels.
