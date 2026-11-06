# BOOT-A3-012: A1's hostile pooled-carry suite verified; both review conditions CLOSED (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-hostile` @
`codex/a1-typed-bound-pipeline@a9e9e2f` (removed afterwards). A1's new suite run
unmodified; draft read at the same SHA.

## Results (exact)

- `tests.test_chunk_units_hostile + tests.test_chunk_units + tests.test_chained_bindings`:
  **21/21 OK** (26.1 s). The 4 new hostile tests:
  `foreign_document_stamp_propagates_and_state_unchanged`,
  `stale_revision_stamp_propagates`,
  `aliased_duplicates_renumbered_not_widened`,
  `forged_pooled_param_used_downstream_surfaces_as_refusal`.
- Draft `docs/CHECKED_CHUNK_CONTRACT_TYPED_BOUND_DRAFT.md` now carries
  **§6.1 "Inherited forgery residual (disclosed per A3 BOOT-A3-007 condition 2)"**:
  same-target forged PARAMETER admitted; forged RESULT/ARITY refused (cites K1/K1b).
- Additive posture preserved (new module + new tests + probes + draft deltas only;
  frozen contract/checker/budgets untouched per the branch diff).

## Review update (supersedes BOOT-A3-007/010 conditions)

- **Condition 1: CLOSED.** Hostile pooled-carry behavior is now builder-owned suite
  coverage (4 tests, green, independently re-run), including the forged-used-fact →
  first_refusal surfacing my K1c probed from outside.
- **Condition 2: CLOSED.** Residual disclosed in the draft itself.
- **Amendment verdict: ENDORSED from verification** — Option A direction + implementation
  + hostile suite + disclosures all check out. Remaining accept/decline is Matthew's
  product decision (and A1's plan-tier integration that follows it), not a verification gap.

## Status

- Candidate7 implementation `6dce37d` unchanged (candidate branch movement is
  outbox-only through `838c46a`); all gate verdicts stand.
- A3 packet work is complete to the extent dependencies allow: 12 receipts
  (BOOT-A3-001…012) covering Full-v2, staged coverage, K4 P1/P2, ingress, hostile
  K1/K1b/K1c, typed-bound repro + review, battery, say-gate, pooled-carry.
- Open mission remainder is builder/owner-owned: amendment acceptance + plan-tier
  integration (A1/Matthew), computed-call-args + SourceBytes native (A2), then A→B→C.
  A3 on standby for re-gate triggers (new implementation SHA carrying the amendment,
  A2 native slices, summons).

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-hostile a9e9e2fe77a4321d6e5a6111b7ec9e7489853fe5
cd D:/Projects/wt-a3-hostile; python -m unittest tests.test_chunk_units_hostile tests.test_chunk_units tests.test_chained_bindings  # 21 OK
```
