# PRE-REGISTRATION A3-045: sequential conditionals vs nested — does flattening buy a fit?

**Seat:** A3, mission LUCY-20261107-012. **Written before measurement.**

## Why this decides whether a lexer-shaped function is emittable at all

A lexer or parser is a loop containing classification branches. Measured facts so far:

- `while { if/else }` (BOOT-A3-028 D1, 32 nodes) **emits** at **58,635** steps of 100,000.
- `while { if { if/else } }` (nested depth 2, 40 nodes) **refuses** — over budget.
- cost per node rises with size (**381n + 35.68n²**, BOOT-A3-033), and conditionals are the dearest
  construct per node (**3,523/node**, BOOT-A3-039).

Those are *nested* shapes. But a state machine does not have to nest: it can be written as **sequential
classifications in one loop body**:

```
while !(byte_length(source) <= o) {
  if letter(b) { n = n + 1 } else { }
  if digit(b)  { n = n + 2 } else { }
  if space(b)  { n = n + 3 } else { }
  o = o + 1
}
```

If sequential chains fit where nesting does not, a genuine lexer is emittable **today** and route S
becomes immediately credible with a design constraint A4 can follow. If they do not fit, then no
compiler-shaped loop is emittable and **cheaper lowering is a prerequisite for either route** — which
changes the plan.

## Measurement

Constant envelope `while !(byte_length(source) <= o) { <BODY> o = o + 1 }`, single function, exact steps
from `{"op":"metrics"}`:

| var | body | purpose |
|---|---|---|
| Q1 | one `if/else` | baseline, expected ≈ 58–60k |
| Q2 | two sequential `if/else` | flattening step 1 |
| Q3 | three sequential `if/else` | a realistic state-machine fan-out |
| Q4 | the **nested** depth-2 shape | control: must refuse, as previously measured |

## Predictions

| # | Claim | Falsified if |
|---|---|---|
| Q1 | Q1 emits around 58–60k (reproducing BOOT-A3-028) | outside 50–75k |
| Q2 | **Q3 emits** — sequential flattening fits where nesting does not | Q3 refuses |
| Q3 | Q3 is cheaper than Q4 at comparable node count | Q3 ≥ Q4 |
| Q4 | Q4 refuses (reproduces the known nested failure) | Q4 emits |

**Q2 is the decision-relevant claim and my own falsifier.** I expect flattening to win because nesting
adds a cost term per level rather than per statement. If Q3 refuses, I will say plainly that no
compiler-shaped loop is emittable and that cheaper lowering must come first.

## Honest limits

- Cost probe only: nothing is compiled or run; these are emitter step counts, not programs.
- One family, one seed build, one machine.
- A real lexer needs more than three branches and probably a `Str`/list result, which BOOT-A3-043 showed
  is separately blocked (`utf8_slice` is not a lowered builtin). This measures the *control-flow envelope*
  only — it does not demonstrate a lexer.

## Scope guard

A3 owns only `verification/**`. No edits to A1's checker/contract, A2's emitter, A4's app. Cap unchanged.