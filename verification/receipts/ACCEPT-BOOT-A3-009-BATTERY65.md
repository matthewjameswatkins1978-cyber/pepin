# BOOT-A3-009: 65-target battery independently confirmed on Candidate7 `6dce37d` (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-batt65` @ `6dce37d`
(removed afterwards). A1's claimed battery from outbox receipt 009, run unmodified.

## Result

`python -m unittest tests.test_a14_c23 tests.test_chunk_cross_call_facts
tests.test_checked_chunk_contract tests.test_c23_arity tests.test_c23_str_result` →
**Ran 65 tests, OK** (134.5 s). Matches A1's builder-run 12/12 + 53/53 exactly.

## Standing

- Builder claim verified, no discrepancy. With BOOT-A3-002 (frozen 15/16, sole red scale
  row) and BOOT-A3-003/004/005/008, candidate `6dce37d` is now covered by: frozen gate,
  strict-coverage measure, seam + K4 + P2 + ingress + hostile sets, and the full
  targeted battery — all SHA-bound.
- No builder SHA moved; nothing re-run beyond this new set. A3 on standby for re-gate
  triggers (new implementation SHA, A2 computed-call-args slice, builder summons).

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-batt65 6dce37da8930bdb4b0f5ba410c8042f23110545d
cd D:/Projects/wt-a3-batt65; python -m unittest tests.test_a14_c23 tests.test_chunk_cross_call_facts tests.test_checked_chunk_contract tests.test_c23_arity tests.test_c23_str_result  # 65 OK
```
