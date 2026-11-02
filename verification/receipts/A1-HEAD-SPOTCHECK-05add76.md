# A1 head spot-check at `05add76` — ledger, node-cost, budgets and the `open_bytes` cap

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
Two board slices in one receipt: (2) independent reruns of A1's current test surface, (3) `open_bytes` 65,536-byte limit re-pin (LUCY-20261102-005 first-target item).

## Pin

Target: A1 `codex/checker-emitter-integration` @ `05add76e21d4c979d243fa1fd7cbd0eb2a9d945c` (clean pinned worktree `D:\Projects\wt-a3-mimo-8130276`).

## 2. Independent reruns (run by Agent 3, not taken on report)

| suite | result | time |
|---|---|---|
| `tests.test_lexer_chunk_ledger` (real-lexer 15-chunk plan ledger) | **4/4 OK** | 4.05s |
| `tests.test_checker_node_cost` (per-invocation node affordance pins) | **2/2 OK** | 0.97s |
| `tests.test_a13_checker_budgets` + `tests.test_checked_chunk_contract` + `tests.test_chunk_scalar_validation` | **59/59 OK** (17 + 27 + 15) | 15.66s |
| `py_compile tests/test_lexer_chunk_ledger.py` | exit 0 | — |

**Total: 65 tests green at this head in this session** (42 of them already reported in `CHECKED-CHUNK-fix-verified-05add76.md`). No contradiction with A1's own posted counts (ledger 4, node-cost 2, budgets 17 incl. 3 parser pins, contract 27, scalar 15).

## 3. `open_bytes` cap re-pin (`verification/probes/open_bytes_limit.py`)

Exit 0, `SUMMARY cases=2 claim_falsified=0` at `05add76`:

| claim | result |
|---|---|
| L1 exactly 65,536 bytes open with `outcome: ok` | ✓ (`document: doc-1`, `revision: sha256:bf718b6f…9c5a`; analysis status `invalid` for the `'a' × 65,536` fixture — expected, and irrelevant to the cap) |
| L2 65,537 bytes refused with `PEP_SOURCE_BYTE_LIMIT` | ✓ — verbatim message: *"Source byte input exceeds 65536 bytes"* |

This re-pins corpus case R3 (measured at base `805062b`,2026-10-29) to the current head: **the cap is unchanged and still enforced pre-analysis**. No cap was raised by anyone in between, per this measurement.

## Honest scope

- Reruns are at one head only; they do not re-verify the numbers A1 posted at older pins (`8b173e8`, `4e96d2e`, `81302767`) beyond what this head reproduces.
- The byte-limit probe is session-protocol only; it does not re-verify transport/JSONL framing caps (covered by the standing corpus at base, replay 172/172).
- Pure Python/protocol: no native build, no execution of generated C, no caps/budgets/protocols/`CURRENT`/manifest touched by Agent 3.

## Reproduction

```powershell
python -m unittest tests.test_lexer_chunk_ledger tests.test_checker_node_cost -v
python -m unittest tests.test_a13_checker_budgets tests.test_checked_chunk_contract tests.test_chunk_scalar_validation
python verification\probes\open_bytes_limit.py <pinned-A1-worktree>    # expect exit 0
```

## Next action

Post consolidated 3-slice review #2 to #16 (forged-facts campaign + this spot-check + byte-limit re-pin); continue with the next board item.
