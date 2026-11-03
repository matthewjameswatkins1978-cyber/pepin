# Node-cost boundary across six A1 pins — S2 moved it by zero nodes; the only gain (+8 nodes) predates S2

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slices 4/5: measure whether the only remaining lever actually moved) · **Evidence label:** `TESTED`
**Instrument:** `verification/probes/checker_axis_scaling.py` (same boolean-chain family, breadth and depth ladders), run against six pinned worktrees.
**Question:** the axis measurement left exactly one lever — steps per node. Did A1's S2 structural slices move the node boundary at all?

## Cross-pin result

| pin | what it is | breadth last ok | depth last ok | first refusal |
|---|---|---|---|---|
| `8396b63` | integration baseline | rung 10 → **52 nodes** | rung 10 → 52 nodes | `PEP_RUNTIME_STEP_LIMIT` |
| `abd372c` | A1 head **before** S2 | rung 12 → **60 nodes** | rung 12 → 60 nodes | `PEP_RUNTIME_STEP_LIMIT` |
| `611616b` | S2 structural slice 1 | rung 12 → 60 nodes | rung 12 → 60 nodes | `PEP_RUNTIME_STEP_LIMIT` |
| `94373fb` | S2 structural slice 2 | rung 12 → 60 nodes | rung 12 → 60 nodes | `PEP_RUNTIME_STEP_LIMIT` |
| `ba4b057` | S2 + IDX3/STALE1 host repairs | rung 12 → 60 nodes | rung 12 → 60 nodes | `PEP_RUNTIME_STEP_LIMIT` |
| `0c5f12b` | + CD3 alignment + slice 4a | rung 12 → 60 nodes | rung 12 → 60 nodes | `PEP_RUNTIME_STEP_LIMIT` |

## Reading

1. **S2 moved the boundary by exactly zero nodes.** `abd372c` → `611616b` → `94373fb` → `ba4b057` → `0c5f12b` all sit at 60 nodes on both axes, with the same refusal code at the next rung. So whatever S2 improved elsewhere (A1 has reported suite-level wins), **it did not reduce steps per node on the family that the 66-node acceptance row belongs to**.
2. **The one real gain predates S2 and is not the integration line's.** `abd372c` reaches 52 → 60 nodes (+8, ~15 %) somewhere in the work before it — and the *integration candidate* `8396b63` is the one stuck at 52. That matters for the next candidate: a combined successor inherits the A1 line's 60-node boundary, not 52, so merging `0c5f12b` alone buys ~15 % on this family even before any new work.
3. **This closes the loop on the 66-node row.** 66 nodes vs a measured 60-node ceiling is ~10 % short, on a line that already gained 15 % once. It is a small, concrete gap — not an architectural wall — but S2, as landed, does not close it.

## Instrument change (declared)

I added an early stop after two consecutive refusals per axis (a ladder past the ceiling buys nothing). Verified against the previous full-ladder run: the same 60-node bracket is produced, so the early stop changes runtime, not the result.

## Honest scope

- One family (boolean expressions inside one function), two axes; statement-level nesting was not measured.
- Node counts come from the transport, so "60 nodes" is comparable across pins only through this instrument.
- Ceilings are bracketed (last success vs first refusal), not exact step counts; the "+8 nodes" is a bracket shift, not a measured step saving.
- `8396b63`'s 52 is measured on the *integration* tree (which carries the emitter merge); the A1 line diverged before it, so the 52 vs 60 difference is a line difference, not a regression introduced by merging.

## Reproduce

```powershell
python verification\probes\checker_axis_scaling.py D:\Projects\wt-a1-fix        # abd372c, 60 nodes
python verification\probes\checker_axis_scaling.py D:\Projects\wt-a3-a1-0c5f12b # 0c5f12b, 60 nodes
python verification\probes\checker_axis_scaling.py D:\Projects\wt-a3-int-8396b63# 8396b63, 52 nodes
```
