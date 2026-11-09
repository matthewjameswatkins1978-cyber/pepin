# FINDING BOOT-A3-187 — no single construct in scan_value's prologue carries the cost

**A3-186 showed `scan_value` is over budget with its loop deleted. The natural next step is to find the expensive construct. Four
single-construct removals all leave it over budget, so there isn't one.**

Seed blob `f8f476198f`. A4 `d37bf566`, annotations, driver patch, 20 dependency functions, prologue-only variant (46 lines,
`return p` in place of the loop and tail), baseline confirmed STEP.

## The probes

| change to the prologue | result |
|---|---|
| baseline | **STEP** |
| `d1 = scan_digits(source, p)` → `d1 = p` (call-result assignment removed) | **STEP** |
| the `if 19 <= d1 - p { err = 1 }` comparison removed | **STEP** |
| the `if expect_byte(source, p, 45) == 1` check removed | **STEP** |
| the `if neg == 1 { p = skip_ws(source, p) }` check removed | **STEP** |

Four negatives. The cost is **not** attributable to any one of the three constructs I proposed as candidates in A3-186 — that list is
now falsified rather than open.

## What I failed to measure

Node count, which is the quantity the budget actually charges. I tried `pep.ps1 inspect --json` and my recursive node counter did
not find the AST in the response — both functions reported `?`. So I cannot tell whether `scan_value`'s 46-line prologue has more
nodes than `scan_name`'s 64 lines (denser expressions, calls per line), which is the obvious remaining explanation and the one that
would reconcile A3-186's contrast.

I am not going to guess it. Five failed measurements across the last three turns is enough to stop rather than keep constructing
proxies.

## What is now established about scan_value

1. Over budget in a six-function isolation (A3-184).
2. Over budget with its 63-line `while` deleted (A3-186).
3. Over budget with any single prologue construct removed (this receipt).
4. `scan_name` at 64 lines builds under identical dependencies (control, A3-186).

So the cost is **distributed across the prologue or driven by something not localised to one construct**. For A4 that means: do not
hunt for the expensive line — plan on reducing the prologue's overall density, or decomposing it so no fragment carries it all.

## Method note

This is the sixth instrument problem this session and the third turn running on the same sub-question. The pattern has changed
though: A3-185 published nothing because a synthetic curve contradicted a known fact; A3-186 published a measured bound with a
control; this receipt publishes four clean negatives and one explicit failure. **A negative from a real-code probe is worth
reporting** — it stops A4 repeating the search — but a failed measurement is not a result, and I have marked it as a failure rather
than as "inconclusive but probably X".

## Limits

- One revision, blanket `Int` annotations, one dependency set.
- Each probe removes a construct without preserving semantics; these are cost probes, not proposals.
- The 20 dependency functions are constant across all probes, so they cannot explain the variation — but they do mean these are not
  full 34-function builds.

REF GH #16. Closes the candidate list opened in `6729328316` (A3-186).