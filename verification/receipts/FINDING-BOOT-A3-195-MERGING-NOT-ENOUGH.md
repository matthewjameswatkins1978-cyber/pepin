# FINDING BOOT-A3-195 — merging scan_value's conditions is not enough; it needs a structural change

**`scan_value` has 15 conditionals inside its `while`. Merging the repeated `if hasop == 1` blocks into one brings that to 9 and it
still exceeds the step budget. Against A3-190's threshold of about 3, local merging cannot close the gap.**

Seed blob `f8f476198f`. A4 `1f98045d` source, annotations, driver patch, A3-184's 20-function BASE dependency set.

## The count

```
conditionals inside scan_value's while: 15
```

Of those, six are `if hasop == 1 { … } else { }` wrappers around chunks that could live in a single branch:

```
      if hasop == 1 { q = q + 1 } else { }
      if hasop == 1 { q = skip_ws(source, q) } else { }
      if hasop == 1 { d2 = scan_digits(source, q) } else { }
      if hasop == 1 { if d2 == q { err = 1 } } else { }
      if hasop == 1 { if err == 0 { … 19 <= d2 - q … } } else { }
      if hasop == 1 { if err == 0 { p = d2  q = d2 } } else { }
      if hasop == 0 { more = 0  q = n } else { }
```

## What merging achieves

Collapsing all seven into one `if hasop == 1 { … } else { more = 0  q = n }`:

| variant | conditionals in loop | result |
|---|---|---|
| as written | 15 | **STEP** |
| `hasop` blocks merged | **9** | **STEP** |

Nine is still three times A3-190's threshold. **Merging buys six conditionals and is not sufficient.**

## What that implies for the fix

The decision tree has to leave the loop, not be compressed inside it. A3-190's measurement says statements in a separate function are
cheap — 40 straight-line conditionals build where 4 in a loop do not — so a helper called once per iteration is the direction.

The obstacle is that the loop body updates **four** values (`q`, `p`, `err`, `more`) and a Pep function returns **one** `Int`. A helper
cannot return them together. Options A4 would have to weigh:

- restructure so the loop carries fewer live values across iterations;
- split into sequential passes, each updating one or two variables with few conditionals;
- or accept that `scan_value` needs rethinking rather than relocating.

I have not designed any of these. Naming a direction the measurements support is not the same as claiming it works, and this lane has
already published two findings it had to retract on exactly that overreach.

## Method note

An earlier run of this experiment failed with `a header chunk must certify exactly one function signature` because my substituted
text was malformed. The clean run above gives `STEP`. I mention it because the failure mode is mine, not the code's, and it has
appeared three times in this lane.

## Limits

- One merge shape. I did not try merging the `q + 1 <= n` and `byte_at` checks, or hoisting the `err == 1` tail out of the loop.
- Conditionals counted textually inside the `while`; nesting depth may matter and I did not test it.
- `scan_value` still has no verified fix. A3-190's threshold is context-specific, so 9 versus 3 is indicative rather than exact.

REF GH #16. Bounds the search opened by `6729513467` (A3-190).