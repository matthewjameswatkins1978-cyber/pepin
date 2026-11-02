# INDEX-CACHE adversarial batch at A1 `05add76` — 2 of 7 claims falsified (prepared gate for the node-ID index)

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Why:** Lucy advisory `LUCY-20261102-006` priority 1 — prepare adversarial regression tests for A1's proposed node-ID indexing/caching over stale revisions, invalid references, duplicate child edges, incorrect cache reuse and diagnostic preservation. The batch runs **now** as the head baseline and re-runs **byte-identical** at A1's future index/caching SHA as the acceptance gate (alongside the unchanged P1 regression bat).

## Identifiers

| Fact | Value |
|---|---|
| Target | A1 `codex/checker-emitter-integration` @ `05add76e21d4c979d243fa1fd7cbd0eb2a9d945c` (clean pinned worktree) |
| Probe | `verification/probes/index_cache_adversarial.py` (exits: 0 claims-held, 1 falsified, 2 harness error) |
| Bat | `verification/bats/index-cache-claims.yaml` — `bat:sha256:3964c1ab56a56123f15ee0db12dd9373590b6f461c8e19c860ecabb063395525` |
| **Receipt** | **`receipt:sha256:86e0ca07086bd0f884ee2132504fac47ceb8a2f873bb5834d962452c50081743`** (execution `8b880939-6d84-44b4-a718-286fb0fb5c93`) |
| Three layers | execution `Completed` / oracle `Falsified` / verdict **`PROVEN`** — “all index/cache claims hold at this commit” is false under recorded conditions |
| Evidence | stdout `evidence:sha256:0facd94d0ffd49812eecc064236afc6ab0a0d592b6a74db2fbcc63c3be2069e5` (digest verified), stderr empty |
| Direct rerun | identical: exit 1, `SUMMARY cases=9 claim_falsified=2` |

## Results — 7 claim cases (5 held, **2 falsified**) + 2 observations

| claim | result |
|---|---|
| IDX1 index refuses missing parent → `CHUNK_PLAN_OPEN_PARENT` | HELD |
| IDX2 index refuses parent at/after child → `CHUNK_INVALID_PARENT_ORDER` | HELD |
| **IDX3 index refuses duplicate child edge (same parent+role+childIndex)** | **FALSIFIED — accepted** |
| CACHE1 same-revision re-query: no reparse/recheck growth, byte-identical diagnostics | HELD (`cache_hits` 0→1→2; parse/typecheck flat 3/3) |
| CACHE2 diagnostics follow a +4-byte edit exactly | HELD (`PEP_UNKNOWN_TYPE` span 21→25 / 35→39, message unchanged) |
| CACHE3 revert restores original revision id + byte-identical diagnostics | HELD |
| **STALE1 crossed pair (rev1 args under rev2 target) refused** | **FALSIFIED — accepted, report mislabelled** |
| IDX4 *(obs)* document-level negative `childIndex` | accepted at index level (chunk validation refuses downstream) |
| STALE0 *(obs)* consistent pre-edit pair after advance | `ok` — older revisions usable by design |

## Finding 1 — IDX3: duplicate child edges accepted (invalid-reference class)

`DocumentIndex.__init__` enforces duplicate ids, contiguity, missing parents and parent
order — but **not sibling-edge identity**. Two nodes `(parent=0, role=statement,
childIndex=0)` and `(parent=0, role=statement, childIndex=0)` build an index without
refusal, and plans/chunks can be built over it. Downstream `(parent, role, childIndex)`
is a key (`child_at`, `count_children`, emitter fixed-slot routing): an ambiguous edge
makes “which child?” unanswerable while every identity check still passes. Anchor:
the chunk-contract provable-piece rule (no authoritative parse can contain two children
with the same edge identity). Owner: A1 (`pep_chunk_contract.py`).

## Finding 2 — STALE1: crossed provenance accepted; report labels rev2, content is empty

After the target advances rev1 → rev2, `tool_invoke pep-c23-checker` with
`arguments=[parsed@rev1]` and `semanticTarget.revision=rev2` returns **`outcome: ok`,
no refusal code**, and a `CheckerReport` that:

- **declares `revision = rev2`** (label taken from the target, not the analysed data), and
- carries **`syntaxNodeCount = 0`**, while legitimate analyses of *either* revision give
  **7** (same-run fresh control: `fresh_nodes=7`, `fresh_declared==fresh_rev=True`;
  consistent-pair control also `ok` with 7).

Contentless analysis wearing the wrong revision's label = one step from cache poisoning:
a consumer caching by `report.revision` stores a **0-node "rev2" result**. The documented
shape for mismatches is a stable refusal (`PEP_TOOL_*`/stale family); `ok` + mislabelled
empty report is neither refusal nor truth. Mechanism (why 0 nodes; deliberate
blank-on-mismatch?) is the owner's to establish. Owner: A1 (host layer `pep_c23.py`).

## Controls / non-vacuity

Consistent pairs work before and after the edit; fresh target works (7 nodes,
self-labelling); CACHE1–3 prove same-reference and edit/revert paths return real,
position-correct diagnostics — so neither falsification is a “tools broken” artifact.
Harness disclosure: my first three runs contained harness bugs (exact-code comparison,
diagnostic-field extraction, over-broad stale claim) — all fixed via Threadmoth (9
certified edits, `unrelated_bytes_changed=false`, `lf→lf`) before the results above were
recorded; a crash path now exits 2 so harness failure can never read as falsification.

## Honest scope

- One head; the crossed-stale mechanism was measured (not inferred) but not bisected —
  current-state finding, offered for bisection if A1 wants it.
- Pure checker/session layer: no emission, no native build, no execution; no builder
  files touched (`verification/**` only).
- `PROVEN` = this claim at this commit. Success at A1's repair SHA = probe exit 0 and
  bat `NOT OBSERVED`, run together with the unchanged P1 gate.

## Reproduction

```powershell
python verification\probes\index_cache_adversarial.py <worktree>        # exit 1 today
terrorbats run verification\bats\index-cache-claims.yaml --repo <worktree> --json   # PROVEN
terrorbats replay receipt:sha256:86e0ca07086bd0f884ee2132504fac47ceb8a2f873bb5834d962452c50081743
```
