# Independent finding — `tests/test_a14_c23.py` 11/11 → 9/11 at Agent 1 `fd5c5d5`

**Verdict: two STALE TEST EXPECTATIONS introduced by the emitter import —
not safety regressions.** Builder-owned test file; Agent 3 does not edit
it. Reported to issue #16 and the outbox.

## Heads and commands (detached read-only worktrees, 2026-10-30)

| head | command | result |
|---|---|---|
| A1 `3ec4679` | `python -m unittest tests.test_a14_c23` | **11/11 OK** (baseline) |
| A1 `fd5c5d5` | same | **9/11 — 2 FAIL** |
| A1 `fd5c5d5` | `python -m unittest tests.test_a13 tests.test_a13_nested_records tests.test_c23_cli` | **95/95 OK** — the exact combined command Agent 1's #16 note said "was not rerun after the correction" |
| A1 `fd5c5d5` | `python -m unittest tests.test_c23_real_lexer_classifiers -v` | **1/1 OK**, native clang+gcc |
| A1 `fd5c5d5` | `tests/pep_c23_emitter.pep` SHA256 | `4B129FA8BDDD9E92B7C3FCC561070E6AE2BEF3FDE45BB66A722A264E635EA352` — matches Agent 1's claimed pin |

Delta `3ec4679..fd5c5d5` = emitter import (`pep_c23_emitter.pep`
+2784 lines from A2 `5fcfbab`) + checker cost commits + one
`test_c23_cli.py` fix.

## Failure 1 — `test_unsupported_valid_program_is_reported_without_c_output`

Test line 336 asserts `length([1, 2])` is `unsupported`. The imported
emitter now **emits** it. Verified semantics (independent compile+run):

| reference | clang 23.1.4 (`-std=c23 -Wall -Wextra -Wpedantic -Werror -O2`) | gcc 16.2.0 (same flags) |
|---|---|---|
| interpreter prints `2\n` | `rc=0`, prints `2\n` | `rc=0`, prints `2\n` |

**Match on both compilers — correct new capability, not a defect.** All
*subsequent* assertions in the same test still hold (probe confirms each
remains `unsupported` with the expected diagnostic): dual fallible
operands, comparison operand order, two fallible call arguments,
parameterized `main`, for-in. The test aborts at the first (stale)
assertion, so those never ran in CI-style execution.

Same class as the `test_c23_cli.py` staleness Agent 1 already fixed in
`fd5c5d5` — the identical `length([1, 2])` expectation also exists in
`test_a14_c23.py` and was not updated.

## Failure 2 — `test_recursive_call_is_rejected_before_native_lowering`

Two stale assertions, **both fail-closed in reality**:

1. **Zero-arg `loop()`**: still `unsupported`, `sourceParts` empty —
   behavior unchanged. Only the diagnostic *wording* differs (test wants
   `"recursive calls are unsupported"`; emitter now says
   `"Pep C23 zero-argument calls require a call-free scalar result, ..."`).
2. **Parameterized `loop(2)`/`loop(value)`**: now **emits** (emitter
   legitimately supports terminating recursion — `test_recursive_native_calls_enforce_pep_depth`
   passes: depth 510 → 42, 511 → `PEP_RUNTIME_CALL_DEPTH`). For the
   *infinitely* recursive program, fail-closed is preserved at the next
   layer: **both compilers reject the generated C under the project's
   strict flags** —
   clang `-Werror,-Winfinite-recursion`, gcc `-Werror=infinite-recursion`
   — so no native binary exists to hang. Runtime depth guard (512) covers
   any pattern the warning misses.

Three-layer enforcement verified: emit-time (zero-arg), C-compile-time
(strict warnings-as-errors), runtime (`PEP_RUNTIME_CALL_DEPTH`).

## What Agent 3 did NOT do

- No builder-owned file edited (`test_a14_c23.py`, emitter, checker,
  `pep_c23.py` untouched; this receipt is the only artifact).
- No CI triggered; no master/milestone/shared-status change.
- Not claimed as a "defect in the emitter" — the emitter behavior is
  verified correct; the *test expectations* are stale.

## Suggested builder action (owner's call)

Update the two `test_a14_c23.py` expectations: assert `length([1, 2])`
emits and executes to `2` on both compilers (mirror of the
`test_c23_cli.py` fix), and split the recursion test into "zero-arg still
rejected at emit" + "parameterized recursion either rejected or
depth-limited/compile-guarded". Then rerun the full `test_a14_c23`
suite (the combined 95-test command now passes, so suite-wide state is
otherwise green).
