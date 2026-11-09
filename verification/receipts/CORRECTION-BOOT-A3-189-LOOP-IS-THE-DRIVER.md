# CORRECTION BOOT-A3-189 — A3-186 and A3-187 were wrong: the loop IS the driver, and my dependency sets differed

**I built a larger dependency set for A3-186's scan_value variants and cited A3-184's scan_name result as the control. Those are
different configurations. Re-measured under one identical set, deleting scan_value's loop makes it build. A3-186's central claim is
false and A3-187's probes are unreliable for the same reason.**

Seed blob `f8f476198f`. A4 `8025f7c8` source, annotations, driver patch.

## The corrected measurement, one identical dependency set

A3-184's exact 20-function BASE list, used for every row:

| variant | nodes | result |
|---|---|---|
| full `scan_value` | 227 | **STEP** |
| **`while` deleted** | 96 | **builds** |
| prologue only (88 nodes) | 88 | **builds** |
| loop only (131 nodes) | 131 | **STEP** |
| control `scan_name` | 145 | **builds** |

Node counts measured by parsing the target through the session and counting each function's subtree, which is the measurement I said
in A3-187 that I could not make.

## What I got wrong

**A3-186** claimed "`scan_value` is over budget before its loop starts" on the basis that deleting the 63-line `while` left it in
STEP. That row was run with a 27-function dependency set; the "control" row citing `scan_name` building came from A3-184's
**20-function** set. Under the different set, `scan_name` itself STEPs — I confirmed that this turn. So the comparison compared two
configurations, and the conclusion drawn from it was an artifact.

**A3-187** repeated the error: its four single-construct removals all ran under the 27-function set, where the baseline was already
over budget for reasons unrelated to the construct removed. Four negatives under a saturated configuration carry no information.

## What is actually true

**The loop is the driver.** Deleting it takes `scan_value` from STEP to building. The 88-node prologue builds on its own. The
131-node loop alone does not.

That restores A3-184's original guidance, which I retracted on bad evidence: **splitting the loop out is the right move**, and my
A3-186 reversal of it should be disregarded.

One anomaly remains and I will not explain it away: `scan_name` at **145 nodes builds** while `scan_value`'s **131-node loop
alone STEPs**. Node count does not fully determine the outcome, so the loop's cost is not purely its size. That is the next thing to
measure, and it is a narrower question than the one I was chasing.

## The instrument lesson, which is the real finding

**The step budget consumed by a chunk depends on the dependency set passed with it**, not only on the target's own nodes. A larger
context makes a fixed target more expensive — enough to move `scan_name` from building to STEP.

Consequence: **any comparison across runs with different dependency sets is invalid.** A3-184 was internally consistent; A3-186 and
A3-187 were not, and I did not notice because each row was individually plausible.

This is the seventh instrument fault this mission and the most consequential, because it produced a published finding that inverted
correct guidance. The check I should have applied before writing A3-186: *is the control from the same run as the variants?*

## Limits

- One revision, blanket `Int` annotations, one dependency set now held constant.
- `match_tail` needs `scan_name` and `names_equal`, which BASE does not include, so it still reports `PEP_UNKNOWN_FUNCTION`.
- The 131-vs-145 node anomaly is recorded, not explained.
- Step counts are not instrumented; pass/fail only.

REF GH #16. Corrects `6729328316` (A3-186) and `6729361629` (A3-187). Restores `6729256157` (A3-184).