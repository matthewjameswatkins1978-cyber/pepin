# ACCEPT BOOT-A3-100 — emission step cost measured: 90% of the budget at 41 nodes, and node count is a poor proxy

**Verdict: emitting a 41-node compiler-A function costs **90,354 steps — 90% of the frozen 100,000**. Emission is usually
*cheaper* than checking the same function (0.50×–0.92×), but at the largest size that fits it is slightly *more*
expensive (1.04×). Crucially, emit cost per node spans **1,047–2,204 (2.1×)** against checking's tight
**1,927–2,189 (1.13×)**, so a node-count threshold is an unsafe sizing key for A2-S2.**

Companion to BOOT-A3-099, which measured the check side. A2-S2 concerns emission, so the emission number is the one that
actually sizes fragments.

## Measured

`emit_any_049.py` with `PEPIN_UNITS_ONLY=1 PEPIN_STEPS=1`, `bea071a`, source `ca732536`:

| function | nodes | check steps | emit steps | emit/check | emit steps/node |
|---|---|---|---|---|---|
| `is_digit` | 18 | 37,346 | **18,853** | 0.50 | 1,047 |
| `is_ws` | 26 | 50,104 | 46,257 | 0.92 | 1,779 |
| `expect_byte` | 27 | 58,017 | 41,335 | 0.71 | 1,531 |
| `is_fn2` | 33 | 69,309 | 59,794 | 0.86 | 1,812 |
| `parse_value` | 34 | 71,251 | 54,431 | 0.76 | 1,601 |
| `is_int3` / `is_ret3` / `is_urn3` / `is_str3` | 41 | 87,055 | **90,354** | **1.04** | 2,204 |
| `is_ws_at` | 26 | 56,918 | — | — | refuses: `Pep C23 calls require a known target` |

The four 41-node `is_*` matchers cost **exactly** 90,354 each, matching the earlier finding that identical structure costs
identically on the check side (87,055 each). Deterministic.

## What this means for A2-S2

1. **The emitter has less headroom than the checker at the same size.** At 41 nodes: check leaves 12,945 steps; emit
   leaves **9,646**. A function that just fits checking has less room on the emission side, so "it checks, therefore it
   emits" is not safe near the boundary.
2. **Node count is a bad sizing key for emission.** Emit cost/node ranges 1,047 (`is_digit`, 18 nodes) to 2,204
   (`is_int3`, 41 nodes) — a 2.1× spread. Two functions with equal node counts can differ substantially, so a fragment
   contract expressed purely in node caps will either refuse valid fragments or admit oversized ones. Sizing by
   **measured steps** (or a conservative cap well under 41) is the safer contract.
3. **Check and emit are separate invocations, and must stay separate.** `is_int3` costs 87,055 to check **and** 90,354 to
   emit; the sum (~177k) is 1.8× the budget, so any future idea of fusing them into one tool call would fail immediately.
   Worth recording before someone proposes it as an optimisation.
4. Emission is generally cheaper, so the *emission* wall is not the only one — checking blocks 11 functions before emission
   is ever reached (A3-083). Fragmentation must satisfy both.

No threshold is proposed here; that is A2/A1's contract decision. The contribution is the cost, measured.

## Instrument defect found and fixed (fourth in this lane)

The first run printed `steps=46257 recompute=222 nodes` — 222 for every unit. That was a leaked loop variable: the
per-unit node count referred to `chunk_nodes` left over from the *previous* loop's last iteration (`main`, 222 nodes). The
step values were correct; the node counts were fiction, and a wrong node count beside a right step count would have produced
nonsense steps/node figures.

Fixed to read the unit's own node list. Reported because it is the second time a plausible-looking number was wrong only in
its label, and because steps/node is the entire analytic content of this receipt — the label had to be right before the
ratio meant anything.

## Limits

- **Emission only measured for the 9 functions that emit.** The 11 step-limited and the 1 call-refused function have no
  emission cost, because emission is never reached. So there is no emit measurement at 48+ nodes at all — the 41-node point
  is the largest emit data available.
- Unit emission only (`emit_c23_function_unit`). Header and epilogue section emission (`emit_c23_section`) are separate calls
  with their own cost, not measured here.
- One source, one emitter pin, one seed. `compiler_a.pep` is `ca732536`, unchanged across A4 revisions.
- As with A3-099, **no curve is fitted**; per-function points only. A3 has falsified three cost hypotheses and will not add
  a fourth guess.

## Reproduce

```
PEPIN_GATE_ROOT=<worktree at bea071a> PEPIN_APP_REL=examples/dogfood/pep0/compiler_a.pep \
  PEPIN_APP_REV=5f62e4b PEPIN_UNITS_ONLY=1 PEPIN_STEPS=1 python verification/probes/emit_any_049.py
```

REF GH #16, companion to BOOT-A3-099 (`6724754681`). Source A4, emitter A2, measurement A3.