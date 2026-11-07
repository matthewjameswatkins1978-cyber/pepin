# PRE-REGISTRATION A3-048: does operand-tree SHAPE (left vs right spine) change emission cost?

**Seat:** A3, mission LUCY-20261107-012. Follows BOOT-A3-047, which falsified per-statement scanning and
suggested expression depth instead. **Written before measurement.**

## The associativity check came first, and it passed

BOOT-A3-047's next step was to establish whether a depth ladder is even expressible, because if Pep
associates both forms identically the variable cannot be isolated. Measured with `inspect --json`:

| program | binary nodes | node-kind traversal |
|---|---|---|
| `1 + 2 + 3 + 4` | 3 | `binary,binary,binary,int,int,int,int` — **left spine** |
| `((1+2)+3)+4` | 3 | `binary,binary,binary,int,int,int,int` — identical to unparenthesised |
| `1 + (2 + (3 + 4))` | 3 | `binary,int,binary,int,binary,int,int` — **right spine** |

So Pep is **left-associative by default**, explicit left parens change nothing, and the right-spine form
produces a genuinely different tree **with the same node count and the same statement count**. The depth
variable is isolatable.

## The experiment

Same `while` envelope, one assignment, **same number of literals and binary nodes**, only the operand-tree
shape differs:

```
L:  n = n + 1 + 1 + 1 + 1 + 1 + 1        (left spine)
R:  n = n + (1 + (1 + (1 + (1 + (1 + 1)))))   (right spine)
```

## Predictions

| # | Claim | Falsified if |
|---|---|---|
| S1 | both chunks have the **same node count** (a fair comparison) | they differ |
| S2 | both **emit** (below budget) | either refuses |
| S3 | the **right spine costs more** than the left spine by at least 15% | the difference is under 15% |

**S3 is my falsifier.** Reading BOOT-A3-047, a deeper operand tree should cost more if the emitter's cost
tracks recursion depth. If the two are within 15%, then operand-tree *shape* is not the driver either, and
I will report that the depth hypothesis is unsupported rather than promote it.

## What each outcome implies

- **S3 holds** → the cost is depth-sensitive in operand trees; A2's optimisation target is the recursive
  lowering of binary expressions, and the measured ratio is a success criterion I can audit.
- **S3 fails** → neither statement count (A3-047) nor operand-tree shape explains the quadratic term. I
  will then report that the driver is unidentified, and that the honest next step is for A2 to instrument
  the emitter rather than for A3 to keep guessing from cost surfaces.

## Honest limits

- Cost probe only; nothing compiled or run. One family, one seed build, one machine.
- The traversal fingerprints above come from JSON kind ordering, which is *evidence* of shape but not a
  formal AST dump; S1 (equal node counts) is the fairness check that matters.
- I have now had two hypotheses falsified in this campaign; this pre-registration is written with that in
  mind, and the falsifier is stated so the negative result is decided in advance rather than negotiated
  afterwards.

## Scope guard

A3 owns only `verification/**`. No edits to A2's emitter. Cap unchanged.