# SHA-bound acceptance run — INTEGRATED-CANDIDATE `8396b63` — **FAIL (not yet acceptable)**

**Date:** 2026-11-03 · **Lane:** Agent 3 (frozen acceptance, per LUCY-003/004 · A1 request BOOT-A1-20261103-003/#16 6598901717+6599049476) · **Evidence label:** `TESTED`
**Candidate:** `codex/checker-emitter-integration` @ **`8396b63b34da75e3e17c1f49b5e1b2c5126ccd19`** — pinned worktree `D:\Projects\wt-a3-int-8396b63` (clean, detached).
**Runner:** frozen `verification/tools/run_acceptance_gates.ps1` blob **`e5cad4df7884168055bafd9acea08045c0d64d90`** at my HEAD `4c75b673b2…` — blob-verified by the run itself (manifest gate 13/13 ok); no modification since Matthew's freeze.
**Command:** `run_acceptance_gates.ps1 -Mode Full -CombinedWorktree D:\Projects\wt-a3-int-8396b63` → **exit 1**, JSON at `%TEMP%\a3-full-8396b63.json` (+ pack detail `%TEMP%\a3-pack-8396b63.json`).

## Ancestry verified before running (all True)
origin `codex/checker-emitter-integration` == `8396b63` (pushed) · contains `05add76` (base) → `f928de8` (P1 fix) → merge `e0e49e5` (emitter; carries `a400ffe` CR3) · contains `d158044` (original regression — LUCY-004's "original regression" requirement) · checker blob `tests/pep_checker_a13.pep` **identical** between `f928de8` and `8396b63` (`59b12d68…`) ⇒ this run also covers A1's `P1-CANDIDATE` (BOOT-A1-20261103-002) checker content; merge-base `b9e26df`, zero overlap (A1's claimed geometry, independently confirmed).

## Gate results (15 gates; every result examined, not just the headline)

| # | gate | expected | actual | pass |
|---|---|---|---|---|
| 1 | frozen-manifest (13) | all match | 13/13 | ✅ |
| 2 | pack parse-check | exit 0 | exit 0 | ✅ |
| 3 | combined suites | 53 OK | **53 OK (133 s)** | ✅ |
| 4 | stage ×3 identical bundle | 3 identical | identical | ✅ |
| 5 | **discriminating rows** | lexer=valid **AND** regression=valid | **lexer=valid ✓ FLIPPED · regression=`PEP_RUNTIME_STEP_LIMIT` ✗ NO FLIP** | ❌ **first_fail** |
| 6 | synthetic-12 bounded-beats-whole | valid/emitted/STEP_LIMIT | as expected | ✅ |
| 7 | synthetic-8 | all green | green | ✅ |
| 8–14 | probes on **combined candidate** (agreement=CR3, bounded, closure, per-unit, refusal, hostile, lextoken-R1) | exit 0 + falsified 0 | **all green** | ✅ |
| 15 | **pack run** | exit 0 + NOT OBSERVED=3 PROVEN=0 | **exit 1, NOT OBSERVED=1, PROVEN=2** | ❌ |

**Pack per-child (campaign `432f9722…`, target `8396b63`):**
- `regression-hole-guard-passes` → **NOT OBSERVED** (`receipt:sha256:1fdfbe6f4553d18bc51c78253ab44542fa9db5dea33311a9f4524a8a120253c2`) — **Agent 3's original P1 finding is CLOSED on this candidate** (the 50-node named-hole fixture passes; matches A1's `P1-CANDIDATE` result).
- `index-cache-claims` → **PROVEN** (`receipt:sha256:05c449d1…`) — IDX3/STALE1 remain open.
- `chunk-diagnostic-claims` → **PROVEN** (`receipt:sha256:9f572465…`) — CD3 message parity remains open.

## Verdict

**FAIL — candidate is NOT yet acceptable.** First failing stage: **discriminating rows** (`regression` = the 66-node d158044-shaped case, `PEP_RUNTIME_STEP_LIMIT` at checker). Five conditions status: NOT OBSERVED **1**≠3 · PROVEN **2**≠0 · gates **13/15**≠15 · exit **1**≠0 · this receipt is SHA-bound ✓.

**Interpretation (consistent with the record, no expectation was moved):**
- Real progress is verified: P1 closed (pack child + A1's fixture), `lexer` 55n row flipped, all bounded-emission/CR3/probe gates green — **no regression in bounded emission**.
- The 66n row fails exactly as A1 measured (`BOOT-A1-20261103-004..006`: ceiling <58n, ~15–20% headroom needed) and **LUCY-20261103-004 ruled**: keep the 66n expectation, A1 performs S2 structural facts-fusion from its fix branch, then publishes a tested S2 SHA + deliberate **pushed successor of `8396b63`** for this same frozen run.
- **IDX3/STALE1 and CD3 remain open**; LUCY-004 says "IDX3/STALE1 remain A3 verification-manifest work, not A1's lane" — the verification *manifest* (bats/probes) is indeed mine and unchanged, but **who repairs the product code behind those claims needs an explicit routing decision** (ownership question flagged to #16 per LUCY-003 §3; not mine to resolve or repair).

**Recommendation:** **HOLD** on `8396b63`; re-run the identical frozen Full on A1's LUCY-004(a) successor when pushed; pack reaches 3/3 only when the IDX3/STALE1 and CD3 owners/repairs are routed and landed. **Acceptance remains Matthew's alone.** No budget/limit/test/runner change; Defender hold intact; master/CURRENT untouched.

## Reproduce
```powershell
# pinned: D:\Projects\wt-a3-int-8396b63 @ 8396b63b34da75e3e17c1f49b5e1b2c5126ccd19
& <verify-root>\verification\tools\run_acceptance_gates.ps1 -Mode Full -CombinedWorktree D:\Projects\wt-a3-int-8396b63   # exit 1
terrorbats pack run verification\bats\agent3-index-gates.yaml --repo D:\Projects\wt-a3-int-8396b63 --json               # 1/3
```
