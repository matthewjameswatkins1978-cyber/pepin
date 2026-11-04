# H-V2: real compiler-owned functions — one runs, one is blocked at a measured step-budget line

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-015 / Campaign H, Workstream V2 · **Evidence label:** `TESTED`
**PIN:** A3 `codex/bootstrap-agent3-verification@2863fd8` (+this commit) · clean · tested A2 `58fc9bf` (A1 pin `2ad750b` seed)
**First next action:** A1 owns the budget (Q1 instrumentation); A2 owns the literal-argument refusal. Nothing for A3 to fix.

Two real Pep-written compiler functions, both extracted **verbatim** with a byte-equality assertion against the checkout:

| function | source | extracted sha256 | checkout match |
|---|---|---|---|
| `lex_error_code(kind: Str, diagnostic: Str) -> Str` | `stdlib/scan.pep:730-741` | `49cd62ce3d6e04911537aa584c34ba148a5c8045590190e04b77da8aebe8774a` | **True** |
| `advance_position(line: Int, column: Int, byte: Int) -> SourcePosition` | `examples/pep_lexer.pep:90-94` | `f09b7106d34890c10ee7f23e6b193c8a9f784b304535259a5787fd39be3c5f89` | **True** |
| `type SourcePosition { line: Int, column: Int }` | `examples/pep_lexer.pep:1` | `6fa28d1075706977883ce0f6bd42b7156634a80c93c315d569bc9ede4ac9fdc7` | **True** |

## Result A — `advance_position` RUNS natively, record return included (6/6 parity)

Three source-grounded vectors; the returned record is collapsed to one Int in `main` so the oracle is numeric (the emitter refuses `say(int_text(..))`, measured separately):

| byte | (line, column) | expected | seed | Clang 23.1.4 | GCC 16.2.0 |
|---|---|---|---|---|---|
| 10 (`\n`) | (3, 7) | 401 | 401 | **401** | **401** |
| 65 (`A`) | (3, 7) | 308 | 308 | **308** | **308** |
| 10 (`\n`) | (0, 1) | 101 | 101 | **101** | **101** |

The `if/else` expression with record constructors on both arms and Int arithmetic inside the returned record is a genuine compiler-owned shape that survives the native path at this revision.

## Result B — the real `lex_error_code` is NOT runnable; boundary measured at rung 3 of 5

Emitting the verbatim five-guard function is refused:

```
check parsed source -> outcome=error
error: PEP_RUNTIME_STEP_LIMIT  "Execution step budget exceeded at 2451:8"
```

Layer: the **checker tool invocation** (`check parsed source`), code `PEP_RUNTIME_STEP_LIMIT`. A2's own test comment calls this the PARSER step budget; the refusal I observe arrives from the checker stage of `pep_c23.emit`, and `2451:8` is a step-counter locus, not a source line of the checkout. Recorded exactly as observed; BUILDER calls it parse-stage, A3 measures it at the checker stage — same code, same position.

**Guard ladder (`verification/probes/lex_error_code_ladder.py`)** — rungs are PREFIX subsets of the real guards in source order plus the always-present fallthrough, two argument shapes:

| guards | Str result (record-field args) | Int result (same guards) |
|---|---|---|
| 1 | EMITTED, native `PEP_LEXER_INPUT` | — |
| 2 | **EMITTED, native `PEP_INT_LITERAL_RANGE`** (= A2's pinned slice) | EMITTED, exit 2 |
| 3 | **REFUSED** EMITTER `PEP_RUNTIME_STEP_LIMIT` @5471:5 | EMITTED, exit 2 |
| 4 | REFUSED (nested variant: CHECKER @2451:8) | — |
| 5 | **REFUSED** CHECKER `PEP_RUNTIME_STEP_LIMIT` @2451:8 | REFUSED CHECKER @2933:32 |

**The discriminator is the result type, not the guard count**: with identical guard shapes, a `Str`-returning chain crosses the budget at 3 guards while an `Int`-returning chain still emits at 3 and only fails at 5. `Str` result is measurably more expensive per guard than `Int` at this revision. Nesting is *not* the trigger: a flat five-guard `Str` variant is refused at the same `2451:8`, and a nested 3-guard variant with one inner guard is also refused.

## Result C — 14-vector discriminating matrix, honestly labelled

`verification/probes/lex_error_code_matrix.py`. The seed runs the **real** function; the native side runs the largest emittable prefix (2 guards). Both use the source's own call shape — record fields, as at `scan.pep:845`.

- **10 vectors PARITY on the runnable prefix**: `unexpected`→`PEP_UNEXPECTED_CHARACTER` (×3), `integer`→`PEP_INT_LITERAL_RANGE` (×3), `bogus`/empty→`PEP_LEXER_INPUT` (×4), with both the two exact `scan_string_at` diagnostics and unrelated ones as distractors.
- **4 vectors UNAVAILABLE — the whole `kind == "string"` branch**: seed returns `PEP_NEWLINE_IN_STRING` / `PEP_INVALID_ESCAPE` / `PEP_UNTERMINATED_STRING` (newline-message, escape-message, other-diagnostic, empty-diagnostic); nothing native exists to compare against, because the real function is refused outright.

These four rows are **not** native misbehaviour — the emitter never ran. The prefix is the largest emittable share of the function, and it cannot stand in for the string branch. Stated this way so no reader converts "prefix returns PEP_LEXER_INPUT" into a false bug.

## Result D — emitter asymmetry worth a builder decision (A2's lane, no repair attempted)

Calling the same two-parameter `Str` function with **literal** arguments is refused:

```
Pep C23 rejects two fallible call arguments because C argument evaluation order is unspecified
```

while **record-field** arguments to the identical function emit fine. The source's only call site passes record fields, so this refusal never fires on real compiler code — but as a language surface it means `f("a", "b")` is rejected where `f(x.kind, x.diagnostic)` is accepted, and the message attributes it to evaluation order rather than to literal-ness. Fail-closed, no unsoundness; reported as a shape inconsistency, not a bug claim.

## Admitted unknowns / limits

- Only two functions inspected, deliberately (A4 owns the broad census). Both are *excerpts in isolation*: `lex_error_code`'s real neighbours (`lex_token`, `scan_string_at`) and `advance_position`'s caller (`make_cursor`) are not present, so no claim is made that "the compiler function runs in its real translation unit".
- `utf8_check` and the `ascii_*` predicates were considered and rejected as second functions: `ascii_digit` was already pinned in Campaign G, `utf8_check` needs `SourceBytes` + `while` + `var`, which is a different investigation.
- No A1/A2/spec/frozen-gate/budget/master/CURRENT change by A3; `verification/**` only.

## Reproduce

```powershell
python -X utf8 verification\probes\advance_position_real.py  D:\Projects\wt-a3-h1-cold
python -X utf8 verification\probes\lex_error_code_real.py    D:\Projects\wt-a3-h1-cold
python -X utf8 verification\probes\lex_error_code_ladder.py  D:\Projects\wt-a3-h1-cold
python -X utf8 verification\probes\lex_error_code_matrix.py  D:\Projects\wt-a3-h1-cold
```
