# FINDING BOOT-A3-200 — scan_value's loop declares two `var`s, which emission refuses; this sits behind the step limit

**Found while testing a sequential-pass restructure. `scan_value` declares `var hasop` and `var d2` *inside* its `while`. Pep's
emitter refuses `var` declarations in loop bodies, so once the step limit is solved, `scan_value` will fail for this instead. The fix
is to hoist both.**

Seed blob `f8f476198f`. A4 `1f98045d` source.

## The rule, measured

Loop body variants, everything else constant:

| statement inside the loop | result |
|---|---|
| `i = i + 1` (assignment) | **ok** |
| `let k = byte_at(source, i)` | **ok** |
| `let k = 1` (literal) | **ok** |
| `var k = byte_at(source, i)` | **refused** |
| `let k = scan_digits(source, i)` | refused |

The emitter's own message names the allowance:

```
Pep C23 unsupported: Pep C23 while bodies support byte_at lets, assignments, returns, …
```

So a loop body may `let`-bind a `byte_at` or a literal, assign, return, branch, or `say` — but **not** declare a `var`, and not
`let`-bind a call other than `byte_at`.

## What scan_value does

```
      var hasop = 0                 <- inside the while
      …
      var d2: Int = q               <- inside the while
```

Both are `var` declarations inside the loop. **Neither is reachable today** because the check fails at the step limit first — the
same invisibility that hid `match_tail`'s empty-then until I looked for it.

## The fix

Hoist both above the `while` and leave the assignments inside:

```
  var hasop = 0
  var d2 = 0
  …
  while q + 1 <= n {
    hasop = 0
    …
    d2 = q
```

Note this makes the step problem marginally **worse**, not better — the loop keeps an extra assignment per declaration hoisted. It is
required for legality, not for the budget.

## Why this matters even though scan_value is unsolved

It is a second, independent defect in the same function. Anyone who solves the budget and then finds emission refusing the loop will
have spent a cycle discovering this. It is one mechanical edit and it can be made now, at zero risk, while the budget question is
still open.

This is the second time in this lane that a blocker sat invisible behind another: `match_tail`'s empty-then (A3-193) was hidden
because the check stopped at `scan_value` first. **A refusal that is invisible is not absent**, and the way to find these is to read
the constructs rather than wait for the message.

## Limits

- The `let k = scan_digits(...)` refusal's exact code was truncated in my output; I recorded that it is refused without claiming
  which diagnostic.
- I did not test nested loops, or `let`/`var` inside an `if` that is inside a loop.
- The hoist is verified legal by the rule but I did not apply it to `scan_value` and re-measure, because the step limit still stops
  the build either way.

REF GH #16. Found while testing option 2 from `6729725146` (A3-199).