# CHECKED-CHUNK malformed-input regression — 11 claim cases vs A1 pin `81302766`

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED` (Terror Bats receipt, deterministic oracle)

## What was tested

Claim under attack (A1-owned `pep_chunk_contract.py`, `pep-checked-chunk-v1`):

> At the pinned repository commit, the checked-chunk validator fails closed on
> every malformed transport-scalar input in the Agent 3 probe: each of the 11
> claim cases is refused with a stable `ContractRefusal` code, so the probe
> exits 0 and reports `claim_falsified=0`.

## Pins (exact, measured)

| Fact | Value |
|---|---|
| Target repository | `D:\Projects\wt-a3-mimo-8130276` (clean disposable worktree) |
| Target commit | `81302766d97b4d85e07a5bcd41d64432dd910cdc` = `origin/codex/checker-emitter-integration` head at run time (`test(checker): pin the real per-invocation node affordance`) |
| Contract introduction | `87c9fec` (`pep_chunk_contract.py` first lands) on that branch |
| Test commit (this branch) | `45f0ee0f63071dbaf0f0f855a5b676d5e8a70c34` — `verification/probes/hostile_chunk_scalar_types.py` + `verification/bats/checked-chunk-malformed-scalars.yaml` |
| Probe script SHA-256 | see `verification/probes/hostile_chunk_scalar_types.py` (content-addressed by the test commit) |

## Terror Bats run (content-addressed)

- Tool: `terrorbats 1.0.0-rc.1` (`terrorbats doctor`: CORE 6/6 OK, READY; worktree mode = reversible/observable, **not** containment)
- Bat identity: `bat:sha256:9c39a559e0d71dfca803d148e4f464bbb3f1668a26dfe0c27fb66f6a5ab84493`
- Claim identity: `claim:sha256:63bcad85bab9f3e769bd1b539078885d1508383a441de94ca234aa760c7dd61b`
- Oracle identity: `oracle:sha256:9861b12817ab463e114a2990318541667e0d661da6d9e7a320538244373e3095`
- Spec source: `evidence:sha256:f8d1e7a05a9fd4e8291189c7b854893deaa901f8fe1de6635152b1fc906a56de`
- **Receipt: `receipt:sha256:e2d49d13eec842f71ad3721efe36a7e89b27cf04930802145a4e0f79d4d7da07`**
- Execution id: `d0702492-dd6e-4f21-9066-4414db184a6b` (wall 2,178 ms; cleanup succeeded)
- Probe stdout evidence: `evidence:sha256:9cfd29ff1f90e084695f664194ee25c514892074b73e0b6d5acc44c705f69e3e` (digest verified on read; stderr empty; `git_status`/`git_diff` evidence empty = attack changed nothing)

### Three layers (never flattened)

| Layer | Result |
|---|---|
| Execution status | `Completed` |
| Oracle result | `Falsified` (`exit_code run:0 equals 1` fired) |
| Verdict | **`PROVEN`** — deterministic evidence established that the tested claim was falsified under the recorded conditions (this repo, this commit, this machine). Not a universal proof, not certification. |

## The 11 claim cases at `81302766`

Probe summary: `SUMMARY cases=12 claim_falsified=8` (11 claim cases + 1 non-claim observation). Direct pre-bat rerun reproduced the identical result (exit 1).

| # | Malformed input | Expected | Actual | Verdict |
|---|---|---|---|---|
| 1 | `childIndex` = float `-0.5` (Int position) | `ContractRefusal` | `ACCEPTED` (`status='valid'`) | **FALSIFIED** |
| 2 | `childIndex` = int `-1` (control) | `ContractRefusal` | `REFUSED` `CHUNK_NEGATIVE_CHILD_INDEX` | held |
| 3 | node `id` = text `'two'` | `ContractRefusal` | raw `ValueError` escapes | **FALSIFIED** |
| 4 | `coveredNodeIds` = bools `[False, True, 2]` | `ContractRefusal` | `ACCEPTED` | **FALSIFIED** |
| 5 | `coveredNodeIds` = strings `["0","1","2"]` | `ContractRefusal` | `REFUSED` `CHUNK_COVERAGE_MISMATCH` | held |
| 6 | `parentId` = float `1.9` (planned `1`) | `ContractRefusal` | `ACCEPTED` | **FALSIFIED** |
| 7 | node `id` = float `2.9` (planned `2`) | `ContractRefusal` | `ACCEPTED` | **FALSIFIED** |
| 8 | `report.syntaxNodeCount` = float `3.0` | `ContractRefusal` | `ACCEPTED` | **FALSIFIED** |
| 9 | chunk `index` = bool `False` (planned `0`) | `ContractRefusal` | `ACCEPTED` | **FALSIFIED** |
| 10 | `suppliedSignatures` = `["0"]` (strings) | `ContractRefusal` | `ACCEPTED` | **FALSIFIED** |
| 11 | `suppliedSignatures` = `[0]` (control) | `ACCEPTED` | `ACCEPTED` | held |
| — | observation: document ids not starting at 0 (`[5..10]`, 2 chunks) | no claim | `ACCEPTED` | recorded, not a claim |

## Defect classification (confirmed, reproducible)

- **D1 — malformed scalars accepted (7 cases: #1, #4, #6, #7, #8, #9, #10).** The validator accepts `float`/`bool`/string-list values in strict Int/int-list positions and returns `status='valid'` for a chunk that cannot come from the real transport. Consistent with Python truthiness/subclass coercion (`bool` is an `int`; `int(float)`/equality-style acceptance) instead of exact-type checks on the decoded transport value.
- **D2 — non-contract exception (#3).** A non-integer id text dies with a raw `ValueError` (`invalid literal for int() with base 10: 'two'`) instead of a stable `ContractRefusal` code. Callers distinguishing `ContractRefusal` from programmer error cannot classify this input; an unhandled path can surface as a host crash rather than a refusal.

Both are **fail-open / fail-crash at a versioned contract boundary** that exists precisely to refuse forged/replayed/malformed facts (`pep-checked-chunk-v1`). Owner: **Agent 1 (checker/host, `pep_chunk_contract.py`)** — Agent 3 does not edit builder-owned files.

## Reproduction (any machine with the pins)

```powershell
# direct (exit 1 = claim falsified; SUMMARY cases=12 claim_falsified=8)
python verification\probes\hostile_chunk_scalar_types.py D:\Projects\wt-a3-mimo-8130276

# Terror Bats (content-addressed receipt)
terrorbats spec check verification\bats\checked-chunk-malformed-scalars.yaml
terrorbats run verification\bats\checked-chunk-malformed-scalars.yaml --repo D:\Projects\wt-a3-mimo-8130276 --json

# replay (new execution; original receipt immutable)
terrorbats replay receipt:sha256:e2d49d13eec842f71ad3721efe36a7e89b27cf04930802145a4e0f79d4d7da07
```

## Caveats (stated, not softened)

- Worktree mode gives reversibility/observation, **not** hostile-code containment; `fs.read`/`network`/`git.remote.write` are UNENFORCED declarations (receipt records this).
- Pure-Python contract boundary: no native build, no C execution, nothing touching the Defender hold.
- `PROVEN` applies to *this claim at this commit*, nothing broader. After A1 repairs the contract, re-run the same bat: expected outcome is `NOT OBSERVED` (probe exit 0), which still would not certify the whole contract.

## Next action

Report D1/D2 to GitHub issue #16 directed at Agent 1 (Muse), cross-linked with the Agent 3 Basic Memory outbox receipt; re-run this bat unchanged after the checker-contract repair.
