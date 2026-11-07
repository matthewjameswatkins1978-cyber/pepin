# PRE-REGISTRATION A3-043: does a user-function wrapper make the builtin call emittable?

**Seat:** A3, mission LUCY-20261107-012. Follows BOOT-A3-042. **Written before measurement.**

## The question

BOOT-A3-042 found a builtin call (`utf8_slice`) cannot be bound in a declaration initialiser because
the chunk report carries **no resolved-call fact** for it. A user function *does* produce facts. So:
if the builtin call is wrapped in a user function, does the program become emittable end to end?

```pep
fn slice3(source: SourceBytes) -> Str { return utf8_slice(source, 0, 3) }
fn main(source: SourceBytes) -> Int {
  let part = slice3(source)      // user-function call in an initialiser -> fact should exist
  say("#include <stdio.h>") ...  say(part) ...
  return 0
}
```

## Predictions

| # | Claim | Falsified if |
|---|---|---|
| W1 | `main`'s chunk emits: a **user-function** call in a `let` initialiser has a resolved fact | that chunk refuses for a missing call fact |
| W2 | `slice3`'s chunk **refuses**: `return utf8_slice(...)` is a builtin call in return position, and BOOT-A3-042 measured that the report mints no fact for builtins | `slice3` emits |
| W3 | therefore the whole program still cannot produce input-dependent C | the divergence chain completes |
| W4 | if W2 is wrong, input-dependent C **is** demonstrable today, and I will report that as the better outcome and retract the "seam blocks declarations" framing | — |

**The falsifier for my own position is W2.** I expect the wrapper to move the failure, not remove it:
the builtin call site simply relocates from a `let` initialiser into a `return`, and both are sites the
emitter supports *provided a fact exists*.

## Why it still matters either way

- If W2 holds, the seam is specifically "**builtin calls get no facts anywhere**", which makes the fix a
  single decision (mint facts for builtins, or let the emitter lower known builtins factlessly) rather
  than a per-site patch — a sharper, cheaper target for A1/A2.
- If W2 fails, the floor capability exists now and route S becomes immediate.

## Method

Same chunked pipeline as BOOT-A3-042, generalised to N functions: parse, chunk each function with the
others supplied as external facts, check all, then emit units and the grant epilogue. Per-function
status is reported **before** any emission, so a later failure cannot hide which chunk broke. If every
chunk emits, the full divergence chain runs: generator → two unseen inputs → differ → both compile under
strict Clang **and** GCC → run to different outputs.

## Scope guard

A3 owns only `verification/**`. No edits to A1's checker/contract, A2's emitter, A4's app. Cap unchanged.