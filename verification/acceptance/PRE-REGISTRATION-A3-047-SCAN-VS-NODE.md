# PRE-REGISTRATION A3-047: is the quadratic cost per-STATEMENT scanning or per-NODE work?

**Seat:** A3, mission LUCY-20261107-012. **Written before measurement.**

## The question A2's fix depends on

BOOT-A3-033 measured `steps ≈ 381n + 35.68n²` and BOOT-A3-045 showed two sequential conditionals in a
loop body already exceed the budget. That tells us emission is quadratic in chunk nodes. It does **not**
tell us *where* the quadratic term comes from, and the two candidates imply very different fixes:

- **Per-statement scanning**: the emitter walks the whole node list for every statement it lowers, as its
  nested `for … in nodes` shape suggests. Cost ≈ statements × nodes → an index/map makes it linear, and
  the fix is well-defined and small.
- **Per-node work**: each node simply costs a lot, and the growth is intrinsic. Cost would then track
  nodes alone and the only levers are fewer nodes or a cheaper per-node path.

## The discriminating experiment

Same envelope, **similar node count**, very different statement count:

| var | body | statements | shape |
|---|---|---|---|
| A | one assignment with a long `+` chain | **1** | many nodes, one statement |
| B | eight sequential assignments `n = n + 1` | **8** | many nodes, many statements |

If cost ≈ statements × nodes, **B should be dramatically more expensive than A at comparable node count**.

## Predictions

| # | Claim | Falsified if |
|---|---|---|
| R1 | A and B land within ~25% of each other in node count (fair comparison) | they differ by more than 25% |
| R2 | **B costs materially more than A** — at least 1.8× the steps | B ≤ 1.8× A |
| R3 | therefore the quadratic term is dominated by per-statement scanning, and an index/map lookup is the indicated fix | R2 fails |

**R2 is the discriminator, and it is falsifiable in one run.** If A ≈ B, my "scan per statement" reading is
wrong and I will say so plainly rather than back-filling an explanation.

## What each outcome implies for the mission

- **R2 holds** → A2's fix is a data-structure change (parent→children index) rather than a cap question or a
  rewrite: the same program becomes affordable without touching the cap. That is the cheapest credible
  route to an emittable compiler-shaped function.
- **R2 fails** → emission cost is intrinsic per node; the mission then needs either much smaller compiler
  units (which BOOT-A3-045/046 showed cannot express a lexer) or a cap decision from Matthew.

## Honest limits

- Cost probe only; nothing compiled or run. One family, one seed build, one machine.
- Node counts cannot be matched *exactly* (AST shapes differ); R1 checks the comparison is fair enough.
- I am not instrumenting A2's code. Any mechanism claim is an inference from the cost surface, labelled as
  such.

## Scope guard

A3 owns only `verification/**`. No edits to A2's emitter. Cap unchanged.