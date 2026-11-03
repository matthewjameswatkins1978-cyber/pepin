# Exact node ladder — the 66-node row is 4 nodes / ≈6 % past the measured boundary on the A1 line (22 % on `8396b63`)

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slices 4/5: turn a bracket into a number) · **Evidence label:** `TESTED`
**Instrument:** `verification/probes/exact_node_ladder.py` (new). Same family as the frozen row (a boolean-chain function over Int comparisons) with trailing `let` statements so the node count can be tuned in steps of 2 instead of 4.

## The ladder at A1 head `0c5f12b` — every node count from 16 to 72

```
nodes 62  bytes 223  ok
nodes 64  bytes 221  PEP_RUNTIME_STEP_LIMIT
nodes 66  bytes 234  PEP_RUNTIME_STEP_LIMIT
```

- **Last passing: 62 nodes. First failing: 64 nodes.**
- Per-node upper bound: **1,613 steps** (100,000 / 62).
- **66 nodes needs ≤ 106,452 steps → 6 % over the fixed 100,000 budget.**

## Cross-pin

| pin | last passing | first failing | 66 nodes would need | over budget |
|---|---|---|---|---|
| `8396b63` (integration baseline) | **54 nodes** | 56 | ≤122,222 steps | **22 %** |
| `0c5f12b` (A1 head) | **62 nodes** | 64 | ≤106,452 steps | **6 %** |

## What this buys the roadmap

1. **The integration gain is now a number, not a story.** Merging the A1 line takes the row's shortfall from **22 % to 6 %** of the step budget — i.e. from "would need a fifth more work" to "would need about one step in seventeen fewer".
2. **The remaining work is small and specific.** Flipping the 66-node row needs either **≈4 fewer effective nodes** on that program or **≈6 % fewer steps per node**. That is a concrete target for S2-style cost work, and it is compatible with A1's earlier observation that attempts moved the failure point by tens of steps.
3. **The boundary is sharp, not gradual.** On this family, 62 passes and 64 fails with no ambiguity between them; the ladder covers every even node count from 16 to 72 (odd counts need a different generator trick and were skipped). So "how far are we" is measured rather than estimated.

## Honest scope

- Even node counts only (steps of 2); the true boundary lies between 62 and 63 inclusive, so "4 nodes past" is accurate to ±1.
- The per-node figure is an *upper bound* from the largest success, not an instrumented step count; the 6 %/22 % are derived from that bound and inherit its direction (true cost could be lower, so the shortfall estimate is a ceiling on the gap, not a floor).
- One family (boolean chains over Int comparisons + `let` statements); record- and match-heavy programs have different ceilings, as the shape profile showed.
- `8396b63` and `0c5f12b` are different lines (the integration tree carries the emitter merge), so the 54→62 improvement is a **line difference** measured on the same generator — not a claim that merging by itself changes the checker.

## Reproduce

```powershell
python verification\probes\exact_node_ladder.py D:\Projects\wt-a3-a1-0c5f12b   # last pass 62
python verification\probes\exact_node_ladder.py D:\Projects\wt-a3-int-8396b63  # last pass 54
```
