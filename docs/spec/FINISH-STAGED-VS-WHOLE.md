# FINISH — staged-vs-whole-checker acceptance decision (one page)

## Decision

**Accept staged checking as the evidence path. Keep the one-shot
whole-program 100k-step gate red until a designed change moves it.
Never infer whole-program validity from staged validity without the
coverage rule.**

## Grounds (all measured by others this campaign, not inferred here)

- A1 K2: identical 66 nodes FAIL whole / PASS as 2×33 and 6×11; guard
  ladder 59n-valid/83n-refused with expiry migrating inside the scan
  family. Parser passes all sizes; transport is wall-ms only.
- A1 K3 STOP: cost is distributed across the whole scan family (two
  shapes, same signature); Pep has no indexed access, so a List-cache
  moves budget without asymptotic gain; S2 fusions already took what
  was takeable (3 landed, 2 reverted diagnostic-unsafe). No
  function-level rewrite moves whole-66 or ladder-83 (open falsifier
  stands: do it with 72 A13 + chunk gates green).
- Second A1 seat: `steps ~= 13.1n^2 + 962n`; removing either term
  alone lifts the ceiling only to ~87–104n — two independent
  derivations of the same NO-GO. Real T5 closure valid at 86n/65,181
  steps: shape beats count, so node-count gates are the wrong
  instrument; per-shape budgets are the honest one.
- A3 K5: on union/match shapes the FIRST wall is a capability gap,
  budget second; bytes are not cost. Whole-program red conflates
  "too expensive" with "never started" (A3 K-A3-7: 4 of 8 rungs die
  host-side pre-emission with no steps to report).

## What counts as acceptance evidence henceforth

1. Staged-valid + seed-oracle parity on the same bytes (the P1 pattern:
   `check` valid AND `run` oracle confirmed).
2. Coverage accounted per the contract (ChunkLedger.complete semantics:
   a chunk report is never whole-program coverage).
3. Targeted gates green at the merged tree (the 65-test pattern), with
   the bundle digest + seed pin marker verified — never exit code
   alone (A1 stale-pin hazard: unpatched probe exits 0 on the wrong
   checker).
4. Full-v2 15/15 on a published Candidate stays the release-grade
   bar; 14/15-with-66n-red is an honest experimental record, not a
   failure to explain away.

## Explicitly deferred (not decided here)

Host-side id→position index / pass-fusion (A1 K3/K8 direction),
content-bound callee facts (my K1 Option S vs trusted-host policy —
A1's K4 chose policy + transcription pin; A3's adapted probe remains
the acceptance authority for the residual), and any cap/budget change.
Revisit the whole-program gate only on: a host-index design landing,
or staged checking making one-shot irrelevant in practice.
