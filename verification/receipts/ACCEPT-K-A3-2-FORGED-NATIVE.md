# K-A3-2: a same-target forged callee fact reaches the emitter and is stopped by the C type system

**Date:** 2026-11-05 · **Mission:** LUCY-20261105-001 / Campaign K, A3 card K2 · **Evidence label:** `TESTED`
**PIN: A3 | `codex/bootstrap-agent3-verification` | A1 `727f8af` + A2 emitter `123d8b3` | clean**
**First next action:** K3 — independent A2 `123d8b3` prototype verification (normal + reverse order).

This closes the Campaign-H unknown I had explicitly left as INFERRED ("the assembled C path is probably fail-closed later … I did not drive unit emission from the forged report"). It is now measured.

## What was run (existing reachable API only)

Bundle = A1 lexer + parser + checker @ `727f8af` **plus** A2 emitter @ `123d8b3` — the seam probe's long-standing pin pair, i.e. a probe over an explicit source set, **not** an integration claim for either branch. Program (whole-source INVALID, oracle `invalid [PEP_TYPE_MISMATCH]`):

```pep
fn scale(v: Int) -> Int { return v * 2 }
fn main() -> Int { return scale("oops") }
```

Chain, all on one opened target:

1. `chunk_signatures` → honest facts for `scale` (`Int` parameter), stamped with the program's own document/revision.
2. Forged variant: parameter retyped `Str`, stamps untouched.
3. `analyze_chunk_typed` on the **caller chunk** → honest `invalid`, forged **`valid`** (K1 reproduced at K2).
4. `analyze_chunk_typed` on the **callee chunk** → `valid` (no external facts needed).
5. `emit_c23_section`/`emit_c23_function_unit` → header 4587 B, scale unit 160 B, main unit 184 B, epilogue 85 B; assembled 5016 B.
6. Strict `-std=c23 -Wall -Wextra -Wpedantic -Werror -O2` compile.

## Result: 7 claims, 7 held

| # | claim | verdict |
|---|---|---|
| 1 | honest facts keep the caller chunk invalid | **HELD** `invalid` |
| 2 | forged facts make the same caller chunk VALID | **HELD** `valid` |
| 3 | callee's own chunk valid without facts (emission prerequisite) | **HELD** `valid` |
| 4 | emitter still produces C from the forged-valid report | **HELD** all four parts emitted |
| 5 | emitted call site lowers the argument by AST, not by the forged fact | **HELD** `pep_str` present |
| 6 | Clang refuses the assembled C | **HELD** `error: passing 'pep_str' to parameter of incompatible type 'int64_t'` (forged.c:90:37) |
| 7 | GCC refuses the assembled C | **HELD** `error: incompatible type for argument 1 of 'pep_fn_scale'` (forged.c:90:46) |

Two mechanism readings recorded verbatim from the artefacts:

- prototype emitted from **parsed nodes**: `int64_t pep_fn_scale(int64_t pep_arg_1);`
- call site emitted from **AST argument kind**: the `"oops"` literal lowers to a `pep_str` compound literal.

So the emitter never consults the external fact to decide C types (`pep_c23_call_argument` reads `parsed.nodes`; the prototype loop walks `topLevelFunctions` from the AST). The forgery changes the *admission verdict* and nothing else.

## The honest shape of the residual

- **Contained, but by accident of layering, not by design.** Two components disagree: the checker trusts supplied facts, the emitter ignores them. Today the C type system is the thing that catches the mismatch. That is a fail-closed outcome, and it is **not** a checker guarantee. If the emitter ever derived prototypes or argument types from checked facts — a plausible future refactor, and exactly what a "facts are authoritative" architecture would do — this becomes a silent miscompile instead of a compile error.
- **The admission decision is still wrong.** The pipeline reports `valid` for a program the seed rejects. Downstream refusal does not retroactively make that verdict correct; it only means no binary escapes.
- **Duplicate rule bounds the attack surface.** My first attempt analysed the *whole* program and the forged fact was refused as `PEP_DUPLICATE_FUNCTION` — a fact for a function declared in the same chunk collides with that declaration. Laundering therefore requires the callee to be genuinely external to the chunk, i.e. the real chunked setting. Worth knowing: the duplicate rule (G-A1-1) already removes the "same-chunk" variant.
- **Threat model unchanged from K1:** not reachable through `chunk_signatures`; reachable by any host that can send a hand-built `tool_invoke`.

## Reproduce

```powershell
git show 123d8b3:tests/pep_c23_emitter.pep > _build\em-123d8b3.pep
python -X utf8 verification\probes\forged_to_native_k2.py D:\Projects\wt-a3-a1-727f8af _build\em-123d8b3.pep
# 7 claims, 7 held; Clang and GCC both refuse forged.c
```

Toolchain: Clang 23.1.4 (x86_64-pc-windows-msvc), GCC 16.2.0 (MinGW), OCaml 5.5.2 seed via `pep.ps1`. Probe artefacts under `_build/a3-k2/` in the A1 worktree (ignored, disposable). No peer file edited; A1 worktree read-only apart from its own ignored `_build`.

## Limits

- One program, one forged axis (parameter type). Return-type forgery is the same code path; not re-measured.
- Emission used the section/unit tools, not a full Candidate7 assembly; `header` came from the callee chunk, so this is not a claim that the seam as a whole is integrated.
- `NOT VERIFIED`: whether a forged *return* type could reach a compiling call site where the C types happen to agree (e.g. `Int`→`Int` arity-only forgery). That is the next falsifier to try, not a finding.

## Signal v0.1 handoff to A1 (K8, handoff 2 of 2)

```text
PIN: A3 | codex/bootstrap-agent3-verification | 670395d (+this commit) | pushed+remote-verified | clean
RESULT: forged same-target callee fact => caller chunk VALID, emitter emits C, strict Clang AND GCC refuse (pep_str to int64_t). Laundering cannot produce a binary today; containment comes from the emitter reading AST, not facts. TESTED.
REPRO: python verification\probes\forged_to_native_k2.py D:\Projects\wt-a3-a1-727f8af _build\em-123d8b3.pep
FALSIFIER: any emitter path that derives prototypes/argument types from checked facts makes this a silent miscompile; try a forged arity or Int->Int return forgery next.
NEEDS: A1 — treat "emitter ignores facts" as load-bearing and protect it, or bind fact content; do not let a refactor move C typing onto facts.
```
