# Bridge Q1 + staged-path fuel mapping (V2 scoping, Agent 3)

**Reviewed pin:** `codex/bootstrap-agent2-b0@62885b8` (record
params/returns tip). Read-only detached worktree (since removed). All
probes call `pep_c23.emit(bytes)` in-process: staged Pep
lexer→parser→checker→emitter executed by the OCaml interpreter, C text
inspected in memory. **No C compiler invoked, no binaries produced.**
No Agent 2 files modified.

## Q1 sharpened: the backends execute disjoint parts of one program

| program | interpreter `run` | staged `emit` |
|---|---|---|
| `say("hi")` only | executes (`hi`) | REJECTED: `Pep C23 emission requires a top-level function named main` |
| `fn main() -> Int { return 42 }` only | silently ignores (exit 0) | EMITTED, 1529 chars (matches A2's reported figure) |
| `fn main() -> Int { return 1 }` + `say("side")` | executes `say`, ignores `main` | EMITTED, 1528 chars — **top-level `say` silently dropped** (one char less than the 42-program: no trace of `side`) |
| empty | nothing to run (exit 0) | REJECTED: same main-required diagnostic |

The emitter's own validation vector already encodes the main
requirement (`pep_c23.py`: expected `unsupported` record for the empty
program), so the requirement is specified behaviour, not a bug. But
the combination is now evidenced end-to-end: for a mixed program, the
interpreter runs exactly the part the emitter discards, and the emitter
emits exactly the part the interpreter ignores. A self-hosted compiler
must produce identical observable behaviour regardless of which backend
built it — today it cannot for this program shape. Filed as bridge
FINDING F1 (observation; entry-point decision owned by Agent 1/2 +
Matthew — no verdict on which side moves).

## Staged-path fuel mapping (tool budget vs file check)

Same 613-byte program (20 trivial `fn fN() -> Int` + `main`):

| stage | result |
|---|---|
| file-based `pep.ps1 check` (OCaml parser+checker) | `valid`, no diagnostics |
| staged `emit` (Pep-written parser as v2 tool) | `PEP_RUNTIME_STEP_LIMIT` ("Execution step budget exceeded at 395:59"), `parse_count: 3`, after ~0.7s |

The failure is at the **parser tool invocation** under the 100,000-step
per-tool-call ceiling — the self-hosted parser path, not the 1M-step
interpreter budget and not the 65,536-byte transport cap. Current
headroom at this SHA: 5 trivial functions emit fine (2,189 chars);
20 trivial functions exhaust the staged parser. This quantifies the
self-hosting gap Agent 1/2 already track (their 154:6 report on larger
sources): parser efficiency, not input size, is the binding constraint
at this scale. No verdict on whose lane fixes it; recorded as bridge
input F2.

## Addendum (file-path breadth scaling, 2026-10-29)

To locate the F2 cliff precisely, the same trivial-function programs were run through the file-based OCaml `check` (10/50/100/200/400 functions): all `valid`, wall time flat at ~0.5s (startup-dominated). The binding constraint is therefore the **staged Pep-parser tool invocation** (100k-step budget), not file breadth through the native checker at this shape. Depth/complexity scaling (e.g. A1's `int_gcd` composition) was not probed here and remains A1's lane.

## Status

F1/F2 are TESTED observations at the emit layer with exact commands in
this file's provenance. Native compile/run of any emitted C stays
`BLOCKED_SECURITY`. No builder files touched; no acceptance claimed.
