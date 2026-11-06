# BOOT-A3-007: A1 typed-bound claims independently reproduced 100% + amendment review (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-typbound` @
`codex/a1-typed-bound-pipeline@9eea380` (removed afterwards). A1's
`tests/probe_typed_bound_pipeline.py` run UNMODIFIED, cold (own seed build).

## 1. Independent reproduction: 5/5 verdicts + all quantities match

| function | A1 claimed | A3 reproduced |
|---|---|---|
| lexer_start | COVERED-CHUNK | COVERED-CHUNK |
| make_progress | COVERED-CHUNK (scoped) | COVERED-CHUNK |
| utf8_check | COVERED-BOUND 21/21 | **COVERED-BOUND 21/21** |
| make_cursor | NOT-COVERED, group 0 | NOT-COVERED, group 0 |
| lexer_step | NOT-COVERED, group 1 | NOT-COVERED, group 1 |

Quantities: utf8_check per-group steps **15,896–89,918** (all < 100k), **9 bindings
carried** at end; make_cursor exactly **1** statement; lexer_step **36** statements.
A1's evidence base (receipts 011/012) is independently confirmed on the published SHA.

## 2. Amendment review (DRAFT `docs/CHECKED_CHUNK_CONTRACT_TYPED_BOUND_DRAFT.md` @ 9eea380)

Input for Matthew — review, not acceptance:

- **Structure endorsed.** Additive Option A (recommended) changes no accepted tool,
  budget, or frozen row; tiling/totality (`UNIT_COVERAGE_MISMATCH`), per-unit
  valid+empty-diagnostics (`UNIT_NOT_VALID`), terminality mirroring `bounded_units`,
  first-failing-unit as first refusing layer, exact symbol-anchored insertion points.
  Honest NOT-closed section (make_cursor needs expression-level staging, lexer_step
  needs staged descent). Agree: A first, B prototyped in scratch before pinning.
- **Condition 1 — adversarial re-verification must be an acceptance condition.**
  The draft requires pool-renumbered same-revision carried facts (citing the 14/21
  raw-pooling aliasing failure) but names no hostile gate for the pooled path. My
  K1/K1b set maps directly: duplicates, aliased ids, foreign/omitted stamps must
  refuse per-group, and the admitted param-type forgery (below) must be shown not
  widened by pooling. Require K1+K1b green on the pooled-fact path before the
  amendment becomes pin-able.
- **Condition 2 — disclose the inherited residual in the draft.** K1-A3 (independently
  confirmed): same-target forged PARAMETER type is admitted; K1b (mine): forged
  result/arity are refused. Pooled carried bindings inherit the param case — stamps
  stay consistency-only across group boundaries. §6 non-goals must state this; it is
  currently silent on it.
- **Handoff-staging verifier: DECLINED-adopt.** A1's `a2_repin_verifier.py` + readiness
  note (from the seat-correction incident, fully withdrawn, my lane verified clean:
  reflog shows `5adb893` → reset → my 6 commits, never pushed) overlap ground my
  BOOT-A3-001/002/003 already prove independently on published SHAs. Adopting it
  would add unowned maintenance to my lane; the staging dir can be removed whenever.

## Status

- A1's typed-bound measurement: **independently verified**. Amendment: **endorse Option A
  direction subject to the two conditions**; Matthew accepts/declines.
- No builder implementation SHA moved for Candidate7 (`6dce37d` intact; `decaa91` is
  outbox-only); all prior A3 verdicts stand. A3 on standby for re-gate triggers.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-typbound 9eea380538351c66a2abb3b367b04a7465c1d745
cd D:/Projects/wt-a3-typbound; python tests/probe_typed_bound_pipeline.py  # 5 verdicts as above
```
