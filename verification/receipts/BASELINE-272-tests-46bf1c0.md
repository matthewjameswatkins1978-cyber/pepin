# Full fifteen-module baseline refresh — A1 `46bf1c0` clean (2026-10-30)

Supersedes the `eb8f7c0` baseline (262 tests) from
`PINNED-ROUND-20261030-eb8f7c0-784050c.md`. Clean detached worktree,
two sequential batches (the parallel-batch gotcha observed in
`FINDING-a2-emit-step-budget-regression-8e076e2.md` applies to all
multi-module runs).

| batch | modules | tests | result |
|---|---|---|---|
| heavy | a13 (87), a13_nested (13), a14 (11), c23_cli (8), real_lexer classifiers (1) | **120** | 2 FAIL — known a14 pair (recursion contract, length exemplar) |
| rest | a6/a7/a8/a10/a11/a12 (62), driver_validation (10), cli (47), textbuf_native (22), moonbit_cli (11) | **152** | 1 FAIL — known arena CRLF (`42\r\n` vs `42\n`, #22 owner item) |

**272 tests, 3 failures — all three previously identified and owned.**
Zero new failures.

## Reconciliation with prior baselines

| baseline | tests | failures | delta explanation |
|---|---|---|---|
| `eb8f7c0` (round 9) | 262 | 3 (same set) | — |
| **`46bf1c0` (this)** | **272** | **3 (same set)** | a13 79→87 (+8, checker chunking/adapter rounds), c23_cli 6→8 (+2) |

Every suite ran green beyond the three known items across both
batches: classifier 1/1, cli 8/8, driver_validation 10/10, moonbit
11/11, a6-a12 all green — including every module NOT re-run at current
pins in this lane since round 9 (the acceptance's "pinned differential
at latest commits" is now complete for all 15 modules, not just the
subsets tracked in rounds 15/19/20).

## Context

- A1-own emitter is still the original `9573c227` — this baseline does
  NOT exercise Wall A (classifier closure cost appears only in the
  combined state with A2's emitter; see `WALLS-AB-distinct-death-regions.md`).
- Wall B (a14 countdown collapse) likewise only manifests with A2's
  emitter — A1-own a14 = 2 known, consistent with round 15.

Replay: corpus/`replay.py`/base untouched — **163/163** current.
