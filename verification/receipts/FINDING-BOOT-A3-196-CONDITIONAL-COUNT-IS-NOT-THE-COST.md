# FINDING BOOT-A3-196 — reducing scan_value's conditional count does not help; A3-190 does not transfer

**Three restructures of `scan_value`'s loop, successively reducing its conditional count from 15 to 9 to 5 to 2, all exceed the step
budget. The conditionals are not the driver. A3-190's threshold was measured on trivial `if`s and does not generalise to ones whose
bodies do work.**

Seed blob `f8f476198f`. A4 `1f98045d` source, annotations, driver patch, A3-184's 20-function BASE dependency set.

## The three attempts

| restructure | ifs in loop | result |
|---|---|---|
| as written | **15** | STEP |
| merge the seven `if hasop == 1` wrappers into one branch (A3-195) | **9** | STEP |
| flag-free early returns: `return o` / `return p` instead of `err`/`more` | **5** | STEP |
| compressed: operator test folded into the loop guard, digit checks merged, `hasop` flag removed | **2** | STEP |

A **2-conditional** loop body still exceeds the budget. Whatever the cost is, it is not branching.

## What this does to A3-190

A3-190 measured that appending `if`-statements to a `while` on this prologue crossed between 3 and 4, while 40 outside a loop were
fine. Every one of those `if`s was trivial — `if qi + j <= n { qi = qi + 1 }`. The `scan_value` restructures above contain
`skip_ws`, `scan_digits` and `byte_at` calls inside the branches.

So the transferable claim is narrower than A3-190 stated: **a conditional inside a loop costs far more than one outside it**, which
still holds — deleting the loop makes the function build (A3-189). But **the number of conditionals is not the unit**, and my
"about 3 fit" figure led me to build three restructures that were doomed. I should have varied branch *content*, not branch count.

## What they cost

Three attempts, each requiring hand-rewriting a 60-line loop body, all negative. The lesson is that I optimised the quantity I had
measured rather than the quantity that mattered, which is the same error as A3-186 in a different costume.

## Where that leaves scan_value

**No fix, and the obvious directions are now closed:**

- merging — A3-195
- early returns with flag elimination — this receipt
- compression of the branch structure — this receipt
- the prologue is not the cause — A3-189

What remains untested: whether the loop's **calls** are the cost (`skip_ws`, `scan_digits`, `byte_at` per iteration), and whether a
loop that performs one call per iteration rather than several would fit. That is a testable question and a better one than counting
branches. I have not done it.

## Limits

- Four variants, one merge/compress strategy each; I did not test call-count reduction.
- Semantics were preserved by construction in the early-return version (errors return `o`, success returns `p`, matching the original
  `out` logic), but I did not execute any variant — all failed at the check.
- "2 ifs" counts textual `if` lines inside the `while`, not branches at any depth.

REF GH #16. Refines `6729513467` (A3-190); extends `6729627850` (A3-195).