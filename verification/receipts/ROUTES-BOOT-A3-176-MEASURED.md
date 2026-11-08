# ROUTES BOOT-A3-176 — both ways to a tracked compiler A, measured

**A3-155 offered two honest options for the class-(ii) contract; A4 took the harder one and it is blocked. I have now measured what
each route actually scores, so the choice is a table rather than an argument.** The runbook gained a `--contract` flag that
changes only the class-(ii) expectations and nothing else.

Seed blob `f8f476198f`. Candidate `b039fc5` + driver recipe + A4 `81dca2f4` source + Bool-local rewrite.

## Measured

| section | route (a) published | route (b) narrowed |
|---|---|---|
| identity | FAIL dirty | FAIL dirty |
| product build | PASS 33,069 B | PASS 33,069 B |
| build fails closed | PASS | PASS |
| gcc build | PASS | PASS |
| M-1 pins (clang) | PASS 15/15 | PASS 15/15 |
| M-1 pins (gcc) | PASS 15/15 | PASS 15/15 |
| positive output | PASS | PASS |
| class (ii) codes | **FAIL 7 of 10 wrong** | **PASS 3/3** |
| malformed codes | PASS 4/4 | PASS 4/4 |
| native path | PASS | PASS |
| **verdict** | **NOT APPROVED, 2 of 10 failed** | **NOT APPROVED, 1 of 10 failed** |

The single difference is the contract section. **Under route (b) everything passes except `identity`, and `identity` fails only
because this worktree carries three unapplied patch files.** On a clean tracked candidate with those patches committed, route (b)
would print `VERDICT: APPROVED`.

## What each route needs

**Route (a) — published contract, nine class-(ii) shapes exit 5.** A4's fallback tier implements it and is blocked by the A13
checker defect (A3-163..167), which reproduces on A1's own tip (A3-173). Needs: A1 fixes `pep_checker_a13.pep` L1933, then A4's
34-function source becomes buildable, then A4's Bool-local rewrite in the new source, then A1 lands the driver recipe.

**Route (b) — narrowed contract, only the three return types.** Needs: A1 lands the driver recipe (the diff exists and applies
cleanly, A3-170), A4 returns to the 21-function source or keeps it, A4 makes the Bool-local rewrite, and the contract text and
oracle pins change to match. **No checker fix required.**

## The honest comparison

Route (b) is **one dependency instead of two** and it is the dependency whose patch already exists. Route (a) delivers more of the
published promise and is blocked on a defect I have reproduced at 31 lines but cannot fix from my lane.

I am not recommending either — the contract is A4's to change and mine to measure. What I can say is that **route (b) is provably
shippable today** given A1's driver patch, and route (a) is not.

## What route (b) costs, stated plainly

Seven seed-valid programs would be reported as malformed rather than unsupported. A caller distinguishing "not Pep" from "Pep,
unsupported" gets the wrong answer seven times out of nine. That is a real regression in the public interface, and it should be an
explicit sentence in `PEP0_SUBSET.md`, not an omission.

## Limits

- Both columns are the same tree; only the runbook's class-(ii) expectation changed. The code is identical, which is the point —
  this measures a *contract* difference, not an implementation difference.
- `identity` cannot pass in this worktree by construction. I did not fake a clean tree to get a green verdict.
- Route (a)'s column is measured with A4's `81dca2f4` source plus my Bool-local rewrite, **not** their latest `d37bf566`, which
  cannot be built at all (A3-163).
- Neither column is a tracked candidate. Both are assembled in a disposable worktree.

REF GH #16. Related: `6728133368` (A3-155, the two options), `6728818349` (A3-171, the runbook), `6728781975` (A3-170, the patch).