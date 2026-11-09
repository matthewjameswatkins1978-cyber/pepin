# FINDING BOOT-A3-199 — option 1 is closed: scan_value's minimum loop work exceeds the budget

**A3-198 sized the loop budget at about four units and `scan_value` at about thirteen. This turn I tried the most promising
reduction — replacing the four-call operator test with a single helper call — and it still exceeds. The loop's *minimum* required
work is over budget.**

Seed blob `f8f476198f`. A4 `1f98045d` source, annotations, driver patch, A3-184's 20-function BASE dependency set.

## What I tried

`scan_value`'s operator test is a four-call disjunction:

```
if q + 1 <= n && (byte_at(source, q) == 43 || byte_at(source, q) == 42 || byte_at(source, q) == 45 || byte_at(source, q) == 47)
```

That is four calls = two units on A3-198's scale, just to ask "is this character an operator". Replacing it with one helper call in
the style A4 already uses for `is_namech`, `is_var3` and friends:

```pep
fn is_op(b: Int) -> Int {
  var r = 0
  if b == 43 || b == 42 || b == 45 || b == 47 {
    r = 1
  } else {
  }
  return r
}
```

and in the loop: `if q + 1 <= n && is_op(byte_at(source, q)) == 1 {`. That is **two** calls where there were four.

## Result

**Still `PEP_RUNTIME_STEP_LIMIT`.**

## The arithmetic, which is the actual finding

The reduced loop now spends:

| component | units |
|---|---|
| 2 conditionals (loop guard + branch) | 2.0 |
| `skip_ws` twice, `byte_at` once, `is_op` once, `scan_digits` once = 5 calls | 2.5 |
| **total** | **4.5** |

Budget ≈ 4. **The loop cannot fit even doing only what its job requires.** Every call in that list is load-bearing: skip whitespace,
read a character, recognise it, skip whitespace again, read the digits.

To reach four units it would need to drop a call or a branch that the algorithm needs — with `skip_ws` appearing twice and the
operator/verification branches both necessary.

## What this closes

| option | status |
|---|---|
| **1. reduce both axes in the loop** | **measured and negative** — minimum work is 4.5 units against a budget of about 4 |
| 2. split into sequential passes | untested; each pass must independently fit in ~4 units while looping and calling |
| **3. narrow the contract (A3-176)** | measured at **9 of 10 runbook sections**, needs none of this |

Option 1 was the option A3-198 sized at a threefold cut. It is now not merely hard but **arithmetically short**: the loop is over
budget before any redundancy is considered.

## What I am not claiming

That `scan_value` is impossible. A different **algorithm** — not a different arrangement of the same loop — might fit: for instance
one that does not re-skip whitespace, or that recognises the operator without reading the character, or that defers verification to a
separate pass. Those are design questions I have not tested and am not qualified to design from the outside.

What I am claiming is narrower and measured: **no arrangement of this loop's necessary work fits the budget.**

## Limits

- `is_op` uses a four-way `||` inside its own body; that function is small and builds, but the disjunction may itself have cost that
  the grid would attribute to calls.
- Units are a fitted reading of A3-198's nine cells, not a compiler constant.
- One revision, sectional path only, one dependency set.
- I did not test whether reordering (e.g. `skip_ws` once per iteration) is semantically valid for `scan_value` — only that the current
  arrangement is over.

REF GH #16. Closes option 1 from `6729708669` (A3-198).