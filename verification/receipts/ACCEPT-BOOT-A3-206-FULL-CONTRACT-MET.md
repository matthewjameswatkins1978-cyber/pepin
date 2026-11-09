# ACCEPT BOOT-A3-206 — A4's fallback tier meets the full published contract and the source builds end to end

**A4's `e4cca7a` lineage (remote tip `1a2f1464`) builds completely through the real driver and scores **class (ii) 10/10** — the
first time the published `PEP0_SUBSET.md` promise has been met. The single M-1 failure is a stale oracle pin, not a defect.**

Seed blob `f8f476198f`. Source: 35 functions, 26,491 B. Driver: `verification/fixtures/a3-m1-driver-recipe.diff` applied.

## The build

```
$ python pep_c23.py build-c23 …/compiler_a.pep --sectional --output X --emit-c X.c
exit=0, C 61,941 B, executable produced
no check failure, no STEP_LIMIT, no emit refusal
```

Loop-free `scan_value` (`cd6f2dc`), Bool-local `find_brace` (`e4cca7a`), and every fallback function clear the driver together. The
budget question that A3-195/196/197/198/199 bounded was solved by removing the loop, not by reducing its work — the option I had
recorded as "unmeasured design work".

## The runbook, published contract

```
product build     PASS   61,941 B
build fails closed PASS
gcc build         PASS
positive output   PASS
class (ii)        PASS   10/10 exit 5
malformed         PASS   4/4
native path       PASS
M-1 clang         FAIL   14/15
M-1 gcc           FAIL   14/15
identity          FAIL   worktree patches unapplied
```

## The single failure, and why it is the pin

```
FAIL a_foo.pep   exit=5 (want 1)   stdout='ERR unsupported' (want 'ERR shape')
```

`a_foo.pep` is `fn foo()->Int{return 1}` — a non-`main` function. `PEP0_SUBSET.md` class (ii) lists *"Non-`main` functions, including
`fn Main(...)` (seed-valid name)"* and assigns them **exit 5**. A4's fallback tier now does exactly that.

**The oracle pin still carries the old expectation of exit 1.** The pin and the spec have disagreed since A3-153 recorded the pin's
value; A4's work resolved the contradiction in favour of the document, which is the correct direction. Updating `a_foo`'s expected
exit from 1 to 5 makes the gate 15/15.

## What this changes about the contract

**No narrowing is needed.** A3-176 and A3-202 measured routes that left class (ii) at 7 of 10 wrong and concluded the contract would
have to be narrowed. That is now superseded: the published promise is met in full.

The `PEPIN_CONTRACT=narrow` option added in A3-204 remains available but is no longer the likely path; the published gate is the one
that should be green.

## What still stands between this and a green runbook

1. **A4 updates `a_foo`'s pin** from 1 to 5 — one line in their oracle.
2. **A1 lands the driver recipe** and produces a clean tracked candidate — the `identity` section requires a committed tree, not a
   patched worktree.

Neither is mine.

## My own error this turn

I had attributed A4's session to A1 and was preparing to report the mission stalled on an exhausted A1 seat. A4 corrected it by
messaging. **The session list names no agents**; I had inferred roles from branch activity and got it wrong. The lesson is the same
one that caught me at A3-181: check the live instrument rather than reasoning from a proxy.

## Limits

- Built in a disposable worktree at candidate `b039fc5` plus A1's driver patch; `identity` fails because those patches are unapplied,
  which is the honest state.
- One M-1 run per toolchain; I did not vary the dependency set or run the strict-warning build on this source.
- A4's own differential model (13k inputs, 0 divergences per their report) is their evidence, not mine.

REF GH #16. Supersedes the narrowing conclusion of `6728916098` (A3-176) and `6729843542` (A3-202).