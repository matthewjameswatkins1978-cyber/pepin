# A2 per-unit cost BASELINE at `c70d5eb` — full re-run corroborated (ratio 0.98)

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Why:** Lucy advisory `LUCY-20261102-006` (issue #16, 18:43) tasks A3 with challenging A2's future *"no full re-run"* claim using **measured per-unit work**. This pins the *current* state so the future claim has something falsifiable to beat.

## Method

Probe `verification/probes/per_unit_cost_baseline.py` at A2 `codex/a2-list-record-fields` @ `c70d5eb7f772f1d9d66c3fb918e21b7a9c43dc31` (clean pinned worktree `D:\Projects\wt-a3-a2-c70d5eb`). Warm session; fixture = two-function program (`total` + `main`); 3 reps of five emit entries (`emit_c23_checked` one-shot, section `header`, section `main`, function units 0 and 1); wall time per invocation; byte identity re-verified.

## Measured (exit 0, 3 reps)

| entry | output bytes | wall ms (min / avg) |
|---|---|---|
| one-shot `emit_c23_checked` | 4,723 | ~1.4 / 1.5 |
| section `header` | 4,317 | 1.3 / 1.4 |
| section `main` | 83 | 1.2 / 1.2 |
| function unit 0 | 202 | 1.1 / 1.5 |
| function unit 1 | 121 | 1.2 / 1.3 |

- **RATIO unit0/full = 0.98** → emitting a 202-byte unit costs ≈98% of emitting the whole 4,723-byte program: **A2's admitted "each entry re-runs the whole emission then slices" is measured and corroborated**, not just asserted.
- **Byte identity holds:** header (4,317) + unit0 (202) + unit1 (121) + main (83) = 4,723 = one-shot ✓.

## The falsifiable target (for A2's next slice)

Success criterion for a *true bounded emit*, to be re-measured with this exact probe: **unit/full ratio must fall well below 1.0** (target: unit cost proportional to its prerequisites, not the whole program) — and it must hold on a **larger** target too (the two-function fixture is tiny; A2's own `LexToken + make_token` case, where the unit call currently exceeds the budget while the header succeeds, is the discriminating corpus). Byte identity on already-supported shapes must stay exact.

## Honest scope

- Wall-clock on a tiny program with a warm session — the *ratio* is the signal, not absolute ms; fuel/steps are not exposed at this emit layer, so this is timing evidence, not step accounting.
- 3 reps, one head, one fixture; no native compile in this probe (byte-equivalence of *C text* only — the Clang/GCC + interpreter parity gate on real `make_token` remains A2's, per Lucy's item 2).
- A2 currently *admits* the full re-run (their `c70d5eb` receipt) — this is corroboration + baseline, **not a new defect**.

## Reproduction

```powershell
python verification\probes\per_unit_cost_baseline.py <A2-worktree-at-c70d5eb>
# expect: RATIO unit0/full ≈ 0.98 today; after a true bounded emit, << 1.0
```

## Next action

Report the baseline (own BM outbox + #16, per advisory); re-run unchanged when A2 publishes a bounded-emit SHA, alongside their byte-parity and native-gate evidence.
