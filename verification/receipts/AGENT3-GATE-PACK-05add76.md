# Agent 3 gate pack — one-command adversarial regression suite at A1 `05add76`

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Why:** Lucy priority 1–2 deliverable — the prepared adversarial regression tests for A1's
node-ID indexing/caching work and the open P1 regression, runnable as a single command.

## Deliverable

`verification/bats/agent3-index-gates.yaml` — Terror Bats **pack** bundling the three
standing gates (each already an individually content-addressed Bat):

| entry | gate | covers (Lucy themes) |
|---|---|---|
| `index-cache-claims.yaml` (`bat:sha256:3964c1ab…5525`) | `verification/probes/index_cache_adversarial.py` | stale revisions (STALE0/STALE1), invalid references (IDX1/IDX2), **duplicate child edges (IDX3)**, incorrect cache reuse (CACHE1–3), index invariants |
| `chunk-diagnostic-claims.yaml` (`bat:sha256:0a82537c…b824`, **new this slice**) | `verification/probes/chunk_diagnostic_preservation.py` | **diagnostic preservation / cross-chunk** (CD1 loss, CD2 extras, CD3 message parity, leakage) |
| `regression-hole-guard-passes.yaml` (`bat:sha256:c8e6b5a4…c04a`) | P1 `d158044` unittest, **byte-unchanged since first report** | priority 2 — armed until A1's fix SHA |

Pack identity: **`pack:sha256:01e9961ba3362922fed1dfac8f6c81eee0aa6315e7e72d4ad62ede74fe8670a0`**
(`terrorbats pack check` OK; `terrorbats spec check` OK on the new child).

## Pack run — the cheapest trustworthy check of the deliverable

```powershell
terrorbats pack run verification\bats\agent3-index-gates.yaml --repo <pinned-A1-worktree> --json
```

- **Campaign: `campaign:sha256:3cf3adfc8d84ac6e750b5adbaad366ac05e5de7eab763901eaccaaae6d3bd214`**
- Target: `D:\Projects\wt-a3-mimo-8130276` @ **`05add76e21d4c979d243fa1fd7cbd0eb2a9d945c`**, 3/3 children completed, 26 s, no stop-early, exit 1 (children proven), zero `INCONCLUSIVE`/`INFRASTRUCTURE ERROR`.
- **Summary: `PROVEN = 3`** (all three claims falsified at this head — the armed state, expected until repairs land):

| # | child | execution | receipt | verdict |
|---|---|---|---|---|
| 1 | `index-cache-claims` | `2c2f004f-2c3c-4cab-97b6-a8d39c3c49c4` | `receipt:sha256:6f1f96e19e165ebdbb5d58fc19b5465540504d08e8025df7bb61e13771a0b09e` | `PROVEN` (IDX3 + STALE1 falsified) |
| 2 | `chunk-diagnostic-claims` | `812124f1-721e-4bea-bc9c-3b10e2b75add` | `receipt:sha256:b652554aed4ee991f42402dd759f60a3a7b719712d1ff685b2b878823ab90aa2` | `PROVEN` (CD3 message parity falsified) |
| 3 | `regression-hole-guard-passes` | `56c773c3-8665-4ca3-97ef-6c0876587c79` | `receipt:sha256:54cde118f877b7417bd0ffd406de44718e88c5f699b3f77e634feba43e07314c` | `PROVEN` (P1 still open) |

## Success criterion (stated once, for the fix/index SHA)

At A1's future repair/index commit, the **same pack command** must yield
**`NOT OBSERVED = 3`, exit 0** — probe exit codes are 0 held / 1 falsified / 2 harness error,
so a harness failure can never masquerade as a pass or a falsification. Any other outcome
keeps the corresponding finding open. Child receipts remain individually replayable
(`terrorbats replay receipt:sha256:…`).

## Honest scope

- Verdict `PROVEN` = *these claims are false at this commit under recorded conditions* —
  never certification of the whole contract; each child receipt carries its own epistemic layers.
- Pure checker/session layer; no native build/execution; no builder files
  (`verification/**` only); worktree mode is reversibility/observation, not containment.
- Pack adds ordering only — no new claims beyond the three children.

## Reproduction

```powershell
terrorbats pack check verification\bats\agent3-index-gates.yaml
terrorbats pack run   verification\bats\agent3-index-gates.yaml --repo <pinned-A1-worktree> --json
```
