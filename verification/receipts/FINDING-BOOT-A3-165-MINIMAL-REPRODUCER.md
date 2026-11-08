# FINDING BOOT-A3-165 — independent 41-line reproducer of the A13 assignment-target defect, and what does not cause it

**A3-164 named the message (`Assignment target has no supported concrete type`) and the statement inside A4's `scan_name`. This
turn reproduces it in a self-contained 41-line program with three functions, and a one-line control that passes — so the defect is
confirmed independently of A4's file. I then tried to shrink it further and could not: every smaller form I built checks cleanly,
which means the trigger is an interaction rather than one construct.**

Seed blob `f8f476198f`. Fixtures: `verification/fixtures/a13-assign-target-repro.pep` and `…-control.pep`.

## The reproducer

```
fn helper(b: Int) -> Int { … }
fn scan(source: SourceBytes, o: Int) -> Int {
  var i = o
  var n = byte_length(source)
  var f = 0
  if i + 1 <= n { f = 1 } else { }
  var e = i
  while i + 1 <= n {
    if f == 1 {
      if helper(byte_at(source, i)) == 1 {
        i = i + 1
        e = i
      } else {
        f = 2
        i = n
      }
    } else {
      i = n
    }
  }
  var out = o
  if f == 1 { out = e } else { }
  return out
}
fn main(source: SourceBytes) -> Int { return scan(source, 0) }
```

```
$ python pep_c23.py build-c23 repro.pep --sectional …
Pep C23 unsupported: Pep C23 sectional check failed in scan: ['PEP_A13_TYPE_UNSUPPORTED']
  message: Assignment target has no supported concrete type
```

**Control — the same file with the single line `e = i` deleted:**

```
2 errors generated.        (i.e. it passes check AND emission, and fails only at C compile)
```

Two A1 defects reproduced in one 41-line file: the A13 assignment-target rejection, and — visible only once the first is out of the
way — the **parameter-binding cast bug** from A3-159 patch 2 (`pep_local_1`/`pep_local_3` undeclared; `scan`'s parameters are ids
1 and 3).

## What does not cause it

Seven variants, one variable each, all **check-clean**:

| variant | result |
|---|---|
| `helper(byte_at(source, i))` → `i == 1` (nested builtin call removed) | still **fails** — not the call shape |
| `while` → `if` (loop removed) | **check-ok** — the loop is necessary |
| `var e = i` moved up with the other locals | still **fails** — declaration position irrelevant |
| assignment straight in the `while` body | check-ok |
| assignment at `while`→`if` depth 2 | check-ok |
| assignment at `while`→`if`→`if` depth 3, loop variable assigned | check-ok |
| assignment at `while`→`if`→`if` depth 3, **outer** variable assigned | check-ok |

So: the loop is **necessary**, the nested call and declaration position are **irrelevant**, and **nesting depth alone is not
sufficient**. The 41-line fixture is the smallest program I could build that reproduces it.

## Honest status of the narrowing

I set out to give A1 a one-line reproducer and did not get there. What I have is a 41-line one, plus a list of seven things that
are *not* the cause. That is still useful — it eliminates the three most natural hypotheses — but it does not identify the rule,
and I am not going to invent one.

The remaining difference between the fixture and my clean variants is the presence of the earlier `if` blocks that assign `f`
before `e` is declared and used, and the post-loop `if f == 1 { out = e }`. A next step is to bisect those two specifically.

## For A1

The defect is in `pep_checker_a13.pep` L1933. It affects **A4's entire fallback tier** — thirteen functions written in this style —
and it is the difference between `pep.ps1 check` saying `valid` and the sectional path refusing the same source.

For A4: no workaround is visible from outside. The control shows the rest of the pipeline handles the program fine once the check
passes.

## Limits

- Product path only (`build-c23 --sectional`), one seed, one checker revision.
- "check-ok" above means the A13 rejection did not occur; some variants then failed at C compile or at a header-chunk rule, which I
  record rather than treat as passes.
- I did not test the same shape against the one-shot checker, which reports the fixture `valid` — that discrepancy is itself part of
  A3-163/A3-164.

REF GH #16. Refines `6728588155` (A3-164). Fixtures committed for A1 to run directly.