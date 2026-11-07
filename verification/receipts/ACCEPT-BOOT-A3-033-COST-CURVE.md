# ACCEPT BOOT-A3-033 — the emitter's cost is quadratic in chunk nodes, not linear

**Verdict: P1, P2 and P4 confirmed; P3 NOT TESTED. 4/4 checks, prediction direction held.**

The headline is a number A2 can act on: over the measured range the cost fits
**`steps ≈ 381·n + 35.7·n²`** where `n` is the chunk's node count — a dominant quadratic term, with
the quadratic share rising from 69% at n=24 to **80.5% at n=44**. That decides the question this
slice was pre-registered to settle: the capacity wall is **largely algorithmic**, not just a
consequence of the program being big.

## Measured curve — `while !(byte_length(source) <= o) { <N flat assignments> o = o + 1 }`

Tree: A1's integrated `scratch/a1-dogfood-scan@4e325e0` (A2 emitter blob `3f5b9582`), fresh detached
worktree, seed built there. Instrument: `{"op":"metrics"}` → `last_execute_steps`, per-emission.

| N assignments | nodes | steps | steps/node | status |
|---|---|---|---|---|
| 1 | 24 | 29,725 | 1,238.5 | emitted |
| 2 | 28 | 38,636 | 1,379.9 | emitted |
| 3 | 32 | 48,705 | 1,522.0 | emitted |
| 4 | 36 | 59,932 | 1,664.8 | emitted |
| 5 | 40 | 72,317 | 1,807.9 | emitted |
| 6 | 44 | 85,860 | 1,951.4 | emitted |
| 7 | 48 | ≥100,001 | — | refused `PEP_RUNTIME_STEP_LIMIT` |
| 8 | 52 | ≥100,001 | — | refused `PEP_RUNTIME_STEP_LIMIT` |

Refused rows report only the budget trip, so their "steps" are **lower bounds**, not measurements.

## Pre-registered predictions

| # | Prediction | Result |
|---|---|---|
| P1 | steps/node rises monotonically with N | **CONFIRMED** — 1,238.5 → 1,379.9 → 1,522.0 → 1,664.8 → 1,807.9 → 1,951.4 |
| P2 | N=6 (≈44 nodes) exceeds 1,900 steps/node | **CONFIRMED** — 1,951.4 at 44 nodes |
| P3 | N=8 exceeds 2,300 steps/node | **NOT TESTED** — N=8 refused, so there is no measurement to compare |
| P4 | a quadratic fit beats a linear fit | **CONFIRMED decisively** — quadratic residual **2,502** vs linear **3.77 × 10⁸** |

P3 is reported as NOT TESTED deliberately. My first version of the check compared N=8's 100,001
boundary value against the threshold and produced a spurious FAIL from a boundary artefact; that
comparison was invalid and was removed rather than reinterpreted.

## The fit, checked against every point

`steps ≈ 380.7538·n + 35.6842·n²` (no constant term in the model)

| n | measured | predicted | Δ | quadratic share |
|---|---|---|---|---|
| 24 | 29,725 | 29,692.2 | −32.8 | 69.2% |
| 28 | 38,636 | 38,637.5 | +1.5 | 72.4% |
| 32 | 48,705 | 48,724.7 | +19.7 | 75.0% |
| 36 | 59,932 | 59,953.9 | +21.9 | 77.1% |
| 40 | 72,317 | 72,324.9 | +7.9 | 78.9% |
| 44 | 85,860 | 85,837.8 | −22.2 | **80.5%** |

Maximum residual is **33 steps out of 85,860** — 0.04%. The curve is convex, and the quadratic term
is not a rounding artefact; it is most of the cost at the sizes that matter.

## What this means for A2 — the measurement, then the inference

**Measurement:** for this family, doubling the number of nodes more than doubles the cost, and at the
44-node size the quadratic term accounts for four fifths of the budget.

**Inference, explicitly not measured:** a cost that is quadratic in the node list is what a walker
produces when it scans *all* nodes at *each* level — consistent with the visible
`for branchStatement in nodes` inside every nested lowering. If that term were removed (a
parent→children index, say), the same 44-node chunk would cost on the order of the linear term alone:
**~16,753 steps instead of ~85,838**, which would sit comfortably inside the unchanged 100k budget.
**I have not instrumented A2's code and do not claim to have proved the mechanism.** A3 implements
nothing here — the decision and the fix are A2's.

**Relevant to A2's current ask:** they are asking A1 for a chunk window. A window would work. This
measurement says a window is not the *only* option, and gives the size of the algorithmic alternative
so the choice can be made on numbers rather than preference.

## One thing the fit does NOT explain — and I am not hiding it

The fit covers the **flat-in-loop** family. Nesting costs more at the same node count: BOOT-A3-028's
D2 (`while { if { if/else } }`) at **40 nodes** exceeded 100,001, while this flat family at **40
nodes** costs 72,317. So there is an additional depth term of **at least 27,684 steps at n=40** that
the quadratic fit does not include. Anyone planning the emitter work should treat the fit as a lower
bound for nested shapes, not a model of the app.

## Limitations, stated

- One family (flat statements in one `while`), one seed build, one machine.
- Nesting is **not** in the fit; the depth term is measured only as a difference at one node count.
- Refused rows are bounds and excluded from the fit; a quadratic through ≤3 points is exact and
  proves nothing, which is why the ladder runs to eight rungs.
- Correlation is not mechanism: the quadratic shape is measured, the cause is inferred and labelled.
- Determinism of `last_execute_steps` is assumed from BOOT-A3-028, not re-proven here.
- The cap is unchanged; A3 proposes no cap change.

## Reproduce

```powershell
git worktree add --detach <t> 4e325e0
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/emitter_cost_curve_033.py     # 4/4, curve printed
```

## Scope

A3 changed only `verification/**`. No edits to A4's app, A1's checker/host, A2's emitter/runtime,
frozen gates, budgets, `CURRENT`, manifest, master or release labels.

REF: GH #16 (BOOT-A3-033).
