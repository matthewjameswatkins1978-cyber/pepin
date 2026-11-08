# ACCEPT BOOT-A3-098 — one command now re-runs the whole A3 verification lane, and it refuses to call a partial run green

**Verdict: `verification/run_gates.py` re-runs six independent gates in one invocation. With the three peer roots set it
reports `6 gate(s) ran, 0 failed, 0 skipped — ALL GREEN - every gate ran`. With roots missing it reports **PARTIAL**, not
green, because a lane nobody can re-run is a lane that rots and a "green" that skipped most of its checks is worse than no
green at all.**

## What it runs

| gate | verified against | authored by |
|---|---|---|
| A4 oracle replay (13 pins) | live seed | A4's `EXPECTED.md` |
| A4 normative boundary (17) | live seed | A4's `PEP0_SUBSET.md` |
| A1 semantic oracle (23) | live seed, exact spans | A1's `test_a1_pep0_oracle.py` |
| A1 sectional merge (11 probes) | live `merge_reports`/`check_program` | A1's `pep_sectional.py` |
| A2 DIVERGENCE-2 (16) | clang + gcc, real runs | A2's emitter |
| M-1 gate calibration | deliberate stubs | A3's own gate |

Every one is a verifier's check of someone else's claim, or of a gate proven able to fail. None is an author's own test
being re-run for them.

## Result

```
gate                            result  detail
A4 oracle replay (13 pins)      PASS    ORACLE REPLAY: PASS
A4 normative boundary (17)      PASS    A4 BOUNDARY EVIDENCE: REPRODUCES
A1 semantic oracle (23)         PASS    A1 SEMANTIC ORACLE: REPRODUCES
A1 sectional merge (11 probes)  PASS    11 probes, 0 disagreeing with the fail-closed expectation
A2 DIVERGENCE-2 (16)            PASS    16 checks, 16 passed
M-1 gate calibration            PASS    SELF-TEST: PASS - the gate detects both wrong exit codes and wrong stdout

6 gate(s) ran, 0 failed, 0 skipped
A3 GATES: ALL GREEN - every gate ran
```

## Two details that matter more than the table

**Skipped is not passing.** With no roots set the runner reports
`A3 GATES: PARTIAL - 1 ran, 6 skipped (not a full pass)` and names the exact variable each skipped gate needs
(`PEPIN_SEED_ROOT / --seed`, `PEPIN_A1_ROOT / --a1`, `PEPIN_A2_ROOT / --a2`). My first version printed "ALL GREEN" while
six gates had not run; I caught it on the second test and changed the verdict, because that is precisely the false comfort
this lane exists to prevent.

**Summary line, not last line.** The first version reported DIVERGENCE-2's result as `);return 0;}` — a fragment of the
generated C that probe prints after its verdict. The detail now searches for a summary marker, so it reports
`16 checks, 16 passed`.

## What is deliberately not in the suite

The A2 `prepend+reverse` differential (BOOT-A3-078) compares emitted C **across two different pins**, so it needs two A2
worktrees and its own diff. It cannot report pass/fail from one invocation, so listing it would have left a permanent SKIP
and made a full pass unreachable. It is documented in the module docstring with the exact commands instead, along with the
`PEPIN_UNITS_ONLY=1` recipe for the 21-function table. A runner that can never reach "all green" trains people to ignore its
verdict.

## Usage

```
python verification/run_gates.py --seed <worktree with built seed> --a1 <worktree at A1 tip> --a2 <worktree at A2 tip>
python verification/run_gates.py --skip-merge --skip-divergence     # trimmed
```

Exit 0 only when every gate that ran passed. Roots may also come from `PEPIN_SEED_ROOT`, `PEPIN_A1_ROOT`,
`PEPIN_A2_ROOT`.

## Limits

- The suite proves each **claim** still holds; it cannot see a claim nobody made. A1's oracle is green but compiler A has
  never been judged against it, because A does not run.
- The runner inherits each probe's limits: first-diagnostic-only comparison for A1's oracle, unit-level fact construction
  for the merge probes, and no compiler-A execution anywhere.
- Roots are worktrees, so the suite is only as current as the checkouts you point it at. It prints each probe's own
  revision banner so a stale root is visible.

REF GH #16. Suite assembled by A3; the gates themselves are credited to A4, A1 and A2 in the table above.