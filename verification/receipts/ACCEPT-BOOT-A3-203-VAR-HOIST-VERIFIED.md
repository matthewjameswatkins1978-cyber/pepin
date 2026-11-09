# ACCEPT BOOT-A3-203 — A4's var hoist verified; the loop-body defect is now zero across the file

**A4's `4470bd9a` hoists `var hasop` and `var d2` above `scan_value`'s loop. Verified correct, and a corrected scan confirms no
function in the file declares a `var` or `let` inside a loop any more.**

Seed blob `f8f476198f`. A4 `4470bd9a`, `compiler_a.pep` blob `f5f15a3c`, 1,548 lines, 35 functions.

## The hoist

```
    44|   var q: Int = p
    45|   var hasop = 0        <- hoisted (A3-200)
    46|   var d2: Int = 0       <- hoisted
    47|   while q + 1 <= n {
    48|     if more == 1 {
    49|       q = skip_ws(source, q)
    50|       hasop = 0           <- assignment stays inside
```

Correct: declarations above, assignments inside.

## A false scan of mine, caught and corrected

My first sweep reported **4 remaining** loop-body declarations — in `scan_digits` and `scan_name`. That was wrong: my check took
everything after the first `while` line to the end of the function, so epilogue declarations after the loop closed were counted as
inside it.

Re-scanned with brace counting: **0 across all 35 functions.**

Worth recording because the false result was plausible — `scan_digits` and `scan_name` both build, and if they had really carried
`var` inside a loop that would have contradicted A3-200's rule outright. The contradiction was the tell.

## Where the fallback tier stands

| # | function | state |
|---|---|---|
| 2 | `names_equal` | **closed** (A4, verified A3-194) |
| 3 | `match_tail` | **closed** (A4, verified A3-201) |
| 1b | `var` in loop | **closed** (A4, verified here) |
| — | bare-name `var` annotations | **closed** (A4, verified A3-188) |
| 1 | `scan_value` | **open** — step budget; minimum loop work 4.5 units vs ~4 |
| 4 | `match_varlet_body`, `is_unsupported_prog` | behind `scan_value` |

**Every mechanical defect in A4's fallback tier is now closed. What remains is one budget question**, which A3-199 showed has no
in-place fix and A3-190/198/199 bounded.

## What this means

The build still stops at `scan_value`'s step limit:

```
Pep C23 unsupported: Pep C23 sectional check failed in scan_value: ['PEP_RUNTIME_STEP_LIMIT']
```

with no var-in-loop refusal behind it any more. So when the budget question is resolved — by a different algorithm or by deferring
the function — there is no second defect waiting.

## Limits

- One commit, one build; the function cannot emit so the hoist's emission-level effect is inferred from the rule, not observed.
- My corrected scan uses brace counting from the `while` line; nested loops would need care and the file has none.

REF GH #16. Closes `6729773967` (A3-200).