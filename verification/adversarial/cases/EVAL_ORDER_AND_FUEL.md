# Evaluation order, errors, holes, fuel (V0 set 4)

All observations via `pep.ps1 check/run/query` from base `805062b`
(OCaml seed, interpreter only).

## S1 — short-circuit order pinned: left-first, right skipped

```pep
say(int_text(if true || (1 / 0 == 0) { 1 } else { 2 }))   // → 1, rc 0
say(int_text(if (1 / 0 == 0) || true { 1 } else { 2 }))   // → 1:18 PEP_RUNTIME_DIVISION_BY_ZERO, rc 1
```

| oracle | result |
|---|---|
| SPEC (seed: short-circuit Boolean operators) | left evaluated first; right skipped when decided |
| OCAML | `TESTED` PASS — trap on the skipped side never fires; trap on the evaluated side reports with byte span. `&&` behaves symmetrically per the shipped example (`false && (1/0==0)` → 42). |

## S2 — first-error priority (single diagnostic)

```pep
fn main() -> Int { return Nope1 + Nope2 }
```

| oracle | result |
|---|---|
| SPEC (seed facts) | checker reports the first invalid-program error, not all |
| OCAML | `TESTED` — `invalid`, exactly one diagnostic: `PEP_UNKNOWN_VARIABLE` at bytes 26–27 (`Nope1`). `Nope2` never reported. Consumers must fix-and-recheck iteratively. |

## S3 — arm-local hole exposes precise scope, type and bindings

```pep
type Expr = Number(Int) | Add(Expr, Expr)
fn ev(e: Expr) -> Int {
 return match e {
 Number(v) => v
 Add(l, r) => ?calc
 }
}
fn main() -> Int { return 0 }
```

`query --holes --json` → `TESTED` PASS: one hole, identity `calc`,
scope `ev`, `expectedType: Int`, bindings `l: Expr, r: Expr, e: Expr`
(arm-locals plus parameter), span bytes 114–119, status `incomplete`.
Matches the A4 arm-local typed-hole contract at the query layer.

## S4 — interpreter fuel exhaustion is a controlled diagnostic

`while x != N { x = x + 1 }` with observable `say(int_text(count()))`:

| N | result |
|---|---|
| 100,000 | `TESTED` PASS — prints `100000`, rc 0 |
| 1,000,000 / 5,000,000 | `TESTED` PASS — `3:8: PEP_RUNTIME_STEP_LIMIT: Execution step budget exceeded`, rc 1, span at the loop condition |

Fuel exhaustion is fail-closed with a byte span, like arithmetic faults
(N4). Note: `<` is not in the seed operator set (`PEP_UNEXPECTED_CHARACTER`
at the `<`); bounds must be written with `!=`/`==`.

## E1b — entry-point divergence between backends (QUESTION, not defect)

```pep
fn main() -> Unit { say("from-main") }
```

| oracle | result |
|---|---|
| observed | `TESTED` — `run` exits 0 silently. The interpreter executes **top-level statements only** (cf. `examples/hello.pep` = one top-level `say`); `fn main` is never invoked. By contrast the C23 lane compiles `fn main() -> Int` as the native entry (`run-c23` executes it). |
| status | No doc states `run` must call `main`, and the final draft allows top-level statements "in selected entry source" — so no defect is claimed. But this is an observable interpreter/native divergence that self-hosting must resolve explicitly: a Pep-written compiler compiled by either backend must agree on what a program's entry is. Filed as bridge question Q1 for Agent 1/2 (see outbox). Supersedes the weaker E1 note in `NEGATIVE_AND_EDGE.md` (which framed it as an unobserved return value). |

## S5 — call-depth budget is independent of the step budget

`fn down(n: Int) -> Int { if n == 0 { return 0 } else { } return down(n - 1) }`:

| probe | observed |
|---|---|
| `down(100)` via `say` | `TESTED` PASS — prints `0`, rc 0 |
| `down(100000)`, self-recursive | `TESTED` — rc 1, `PEP_RUNTIME_CALL_DEPTH` ("Maximum function call depth exceeded") with span, returned fast (depth trips long before the 1M-step budget) |
| mutual `a↔b` at 100000 | `TESTED` — same `PEP_RUNTIME_CALL_DEPTH` with span |

Depth and steps are separately policed budgets with distinct codes
(`PEP_RUNTIME_CALL_DEPTH` vs `PEP_RUNTIME_STEP_LIMIT`), both with byte
spans and nonzero exit. No runaway recursion is possible, silent or otherwise.

## Coverage boundary

Interpreter layer only. Short-circuit/fuel/error-priority through the
staged Pep checker/emitter path stay `NOT_RUN`/`BLOCKED_SECURITY`.
