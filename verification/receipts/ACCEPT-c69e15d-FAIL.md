# SHA-bound verdict — INTEGRATED-CANDIDATE-3 `c69e15d` — **FAIL** on one gate (66-node row); gate 15 green; semantic matrices unchanged

**Date:** 2026-11-04 · **Mission:** PEP-WB-A3-20261104-B priorities 1–2 · **Evidence label:** `TESTED`
**Candidate:** `codex/checker-emitter-integration` @ **`c69e15d3cf9a7aeb56e84a35c43733347fd820c8`** ("Merge codex/p1-checker-cost-fix: bounded units, chained binding facts (INTEGRATED-CANDIDATE-3)") — pinned worktree `D:\Projects\wt-a3-int-c69e15d`, clean, `origin` == candidate.
**Frozen instrument (baseline v2, verified before the run):** runner **`b464e00e61e710023f506b11d6071347823e0270`**, probe **`688042d7d394144aafb208ff641fb0a26dafd5e2`**, manifest **13/13 by `git hash-object`**, v1 (`e5cad4df` / `e819607c`) archived intact, pack parse-check exit 0.
**Command:** `pwsh -File verification\tools\run_acceptance_gates.ps1 -Mode Full -CombinedWorktree <candidate>` → **exit 1**; JSON `_build\full-c69e15d.json`.

## RESULT: **FAIL** — 14/15 gates; first failure = `discriminating rows` (66-node regression)

| # | gate | actual | pass |
|---|---|---|---|
| 1 | frozen-manifest (13) | 13/13 match | ✅ |
| — | baseline v2 audit | v1 archive intact | ✅ |
| 2 | pack parse-check | exit 0 | ✅ |
| 3 | combined emitter suites | **Ran 53 tests in 156 s, OK** | ✅ |
| 4 | stage ×3 identical bundle | one bundle `92167083…` | ✅ |
| **5** | **discriminating rows** | **`lexer=valid` ✅ flipped · `regression=PEP_RUNTIME_STEP_LIMIT` ❌** | ❌ **first_fail** |
| 6 | synthetic-12 | `check=valid unit0=emitted all=PEP_RUNTIME_STEP_LIMIT` | ✅ |
| 7 | synthetic-8 | green | ✅ |
| 8–14 | all seven probes | exit 0, `claim_falsified=0` | ✅ |
| **15** | **pack at integrated SHA** | **`NOT OBSERVED=3 PROVEN=0 INCONCLUSIVE=0`** — receipts `b93284e4…`, `6d8ad056…`, `32a35f73…` | ✅ |

No gate was skipped.

## Priority 2 — existing semantic instruments re-run at this candidate

| instrument | `bcfa3c0` | **`c69e15d`** |
|---|---|---|
| `dup_decl_minimiser.py` | 81-byte flip, seed `PEP_DUPLICATE_TYPE` | **unchanged**: 81-byte flip, same seed code, single-declaration control order-stable |
| `staged_metamorphic_matrix.py` | 13 cells, 12 pass / 1 fail | **identical**: 12 pass / 1 fail (same `dup_decl` cell) |
| `staged_partial_provenance.py` | 9 cells, 8 pass / 0 fail / 1 obs | **identical**: 8 pass / 0 fail / 1 observation |

So A1's bounded-unit, caller-supplied-group and BindingPool work **did not change the duplicate-declaration
defect** and did not disturb any invariant my matrices already cover: declaration-order invariance,
chunk-boundary invariance, missing/foreign fact closure, hole handling and diagnostic parity all still hold.

## First failure, precisely

`regression` = the 66-node boolean-chain fixture → `PEP_RUNTIME_STEP_LIMIT` at the checker. Independently
measured shortfall (unchanged): the A1 line passes 62 nodes and refuses 64, so 66 needs ≈6 % over the fixed
100,000-step budget (`EXACT-NODE-LADDER.md`).

## Reading

- This is the strongest candidate yet on instrument terms: 14/15 with gate 15 genuinely satisfied and all
  suites/probes green.
- Nothing here is acceptable: one gate is red and the acceptance standard is unchanged. The remaining gap
  is the same ~6 % per-node cost question LUCY-20261103-004 already routed to A1 — merging and staging
  features have not moved it.
- New work (priority 3) found a **genuine fail-open in the binding-fact path**, reported separately in
  `BINDING-POOL-ATTACKS-c69e15d.md`; it is *not* one of the fifteen gates, but it is a soundness hole in
  the same staged-compilation contract.

## Boundaries

No builder file modified, nothing merged or cherry-picked, no budget/limit changed, no frozen artifact
altered (manifest and both v1 blobs verified in-run). Diagnostic verification only — this FAIL is not
milestone acceptance.

## Reproduce

```powershell
pwsh -File verification\tools\run_acceptance_gates.ps1 -Mode Full -CombinedWorktree D:\Projects\wt-a3-int-c69e15d
python verification\probes\dup_decl_minimiser.py        D:\Projects\wt-a3-int-c69e15d
python verification\probes\staged_metamorphic_matrix.py D:\Projects\wt-a3-int-c69e15d
python verification\probes\staged_partial_provenance.py D:\Projects\wt-a3-int-c69e15d
```
