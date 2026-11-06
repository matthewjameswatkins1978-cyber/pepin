# BOOT-A3-011: say-gate triple confirms A4's corrected K4 oracle description (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-saygate` @ `6dce37d`
(removed afterwards); fixtures under ignored `_build/a3-saygate/` only. Seed
`pep.ps1 check --json`, unmodified. Closes the one part of A4's `9ea369a` correction
no lane had independently reproduced (P1/P2 were closed in BOOT-A3-003/004).

## Results (exact, candidate `6dce37d`)

- `say(41)` → `invalid`, `PEP_TYPE_MISMATCH`, "Expected Str but found Int" (bytes 25–27), **exit 1**.
- `say("hi")` → `valid`, **exit 0** (control: Str argument accepted).
- `say(int_text(41))` → `valid`, **exit 0** (control: the int_text route A2's K4 probe uses).

## Reading

- Confirms the correction: `say` is `[Str] -> Unit` at this SHA, so a naive
  `say(a.line)` reconstruction is a type error, not an oracle — values must pass
  through `int_text`, exactly as A2 measured and A4 recorded. No new semantics;
  the builtin gate behaves as documented.
- Fixture hygiene note: my first `say("hi")` fixture carried shell-escaped quotes
  (`\"hi\"` → `PEP_UNEXPECTED_CHARACTER`); rewrote the fixture bytes and re-ran —
  the invalid result above is from the corrected fixture. Stated so the log trail
  stays honest.
- No builder SHA moved; all prior verdicts stand. A3 on standby for re-gate triggers.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-saygate 6dce37da8930bdb4b0f5ba410c8042f23110545d
./pep.ps1 check _build/a3-saygate/say_int.pep --json      # invalid MISMATCH exit 1
./pep.ps1 check _build/a3-saygate/say_str.pep --json      # valid exit 0
./pep.ps1 check _build/a3-saygate/say_inttext.pep --json  # valid exit 0
```
