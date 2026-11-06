# BOOT-A3-006: same-target forged RESULT/ARITY are REFUSED — residual narrowed (Agent 3)

**Seat:** Agent 3. New probe `verification/probes/forged_result_arity_k1b.py` (committed here);
detached read-only scratch `D:/Projects/wt-a3-k1b` @ `6dce37d` (removed afterwards).
K1's registration flow reused verbatim; only the forgery variants are new.

## Results (exact, candidate `6dce37d`)

- Controls: C0 honest positive `valid`; C1 honest negative `invalid/PEP_TYPE_MISMATCH`;
  seed oracles agree (`invalid`+MISMATCH / `valid`).
- **A6 forged RESULT Int→Str (honest stamps): `invalid`, `PEP_TYPE_MISMATCH` — REFUSED.**
- **A7 forged ARITY 1→2 (ptypes untouched): `invalid`, `PEP_ARGUMENT_COUNT` — REFUSED.**
- **A8 forged ARITY 2 + matching second Int ptype: `invalid`, `PEP_ARGUMENT_COUNT` — REFUSED.**
- `SUMMARY forged-admitted=none`.

## Reading (stated, not relabeled)

- K1's admitted residual stands but is now bounded: same-target **parameter-type** forgery is
  admitted (stamps are consistency-only there), while same-target **result-type** and **arity**
  forgeries are caught by the checker's own gates with named codes. A future content-binding
  mechanism still needs to close the param case; nothing here claims it closed.
- Hand-supplied facts, not executable attacks (no such program exists for a seed oracle) —
  the honest-producer boundary from the dispatch, preserved.
- No builder SHA moved (A1 `1aaead7`, A2 `6f7d72d`, candidate impl `6dce37d` unchanged);
  all prior verdicts stand. A3 remains on standby for re-gate triggers.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-k1b 6dce37da8930bdb4b0f5ba410c8042f23110545d
python verification/probes/forged_result_arity_k1b.py D:/Projects/wt-a3-k1b  # admitted=none
```
