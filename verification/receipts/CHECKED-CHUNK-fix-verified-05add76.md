# CHECKED-CHUNK malformed-input regression — **re-verified repaired** at A1 `05add76`

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Supersedes the open verdict of** `CHECKED-CHUNK-malformed-scalars-8130276.md` (defects D1/D2 at `81302766`); both receipts stay for provenance.

## What changed

A1 pushed `05add76e21d4c979d243fa1fd7cbd0eb2a9d945c` — `fix(host): refuse lossy or malformed scalars at the chunk boundary`
(2026-11-02 15:13 UTC; `pep_chunk_contract.py` +105/-29, new `tests/test_chunk_scalar_validation.py`, `docs/CHECKED_CHUNK_CONTRACT.md` +26).
Timestamp note: the fix commit **predates** my issue #16 report (comment `6580694862`) — no causality is claimed; it is measured and reported as an independent convergence, then independently verified by me.

## Re-verification (same bat, unchanged — only the target pin moved)

| Fact | Value |
|---|---|
| Target commit | `05add76e21d4c979d243fa1fd7cbd0eb2a9d945c` (clean pinned worktree `D:\Projects\wt-a3-mimo-8130276`, detached) |
| Direct probe | `python verification\probes\hostile_chunk_scalar_types.py <worktree>` → **exit 0**, `SUMMARY cases=12 claim_falsified=0` |
| Terror Bats | `terrorbats run verification\bats\checked-chunk-malformed-scalars.yaml --repo <worktree> --json` → `terrorbats` exit 0 |
| **Receipt** | **`receipt:sha256:cd5195b5e38e4d43e0e52e47dc19f7bff59000cf001b3baf4b7a33b939ecd9a8`** (execution `0647bb92-d61c-499d-81ab-02a4b5fe001f`) |
| Three layers | execution `Completed` / oracle `NotFalsified` / verdict **`NOT OBSERVED`** — this attack did not falsify the claim. **Never** "the contract is correct". |
| Probe stdout evidence | `evidence:sha256:caa314a21d7e092f3448498f09030f97683524f37f10220aad2d4b80126713ab` (digest verified on read) |
| Spec identity | unchanged (`bat:sha256:9c39a559…`, `claim:sha256:63bcad85…`, `oracle:sha256:9861b128…`) — the two receipts are directly comparable |

## Per-case result at `05add76` (11 claim cases)

| case | outcome | code |
|---|---|---|
| `childIndex = -0.5` | REFUSED | `CHUNK_SCALAR_TYPE` |
| `childIndex = -1` (control) | REFUSED | `CHUNK_NEGATIVE_CHILD_INDEX` |
| node `id = 'two'` | REFUSED | `CHUNK_SCALAR_FORMAT` |
| `coveredNodeIds` bools | REFUSED | `CHUNK_SCALAR_TYPE` |
| `coveredNodeIds` strings | REFUSED | `CHUNK_SCALAR_TYPE` |
| `parentId = 1.9` | REFUSED | `CHUNK_SCALAR_TYPE` |
| node `id = 2.9` | REFUSED | `CHUNK_SCALAR_TYPE` |
| `report.syntaxNodeCount = 3.0` | REFUSED | `CHUNK_SCALAR_TYPE` |
| `chunk.index = false` | REFUSED | `CHUNK_SCALAR_TYPE` |
| `suppliedSignatures = ["0"]` | REFUSED | `CHUNK_SCALAR_TYPE` |
| `suppliedSignatures = [0]` (control) | ACCEPTED | — |
| (observation) ids not starting at 0 | ACCEPTED | — |

Both defect classes are closed: **D1** (7 loose-scalar acceptances) now refuses with stable `CHUNK_SCALAR_TYPE`; **D2** (raw `ValueError`) now refuses with stable `CHUNK_SCALAR_FORMAT`. Non-claim observation unchanged.

## Corroboration (independent rerun of the builder's own suite)

`python -m unittest tests.test_chunk_scalar_validation tests.test_checked_chunk_contract -v` at `05add76` → **42 tests, OK** (0.761s) — A1's new scalar-validation module plus the pre-existing 27 hostile contract cases, run by Agent 3, not taken on report.

## Honest scope

- `NOT OBSERVED` is the correct ceiling here: my 11-case probe no longer falsifies the claim at this commit. It does not certify the whole `pep-checked-chunk-v1` surface, the session transport path (`NOT_RUN`), or native/C behaviour (Defender hold; untouched).
- Worktree mode = reversible/observable, not containment (recorded in both receipts).
- Pure-Python boundary; no caps, budgets, protocols, `CURRENT`/manifest or builder files changed by Agent 3 (`verification/**` only).

## Reproduction

```powershell
git -C <worktree> checkout --detach 05add76e21d4c979d243fa1fd7cbd0eb2a9d945c
python verification\probes\hostile_chunk_scalar_types.py <worktree>                      # expect exit 0
terrorbats run verification\bats\checked-chunk-malformed-scalars.yaml --repo <worktree> --json  # expect NOT OBSERVED
terrorbats replay receipt:sha256:cd5195b5e38e4d43e0e52e47dc19f7bff59000cf001b3baf4b7a33b939ecd9a8
```

## Next action

Close D1/D2 on #16 with this receipt; continue the board queue (A2 `codex/a2-list-record-fields@c70d5eb` bounded-emitter slice is the next candidate). Re-run this bat on any future `pep_chunk_contract.py` change.
