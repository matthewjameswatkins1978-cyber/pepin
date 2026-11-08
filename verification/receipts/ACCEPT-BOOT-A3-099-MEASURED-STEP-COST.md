# ACCEPT BOOT-A3-099 — measured step cost per compiler-A function: ~2,100 steps/node, headroom at 41 nodes is ~6 nodes

**Verdict: a whole-function chunk check costs about **2,100 tool steps per AST node**, tightly linear across the range that
completes (1,927–2,189/node). The frozen 100,000-step budget therefore binds at roughly **47 nodes**, which is exactly why
41 nodes passes and 48 fails. At 41 nodes — the largest that completes — only **12,945 steps** remain, about six more nodes.
A2-S2 and A1-S2 finally have the number that decides fragment size, measured rather than guessed.**

## The measurement

`verification/probes/step_cost_099.py`, `bea071a`, source `5f62e4b:examples/dogfood/pep0/compiler_a.pep` (blob `ca732536`):

| function | nodes | steps | steps/node | % of 100k |
|---|---|---|---|---|
| `is_digit` | 18 | 37,346 | 2,075 | 37% |
| `is_ws` | 26 | 50,104 | 1,927 | 50% |
| `is_ws_at` | 26 | 56,918 | 2,189 | 57% |
| `expect_byte` | 27 | 58,017 | 2,149 | 58% |
| `is_fn2` | 33 | 69,309 | 2,100 | 69% |
| `parse_value` | 34 | 71,251 | 2,096 | 71% |
| `is_int3` / `is_ret3` / `is_urn3` / `is_str3` | 41 | **87,055** | 2,123 | **87%** |
| `skip_ws`, `scan_digits`, `is_main4`, `is_bool4`, `is_unit4`, `check_tail`, `find_parens`, `find_fn`, `find_ds`, `main`, `find_brace` | 48–288 | 100,001 | LIMIT | LIMIT |

The session reports `budget + 1` when a run aborts, so `100001` is the limit marker, not a cost.

**Determinism, checked rather than assumed.** Four functions were re-measured in *independent sessions*; both runs gave
identical values (`is_digit` 37,346; `is_ws` 50,104; `is_int3` 87,055; `is_ret3` 87,055). And `is_int3`/`is_ret3`/`is_urn3`/
`is_str3` are the same 41 nodes structurally and cost **exactly** 87,055 each — structure drives cost, reproducibly.

## What this settles for A2-S2 / A1-S2

1. **The wall is a step budget, not a semantic limit.** 41 × 2,123 = 87,055 fits; 48 × ~2,100 ≈ 101,000 does not. The sharp
   41/48 boundary I reported in A3-083 is now explained by measured cost rather than observed by pass/fail alone.
2. **A whole-function chunk cannot exceed ~47 nodes.** Any fragment contract must target materially below that. At 41 nodes
   there are only ~6 nodes of margin, which one more `&&` conjunct can consume.
3. **Cost is per node, not per statement.** So "split by statement" only helps if it actually *reduces node count per
   invocation* — a long statement chain in one fragment buys nothing. Fragments should be sized by node count (or measured
   steps), not by statement count.
4. **Leave margin: per-node cost varies 13% (1,927–2,189).** A fragment sized at the 41-node edge can fail depending on
   construct mix. Sizing at ~30 nodes leaves real headroom.

I am not proposing a specific threshold — that is A2/A1's contract decision. I am reporting that a threshold is needed and
what the cost actually is.

## Two instrument errors, recorded because they nearly produced false data

My first version differed `last_execute_steps` against a pre-invoke reading and emitted "costs" of −12,758 and 48,552 —
**negative costs**. The counter does not accumulate: each `tool_invoke` overwrites it, so a delta of two absolute readings is
meaningless. My second version read absolutes but reported them alongside a delta column, still hinting at accumulation.

Fixed by reading the value absolutely and validating it against independent fresh sessions. What made the error visible was
that a negative number is impossible for a cost — worth stating, because "steps 48,552" alone would have looked plausible.
This is the fourth instrument defect I have found and corrected in this lane, and the second where the *shape* of the wrong
number (negative, decreasing) was the only clue.

## Limits

- **No curve is fitted.** Steps/node is reported per function. A3 has previously falsified three cost hypotheses
  (BOOT-A3-045/047/048); a regression line through these seven points would be another guess dressed as a finding. The
  cluster is tight and linear-looking, and that is all I claim.
- **Chunk check only.** These are `analyze_chunk_typed` step costs. A1's `analyze_chunk_typed_bound` chain path and the
  emitter's own `emit_c23_*` calls have different cost profiles and are **not** measured here. A2-S2 concerns emission, so
  the emitter's cost is still unknown — this measures the check it must be fed.
- Step cost may vary with the *other* signatures passed as external facts; I passed all non-entry signatures, matching
  A3-083's baseline so the 41/48 boundary lines up.
- One source, one emitter pin, one seed. `compiler_a.pep` is `ca732536`, unchanged across A4 revisions.

## Reproduce

```
PEPIN_GATE_ROOT=<worktree at bea071a> python verification/probes/step_cost_099.py
```

REF GH #16. Source A4, emitter A2, measurement A3.