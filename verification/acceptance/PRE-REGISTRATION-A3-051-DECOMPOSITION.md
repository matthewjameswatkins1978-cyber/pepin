# PRE-REGISTRATION A3-051: can DEEP nesting hide in a loop-free helper?

**Seat:** A3. **Written before measurement.** Follows BOOT-A3-045/046, which concluded no restructuring
escapes the one-conditional-per-loop-body ceiling.

## What just changed the picture

BOOT-A3-033 recorded an emitter refusal "functions require local bindings and supported loops followed by
one return", and I carried that into a belief that loop-free functions cannot emit. **Measured now, that is
wrong**: a loop-free `classify(b: Int) -> Int` with a single `if/else` (12 nodes) **emits cleanly**
(245 C bytes), and a `main` whose loop body contains **one** conditional calling it emits too.

So the ceiling is specifically about **conditionals inside a loop body**, not about functions.

## The hypothesis this makes testable

If a **loop-free** helper may contain **deep nested conditionals**, then a lexer can be decomposed:

- `main` — `while { n = n + classify(byte_at(source, o)); o = o + 1 }`: **zero** conditionals in the loop;
- `classify` — nested `if/else` depth 3–4, **no loop**.

If every function emits, a lexer-shaped program is emittable **today**, and my BOOT-A3-045/046 conclusion
("no restructuring gets a compiler-shaped function under the budget") is **too strong** and must be
corrected.

## Predictions

| # | Claim | Falsified if |
|---|---|---|
| T1 | a loop-free helper with **depth-3 nested** conditionals checks valid | not valid |
| T2 | that helper **emits** | refused, with the exact text |
| T3 | a `main` whose loop body has **zero** conditionals (just a call and an increment) emits | refused |
| T4 | therefore decomposition escapes the ceiling and a lexer-shape is emittable today | any of T2/T3 fails |

**T4 is the consequential claim and it cuts against my own published conclusion.** If it holds, I will say
plainly that A3-045/046 were too strong: they showed that *nesting inside a loop* fails, not that lexing is
impossible.

## Honest limits

- Emission feasibility only; nothing compiled or run, so no claim about generated-binary correctness.
- One program shape, one seed build, one machine.
- A real lexer also needs `Str` production, which remains blocked (A3-043: `utf8_slice` is not a lowered
  builtin). Decomposition escaping the *control-flow* ceiling does not by itself give a working lexer.

## Scope guard

A3 owns only `verification/**`. No edits to A2's emitter. Cap unchanged.