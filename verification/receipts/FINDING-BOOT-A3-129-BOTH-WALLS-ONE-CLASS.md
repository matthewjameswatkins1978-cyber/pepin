# FINDING BOOT-A3-129 — both walls are the same class of cause in two files, and the 41/48 boundary is that slope crossing the budget

**The check wall and the emit wall have the same structural cause: repeated full scans of the function's node list, in the
checker and in the emitter respectively. Both costs are linear in function node count — **~2,326 steps/node for checking** and
**462/node for a fragment's branch lowering** — so the long-cited 41-pass/48-fail boundary is simply the check slope crossing
100,000 near 50 nodes, not a semantic limit.**

Seed blob `f8f476198f`. Emitter `3d9ac7d3`. Driver A1 `9bf18699`.

## Check cost, measured with the same sweep method

One function, padding grown to enlarge it, checked whole through `analyze_chunk_typed`:

| function nodes | check steps | outcome |
|---|---|---|
| 17 | 21,261 | VALID |
| 29 | 45,270 | VALID |
| 41 | 77,091 | VALID |
| 53 | 100,001 | LIMIT |

Slope ≈ **2,326 steps per function node**; the 100,000 budget is reached near **50 nodes** for this shape. That is consistent
with BOOT-A3-083's independently measured boundary on real `compiler_a.pep` functions — 41 nodes pass, 48 fail — which I had
previously been able to report only as an observed sharp cut-off.

So the boundary was never a semantic ceiling or a construct limit. It is a linear cost crossing a fixed budget, exactly like
the fragment wall.

## The same cause, two files

| file | `for … in nodes` loops | the hot helper |
|---|---|---|
| `tests/pep_checker_a13.pep` | **55** | `count_children` (L76) — full scan, **no early exit**, counts every match |
| `tests/pep_c23_emitter.pep` | **90** | `pep_c23_child` (A3-126) — full scan, returns first match |

`count_children` is worse than `pep_c23_child`: it cannot return early because it must count all matches. Called from
expression and statement lowering, it makes checking cost proportional to *nodes × call sites*, which is the measured slope.

## Why this matters more than the fragment work

The entire sectional apparatus — A1's chain driver, the merged reports, the bindings translation, the fragment contract —
exists to work around a 100,000-step budget that these two helpers exhaust on functions of ordinary size. `main` is 222 nodes;
at 2,326/node a whole-function check would cost roughly **516,000 steps**, five times the budget.

Index children once per call in the checker and that term disappears, leaving cost proportional to lookups rather than
lookups × nodes. **Hypothesis worth stating plainly: whole-function checking of `main` would then plausibly fit inside the
budget, and the whole chain/merge/fragment apparatus would become unnecessary for programs of this size.** I have not
measured that — no post-fix checker exists — and it is a much larger change than the fragment work, in a file owned by A1/A2
with semantic consequences I cannot certify.

But it changes the cost/benefit of the roadmap: the campaign is currently spending substantial effort on fragment
infrastructure to route around a helper that a targeted optimisation could make irrelevant. Whoever owns the roadmap should
know that before more fragment work is funded.

## What is measured versus inferred

- **Measured:** check cost linear at ~2,326/node over 17–41 nodes; emit fragment slope 462/node over 51–221 (A3-125/128);
  55 and 90 node-scanning loops respectively; `count_children` has no early exit; the 41-node check passes and 53 fails.
- **Inferred:** that the crossing near 50 nodes *is* A3-083's 41/48 boundary (same phenomenon, different source shapes, so the
  exact node number differs); that indexing would bring `main` under budget; that the 516,000 figure extrapolates.
- **Not attempted:** any checker change. `pep_checker_a13.pep` is A1/A2's file and a semantic change there is beyond A3's
  authority to author.

## Limits

- One program shape per sweep. Padding statements are `var pN = N`, which also increase binding counts; the slope may mix
  child-scan and binding-lookup cost.
- The check slope (2,326) and emit slope (462) are not directly comparable: they measure different operations on different
  shapes. What they share is linearity in function size and a repeated full node scan as the mechanism.
- Extrapolating either slope to 222 nodes is an extrapolation; only the 17–41 (check) and 51–221 (emit) ranges are measured.
- The recommendation is a hypothesis about a change I have not made or measured.

## Reproduce

Check sweep: `fn a3_c(source: SourceBytes)` with `var e`, `let n`, one trivial `if`, P `var pK = K`, `return e`; invoke
`analyze_chunk_typed` on the whole function and read `metrics.last_execute_steps`, sweeping P. Emit sweep: A3-125/128.

REF GH #16. Parents: `6725742376` (A3-128), `6725694094` (A3-126), `6725672583` (A3-125).