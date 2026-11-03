# Scaling axis at `8406206` — the checker's budget is spent per NODE, not per nesting depth (my prediction was falsified)

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slices 4/6: give S2 a target curve instead of a single ceiling) · **Evidence label:** `TESTED`
**Measured in:** scratch tree `8406206` (`0c5f12b` + `cf02095`; local only, never pushed, removed after measuring — not an integration candidate)
**Instrument:** `verification/probes/checker_axis_scaling.py` (new)
**Headline:** breadth and depth both exhaust the checker at **exactly 60 nodes** (ratio 1.00). My stated hypothesis — that depth would be the binding axis — is **falsified** and is reported as such.

## Curves (boolean-chain family, one axis varied at a time)

| axis | generator | last success | first refusal |
|---|---|---|---|
| **breadth** | `x == 0 && x == 1 && … && x == k` | rung 20 → **60 nodes** (283 B) | rung 21 → 96 nodes (294 B), `PEP_RUNTIME_STEP_LIMIT` |
| **depth** | `x == 0 && (x == 1 \|\| (x == 2 && …))` | rung 12 → **60 nodes** (219 B) | rung 13 → 64 nodes (232 B), `PEP_RUNTIME_STEP_LIMIT` |

- **D1 held** — breadth has a measurable ceiling (60 nodes), well above 2.
- **D2 held** — depth has a measurable ceiling (60 nodes).
- **D3 FALSIFIED** — `breadth/depth = 60/60 = 1.00`, not the required ≥1.5. **Depth is not the binding axis.**
- **O1** — the refused rungs are seed-valid (`valid`), so the ceilings are the budget, not the language.

Depth rungs ≥ 18 arms additionally fail at *parse* (the parser's own budget), which is the same wall measured earlier and not a separate finding.

## What this means for A1's S2 work

1. **Cost is node-count driven, within measurement resolution.** A 60-node flat chain and a 60-node deeply nested expression die at the same point. So the lever is **steps per node**, not a depth-specific special case: any S2 change that removes work per node helps uniformly; one that only flattens nesting will not move the acceptance row.
2. **60 nodes is a hard, repeatable boundary on this family** — and it sits just under the 64 nodes the plain `lets` family reached in the cost profile. Two different families converging on 60–64 nodes is strong evidence that the *budget*, not the shape, is what runs out; shape only decides how many nodes a given byte count buys.
3. **This sharpens the 66-node row's status**: 66 is ~10 % past a boundary that three independent generators all hit at 60–64 nodes. That is a much smaller gap than "we need an order-of-magnitude win", and it is consistent with A1's reported near-misses (failure point moving by tens of steps rather than clearing).

## Honest scope and self-report

- Two generators, one family (boolean expressions inside one function). Deeply nested *statements* (nested `if`/`while` bodies) are a different axis and were not measured; depth there might behave differently.
- Nodes here are AST node counts from the transport, so "60 nodes" is comparable only within this instrument.
- The ceiling is bracketed (last success vs first refusal), not exact.
- **Self-report:** I predicted depth-driven scaling in the probe's own claim set and the data contradicted it. I left the claim in and let it falsify rather than rewriting the prediction to fit the result. That is the second time this mission that the honest outcome was "my hypothesis was wrong" (the first was the "sub-pass outlasts the whole checker" expectation).

## Reproduce

```powershell
python verification\probes\checker_axis_scaling.py <scratch-tree-with-checker>   # exit 1 (D3 falsified, as designed)
```
