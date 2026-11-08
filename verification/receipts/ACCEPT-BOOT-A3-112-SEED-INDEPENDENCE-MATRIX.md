# ACCEPT BOOT-A3-112 — the lane is seed-independent except for `str_concat`: 7/7 gates green on both seeds

**Verdict: the whole verification lane passes on the campaign-base seed as well as the newer one. Only the two
`str_concat`-dependent differential cases are seed-sensitive, and the probe reports them as `N/A` rather than as failures. So
the A3-110 divergence is real but narrow: it does not contaminate any other gate.**

Seed blobs: `c92f9cc4a3` (143,092, campaign base / A1 ledger / A4) and `f8f476198f` (146,713, A1 pipeline / A2).

## Matrix

| gate | old seed `c92f9cc4a3` | new seed `f8f476198f` |
|---|---|---|
| A4 oracle replay (13 pins) | PASS | PASS |
| A4 normative boundary (17) | PASS | PASS |
| A1 semantic oracle (23) | PASS | PASS |
| A1 sectional merge (11 probes) | PASS | PASS |
| A2 DIVERGENCE-2 (16) | PASS | PASS |
| M-1 gate calibration | PASS | PASS |
| Seed vs emitted differential | **PASS** — `AGREE on 7/9 (rest need a newer seed)` | **PASS** — `AGREE on all` |
| | **7 ran, 0 failed, 0 skipped** | **7 ran, 0 failed, 0 skipped** |

This is the reassurance that the seed divergence needed. `str_concat` was the one builtin that differed in A3-110, and it
turns out not to be load-bearing for any other gate: the A4 oracle, the A4 boundary, A1's 23-shape oracle, A1's merge
fail-closed probes, DIVERGENCE-2 and the M-1 calibration all behave identically on both seeds.

It also means the differential's own design goal is met: a seed difference shows up as *applicability*, never as a false
disagreement about the emitter.

## Also fixed

The gate label in `run_gates.py` still said "Seed vs emitted differential (4)" from when the probe had four cases. It now
reads without a hard-coded count, so it cannot drift again as cases are added. Cosmetic, but a stale count in a summary table
is the kind of small wrongness that erodes trust in the table.

## What this does and does not settle

- **Settles:** no other gate is quietly relying on the newer seed. A1-S3 can merge A1-pipeline + A2 knowing the seed change
  is confined to `str_concat` availability, not to a broad behavioural shift.
- **Does not settle:** which seed the candidate *should* carry, and whether `str_concat` belongs in the accepted language.
  That is A1's integration call with Lucy, restated from A3-110 and still open. This receipt only bounds the blast radius.
- **Does not settle:** whether the two seeds agree on programs that *use* `str_concat` in a way the emitter lowers
  differently — only the newer seed can evaluate those at all, so there is nothing to compare against on the older one.

## Limits

- Six of the seven gates use `PEPIN_SEED_ROOT` centrally; DIVERGENCE-2 runs against the `gate` root's own `pep.ps1`, so it
  uses whatever seed that worktree carries (`f8f476198f`) in both columns. Its row therefore demonstrates emitter-side
  stability, not seed-independence.
- Gate results are pass/fail; the matrix says nothing about *how close* any gate came to failing on either seed.
- Roots are worktrees, so the matrix is only as current as those checkouts.

## Reproduce

```
# old seed
PEPIN_SEED_ROOT=D:/Projects/pepin     PEPIN_A1_ROOT=<a1> PEPIN_A2_ROOT=<a2> python verification/run_gates.py
# new seed
PEPIN_SEED_ROOT=D:/Projects/wt-a3-dbea PEPIN_A1_ROOT=<a1> PEPIN_A2_ROOT=<a2> python verification/run_gates.py
```

REF GH #16. Parent `6725074837` (A3-110, where the divergence was found). Suite A3; gates credited to A1/A2/A4 in the table.