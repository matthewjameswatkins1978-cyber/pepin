# BOOT-A3-015: interior-availability pricing reproduced exactly (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-interior` @
`codex/a1-typed-bound-pipeline@a9e9e2f` (removed afterwards).
`tests/probe_interior_availability.py` run unmodified.

## Results (exact)

- lexer_step pos 4/5/6/10: `if_statement`, `body_parts=0`, no interiors.
- lexer_step pos 32: `while`, `body_parts=1` — the single-part "interior" equals the
  whole 1,033-node statement (recursive descent required, not one-level interiors).
- make_cursor pos 0: `return`, `body_parts=0`, no carving possible via interiors.
- Matches the probe's documented claim verbatim, including the pos-32 nuance.

## Standing

- A1's interior-availability pricing is independently confirmed; with BOOT-A3-014 the
  full stay-gap evidence (map + sizing + interior shapes) is now verifier-reproduced.
  No builder SHA moved; all verdicts stand. A3 on standby for re-gate triggers
  (sourceGrant feature SHA, A4 seam handoff, summons). No human action needed.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-interior a9e9e2fe77a4321d6e5a6111b7ec9e7489853fe5
cd D:/Projects/wt-a3-interior; python tests/probe_interior_availability.py
```
