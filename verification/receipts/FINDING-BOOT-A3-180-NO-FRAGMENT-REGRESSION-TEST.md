# FINDING BOOT-A3-180 — nothing tests compiler_a.pep through the fragment path; the gap is now stated plainly

**A2 answered directly: their 85/85 emitter suite does not include `compiler_a.pep` as an input, and they never claimed it did. I
verified that from the source independently. The consequence is a real gap: the one program that exercises the fragment path at
scale has no owner-side regression test.**

Seed blob `f8f476198f`. Searched the candidate tree `b039fc5`.

## The search

Six references to `compiler_a` or `pep0` across all of `tests/**/*.py`. **All six are prose inside docstrings or comments:**

| file | line | text |
|---|---|---|
| `test_c23_arith_guard.py` | 3, 10 | "compiler_a's bounds guards are all of the form…" (docstring) |
| `test_c23_checker_budget_walls.py` | 3, 12 | "A4's first real compiler-A source (`…/compiler_a.pep`…" (docstring) |
| `test_c23_checker_budget_walls.py` | 83, 94 | "# compiler_a.pep (1100 nodes) hits." (comments) |

**No executable reference. No test opens the file.** Both tests that mention it build synthetic programs instead:

- `test_c23_arith_guard.py` builds a hand-written `fn main(source: SourceBytes)` using the *shape* of compiler_a's guards
  (`o + 1 <= byte_length(source)`), not compiler_a itself.
- `test_c23_checker_budget_walls.py` builds synthetic programs of ~180 functions to reproduce budget walls, and cites compiler_a's
  node count in prose.

## What A2 does cover, per their message

- `tests/test_c23_statement_fragment.py` — the fragment **entry** contract on synthetic statement ranges (7 tests).
- `tests/test_c23_compiler_a_backend.py` — the capabilities compiler_a *needs* (mutable Str local via `str_concat`, loop-local
  `utf8_slice` let, `List[Str]` prepend) on synthetic programs.
- `tests/test_c23_cross_chunk_*.py` — cross-chunk calls and conditions.

That is the right coverage for an emitter suite: the primitives, not one consumer. **A2's 85/85 is accurate as stated.**

## The gap, stated plainly as A2 asked

**The fragment path at scale is verified only by A1's integration and by A3's gate. Neither is a test in the repository.**

Practical consequence: if `build_fragmented_function` regresses — narrowing, the parameter-binding cast, statement ordering, the
carried-binding check — **nothing in the test suite fails.** The regression would be found only when someone runs a sectional build
by hand, or when my gate runs. My gate lives on `codex/bootstrap-agent3-verification`, not on the integration branch, and it
requires the committed M-1 fixture rather than building compiler_a.pep from the tree.

So there is a window between "A1's driver breaks" and "anyone notices", and it is as wide as the interval between manual runs.

## What would close it

A single test that builds `examples/dogfood/pep0/compiler_a.pep` through `build-c23 --sectional` and asserts rc 0 plus a non-empty
C file. That is essentially the first section of my runbook:

```
python verification/probes/gate_candidate_171.py --root <tree>
```

I am not proposing to author it — it belongs on A1's branch beside the driver it tests, and a test that lives only in my lane will
not run in anyone's CI. But the assertion is one line and it is currently unowned.

## Tooling note

My first script labelled four of the six references "CODE" because it judged by line prefix, not by whether the line sits inside a
triple-quoted string. I read them and confirmed all six are prose. The heuristic was wrong and the count of executable references
is **zero**.

## Limits

- Static search of `tests/**/*.py` only. A test elsewhere (a `.ps1`, a CI job, an `_build` script) could build compiler_a.pep; I did
  not search those, and the campaign branch may differ.
- A2's coverage list is taken from their message, not re-verified by me.

REF GH #16. Suggested by A2's reply; independently confirmed.