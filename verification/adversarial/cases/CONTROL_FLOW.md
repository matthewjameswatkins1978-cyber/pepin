# Control flow: for-in, loop exits, negation, wildcards (V0 set 8)

All observations via `pep.ps1 check/run` from base `805062b` (OCaml
seed, interpreter only).

## for-in over lists: correct, including empty and nested

| probe | observed |
|---|---|
| sum `[1,2,3]` with `var total` accumulator | `TESTED` PASS — prints `6` |
| empty annotated list (`let e: List[Int] = []`), non-entering binding | `TESTED` PASS — prints initial `99`; zero-iteration loops are no-ops |
| nested `for row ... for v in row` over `[[1],[2,3]]` | `TESTED` PASS — prints `6` |
| bare `[]` as iterable | `TESTED` — `PEP_EMPTY_LIST_NEEDS_TYPE` (consistent with A6 contextual-empty-list rule; annotation required) |

(`let` accumulators inside loop bodies correctly fail with
`PEP_ASSIGN_IMMUTABLE` — first probe authoring error, retained as a
reminder that only `var` rebinds.)

## break / continue: absent from the seed surface

`break` / `continue` in a `while` body (and `break` in a function
outside any loop) are rejected with the generic
`PEP_UNKNOWN_VARIABLE` (`TESTED`, check layer) — they are not keywords
and there is no dedicated loop-exit diagnostic. No loop-control exits
exist in this seed; `while` loops terminate by condition only
(S4 probed the fuel consequence). Recorded as behavior, not a defect.

## Negation and wildcard arms

| probe | observed |
|---|---|
| `if !true {1} else {2}` | `TESTED` PASS — prints `2` |
| `match B() { A(v) => v _ => 7 }` | `TESTED` PASS — prints `7` |
| `_`-only arm over `A(5)` | `TESTED` PASS — prints `0` |

## Nullary constructors require parens everywhere

`type E = A(Int) | B` (bare `B`) is a **parse** error
(`PEP_PARSE_EXPECTED` "Expected '('"), reported at the following line
start (offset 21 = line 2 col 1 for a one-line declaration), not at the
`B`. With parens — `type E = A(Int) | B()` — declaration, pattern
`B()` and value `B()` all work. Bare `B` is never a constructor
reference in this seed. (Consistent with Agent 1's "matchable as `B()`"
correction; the declaration side follows the same rule.)

## Status

No findings. One behavior note (no loop-exit keywords / generic
diagnostic) and one syntax rule (parens-required nullaries with
next-line error position) recorded. A13 parity and native behavior
stay `NOT_RUN`/`BLOCKED_SECURITY`.
