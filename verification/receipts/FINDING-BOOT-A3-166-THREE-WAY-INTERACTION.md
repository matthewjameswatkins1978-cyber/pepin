# FINDING BOOT-A3-166 — the A13 assignment-target defect is a three-way interaction, now at 31 lines

**A3-165 left a 41-line reproducer and seven eliminations. Building up from a clean baseline instead of down from the fixture
found the shape: the defect needs three features present at once, and removing any one of them clears it.**

Seed blob `f8f476198f`. Fixtures: `a13-assign-target-reduced.pep` (31 lines, 432 B) and `…-reduced-control.pep`.
The earlier 41-line pair is still committed alongside them.

## The reduced reproducer

```
fn scan(source: SourceBytes, o: Int) -> Int {
  var i = o
  var n = byte_length(source)
  var e = i
  var f = 0
  if i + 1 <= n { f = 1 } else { }          <-- feature 1: a conditional that assigns f
  while i + 1 <= n {                        <-- feature 2: a loop assigning e inside nested ifs
    if f == 0 {
      if i == 1 { e = i } else { i = n }
    } else { i = n }
  }
  var out = o                               <-- feature 3: a post-loop variable that copies e
  if f == 0 { out = e } else { }
  return out
}
```

```
reduced          A13-FAIL   sectional check failed in scan: ['PEP_A13_TYPE_UNSUPPORTED']
reduced_control  check-ok   (fails later, on an unrelated conditional-lowering rule)
```

## How it was found, and why the first direction failed

Bisecting **down** from the 41-line fixture gave seven variants that all checked cleanly — each removal cleared the error but no
smaller program existed along that path. So I ran it the other way: start from a minimal clean program and **add** one feature at a
time.

| step | result |
|---|---|
| baseline (loop, nested ifs, single `e = i`) | check-ok |
| + a two-statement innermost branch | check-ok |
| + a pre-loop `if` assigning `f` | check-ok |
| + a post-loop `var out` copying `e` | check-ok |
| **all three together** | **A13-FAIL** |

Then pairs:

| pair | result |
|---|---|
| pre-loop `if` + two-statement branch | check-ok |
| two-statement branch + post-loop `out` | check-ok |
| **pre-loop `if` + post-loop `out`** | **A13-FAIL** |

So the two-statement branch is unnecessary — features 1 and 3 with a substantially simpler loop suffice.

## And each of those two can be removed in place

| variant of the failing pair | result |
|---|---|
| drop `var out`, `return e` directly from inside a post-loop `if` | check-ok |
| simplify the loop body to `e = i; i = n` | check-ok |
| drop the pre-loop `if` | check-ok |
| drop the loop entirely | check-ok |

**Every single-feature removal clears it.** That is the signature of an interaction in state tracking, not of one unsupported
construct — and it explains why A4's thirteen new functions, all written in this style, fail one after another as each is
simplified.

## Hypothesis, stated as a hypothesis

Binding/type information for a variable assigned **inside a loop** is not visible to an assignment check **after** the loop, once
an earlier conditional has introduced another binding. `e` is assigned only inside the `while` nest and then copied to `out` after
the loop; `f` is assigned before the loop. Remove any of the three and the checker tracks `e` correctly.

I have not read the type-inference code path to confirm that, and I am not claiming it. The reproducer and the three-way
dependency are established; the mechanism is not.

## For A1

`pep_checker_a13.pep` L1933, `"Assignment target has no supported concrete type"`. The 31-line fixture runs in about a minute:

```
python pep_c23.py build-c23 verification/fixtures/a13-assign-target-reduced.pep --sectional --output /tmp/x.exe
```

One control differs from it by a single line and passes the check. This is the whole of A4's fallback tier blocked on a checker
scope rule.

## Limits

- Product path only, one seed, one checker revision.
- "check-ok" means the A13 rejection did not occur; the reduced control then fails on a different rule ("conditional lowering
  requires a non-…"), which I record rather than count as a pass.
- The reduced control **no longer** exhibits the parameter-binding cast bug that the 41-line control did — that bug needs a
  parameter bound through a carried-binding path, and the smaller program does not reach it. The 41-line pair remains the
  reproducer for that second defect.
- Three-way dependency established by removal in place; I did not enumerate a fourth feature.

REF GH #16. Refines `6728624012` (A3-165). Fixtures committed.