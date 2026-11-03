# Checker cost attributed by pass — the expensive shapes' cost is in the whole-checker path, not in signatures or type declarations

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slices 4/6: attribute cost to a pass instead of inferring from totals) · **Evidence label:** `TESTED`
**Measured in:** scratch both-lanes tree `84062064` (`0c5f12b` + `cf02095`; local only, never pushed, removed after measuring — not an integration candidate; `codex/checker-emitter-integration` remains `8396b63`)
**Instrument:** `verification/probes/checker_pass_attribution.py` (new). Each exported checker pass is registered as its own tool and laddered over the same shapes under the same fixed 100,000-step budget. **No builder file was edited.**

## Ceilings — nodes at last success

| shape | `analyze_parsed` (whole checker) | `chunk_signatures` | `chunk_type_declarations` |
|---|---|---|---|
| `lets` | 64 | 64 | 64 |
| `records` | 104 | 164 | 164 |
| **`bool_chains`** | **44** | **164** | **324** |
| **`match_arms`** | **36** | 108 | 108 |

`SUMMARY claims=4 claim_falsified=0`.

## What the attribution says

1. **The expensive shapes are not blocked by the two passes I could isolate.** On `bool_chains` — the family the frozen 66-node fixture belongs to — the whole checker stops at **44 nodes** while `chunk_signatures` reaches **164** and `chunk_type_declarations` reaches **324**, i.e. 3.7× and 7.4× further on the *same* parsed tree and the *same* budget. On `match_arms` the whole checker stops at 36 while both sub-passes reach 108.
   → The extra cost lives in what `analyze_parsed` does **beyond** signatures and type declarations: the expression/statement checking path. That is exactly the surface A1's S2 expression-facts work targets, and this is the first measurement that says so from pass-level evidence rather than cost-per-node totals.
2. **The cheap shapes are bounded by something shared, not by one pass.** On `lets` all three pass ceilings are 64 and on `records` the whole checker (104) is *below* both sub-passes (164) — so on those shapes the whole checker is no more expensive than a single pass, and the wall is the budget itself rather than any one pass.
3. **`chunk_type_declarations` is the cheapest pass measured** (324 nodes on bool chains): the slice-4a producer A1 just added is not where the budget goes.

## Claims, including the one I expected to fail

| claim | result |
|---|---|
| **A1** control: whole-checker ceiling varies materially by shape | **held** — records 104 vs match arms 36, ratio 2.89 |
| **A2** a sub-pass survives beyond the whole checker on the expensive shape | **held** — `match_arms`: whole 36, best sub-pass 108 |
| **A3** no sub-pass is <2× the whole checker on the cheapest shape | **held** — `records`: whole 104, subs 164/164 |

## Honest scope and discipline

- The sub-pass ceilings are capped by the same budget, so a pass that would finish under budget on bigger input may be limited by the budget rather than by its own cost. What is solid: **no sub-pass varies with shape the way the whole checker does**, so none of them is the expensive shapes' bottleneck.
- Only three passes are exported with a `ParserProgress` signature; the expression-facts and infer paths are internal and cannot be isolated without editing builder code, which I will not do. The attribution is therefore by elimination, not by direct timing.
- `match_arms` rungs beyond 16 arms fail at parse, so its whole-checker ceiling is bracketed by 36 (ok) and 60 (refused at the next rung).
- **Discipline note:** a draft of the announcement for this result was written before the probe had run and contained placeholder numbers; it was discarded unposted. Only measured numbers appear in this receipt and on #16.

## Reproduce

```powershell
python verification\probes\checker_pass_attribution.py <scratch-tree-with-checker>   # exit 0
```
