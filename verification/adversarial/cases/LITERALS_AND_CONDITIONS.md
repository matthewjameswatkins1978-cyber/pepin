# Literals, escapes and conditions (V0 set 6)

All observations via `pep.ps1 check/run` from base `805062b` (OCaml
seed, interpreter only). Complements the fuel/order sets with
lexical and checked-arithmetic edges.

## String escapes

| probe | source bytes | observed |
|---|---|---|
| `esc-n` | `say("a\nb")` | `TESTED` PASS — prints `a<newline>b`; `\n` supported |
| `esc-quote` | `say("a\"b")` | `TESTED` PASS — prints `a"b`; `\"` supported |
| `esc-bad` | `say("a\qb")` | `TESTED` — `run` fails closed: `PEP_INVALID_ESCAPE` ("Unsupported string ...") at the literal span, nonzero exit. No silent passthrough of unknown escapes. |

## Checked Int64 boundaries (DEC-005: checked signed 64-bit)

| probe | observed |
|---|---|
| `int-max` (`9223372036854775807`) | `TESTED` PASS — prints as-is |
| `int-over` (literal `9223372036854775808`) | `TESTED` — `check` reports `invalid`, `PEP_INT_LITERAL_RANGE` (static, no execution) |
| `add-overflow` (`max + 1` via `say`) | `TESTED` — `1:14: PEP_RUNTIME_OVERFLOW: Integer addition overflow`, rc 1, byte span |
| `to-min` (`0 - max - 1`) | `TESTED` PASS — prints `-9223372036854775808` (min representable; no wrap) |
| unary minus (`say(int_text(-1))`) | `TESTED` PASS — prints `-1` |

Static range rejection for literals, controlled traps for runtime
overflow, exact min representable — the checked-arithmetic contract
holds on both layers. (Earlier `E1`-style `return -1` in `fn main`
probes are vacuous: `run` never invokes `main` — see E1b.)

## Condition positions

| probe | observed |
|---|---|
| `while 1 { }` | `TESTED` — `invalid`, `PEP_TYPE_MISMATCH` (conditions are Bool-only) |
| `for x in 5 { }` | `TESTED` — `invalid`, dedicated `PEP_FOR_REQUIRES_LIST` |
| `if true { say("s") }` (no else) | `TESTED` — rejected at parse: `PEP_PARSE_ELSE` "Expected else after if" |
| `if true { say("s") } else { }` | `TESTED` PASS — prints `s` |

## G1 (design gap, not a defect)

The accepted final draft (§2) states an `if` *statement* can omit
`else`, but the current seed requires `else` even for statement
position (empty `else { }` accepted). Same class as N2 (`edit`
absent): accepted design earmarked, seed grammar narrower. No defect
claimed; recorded so a future grammar change is differential-tested
rather than assumed.

## Status

No findings. A13 differential parity for these codes and any native
behavior stay `NOT_RUN`/`BLOCKED_SECURITY`.
