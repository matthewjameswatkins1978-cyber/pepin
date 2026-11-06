# BOOT-A3-018: K1c pooled forgery holds on Candidate7 itself (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-k1ccand` @ `6dce37d`
(removed afterwards). Committed probe `pooled_forgery_k1c.py` run unmodified.

## Why this run

K1c (BOOT-A3-008) measured the typed-bound branch. Static check showed the
candidate already carries the pooled machinery (`BindingPool` in
`pep_chunk_contract.py`, `analyze_chunk_typed_bound` in the checker,
`test_chained_bindings`/`test_chunk_typed`/`chunk_helper` all present), so the
same hostile question applies to the acceptance SHA directly.

## Results (exact, candidate `6dce37d`)

- group0 honest `valid`; group1 CONTROL (honest pool) `valid`.
- **F1 forged USED carried binding (`first` Int→Str, honest stamps): `invalid`,
  `PEP_TYPE_MISMATCH` — REFUSED.**
- F2 forged unused binding: `valid` (documented vacuity control, non-evidence).

## Standing

- Pooled carried-fact enforcement now demonstrated on BOTH the amendment branch
  and the candidate: the mechanism is in the shared machinery, not a branch artifact.
- No builder SHA moved; all gate verdicts stand. A3 on standby for re-gate triggers.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-k1ccand 6dce37da8930bdb4b0f5ba410c8042f23110545d
python verification/probes/pooled_forgery_k1c.py D:/Projects/wt-a3-k1ccand  # F1 refused
```
