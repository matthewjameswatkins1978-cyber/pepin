# `pep-checked-chunk-v1` forged-facts campaign — 12 claim cases hold at A1 `05add76`

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Scope:** the documented refusal-code list in `docs/CHECKED_CHUNK_CONTRACT.md` — deliberately **additive** to A1's own 27-case `tests/test_checked_chunk_contract.py` (read first, then attacked only the unnamed edges).

## Pins and identities

| Fact | Value |
|---|---|
| Target | A1 `codex/checker-emitter-integration` @ `05add76e21d4c979d243fa1fd7cbd0eb2a9d945c` (clean pinned worktree `D:\Projects\wt-a3-mimo-8130276`) |
| Probe | `verification/probes/hostile_chunk_forged_facts.py` |
| Bat | `verification/bats/chunk-forged-facts.yaml` — `bat:sha256:35ad69de6d09bff82299a44cf99397ea80bfd8f8796f84012208142bcce460ba` |
| **Receipt** | **`receipt:sha256:607656e6c4435e7c9a195b78b7b31afa7b21574b53eb5d0507db95f700fa056a`** (execution `d54c9d1b-f715-4f87-ba68-aa7ecb75135e`) |
| Three layers | execution `Completed` / oracle `NotFalsified` / verdict **`NOT OBSERVED`** — this attack did not falsify the claim; never a whole-contract certificate |
| Probe stdout evidence | `evidence:sha256:7a30ac8b625a603fe8551dee90f8156436b65b8e139d8faf3f0109d56d1833f3` (digest verified on read) |
| Direct rerun | identical: exit 0, `SUMMARY cases=14 claim_falsified=0` (12 claim cases + 2 observations) |

## Result: 12/12 claim cases refused with the documented code

| # | forged/malformed edge | expected | observed |
|---|---|---|---|
| P1 | empty plan | `CHUNK_PLAN_EMPTY` | `CHUNK_PLAN_EMPTY` ✓ |
| P2 | plan chunk that opens a parent (coverage complete) | `CHUNK_PLAN_OPEN_PARENT` | `CHUNK_PLAN_OPEN_PARENT` ✓ |
| P3 | node record with wrong type tag (`AstNode`) | `CHUNK_TYPE_MISMATCH` | `CHUNK_TYPE_MISMATCH` ✓ |
| P4 | `nodes` as bare int list | any refusal | `CHUNK_TYPE_MISMATCH` ✓ |
| P5 | **report from another DOCUMENT** | `CHUNK_REPORT_MISMATCH` | `CHUNK_REPORT_MISMATCH` ✓ |
| P6 | chunk envelope from another DOCUMENT | any refusal | `CHUNK_STALE_REVISION` ✓ |
| P7 | `report.status = True` (bool in Str field) | any refusal (scalar rule) | `CHUNK_SCALAR_TYPE` ✓ |
| P8 | `report.status = "VALID"` (wrong case) | `CHUNK_REPORT_STATUS_UNKNOWN` | `CHUNK_REPORT_STATUS_UNKNOWN` ✓ |
| P9 | `coveredNodeIds` descending (documented "ascending") | any refusal | `CHUNK_COVERAGE_MISMATCH` ✓ |
| P10 | `coveredNodeIds` with duplicate entry (documented "unique") | any refusal | `CHUNK_COVERAGE_MISMATCH` ✓ |
| P11 | `suppliedSignatures = [False]` (`False == 0` in Python) | any refusal | `CHUNK_SCALAR_TYPE` ✓ |
| P12 | `suppliedSignatures = [True]` | any refusal | `CHUNK_SCALAR_TYPE` ✓ |
| O1 | `ChunkLedger.complete()` before any chunk | observation | raises `CHUNK_INCOMPLETE` — the ledger refuses to *lie* rather than returning a false `True` |
| O2 | `CONTRACT_VERSION` | observation | `pep-checked-chunk-v1` |

Notably closed attack classes: **bool-as-int equality** (`False`/`True` in every integer position), **cross-document identity** (both report and envelope), and **documented ordering/uniqueness enforcement** on `coveredNodeIds`.

## Why no defect this time

The two boolean-signature cases were the sharpest: Python `False == 0` would have certified an uncertified signature under a naive `in`-set membership. The post-`05add76` exact-int rule (`bool` explicitly rejected) refuses them, consistent with the "Scalar rules (Agent 3 finding, repaired)" section A1 added to the contract doc.

## Honest scope

- `NOT OBSERVED` bounds exactly these 12 edges at this commit. The remaining documented codes not attacked here (`CHUNK_VERSION_UNKNOWN`, `CHUNK_REPEATED`/`OUT_OF_ORDER`, `CHUNK_INDEX_OUT_OF_RANGE`, shared-root plan rules, report node-count) are covered by **A1's own** 27-case suite, independently rerun earlier this session at 42/42 OK — but my probe does not re-assert them; combined coverage is complementary, not duplicated.
- Pure-Python contract layer; no native build/execution; no caps, budgets, protocols, `CURRENT`/manifest or builder files changed by Agent 3.
- Worktree mode = reversible/observable, **not** hostile-code containment (recorded in the receipt).

## Reproduction

```powershell
python verification\probes\hostile_chunk_forged_facts.py <pinned-A1-worktree>   # expect exit 0
terrorbats run verification\bats\chunk-forged-facts.yaml --repo <pinned-A1-worktree> --json  # expect NOT OBSERVED
terrorbats replay receipt:sha256:607656e6c4435e7c9a195b78b7b31afa7b21574b53eb5d0507db95f700fa056a
```

## Next action

Keep both bats as standing regression pins on any `pep_chunk_contract.py` change; carry this green result into the next consolidated 3-slice review on #16 (per the standing rule that healthy green runs may be consolidated); continue the board queue.
