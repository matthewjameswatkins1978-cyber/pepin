# A3 verification status — index and handoff

**Purpose.** This lane has produced **316 receipts and 96 probes**. This file is the entry point: what is verified *now*, by what
method, at which pin, and what is not. Historical receipts remain authoritative for their own pins; this index tells a successor
where to look and what not to re-derive.

**CURRENT STATE: the gate suite is RED, deliberately.** Two of nine gates fail and both failures are real. Do not read a prior
"all green" claim from any receipt — the suite gained the two gates that can see the defects the earlier suite could not.

## Run everything

```
PEPIN_SEED_ROOT=<seed worktree> PEPIN_A1_ROOT=<A1 worktree> PEPIN_A2_ROOT=<A2 worktree> \
  PEPIN_CA_ROOT=<tree whose pep_sectional.py to test> \
  python verification/run_gates.py
```

```
A4 oracle replay (13 pins)      PASS
A4 normative boundary (17)      PASS
A1 semantic oracle (23)         PASS
A1 sectional merge (11 probes)  PASS
A2 DIVERGENCE-2 (16)            PASS
M-1 gate calibration            PASS
Seed vs emitted differential    PASS
Compiler A contract (14 cases)  FAIL    7/14 match PEP0_SUBSET.md
A13 assignment-target defect    FAIL    pep_checker_a13.pep L1933

9 gate(s) ran, 2 failed, 0 skipped — A3 GATES: 2 FAILING
```

It reports `PARTIAL` (never "green") when anything is skipped. Exit 3 from a probe means "cannot run in this tree" and is treated
as a skip, never a pass.

## Live pins

| lane | SHA | note |
|---|---|---|
| A1 `codex/a1-typed-bound-pipeline` | `333c5805` | sectional driver; bindings carry landed |
| A2 `codex/a2-divergence-spike` | `e07e278f` | emitter `32bc253d`; **this is the shipped emitter** |
| A4 `spec/agent4-spec-lab` | `d37bf566` | `compiler_a.pep` blob `7ed71672`, 34 functions, **unbuildable** (A3-163) |
| A3 `codex/bootstrap-agent3-verification` | this lane | |
| candidate `scratch/a1-s3-candidate` | `b039fc5` | A1+A2 merge; the tree most measurements use |

**Two seed blobs are in play and their builtin sets differ by exactly one name.** `f8f476198f` (146,713 B) knows `str_concat`;
`c92f9cc4a3` (143,092 B) does not. **Every claim names its seed.**

## What is verified

### Compiler A and M-1

| claim | method | evidence |
|---|---|---|
| **M-1 passes through the real product path** | `build-c23 --sectional`, 33,069 B C, **15/15 on clang AND gcc**, no hand assembly | A3-159 |
| The same C is clean under strict warnings | `-Wall -Wextra -pedantic -Werror -O2` on both compilers; strict binary still 15/15 | A3-179 |
| No hidden semantic compiler | binary imports **KERNEL32.dll only**; zero python/ocaml/opam markers; fails closed without argv | A3-161 |
| The four fixes that make M-1 possible are each necessary | narrowing → parameter-binding cast → epilogue → Bool-local rewrite | A3-159, A3-170 |
| Driver recipe travels without A4's source | `verification/fixtures/a3-m1-driver-recipe.diff`, `git apply --check` clean on A1's branch too | A3-170 |
| The approval runbook can fail | a 3-line stub compiler scores M-1 **1/15**; 6 of 10 sections catch it | A3-172 |

### The contract defect

| claim | method | evidence |
|---|---|---|
| Compiler A misclassifies 7 of 9 class-(ii) shapes | exit 1/2/3 where `PEP0_SUBSET.md` requires 5, on the product-path binary | A3-153, A3-160 |
| The seven reduce to three source sites | `find_fn` L200, `find_ds` L347/L368, `check_tail` L407 | A3-155 |
| Exit 5 is reachable from exactly one place | `find_brace` L288-296, three type-word tests | A3-155 |
| M-1's oracle cannot see this | one example per class; `Str`/`Bool`/`Unit` share one code path | A3-162 |

### The A13 checker defect

| claim | method | evidence |
|---|---|---|
| **Root cause: a `var` initialised from a bare mutable local gets no type** | substitution: `var e = i` fails; `var e = 0`, `var e = o`, `var e: Int = i` all pass | A3-183 |
| The diagnostic is the messenger | fires when `binding.typeName` and `typeShape` are both empty | A3-183 |
| An annotation clears it on A4's real source | A13 gone from `scan_name`; build advances to the step limit | A3-183 |
| It is narrow, not general | **0 of 63** `.pep` files in the repo trigger it | A3-181 |
| It is A1's, at their tip | reproduces on `333c5805` with that branch's own driver | A3-173 |
| A 31-line reproducer exists, with a one-line control | `verification/fixtures/a13-assign-target-reduced.pep` | A3-166/167 |

### The fallback tier (A4's blocked work)

| claim | method | evidence |
|---|---|---|
| 4 of 8 functions build once annotated | `scan_name`, `scan_string`, `match_return_ws`, small matchers | A3-184 |
| `names_equal` is refused for two fallible operands, blocking `match_tail` | emitter refusal on a 27-line function | A3-184 |
| **`scan_value` is over budget before its loop starts** | STEP with the 63-line `while` deleted; control `scan_name` at 64 lines builds | A3-186 |
| No single construct carries that cost | four single-construct removals all still STEP | A3-187 |

## What is NOT verified — the honest gaps

1. **No tracked compiler A exists.** The M-1 result is a disposable worktree carrying four unlanded patches. A tracked-tree M-1
   needs A1 to commit the driver recipe and A4 to make the contract decision.
2. **A4's source cannot be built by either path.** One-shot exceeds the 1 MiB JSONL limit at 24,745 B; sectional rejects it at the
   checker (A3-163). The annotation workaround (A3-183) moves it to the step limit but does not build it.
3. **The fragment path at scale has no owner-side regression test.** Six references to `compiler_a.pep` in `tests/`, all prose in
   docstrings; no executable reference (A3-180). If A1's driver regresses, nothing in the suite fails.
4. **Only 10 of 63** repository `.pep` files build through the sectional path at all — 24 are refused for top-level declarations, a
   documented scope limit (A3-181). "Builds through the tooling" describes a minority of the repository.
5. **`scan_value`'s cost is distributed.** Why a 46-line prologue exceeds a budget a 64-line function passes is **open** — the
   node-count instrument I tried did not work (A3-187).
6. **19 of 21 functions have only a source-derived oracle.** The seed cannot execute them because `source_bytes()` is host-gated in
   run mode. The input-access wall bounds verification exhaustiveness, not just compiler capability.
7. **Exit codes carry no information on the unpatched tree.** Every program exits 0 regardless of what it computes (A3-182).

## Standing cautions for the next verifier

- **A green suite that cannot see the blocking defects is worse than a red one.** Two gates are red on purpose.
- **Mixed lanes are not an integration.** Most measurements drive A1's host against A2's emitter; both unmodified, neither merged.
- **The candidate is a patchwork:** sectional driver and parser from A1's tip, emitter from A2's tip, checker from **neither**
  (A3-177). The checker divergence is behaviourally inert on the sectional path (A3-175) but is unreconciled.
- **A1's published figures were measured on emitter `efedda39`, not the shipped `32bc253d`.** Do not carry them across in either
  direction (A3-178).
- **Optimisations keep narrowing correctness silently.** When an optimisation skips work because of a name or shape, test that the
  language cannot produce that name or shape.
- **This lane's own conclusions were sometimes wrong.** Retracted or corrected: A3-131, A3-137, A3-147, A3-157, A3-169, A3-174,
  A3-175's first attempt, A3-176's framing. Read the correction, not the original.
- **Instrument defects are the main risk.** Eight found in this mission alone, on top of eight from earlier missions, and all of
  them in this lane's harness rather than the code under audit. The most instructive three: an aliased executable path that made ten
  different programs report identical output (A3-182); a `check-ok` label read as "passed" when it actually meant "not an A13
  failure" (A3-174); and a synthetic budget curve that contradicted a result I had already measured (A3-185). **Prefer the real
  object over a stand-in, and distrust any table whose rows look too uniform for its inputs.**

## Instrument quick reference

| need | probe |
|---|---|
| whole lane | `run_gates.py` |
| **independent approval of a candidate** | `gate_candidate_171.py --root <tree> [--expect-sha S] [--contract published\|narrow]` |
| M-1 acceptance | `verify_m1_081.py --compiler-cmd '["<exe>"]'`, `--selftest` |
| compiler A's input contract | `contract_c7_162.py` (`PEPIN_CA_EXE` for a tracked build) |
| A13 assignment-target regression | `a13_assign_gate_168.py` (`PEPIN_CA_ROOT`) |
| emit/execute an app, per-function status | `emit_any_049.py` — **prints the product-path verdict first**; its per-function status uses the legacy checker tool and is diagnostic only |
| seed vs emitted expression semantics | `seed_differential_106.py` |
| step cost per function / per fragment | `step_cost_099.py` |
| A1 sectional merge fail-closed | `sectional_negatives_080.py` |
| A4 oracle, boundary, A1 oracle replay | `pep0_oracle_079.py`, `pep0_boundary_088.py`, `pep0_a1_oracle_093.py` |
| DIVERGENCE-2 input-dependent C | `divergence_2_042.py` |

## Next action for whoever picks this up

Run `gate_candidate_171.py` against any new candidate. It needs `identity` to pass, which means **a committed candidate, not a
patched worktree**. Two routes to that are measured (A3-176): the narrowed contract needs only A1's existing driver patch; the
published contract additionally needs the A13 checker fix.

If `PEPIN_CA_ROOT` points at a tree without the `bound-chunk` sectional path, the A13 gate skips rather than passing — that is
deliberate, and binding it to a stale pin produced a false green once (A3-168).
