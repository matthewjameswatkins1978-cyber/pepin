# Calls and scope (V0 set 7)

All observations via `pep.ps1 check` from base `805062b` (OCaml seed,
interpreter only; static layer — no execution needed).

| probe | source shape | observed |
|---|---|---|
| unknown-fn | `return nosuchfn()` | `TESTED` — `invalid`, `PEP_UNKNOWN_FUNCTION` (distinct from `PEP_UNKNOWN_VARIABLE` for value names) |
| arity-many | `one(1, 2)` for 0-param `one` | `TESTED` — `invalid`, `PEP_ARGUMENT_COUNT` |
| arity-few | `two(1)` for 2-param `two` | `TESTED` — `invalid`, `PEP_ARGUMENT_COUNT` (both directions, one code) |
| dup-fn | two `fn f` definitions | `TESTED` — `invalid`, `PEP_DUPLICATE_FUNCTION` |
| dup-let | two top-level `let x` | `TESTED` — `invalid`, `PEP_DUPLICATE_BINDING` (bindings have their own duplicate code, distinct from functions) |
| top-return | `return 1` at top level | `TESTED` — `invalid`, `PEP_RETURN_OUTSIDE_FUNCTION` (entry form is statements, but `return` is still function-scoped) |
| say-int | `say(42)` | `TESTED` — `invalid`, `PEP_TYPE_MISMATCH` (no implicit Int→Str) |
| arg-type | `id(true)` for `(Int) -> Int` | `TESTED` — `invalid`, `PEP_TYPE_MISMATCH` at the argument span |

No findings: every malformed call/scope shape is rejected statically
with a dedicated code before any execution. Together with S2
(first-error priority), this pins the checker's fail-closed call
boundary at the seed layer. A13 parity and native behavior stay
`NOT_RUN`/`BLOCKED_SECURITY`.
