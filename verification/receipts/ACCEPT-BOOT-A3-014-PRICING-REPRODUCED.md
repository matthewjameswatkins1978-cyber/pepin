# BOOT-A3-014: A1 receipts 015/017 pricing independently reproduced exactly (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-fullmap` @
`codex/a1-typed-bound-pipeline@a9e9e2f` (removed afterwards). A1's probes run
unmodified: `tests/probe_lexerstep_fullmap.py`, `tests/probe_staged_descent_sizing.py`.

## Results (exact)

- **Full map: lexer_step 23/36 valid**; failing positions
  [1,3,4,5,6,7,8,9,10,32,33,34,35]; **make_cursor 0/1** (group 0 fails).
- **Split confirmed by per-position codes/steps:**
  9× `PEP_UNKNOWN_VARIABLE` (pos 1: 28n/93,928 steps; 3: 3n/12,629; 7,8,9: 26n/~80k;
  33: 7n/18,459; 34: 21n/69,817; 35: 21n/59,727 — range 12,629–93,928 as claimed);
  4× `PEP_RUNTIME_STEP_LIMIT` at 100,001 (pos 4: 39n; 5: 45n; 6: 35n; 10: 51n);
  1× `PEP_TOOL_VALUE_LIMIT` (pos 32: **1,033 nodes**, 10,502 steps);
  make_cursor pos 0: **34n**, `PEP_RUNTIME_STEP_LIMIT`, 100,001 steps.
- Every figure matches receipts 015/017 verbatim, including the three design facts:
  STEP_LIMIT groups are small (35–51n, context-driven); pos 32 is the 1,033-node
  transport core; make_cursor dies at 34n (cost center, not granularity).

## Standing

- A1's pricing base is now independently verified end to end (map + sizing + the
  earlier 5/5 typed-bound verdicts). No builder SHA moved (typed-bound `a9e9e2f`,
  candidate impl `6dce37d`); all gate verdicts stand.
- A3 on standby for re-gate triggers (sourceGrant feature SHA per the armed checklist,
  A4's single seam handoff, summons). No human action needed.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-fullmap a9e9e2fe77a4321d6e5a6111b7ec9e7489853fe5
cd D:/Projects/wt-a3-fullmap; python tests/probe_lexerstep_fullmap.py       # 23/36 as above
python tests/probe_staged_descent_sizing.py                                  # table as above
```
