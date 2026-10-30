# Wall B deepened — all-in-one countdown headroom collapsed to zero across the series (2026-10-30)

New measurement of the a14 all-in-one contract's headroom, before vs
after the parser/checker series. Clean controls, sequential runs.

## The ladder

| program (via a14 harness `emit_c23`, shared 100k) | `46bf1c0` (pre-series) | `a0e682a` (current) |
|---|---|---|
| `countdown(0)` (trivial body) | **emitted** | **STEP_LIMIT** |
| `countdown(6)` | **emitted** | **STEP_LIMIT** |
| `countdown(100)` | **emitted** | **STEP_LIMIT** |
| ladder 0/1/3/6/10/50/99 | (emits) | **ALL STEP_LIMIT** |

**Headroom for this shape went from "fits even 100" to negative —
even a 5-line program no longer fits the shared invocation.**

## Controls and positions

- **Host unchanged**: `pep_ocaml.ml` identical across
  `46bf1c0..a0e682a`, `tool_step_budget = 100_000` — the variable is
  the Pep-side work, not the budget.
- **Death position (current):** both `countdown(0)` and `countdown(6)`
  die at **bundle 6153 = `pep_c23_emitter.pep` line 499 = the closing
  brace of `pep_c23_c_scalar_type`** — a 5-line trivial function that
  emit touches early for return/param types. Identical positions for
  trivial and larger programs ⇒ parse+analyze consumed ~the whole
  invocation before/during emit's first type mappings; the position
  names where the shared budget emptied, not a cost center in that
  function (exhaustion-position caveat, applied consistently).
- **Staged path unaffected:** `a0e682a`'s new driver test emits
  composed recursive calls green (13/13) — the staged contract has the
  headroom the all-in-one lost (RECONCILIATION receipt, now sharpened).

## What this adds to the Wall B decision

The all-in-one contract didn't just oscillate — across
`ae91bdc`+`e37218a`+`eda6a0f` its effective capacity for countdown
shapes **collapsed to zero** (chains + analyzer-staging overhead inside
one invocation). The migration option (a14 → `emit_c23_checked`) now
looks less like tidiness and more like the only route to green a14
without re-deriving the pre-series cost profile. Isolating WHICH stage
(parsers chains vs `e37218a` analyzer) dominates would need per-stage
step instrumentation — noted as the next probe if wanted.

Replay **172/172**; INDEX current.
