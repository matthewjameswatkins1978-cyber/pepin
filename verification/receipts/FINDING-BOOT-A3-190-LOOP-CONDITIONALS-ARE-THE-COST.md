# FINDING BOOT-A3-190 — conditionals inside a loop are the dominant cost; ~3 per loop fit on scan_value's prologue

**A3-189 established the loop is `scan_value`'s driver, with the dependency set held constant. This turn locates the cost further:
it is the number of `if`-statements *inside* a loop, not statements in general. Forty sequential `if`s outside a loop build fine;
the fourth inside one does not.**

Seed blob `f8f476198f`. A4 `8025f7c8` source, annotations, driver patch, **A3-184's 20-function BASE dependency set on every row**.

## The curve

Adding sequential `if`-statements to a `while` appended to `scan_value`'s real 88-node prologue:

| `if`s inside the loop | result |
|---|---|
| 1 (single assignment) | ok |
| 1 (if/else) | ok |
| 2 | ok |
| 3 | **ok** |
| 4 | **STEP** |
| 5 | STEP |
| 10 | STEP |

## The contrast that isolates it

| shape | count | result |
|---|---|---|
| sequential `if`s **outside** any loop, appended to the same prologue | **40** | **ok** |
| sequential `if`s **inside** a `while`, same prologue | 4 | STEP |

**Forty conditionals in straight-line code build; four in a loop do not.** That is a factor of at least ten, and it is the
mechanism-shaped answer the last four turns were circling.

## It explains every earlier observation

| observation | explained |
|---|---|
| `scan_value` full (loop has ~10 `if`s) | STEP — well past 4 |
| `scan_value` with `while` deleted | builds — no loop conditionals |
| prologue alone, 88 nodes | builds — no loop |
| prologue + 40 straight-line `if`s | builds — not in a loop |
| **control `scan_name`** (2 `if`s nested in its while) | **builds — under the threshold** |
| loop-only, 131 nodes | STEP — its `if`s are in a loop |

The 131-vs-145 node anomaly that A3-189 left open is resolved: `scan_value`'s loop carries far more conditionals than `scan_name`'s,
and node count was never the right unit.

## What A4 can do with it

**Move conditionals out of the loop.** The loop admits roughly three; `scan_value` wants about ten. Options are to hoist invariant
conditions above the loop, to factor the loop body's decision tree into a helper function called once per iteration, or to split the
loop into several passes each with few conditionals.

## The figure is context-specific — say so

Per A3-189, the budget a chunk consumes depends on its dependency set, so **"3 ifs" is not a constant of the language**. It is the
crossing for this prologue under this 20-function set. A smaller context will admit more; a larger one fewer. What transfers is the
**ratio** — loop conditionals cost roughly an order of magnitude more than straight-line ones — not the number.

## Why this result is more trustworthy than the last three

Every row used the same dependency set, valid Pep, and a real function's prologue. No synthetic stand-in, no cross-configuration
control, no truncation that breaks brace balance. Four turns of failures bought the discipline to build it this way.

## Limits

- Crossing pinned at 3-ok / 4-STEP; I did not test 3 vs 4 at other prologue sizes.
- `if`-statements only; I did not vary `while` nesting depth or test `for` loops.
- Step counts not instrumented — pass/fail only.
- One revision, blanket `Int` annotations.
- The appended `if`s are uniform (`qi + j <= n`), so the cost per `if` may vary with condition shape; I did not test that.

REF GH #16. Explains `6729463912` (A3-189); supersedes the framing of `6729256157` (A3-184) and the withdrawn `6729328316` (A3-186).