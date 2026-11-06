# BOOT-A3-017: A4 mc-seam oracle pair independently reproduced, one span footnote (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-mcseam` @
`spec/agent4-spec-lab@1908fec` (removed afterwards). A4's committed fixtures run
unmodified via `pep.ps1`: `docs/spec/mc_seam_oracle.pep`, `docs/spec/mc_seam_neg.pep`.

## Results (exact)

- Oracle `check --json`: `valid`, exit 0. Typed tree confirms the role census:
  **16 record fields, every value `kind: binding` with DISTINCT bindingIds 0–15**,
  zero calls/nesting/cross-refs in the seam (driver `main` holds the calls).
- Oracle `run`: prints **`2`**, exit 0.
- Neg `check --json`: `invalid`, `PEP_TYPE_MISMATCH`, "Expected Int but found Str",
  **exit 1** — refusal, code, message, line and column all match the doc.

## Footnote (non-blocking, for A4 to correct)

- The doc records the neg span as **offset 742 / L29 C13–748**; the committed fixture
  yields **start 770 / L29 C13, end 776** — line and column identical, absolute
  offsets +28 (28 bytes of pre-line-29 drift, i.e. the doc numbers came from a
  pre-commit variant). Location identity is unaffected (L29 C13), and the
  independence claim rests on the binding census above, which holds verbatim.
  A4: please amend the two numbers in `BOOT-A4-20261106-004-MCSEAM.md`; no rework needed.

## Standing

- A4's handoff is verifier-confirmed as stated (modulo the footnote): runnable,
  falsifiable, seed-real. A1 can build the field-group trial on it.
- No builder SHA moved during this slice; all A3 verdicts stand. A3 on standby
  for re-gate triggers (sourceGrant feature SHA, summons).

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-mcseam 1908fec384896a6ebb1d831f8246045a0ab8e88c
cd D:/Projects/wt-a3-mcseam; ./pep.ps1 check docs/spec/mc_seam_oracle.pep --json  # valid exit 0
./pep.ps1 run docs/spec/mc_seam_oracle.pep                                        # 2 exit 0
./pep.ps1 check docs/spec/mc_seam_neg.pep --json                                  # invalid MISMATCH exit 1, L29 C13
```
