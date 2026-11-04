# SHA-bound verdict — INTEGRATED-CANDIDATE `bcfa3c0` — **FAIL** on one gate: the 66-node regression row. Everything else, including gate 15, is green.

**Date:** 2026-11-04 · **Mission:** PEP-A3-20261104-001 (independent adversarial verification) · **Evidence label:** `TESTED`
**Candidate:** `codex/checker-emitter-integration` @ **`bcfa3c011c67f25142c2866755a525bc3817a42a`** — pinned detached worktree `D:\Projects\wt-a3-int-bcfa3c0`, clean; `origin` == candidate (verified).
**Frozen instrument (baseline v2):** runner **`b464e00e61e710023f506b11d6071347823e0270`**, corrected probe **`688042d7d394144aafb208ff641fb0a26dafd5e2`**, manifest **13/13 by `git hash-object`**, pack `pack:sha256:01e9961ba3362922fed1dfac8f6c81eee0aa6315e7e72d4ad62ede74fe8670a0`. v1 (`e5cad4df` / `e819607c`) archived intact.
**Command:** `pwsh -NoProfile -File verification\tools\run_acceptance_gates.ps1 -Mode Full -CombinedWorktree <candidate>` → **exit 1**; JSON `_build\full-bcfa3c0.json`.

## RESULT: **FAIL** — 14/15 gates; first failure = `discriminating rows`

| # | gate | expected | actual | pass |
|---|---|---|---|---|
| 1 | frozen-manifest (13) | all match | **13/13 match** | ✅ |
| — | acceptance baseline v2 audit | v1 archive intact | v1 archive intact | ✅ |
| 2 | pack parse-check | exit 0 | exit 0 | ✅ |
| 3 | combined emitter suites | 53 OK | **Ran 53 tests in 153.2 s, OK** | ✅ |
| 4 | stage probe ×3 identical bundle | 3 identical | one bundle `9bdd3541…` | ✅ |
| **5** | **discriminating rows** | `lexer=valid` **and** `regression=valid` | **`lexer=valid` ✅ FLIPPED · `regression=PEP_RUNTIME_STEP_LIMIT` ❌** | ❌ **first_fail** |
| 6 | synthetic-12 bounded-beats-whole | valid/emitted/STEP_LIMIT | `check=valid unit0=emitted all=PEP_RUNTIME_STEP_LIMIT` | ✅ |
| 7 | synthetic-8 | green | green | ✅ |
| 8 | probe declaration_emittability_agreement | exit 0 | cases=4 claim_falsified=0 | ✅ |
| 9 | probe bounded_emitter_attacks | exit 0 | cases=5 claim_falsified=0 | ✅ |
| 10 | probe prereq_closure_attacks | exit 0 | cases=8 claim_falsified=0 | ✅ |
| 11 | probe per_unit_cost_baseline | exit 0 | exit 0 | ✅ |
| 12 | probe refusal_code_coverage | exit 0 | cases=2 claim_falsified=0 | ✅ |
| 13 | probe hostile_chunk_scalar_types | exit 0 | cases=12 claim_falsified=0 | ✅ |
| 14 | probe lextoken_make_token_checker | exit 0 | cases=2 claim_falsified=0 | ✅ |
| **15** | **pack run at integrated SHA** | exit 0 + `NOT OBSERVED=3 PROVEN=0` | **exit 0, NOT_OBSERVED=3 PROVEN=0 INCONCLUSIVE=0** | ✅ |

**No gate was skipped:** the runner executes all fifteen and reports the first failure without stopping; every later gate ran and passed.

## Gate 15 in detail (first time it is genuinely green on an integrated candidate)

```
3 children, all NOT OBSERVED:
  receipt:sha256:3f112389ffd3066eb9aba738b11d9c46cf4377515362ae3db51079226db311c0
  receipt:sha256:2634866ee0d43d15aad9c6ff875f7affef052568cc4d06f43e94333fe2b13b75
  receipt:sha256:01cabc372a1d1cd301766f458f8ac0d578dc25889aa4abb7e5274bef91f9e5e8
```
Both of A1's repairs (IDX3/STALE1 `ba4b057`, CD3 `844c8b0`) survive the merge, and the v2 probe can finally *observe* them — under v1 this child was unmeasurable and would have reported `PROVEN` regardless.

## Ancestry verified before running

`8396b63` ✔ → contains emitter `e0e49e5` ✔ → A1 slice 4a `0c5f12b` ✔ → slices 4b `49db581`, 4c `e5cf0cd` ✔, merged as `3e92286` "INTEGRATED-CANDIDATE" → `bcfa3c0`. A2's head `b37532a` is **not** included (B3 stays outside the integration candidate by routing — expected, not a defect).

## First failure, precisely

`regression` = the 66-node boolean-chain fixture: `PEP_RUNTIME_STEP_LIMIT` at the checker. My independent measurements predicted exactly this and quantified it: the A1 line passes **62 nodes** and refuses **64**, so **66 nodes needs ≈106,500 steps — 6 % over the fixed 100,000 budget** (`EXACT-NODE-LADDER.md`). The row is 4 nodes / ~6 % away, not an order of magnitude.

## Recommendation

**Do not accept `bcfa3c0`** — one gate is red and the acceptance standard is unchanged. But this is the strongest candidate yet: 14/15 with gate 15 genuinely satisfied. The single actionable target is **≈6 % fewer steps per node** (or ≈4 fewer effective nodes) on the boolean-chain path; merging bought ~15 % already (`8396b63` 54 → A1 line 62 nodes), so one more comparable slice would flip it. Re-run the same unchanged procedure on A1's next pushed successor; I will produce the same SHA-bound verdict.

## Boundaries

No builder file modified, nothing merged or cherry-picked, no budget/limit changed, no frozen instrument altered (manifest 13/13 and both v1 blobs verified in-run). Diagnostic verification only: this FAIL is not milestone acceptance, and a future PASS would not by itself prove A→B→C self-hosting.
