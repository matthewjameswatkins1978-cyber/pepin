# Declaration edges: nesting, duplicates, shadowing (V0 set 19)

All observations via `pep.ps1 check/run` from base `805062b` (OCaml
seed). Same fail-closed family as set 7 (CALL_AND_SCOPE), one level
deeper: what the declaration layer permits and how names resolve.

## Shapes rejected with dedicated codes

| probe | observed |
|---|---|
| nested `fn` inside a function body | `TESTED` — `invalid`, `PEP_PARSE_EXPRESSION` (no nested function definitions; functions are top-level only) |
| `if 1 {...} else {...}` | `TESTED` — `invalid`, `PEP_TYPE_MISMATCH` (conditions are Bool-only, same as `while`) |
| `P { x: 1, x: 2 }` | `TESTED` — `invalid`, dedicated `PEP_DUPLICATE_FIELD` |
| `Number("x")` for `Number(Int)` | `TESTED` — `invalid`, `PEP_TYPE_MISMATCH` at the construction site (fail-closed before any match runs) |
| two `fn main` definitions | `TESTED` — `invalid`, plain `PEP_DUPLICATE_FUNCTION` (no special-cased main; entry-ness does not exempt the duplicate rule) |

## Builtin-name parameters are allowed — and resolve by position

`fn f(say: Int) -> Int` checks `valid`: only top-level function
*definitions* collide with builtin names, not parameter bindings.
Resolution is then positional, TESTED at runtime:

- value position reads the binding: `f(41)` with body `return say`
  → prints `41`.
- call position still reaches the builtin: `f(1)` with body
  `say("x")` → prints `x` (no "cannot call Int" error).

So a parameter can shadow a builtin *name* without capturing its
*call* meaning — calls resolve to builtins, names to bindings. No
defect claimed (consistent, documented here as observed semantics);
worth knowing before anyone tightens the reserved-name rule to cover
parameters, which would be a breaking change for no tested benefit.

## Status

No findings. All malformed declarations fail closed with dedicated
codes; the one permitted overlap (builtin-named parameters) behaves
coherently by position. A13 parity and native behavior stay
`NOT_RUN`/`BLOCKED_SECURITY`.
