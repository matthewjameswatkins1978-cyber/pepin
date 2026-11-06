# BOOT-A3-019: battery split independently confirmed 12/12 + 53/53 (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-split` @ `6dce37d`
(removed afterwards). Splits A1's claimed 65-target battery (receipt 009) into the
reported modules and checks counts + timings, not just the total (BOOT-A3-009).

## Results (exact)

- `tests.test_a14_c23` alone: **Ran 12 tests, OK** (67.4 s; A1 reported 63.3 s — same
  count, timing within machine noise).
- `test_chunk_cross_call_facts + test_checked_chunk_contract + test_c23_arity +
  test_c23_str_result`: **Ran 53 tests, OK** (51.4 s; A1 reported 51.6 s).
- Split sums to the independently measured 65/65 total. Builder timing claims check out.

## Standing

- No builder SHA moved; all verdicts stand. A3 on standby for re-gate triggers
  (sourceGrant feature SHA, A1 integration SHA, summons). No human action needed.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-split 6dce37da8930bdb4b0f5ba410c8042f23110545d
cd D:/Projects/wt-a3-split; python -m unittest tests.test_a14_c23  # 12 OK
python -m unittest tests.test_chunk_cross_call_facts tests.test_checked_chunk_contract tests.test_c23_arity tests.test_c23_str_result  # 53 OK
```
