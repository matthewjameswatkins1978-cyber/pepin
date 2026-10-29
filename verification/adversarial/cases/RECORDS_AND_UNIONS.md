# Records and tagged unions (V0 set 5 — DEC-004/005 surface)

All observations via `pep.ps1 check/run` from base `805062b` (OCaml
seed, interpreter only). Header used below:
`type Point { x: Int y: Int }` and
`type Expr = Number(Int) | Add(Expr, Expr)`.

## Positives (run, both print as specified)

| probe | source shape | observed |
|---|---|---|
| field-access | `Point { x: 1, y: 2 }.x` via `say` | `TESTED` PASS — prints `1` |
| match-eval | `match Number(5) { Number(v) => v Add(l, r) => 0 }` | `TESTED` PASS — prints `5` |

## Negatives (check, all fail closed with precise codes)

| probe | source shape | observed |
|---|---|---|
| wrong-field | `Point { x: 1, z: 2 }` | `TESTED` — `invalid`, `PEP_MISSING_FIELD` "Missing field 'y'" at the constructor span (offset 20). Note: the *missing* field is reported, not the unknown `z` — missing-field precedence over unknown-field at construction sites. |
| field-access-bad | `p.z` where `p: Point` | `TESTED` — `invalid`, `PEP_UNKNOWN_FIELD` "Record 'Point' has no field 'z'" at the access span. Construction vs projection use distinct codes (`MISSING` vs `UNKNOWN`) — precise. |
| nonexhaust | `match Number(1) { Number(v) => v }` | `TESTED` — `invalid`, `PEP_NON_EXHAUSTIVE_MATCH`, names missing constructor `Add` and requires an irrefutable arm. Actionable message. |
| dup-arm | two `Number` arms | `TESTED` — `invalid`, `PEP_DUPLICATE_MATCH_ARM` at the second arm. |
| match-int | `match 1 { Number(v) => v }` | `TESTED` — `invalid`, `PEP_MATCH_NON_UNION` "subject type 'Int' is not a tagged union". |
| arity | `Number(1, 2)` | `TESTED` — `invalid`, `PEP_ARGUMENT_COUNT` "expects 1, found 2" (constructors share call-arity wording). |
| fwd-ref | `type Box { p: Point }` with `Point` undeclared | `TESTED` — `invalid`, `PEP_UNKNOWN_TYPE` at the reference span. Type names must be declared before use; no forward type references at this scope. |

## Position

No findings: every negative is rejected with a specific code and byte
span; positives evaluate as specified. This set covers the DEC-005
nominal-data surface the value-copy set did not. A13 differential
parity for these codes (Agent 1 owned) and native lowering (Agent 2
owned, unions unsupported per B0) stay `NOT_RUN`/`BLOCKED_SECURITY`.
Precedence note (missing-vs-unknown field) and the no-forward-types
observation are recorded as behavior, not defects.
