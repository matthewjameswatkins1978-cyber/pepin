# ACCEPT BOOT-A3-128 — cost model validated: a 9-`say` if emits only while the function is ≤ ~173 nodes, and the fitted crossing is 176

**The linear model from A3-125/126 survives a prediction test. Fitting 462 steps per function node to the 141-node point
predicts the 100,000-step crossing at **176 nodes**; measuring around it puts it between **171 nodes (98,745, emits)** and
**177 nodes (limit)**. And at 221 nodes — `main`'s exact size — the same 9-`say` if hits the limit, so statement 23's
failure is the model applied, not an outlier.**

Seed blob `f8f476198f`. Emitter `3d9ac7d3`. Driver A1 `9bf18699`.

## The crossing, measured

One `if` with nine `say(int_text(N))` statements, padding grown to enlarge the function; **the fragment itself is unchanged
in every row**. Force-chained so every row is a merged report.

| function nodes | steps | outcome |
|---|---|---|
| 141 | 83,985 | EMITTED |
| 161 | 93,775 | EMITTED |
| **171** | **98,745** | **EMITTED** |
| **177** | 100,001 | **LIMIT** |
| 183 | 100,001 | LIMIT |
| 191 | 100,001 | LIMIT |
| **221** | 100,001 | **LIMIT** ← `main` is 222 |
| 241 | 100,001 | LIMIT |

Fitted from the 51–141 range (`slope = 462 steps/node`, `intercept = 18,843`), the crossing lands at **176 nodes** — one node
from where it was measured to fall. That is the first time this model has been used to predict something it was not fitted
on, and it held.

## The practical threshold

**A `if` containing nine `say(int_text(N))` statements emits only while the enclosing function is ≤ ~173 nodes.** `main` is
222, so statement 23 is over by about 46 nodes' worth of cost — roughly 21,000 steps.

That reframes the two available remedies precisely:

- **Shrink the function** — remove ~46 nodes from `main` and #23 would emit. Not attractive: it means changing A4's source to
  suit an emitter cost profile.
- **Remove the slope** (the child-index fix) — the cost then no longer depends on function size at all, and the extrapolated
  intercept of ~18,800 is **19% of the budget** at any size. Validated in-range over 141–221 nodes; the intercept itself is
  still an extrapolation to zero nodes, and I have not measured a post-fix emitter.

The second is the right one, and this run strengthens it: the same fragment goes from `LIMIT` to under one-fifth of budget as
function size grows, so the fix buys more the larger the program — which is the direction a self-hosting compiler needs.

## What this does not change

A3-127's corrected magnitude stands: the fix removes ~84% of statement 23's cost at 222 nodes, about **6.4×**, not the 50× I
published in A3-126 and withdrew. The constant-factor work A2 already did (`prepend+reverse`, 752 steps) remains worth having
and remains irrelevant to this term.

## Limits

- One shape: nine `say(int_text(N))` statements in one `if`. A different branch body has a different intercept and a
  different slope; the **linearity in function size** is the transferable finding, not the 462 coefficient.
- Padding statements are `var pN = N`, which also increase the carried binding count, so part of the slope could be binding
  lookup rather than child lookup. I have not separated the two. This does not affect the threshold, only the attribution.
- Intercept extrapolation as stated; no post-fix measurement exists.
- All rows force-chained; a raw whole-function report may differ.

## Reproduce

`fn a3_x(source: SourceBytes)` with `var e = 0`, `let n = byte_length(source)`, `if e == 0 { 9 × say(int_text(k)) }`, P
`var pK = K` statements, `return e`. Force-chain, emit statement 2 as a fragment, read `metrics.last_execute_steps`, and sweep
P.

REF GH #16. Parents: `6725672583` (A3-125 law), `6725694094` (A3-126 mechanism), `6725722100` (A3-127 correction).