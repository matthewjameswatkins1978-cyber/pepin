# ACCEPT BOOT-A3-083 — independent 21-function table: 10/21 check whole, 11 hit the step limit, and A2's arithmetic widening moves none of them

**Verdict: measured independently on A4's canonical `compiler_a.pep`, 10 of 21 functions check as a whole function and 11 hit
`PEP_RUNTIME_STEP_LIMIT`. The boundary is sharp — every function ≤41 nodes passes, every function ≥48 nodes fails. The
result is byte-for-byte identical at `1885566` and `bea071a`, so `b758c91`'s arithmetic `may_fail` widening produces exactly
zero movement for compiler A.**

## Method, stated precisely so nobody reads this as a different stage

`verification/probes/emit_any_049.py` drives `pep-c23-checker-chunk` / `analyze_chunk_typed` with **one whole-function
chunk** and every other signature as external fact. That is the pre-bound whole-chunk stage. A1's driver uses
`analyze_chunk_typed_bound` plus statement-group chains (`fact_closure`, `BindingPool`), which is a *different* stage — so my
10/21 and A1's 21/21 CHECK green are not in conflict: A1's number comes from the chain path, and mine says exactly which 11
functions need it.

## The table (source `5f62e4b:examples/dogfood/pep0/compiler_a.pep`, blob `ca732536`, 9,639 B, 21 fns)

| function | nodes | whole-chunk CHECK |
|---|---|---|
| `is_digit` | 18 | **valid** |
| `is_ws` | 26 | **valid** |
| `is_ws_at` | 26 | **valid** |
| `expect_byte` | 27 | **valid** |
| `is_fn2` | 33 | **valid** |
| `parse_value` | 34 | **valid** |
| `is_int3` | 41 | **valid** |
| `is_ret3` | 41 | **valid** |
| `is_str3` | 41 | **valid** |
| `is_urn3` | 41 | **valid** |
| `skip_ws` | 48 | `PEP_RUNTIME_STEP_LIMIT` |
| `scan_digits` | 48 | `PEP_RUNTIME_STEP_LIMIT` |
| `is_main4` | 49 | `PEP_RUNTIME_STEP_LIMIT` |
| `is_bool4` | 49 | `PEP_RUNTIME_STEP_LIMIT` |
| `is_unit4` | 49 | `PEP_RUNTIME_STEP_LIMIT` |
| `check_tail` | 66 | `PEP_RUNTIME_STEP_LIMIT` |
| `find_parens` | 82 | `PEP_RUNTIME_STEP_LIMIT` |
| `find_fn` | 101 | `PEP_RUNTIME_STEP_LIMIT` |
| `find_ds` | 122 | `PEP_RUNTIME_STEP_LIMIT` |
| `find_brace` | 288 | `PEP_RUNTIME_STEP_LIMIT` |
| `main` | 222 | `PEP_RUNTIME_STEP_LIMIT` |

**10 valid / 11 step-limited, with no exception and no borderline case.** The threshold sits between 41 and 48 nodes for
this checker on this build — a sharper figure than the ~32–34 node emission boundary I measured earlier, because this is the
check stage rather than the emit stage. The two numbers must not be conflated: 41 nodes checks fine and can still fail to
emit.

## The finding that matters for A2

Both pins were run with the same app, same seed, same node counts:

| pin | valid | step-limited |
|---|---|---|
| `1885566` | 10 | 11 |
| `bea071a` | 10 | 11 |

**Identical, function for function.** So `b758c91` (`may_fail = OR(operands)`, literal `/ 0` stays fallible) and the two
`prepend+reverse` perf commits moved **nothing** on compiler A. That is worth saying plainly because A2's arithmetic work is
easy to mistake for progress on the 21-function build: it is not. The binding constraint on compiler A is the
**100,000-step budget**, not operand fallibility. Statement-granular emission (A2-S2 / A1-S2) is therefore confirmed as the
critical path by independent measurement, not by assumption.

It also means A3-078's finding stands on its own merits rather than being a proxy for progress: narrowing `/` fallibility
correctly costs nothing here, because no compiler-A function reaches the emitter today for a fallibility reason.

## Limits — honest

- **No step counts.** The refusal returns the code, not the consumed steps, so I cannot say how far over 100,000 each of the
  11 ran. A1's driver measures steps; I do not, and I will not guess.
- **Check only, not emission.** Nothing here reports how many of the 10 would *emit*. `main` is among the 11, and a C build
  needs `main`, so M-1 remains unreachable whatever the other 20 do.
- **One revision of one file.** `5f62e4b` and `d78735e` carry the same `compiler_a.pep` blob (`ca732536`), so the source
  identity is currently unambiguous; a future A4 revision must be re-pinned.
- My instrument never emitted C here, so no claim is made about A2's emission quality from this run — that is A3-078's
  separate, byte-identical result.

## Reproduce

```
PEPIN_GATE_ROOT=<worktree> PEPIN_APP_REL=examples/dogfood/pep0/compiler_a.pep PEPIN_APP_REV=5f62e4b \
  python verification/probes/emit_any_049.py
```

Runs in ~3 s per pin. Instrument change this turn: refusals now also print the node count, so the shape needing the chain
path is visible without a second pass.

REF GH #16. Input SHAs `1885566`, `bea071a`; source `5f62e4b:examples/dogfood/pep0/compiler_a.pep`. Source authored by A4,
emitter by A2, independent measurement by A3.