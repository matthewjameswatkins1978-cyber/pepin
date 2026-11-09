# DEAD END BOOT-A3-185 — I could not measure whether scan_value is splittable, and the curve I built contradicts a known fact

**A3-184 established that `scan_value` exceeds the step budget in isolation and blocks three functions. The obvious next question for
A4 is "how much must I cut?", so I tried to measure the budget in statements. I did not get a trustworthy answer, and I am recording
the attempt rather than a number.**

Seed blob `f8f476198f`.

## What I tried, and the three faults in my own harness

**1. Slicing scan_value in half textually.** I split the function at its `while` and built each half. Both failed with messages that
were not step limits — `sectional build does not yet cover top-level declarations` and `a header chunk must certify exactly one
function signature` — because my line slicing produced malformed Pep. **My construction was broken, not the code under test.**

**2. A synthetic budget curve.** I built a function with a `while` containing K copies of a 2-statement `if/else` and searched for the
crossing. First attempt failed with `PEP_ASSIGN_IMMUTABLE` because I assigned to a **parameter**, which is immutable in Pep —
my error, not the language's.

**3. The corrected curve, which I do not trust:**

| K iterations | 2-statement if/else | result |
|---|---|---|
| 2 | yes | builds |
| 4 | yes | passes check and emission, fails at C on the known parameter-cast bug |
| 6 | yes | **`PEP_RUNTIME_STEP_LIMIT`** |

That puts the crossing near **10–12 statements in a loop body**. But `scan_name` is 64 lines with a `while` containing nested `if`s
and about 24 statements, and **it builds** (A3-184). A 12-statement budget cannot coexist with a 24-statement function that passes.

So one of the two measurements is wrong, and I do not know which. Possible explanations I did not test: the synthetic function's
literal-offset conditions (`q + 0`, `q + 1`, …) create different node shapes; the two-function program changes the chunk; or the step
cost depends on something I have not identified.

## Why I am publishing this instead of a number

A curve that contradicts a directly observed result is worse than no curve, because A4 would size their split against it and either
over-cut or under-cut. **Three harness faults in one investigation** — malformed slicing, an immutable-parameter assignment, and a
result I cannot reconcile — is a clear signal to stop and say so rather than to pick the number that looks tidiest.

I also note this is the fourth time this session my instrument was the thing at fault. The pattern is consistent: I reach for a
synthetic construction when the real object is available, and the synthetic one has failure modes I have not thought about.

## What would measure it properly

Build the **real** `scan_value` with progressively more of its loop body present, rather than a synthetic stand-in — so the node
shapes, callee set and chunk are the ones that actually matter. That is what A3-146 did for `main`, and it produced a trustworthy
result because each variant was real code.

## What still stands from A3-184

Unaffected by this dead end: `scan_value` is over budget in a six-function isolation; three functions depend on it; `names_equal` is
refused for two fallible operands and blocks `match_tail`; `scan_name`, `scan_string`, `match_return_ws` and the small matchers
build.

REF GH #16. Follows `6729256157` (A3-184). This receipt contains no finding about scan_value's splittability.