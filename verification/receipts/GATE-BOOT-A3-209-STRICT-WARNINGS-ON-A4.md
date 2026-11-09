# GATE BOOT-A3-209 — A4's 61,941-byte C is clean under -Werror and its binaries pass M-1 23/23

**A3-208 named one unmeasured item: it had not run the strict-warning build on A4's 61,941-byte artifact. Closed. `-Wall -Wextra
-pedantic -Werror -O2` builds clean on clang and gcc, and both strict binaries score M-1 23/23.**

Seed blob `f8f476198f`. A4 `f6cf9caf` source (blob `e3109cab`, unchanged at their `30b2b58`), driver recipe applied, 61,941 B C.

## The runs

```
clang -std=c23 -Wall -Wextra -pedantic -Werror -O2   exit=0
gcc   -std=c2x -Wall -Wextra -pedantic -Werror -O2   exit=0

clang -Werror binary:  23/23 pass
gcc   -Werror binary:  23/23 pass
```

**No warnings, on either toolchain, at both `-O2` and with the strict flag set.** The 23/23 is against the corrected 21-pin oracle
(A3-208), so it covers every shape `PEP0_SUBSET.md` documents.

## Why this was worth closing

A3-179 ran the same flags on the earlier 33,069-byte artifact. This is a different, larger program — 35 functions rather than 21,
with the whole fallback tier present — and a warning can appear at any size. The strict-warning result does not transfer between
them, which is why I listed it as a limit rather than assuming it.

## What is now measured about this artifact

| property | result |
|---|---|
| builds by the real tooling | `build-c23 --sectional`, 61,941 B C, rc 0 |
| clean under strict warnings | clang and gcc, `-Werror -O2` |
| M-1 contract | **23/23** on both toolchains |
| class (ii), published contract | **10/10 exit 5** |
| malformed, positive, gcc | all pass |
| native path | KERNEL32.dll only, zero interpreter markers |
| source builds end to end | 35 functions, no check failure, no step limit |

## What is still not measured

- **No committed candidate.** `identity` fails because the driver patch sits unapplied in a disposable worktree. That is the one
  runbook section outstanding and it is A1's integration, escalated to NEEDS_HUMAN.
- Optimiser levels above `-O2` untested; `-O0` untested.
- A4's own 13k-input differential model is their evidence, not mine.

## Limits

- One source revision; A4's `30b2b58` carries the same `compiler_a.pep` blob so no re-run was needed.
- Strict flags as above only; I did not add `-Wconversion` or sanitisers.

REF GH #16. Closes the limit stated in `6730418090` (A3-208).