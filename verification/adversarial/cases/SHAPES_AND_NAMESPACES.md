# Shapes and namespaces (V0 set 21)

All observations via `pep.ps1 check/run` from base `805062b` (OCaml
seed, interpreter only).

| probe | observed |
|---|---|
| `match true { true => 1 false => 0 }` | `TESTED` — `invalid`, `PEP_MATCH_NON_UNION` (matches are for tagged unions only; `Bool` is not matchable, consistent with set 5's `match 1` case) |
| `if true { 1 } else { \"s\" }` (expression, mismatched branches) | `TESTED` — `invalid`, `PEP_TYPE_MISMATCH` (branches must share a type) |
| `type E { }` (empty record declaration) | `TESTED` — `valid`. Empty nominal records are accepted by the seed checker (A2's emitter separately requires non-empty layouts — a builder-stated boundary, not re-tested here) |
| `fn Point()` alongside `type Point { x: Int }` | `TESTED` — `valid`: function and type/constructor namespaces coexist with the same name |
| `Point()` call with both present | `TESTED` — prints `1`: the call resolves to the *function*, not a record construction. Calls and constructor namespaces are distinct; no ambiguity error. Consistent with the checker's resolve-functions-before-constructors rule |

No findings. Match subjects stay union-only; branches must agree;
empty records are allowed; same-name functions and types coexist with
call-position resolution to the function. A13 parity and native
behavior stay `NOT_RUN`/`BLOCKED_SECURITY`.
