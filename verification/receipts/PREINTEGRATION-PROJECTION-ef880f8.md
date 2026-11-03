# Pre-integration projection — merging `8396b63` with A1 `0c5f12b` is conflict-free and lands at 14/15 gates, with gate 5 the only red one

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slices 4/6: stress real composition and state exactly what the next candidate will measure) · **Evidence label:** `TESTED`
**Purpose:** A1 has not published a combined successor yet. This is a **verification dry run** — not a candidate, not a published branch, not an acceptance run — to tell A1 and Lucy precisely what the next integration will score and whether the merge itself breaks anything.

## The dry-run tree

| fact | value |
|---|---|
| merge inputs | `8396b63` (integration candidate: checker P1 + emitter `e0e49e5`) and `0c5f12b` (A1 head: host repairs, CD3 alignment `844c8b0`, slice 4a) |
| merge base | `f928de8` |
| merge result | **conflict-free** — `git merge-tree --write-tree` exit 0, tree `1a5bfa7512a1d11fd1de01d846fb4cb73405c702` |
| scratch commit (local object only, never pushed, no branch created) | `ef880f87d1499606e233d2564a9816ce3a8d3cd4` |
| worktree | `D:\Projects\wt-a3-dry-run`-style detached tree, removed after measurement |

Integration remains A1's to perform; this tree exists only as evidence and is not offered as a candidate.

## Measured on the merged tree — everything green except the 66-node row

| gate | result on the merged tree |
|---|---|
| 1 frozen-manifest (13) | **ok** — 13/13 under baseline v2 |
| baseline v2 (audit) | **ok** — archived v1 bytes intact |
| 2 pack parse-check | **ok** |
| 3 combined emitter suites | **ok — 53 tests** |
| 4 stage probe ×3 identical bundle | **ok** |
| **5 discriminating rows** | **FAIL** — `lexer=valid` (55n flipped) but `regression=PEP_RUNTIME_STEP_LIMIT "… at 2454:8"` (66n **not** flipped) |
| 6 synthetic-12 bounded-beats-whole | **ok** (`check=valid unit0=emitted all=PEP_RUNTIME_STEP_LIMIT`) |
| 7 synthetic-8 | **ok** (`check=valid unit0=emitted all=emitted`) |
| 8–14 probes on the combined tree | **all ok** — `declaration_emittability_agreement`, `bounded_emitter_attacks`, `prereq_closure_attacks`, `per_unit_cost_baseline`, `refusal_code_coverage`, `hostile_chunk_scalar_types`, `lextoken_make_token_checker` |
| **15 pack run** | **`NOT OBSERVED=3  PROVEN=0  INCONCLUSIVE=0`** (`3975f4ab…`, `28ee1434…`, `2905d529…`) |

Independent probe runs on the same tree agree: `index_cache_adversarial` 9/9 held,
`chunk_diagnostic_preservation` 6 cases / 0 falsified (**CD3 survives the merge**),
`prereq_closure_attacks` 8/8, `declaration_emittability_agreement` 4/4, `bounded_emitter_attacks` 5/5.

**Projection: a genuine combined successor built this way scores 14/15, and the single red gate is gate 5
on the `regression` row.** Note that one of the two emitter-only probes that *cannot run* on A1's branch
(`prereq_closure_attacks`, `declaration_emittability_agreement` — they need `emit_c23_function_unit_bounded`
from A2's `e0e49e5`) passes once the trees are combined, so the merge does not disturb them.

The two repairs that closed gate 15 (IDX3/STALE1 at `ba4b057`, CD3 at `844c8b0`) both survive the merge,
and the pre-existing P1 child stays green — so the pack is genuinely 3/3 on a combined tree, not an
artefact of measuring one branch in isolation.

## What this means for the one open question

Integration readiness now rests entirely on the 66-node row, unchanged at `2454:8` across
`abd372c`, `611616b`, `94373fb`, `ba4b057`, `0c5f12b` **and this merged tree**. Nothing about merging
moves it; it is a checker-budget fact, not a merge fact. A1 therefore does not need to discover the
projection by trial — publishing the successor and flipping that row are the only two remaining steps,
and the second is the hard one (LUCY-20261103-004's routing: structural checker work, expectation unmoved).

## Honest scope

- Dry-run merge: one merge geometry (`8396b63` + `0c5f12b`), no A2 `cf02095` content (B3 stays outside the
  integration candidate by routing), no native build, no execution of emitted C.
- Preflight mode asserts the *pre-P1* rows, so its "discriminating rows" line reports FAIL on any
  P1-carrying tree by design; the meaningful statement here is the measured `actual:` column, and Full mode
  expects `check=valid` on both rows — which the `regression` row does not deliver.
- One run per gate; totals were inspected individually, not inferred from a summary.
- The scratch commit is an unreferenced local object; nothing was pushed, no branch was created, and A1's
  ownership of integration is untouched.

## Reproduce

```powershell
git merge-tree --write-tree 8396b63 0c5f12b                                  # tree 1a5bfa75…, exit 0
git commit-tree 1a5bfa7512a1d11fd1de01d846fb4cb73405c702 -p 8396b63 -p 0c5f12b -m "dry run"
pwsh -File verification\tools\run_acceptance_gates.ps1 -Mode Preflight -WorktreeA1 <dry-run> -WorktreeA2 <dry-run>
terrorbats pack run verification\bats\agent3-index-gates.yaml --repo <dry-run> --json
python verification\probes\regression_row_recheck.py <dry-run>
```
