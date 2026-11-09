# FINDING BOOT-A3-193 — match_tail: an empty then-branch, with a verified one-line fix

**`match_tail` is refused with "conditional lowering requires a non-empty then branch". The cause is one construct: `if qe == q { }`
with the work in the `else`. Inverting it makes the function build. It is the only such construct in A4's file.**

Seed blob `f8f476198f`. A4 `8025f7c8` source, annotations, driver patch, A3-184's 20-function BASE dependency set, the A3-191
`bytes_eq` helper applied so `names_equal` is not the blocker.

## The cause

`match_tail` L796:

```
        if qe == q {
        } else {
          tact = 1
        }
```

The `then` branch is empty. The emitter refuses it — the same rule I saw on A1's branch in A3-173 and mistook there for a checker
difference.

## The fix, verified

```
        if qe != q {
          tact = 1
        } else {
        }
```

| variant | result |
|---|---|
| as written | **refused: non-empty then branch** |
| inverted | **builds** |

**Only one empty-then branch exists in the file** — found by scanning every `if … {` whose next line is `} else {`.

## The accumulating fix set for A4's fallback tier

Three distinct blockers now have measured fixes:

| # | function | cause | fix |
|---|---|---|---|
| 2 | `names_equal` | two fallible `byte_at` calls in one comparison | extract to `bytes_eq` helper (A3-191) |
| 3 | `match_tail` | empty `then` branch | invert the condition (this receipt) |
| — | all | bare-name `var` init untyped | annotate (A4 already applied, A3-188) |

and one that does not:

| # | function | cause | what is needed |
|---|---|---|---|
| 1 | `scan_value` | ~10 conditionals inside one loop; ~3 fit | restructure the loop (A3-190) |

## What is not yet known

`match_varlet_body` (347 nodes) and `is_unsupported_prog` (687 nodes) sit behind `scan_value`, which I have not fixed. With
`names_equal` and `match_tail` cleared, they are the next things measurable once the loop is dealt with.

## Method note

Every blocker in this sequence was found the same way: take the refusal message, locate the single construct, change one thing,
re-measure with the dependency set held constant. That discipline is what A3-186/187 lacked and why they were wrong. Three
consecutive findings have held.

## Limits

- Fixes verified in isolation with a fixed dependency set, not in a full 34-function build.
- The `bytes_eq` helper name/signature are mine; A4 owns the file.
- I did not check whether inverting the condition interacts with any later logic — `qe != q` is the exact negation of `qe == q`
  for Ints, but A4 should confirm the semantics they intended.
- Only one empty-then exists; if A4 adds more, the scan should be repeated.

REF GH #16. Blocker 3 in the sequence after `scan_value` (A3-190) and `names_equal` (A3-191).