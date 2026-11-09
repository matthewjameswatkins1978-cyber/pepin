# FINDING BOOT-A3-181 — the A13 defect's blast radius is one file, not the corpus

**I have been describing the A13 assignment-target defect as "the blocker" for several turns. Measured across every `.pep` file in
the repository, it affects none of them. It blocks A4's new fallback-tier source and my 31-line reproducer, and nothing else that
exists.**

Seed blob `f8f476198f`. Candidate `b039fc5`, 63 `.pep` files, each through `build-c23 --sectional`.

## The corpus run

| outcome | files |
|---|---|
| built | 10 |
| refused: top-level declarations unsupported | 24 |
| refused: other | 16 |
| refused: `PEP_RUNTIME_STEP_LIMIT` | 9 |
| refused: other check failure | 4 |
| **refused: `PEP_A13_TYPE_UNSUPPORTED` / assignment target** | **0** |

**Zero.** Not one file in `examples/`, `examples/dogfood/`, `stdlib/`, `runtime/` or `tests/fixtures/` triggers it.

## What this changes about priority

I have been writing "the A13 checker defect blocks the deliverable" as if it were a general hazard. It is not. It is a
**narrow** defect that happens to sit directly across A4's chosen path, because A4 wrote thirteen new functions in the shape that
trips it.

That distinction matters for A1, who is the only unblocked seat:

- **If A1 reads my earlier receipts**, the defect sounds like it may break existing programs. It does not.
- **If A1 deprioritises it because of that**, the contract completion stalls, because the fallback tier is the only thing that trips it.
- **The accurate statement is:** fixing it costs nothing to the existing corpus and unblocks A4 entirely; leaving it blocks exactly
  one lane.

## A second measurement worth stating

Only **10 of 63** files build through the sectional path at all. That figure needs care: many of the 63 are libraries with no `main`,
fixtures built for other purposes, and deliberate negatives. The 24 top-level-declaration refusals are record/union programs the
sectional path has never supported.

But it does bound a claim the dispatch makes — "compiler A builds reproducibly through the real project tooling". The tooling
builds a minority of the repository's Pep files, and the largest single refusal category is not a defect but a documented scope
limit. Worth knowing before anyone reads "builds through the tooling" as "handles the repository".

## Method

Each file got `build-c23 … --sectional`, and the outcome was classified from the tool's final line. A13 was matched on both the
message text and the `PEP_A13_TYPE_UNSUPPORTED` code combined with `check failed`, so a code-only rendering would still be caught.

## Limits

- 63 files, one revision, sectional path only. The one-shot path was not exercised; it refuses at 1 MiB on large sources (A3-163).
- Classification is by the last output line, so a file that fails for two reasons is counted once, by whichever surfaced.
- I did not check whether the 10 that built actually *run* correctly — this measures whether the tooling accepts them, which is a
  different question.

REF GH #16. Reframes severity in `6728741555` (A3-168) and `6728856038` (A3-173).