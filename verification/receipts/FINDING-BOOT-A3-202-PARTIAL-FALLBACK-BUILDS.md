# FINDING BOOT-A3-202 — a buildable compiler A from A4's current source by deferring the fallback entry point

**A4's `239d10d2` can be made buildable today with three edits that keep 9 of their 13 new functions: drop four functions that cannot
pass the check, remove `main`'s call to one of them, and apply the A3-148 Bool-local rewrite. The result builds, passes M-1 15/15 on
clang and gcc, and is clean under the runbook's build and native checks. It does not improve classification — the improvement lived
in the function that gets deferred.**

Seed blob `f8f476198f`. A4 `239d10d2`. Fixture: `verification/fixtures/a4-partial-fallback.pep` (13,677 B, 31 functions).

## The three edits

1. **Remove four functions** that cannot pass the check: `scan_value` (budget), `match_tail`, `match_varlet_body`,
   `is_unsupported_prog` (the last two depend on `scan_value`).
2. **Remove `main`'s guard block** `if err == 1 || err == 2 || err == 3 { if is_unsupported_prog(source) == 1 { err = 5 } … }`.
   Removing only the inner call leaves an empty `then` branch, which the emitter refuses — the same trap as A3-193, in my own edit.
3. **Apply the A3-148 Bool-local rewrite** to `find_brace`'s three 5-conjunct conditions. This is not in A4's source and never was —
   it was my probe in A3-148/159, and route (b) has depended on it all along without that being stated. With the fallback tier's four
   functions gone, `find_brace` becomes reachable and blocks at fragment 14 without it.

## The runbook

```
product build                 PASS    rc=0 C=42588B
build fails closed            PASS
gcc build                     PASS
M-1 pins (clang)              PASS    15/15
M-1 pins (gcc)                PASS    15/15
positive output               PASS
class (ii) codes [published]  FAIL    7 of 10 wrong
malformed codes               PASS    4/4
native path                   PASS
identity                      FAIL    worktree carries unapplied patches
```

## What it is and is not

**Is:** a compiler A that builds from A4's current source, passes M-1 fully on both toolchains, and needs three mechanical edits rather
than a rewrite or a revert. It keeps nine of A4's thirteen new functions in the tree.

**Is not:** an improvement in behaviour. `class (ii)` is still 7 of 10 wrong, because the classification improvement lived in
`is_unsupported_prog`, which is exactly what gets deferred. This is route (b)'s behaviour with A4's work mostly intact.

So it is a **buildable base**, not a contract improvement. A4 could work on `scan_value` against a tree that builds, rather than
against one that does not.

## Correction to my own route (b) framing

A3-176 presented route (b) as needing "only A1's driver patch". That was incomplete: it also needs **A4's Bool-local rewrite**, which
I had measured as a probe and never separated from A4's own source. Anyone reading A3-176 alone would have been surprised at
`find_brace` fragment 14.

## Limits

- Built in a disposable worktree with A1's driver patch; not a tracked candidate.
- The four dropped functions are A4's; dropping them is a decision for A4, not a patch for me to apply.
- The Bool-local rewrite is my shape; A4 may prefer a different formulation of the same remedy.
- I did not verify that `main` still behaves correctly without the `is_unsupported_prog` guard beyond the M-1 pins and malformed
  cases, which is what those pins cover.

REF GH #16. Depends on `6728365639` (A3-159, the driver recipe) and `6728781975` (A3-170). Corrects the scope stated in `6728916098`
(A3-176).