# Cited-vs-asserted refusal-code sweep at A1 `05add76` — 2 gaps found, 2 closed (25/25)

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Method:** static audit (cheapest first) → targeted probe for the gaps.

## Audit

Source of truth: every `CHUNK_*` code cited in `docs/CHECKED_CHUNK_CONTRACT.md`
(case-sensitive extraction) must be asserted by at least one test in builder
`tests/**` or Agent 3 `verification/**` (my base-era precedent: 54/54 cited-vs-asserted
at `805062b`; this re-pins the contract doc at head).

| metric | count |
|---|---|
| codes cited in the contract doc | **25** |
| asserted in builder `tests/**` | 22 |
| asserted in `verification/**` | 16 (overlapping) |
| **gaps (cited, asserted nowhere)** | **2 → now closed** |

**Gaps found:** `CHUNK_OPEN_PARENT` (chunk-time) and `CHUNK_PLAN_SHARED_NOT_PLANNED`
(plan-time). Both were *implemented* (`pep_chunk_contract.py:404` and `:319`, both in
the `CONTRACT` dict) but never asserted anywhere.

## Probe — `verification/probes/refusal_code_coverage.py`

Run at A1 `codex/checker-emitter-integration` @ `05add76` (clean pinned worktree):
**exit 0, `SUMMARY cases=2 claim_falsified=0`** — both cited codes fire with their
exact documented identity:

| case | result |
|---|---|
| **G1** chunk that passes coverage with the exact planned id list, then has a node's `parentId` mutated to a missing node (`0` → `-5`) | **`CHUNK_OPEN_PARENT`** ✓ — reachable through `validate_chunk` (defense-in-depth line is live, not dead) |
| **G2** `plan_ids(index, [[0,1,2]], shared_roots=(3,))` — incomplete coverage naming a shared root that lies in no planned chunk | **`CHUNK_PLAN_SHARED_NOT_PLANNED`** ✓ — the shared-root check runs **before** the coverage-incomplete check |

**Sweep result: 25/25 cited codes are now asserted.**

## Note for A1 (test-comment refinement, no builder edit made)

`tests/test_checked_chunk_contract.py::test_shared_root_containment_guard_is_defensive`
comments that the guard "stays unreachable through `plan_chunks`/`plan_ids`". That holds
for **full-coverage** plans (their test uses them — under full coverage + parent
closure, splitting a subtree is impossible, as their comment reasons). It is reachable
through `plan_ids` with **incomplete coverage naming an unplanned shared root** (G2
above): per-node checks pass, the shared-root check fires before the missing-coverage
check. The code and its doc/dict listing are correct; only the reachability comment
overstates. Suggested (owner's call): extend their defensive test with the G2 shape or
narrow the comment to "unreachable through full-coverage plans". My probe asserts the
code either way.

## Honest scope

Contract layer only (pure Python, no session/emission/native). Static counts are
exact for the contract doc at this head; other docs' transport codes were covered by
the base-era audit and were not re-derived here. Probe committed under `verification/**`
and stands as the regression pin for both codes (re-run: exit 0 required).

## Reproduction

```powershell
python verification\probes\refusal_code_coverage.py <worktree-at-05add76>   # exit 0
```
