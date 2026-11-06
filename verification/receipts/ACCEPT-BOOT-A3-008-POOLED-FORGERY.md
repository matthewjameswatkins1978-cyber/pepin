# BOOT-A3-008: pooled carried-fact forgery — USED binding refused, mechanism exists (Agent 3)

**Seat:** Agent 3. New committed probe `verification/probes/pooled_forgery_k1c.py`;
detached read-only scratch `D:/Projects/wt-a3-poolf` @
`codex/a1-typed-bound-pipeline@9eea380` (removed afterwards). Supports the acceptance
condition imposed in BOOT-A3-007 (K1/K1b green on the pooled path before pinning).

## Results (exact, utf8_check groups 0→1)

- group0 honest `valid`; group1 CONTROL (honest pool) `valid`.
- **F1 — forged USED carried binding (`first` Int→Str, honest stamps): `invalid`,
  `PEP_TYPE_MISMATCH` — REFUSED.** The pooled path enforces carried types at use sites.
- **F2 — forged binding group 1 does not use (`source`): `valid` — vacuous admission,
  documented as non-evidence.** An earlier scratch run misread an F2-shaped result as
  enforcement failure; correcting here: only F1 discriminates. The unused-binding case
  proves nothing either way.

## Reading

- The amendment's pooled carried-fact path already refuses retyped bindings where they
  are consumed — the mechanism Condition 1 demands exists; the remaining acceptance
  work is running the FULL K1/K1b hostile set (duplicates, aliases, foreign/omitted
  stamps, param/result/arity forgeries) against pooled facts before pinning, plus
  stating the inherited param-forgery residual (Condition 2).
- K1's admitted param forgery concerns callee SIGNATURE facts, a different record kind
  from carried BINDING facts — the two residuals must not be conflated in review.
- No builder SHA moved (typed-bound `9eea380`, candidate impl `6dce37d` unchanged);
  all prior verdicts stand.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-poolf 9eea380538351c66a2abb3b367b04a7465c1d745
python verification/probes/pooled_forgery_k1c.py D:/Projects/wt-a3-poolf
# F1 invalid/PEP_TYPE_MISMATCH (refused); F2 valid (vacuous control)
```
