# FINDING BOOT-A3-186 — scan_value is over budget before its loop starts

**A3-185 failed to measure how much of `scan_value` must be cut. This turn, using the real function and a clean control, the answer
is more useful than a threshold: `scan_value` exceeds the step budget with its `while` removed entirely. Splitting the loop will not
fix it.**

Seed blob `f8f476198f`. A4 `d37bf566`, annotations applied, driver patch applied, 20 dependency functions, each variant real code.

## The measurement

| variant | lines | result |
|---|---|---|
| full `scan_value` | 113 | **STEP** |
| prologue + tail, `while` removed (lines 45–107 deleted) | 50 | **STEP** |
| prologue only, `while` and tail removed | 46 | **STEP** |
| **control: `scan_name`** | **64** | **builds** |

The control is the important row: **`scan_name` is 64 lines and builds under the identical dependency set.** So the harness is not
systematically too expensive — a larger function than the failing prologue passes.

## What this means for A4

`scan_value`'s step cost is **not** in its loop body. Cutting the 63-line `while` out entirely leaves the function still over budget,
and three functions sit behind it. So the split A3-184 implied — "divide the 113 lines" — will not work if the division leaves the
prologue intact.

The reduction has to come from the prologue itself, or `scan_value` has to be decomposed so that no single function contains both the
prologue's work and the loop's.

## What I could not establish, and will not guess at

**Why 46 lines of prologue exceeds a budget that 64 lines of `scan_name` passes.** I tried to bisect the prologue and every attempt
produced malformed Pep (`a header chunk must certify exactly one function signature`) because I truncated mid-construct, breaking
brace balance.

Candidate explanations I did **not** test: the five `var` declarations before the loop; the `d1 = scan_digits(source, p)` assignment
whose value is a call; the `19 <= d1 - p` comparison; or a node-shape difference I have not identified. Any of these is a guess and
I am not offering one.

## Honest position on this measurement

This is the fifth instrument problem this session, and the second turn in a row where I could not fully explain a result. What is
different here is that the finding rests on a **direct comparison with a control under identical conditions** rather than on a
synthetic curve that contradicted known facts. The observation "over budget with the loop removed, while a longer function passes"
is reproducible from the fixtures; the mechanism is not established.

So: the **actionable** conclusion is solid — do not plan a split that leaves the prologue alone — and the **explanatory** part is
open. I am labelling which is which.

## Limits

- One revision, annotations blanket `Int` (A3-183's caveat), 20 dependency functions.
- Truncation at line boundaries broke Pep; I did not find a valid way to bisect the prologue, so there is no threshold, only an
  upper bound of 46 lines.
- Isolated builds are not full 34-function builds.
- The 46-line figure counts source lines, not AST nodes; node count is the quantity the budget actually charges.

REF GH #16. Supersedes A3-185's dead end with a measured bound; qualification of A3-184's implied split.