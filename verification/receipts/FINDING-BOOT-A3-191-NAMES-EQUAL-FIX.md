# FINDING BOOT-A3-191 — names_equal: two fallible calls in one comparison, with a verified fix

**`names_equal` is refused with "rejects two fallible operands because C operand evaluation order is unspecified". The cause is one
line: `byte_at(source, a1 + k) == byte_at(source, b1 + k)`. Extracting that comparison into a helper makes the function build.**

Seed blob `f8f476198f`. A4 `8025f7c8` source, annotations, driver patch, A3-184's 20-function BASE dependency set.

## The cause

```
      if byte_at(source, a1 + k) == byte_at(source, b1 + k) {
```

`byte_at` is fallible — it bounds-checks and can fail. Two calls in one comparison means two fallible operands, and C does not
specify operand evaluation order, so the emitter cannot say which error would surface first. It refuses rather than emit
ambiguous code. This is the same rule as A3-078's arithmetic `may_fail`, applied across a comparison.

## Three attempts

| variant | result |
|---|---|
| as written | **refused: two fallible operands** |
| hoist one call into `var c1 = …` inside the loop | **STEP** — the extra statement pushes it past the loop-conditional budget |
| **extract the comparison into a `bytes_eq` helper** | **builds** |

The middle row matters: **the obvious fix clears the refusal and trips the other blocker.** A3-190 established that conditionals
inside a loop are the dominant cost, and adding a statement there is exactly what makes it worse.

## The verified fix

```pep
fn bytes_eq(source: SourceBytes, i: Int, j: Int) -> Int {
  var a = byte_at(source, i)
  var b = byte_at(source, j)
  var r = 0
  if a == b {
    r = 1
  } else {
  }
  return r
}
```

and in `names_equal`'s loop:

```
      if bytes_eq(source, a1 + k, b1 + k) == 1 {
```

The two `byte_at` calls become **separate statements** in the helper, so no expression has two fallible operands. The loop keeps
exactly the two conditionals it had, so the step budget is unaffected. Measured: `ok`.

## Why the helper form rather than a hoist

A hoist inside the loop adds a statement to the expensive region. The helper moves the work to a **separate function** where
statements are cheap (A3-190: 40 straight-line conditionals build where 4 in a loop do not). It is the same principle the scan_value
guidance rests on, applied to a smaller function.

## What this unblocks

`match_tail` calls `names_equal`, so it inherits the refusal (A3-184). Fixing `names_equal` should clear that dependency, though
`match_tail` has 181 nodes of its own and I did not re-measure it after the fix.

## Limits

- The helper name, placement and signature are mine; A4 owns the file and may prefer a different factoring.
- Verified for `names_equal` in isolation with a fixed dependency set. Not re-run inside a full 34-function build.
- I did not check whether other functions carry the same two-fallible-call pattern. `scan_value` has `byte_at(source, q)` in a
  condition with a single call, so not there; a sweep would be cheap and I have not done it.
- `bytes_eq` returns Int rather than Bool to match the file's existing style.

REF GH #16. Blocker 2 of A4's fallback tier, after `scan_value` (A3-190) and before `match_tail`.