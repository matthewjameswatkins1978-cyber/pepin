# BOOT-A3-004: K4 P2 record-mismatch negative independently reproduced on Candidate7 `6dce37d` (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-p2neg` @ `6dce37d`
(removed afterwards); fixtures under ignored `_build/a3-p2neg/` only — never committed.
Seed CLI `pep.ps1 check --json`, unmodified.

## Result

- **P2 mismatch** (`type R { text: Str }`, `R { text: 0 }`):
  `status=invalid`, `code=PEP_TYPE_MISMATCH`, message `Expected Str but found Int`,
  span bytes 60–61 (the `0` literal), **exit 1**. Matches A4's doc verbatim.
- **Positive control** (`R { text: "hi" }`): `status=valid`, **exit 0**; typed tree binds
  `r: R` with `fieldId 0: text: Str`. The gate discriminates on the field type, not the shape.

## Standing

- With BOOT-A3-003 (P1 record-return native PASS, 21/48 clang+gcc), the K4 doc's full
  falsifier pair is now independently closed on the candidate: P1 lowers natively with seed
  parity; P2 refuses at construction with the exact diagnostic. No laundering path through
  record construction on this SHA.
- No new builder SHA observed (A1 `1aaead7`, A2 `6f7d72d`, candidate impl `6dce37d`,
  A4 `9ea369a` all unchanged at check time); all prior verdicts stand, nothing re-run.
- A3 remains on standby for re-gate triggers (new implementation SHA, A2 computed-call-args
  slice, or builder summons).

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-p2neg 6dce37da8930bdb4b0f5ba410c8042f23110545d
# _build/a3-p2neg/p2_record_mismatch.pep as above
./pep.ps1 check _build/a3-p2neg/p2_record_mismatch.pep --json   # invalid PEP_TYPE_MISMATCH exit 1
./pep.ps1 check _build/a3-p2neg/p2_record_ok.pep --json          # valid exit 0
```
