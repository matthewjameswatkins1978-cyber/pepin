# Agent-4 review checkpoint: slices 1–3 (cumulative materials)

Date: 2026-10-29. Reviewer: none available in this worker session
(logged per campaign rule; no self-certification claimed). Integrator
and sibling agents are invited to append findings below.

## Scope under review

Isolated directory `runtime/pep_text/` plus `tests/test_textbuf_native.py`.
No edits to checker, emitter, testing, packets, or master at any point.

- Slice 1 (`7039965` + outbox `9dffe51`): growable text/byte builder.
  Pep capacity model (emitter-verified 282-byte core + interpreter-executed
  full model), C23 `pep_textbuf`, standalone demo, Agent-2 join note.
- Slice 2 (`5c395a5`): UTF-8 validate/decode/encode transcribed from the
  Pep lexer `utf8_error`, 31-vector probe, Pep classifier mirror,
  emitter-verified core, plus proof that slice-1 builder output compiles
  under Clang/GCC and runs (prints 13).
- Slice 3 (this commit): span locate + diagnostic render
  (`pep_span.h/.c`), `span_probe`, hand-computed excerpt/caret blocks and
  OCaml-`inspect` differential over every AST span of LF/CRLF/UTF-8
  programs.

## Evidence (all re-run green at each ship)

- `python -m unittest tests.test_textbuf_native`: 11/11 OK.
- Pep side: `check` valid on all four `.pep` models; `run` prints exact
  predicted values (14 capacity, 20 UTF-8 classifier).
- Emitter path: 282-byte core and 235-byte UTF-8 core lower through the
  Pep-written C23 emitter; built exes print `0`.
- Native: Clang 23.1.4 (MSVC target) and GCC 16.2.0, strict C23 warnings
  as errors; all tool outputs byte-identical across toolchains.

## Adversarial notes (builder's own — not independent review)

1. Off-by-one class found by execution, twice: the `!(K <= x)` Pep idiom
   means `x < K`, so inclusive bounds need K = bound + 1. The C table was
   already exact; the Pep mirror is now exact too.
2. A wrong test expectation (42 vs 13) was caught because the test
   executes the generated program instead of comparing text. Kept as
   evidence that execution beats narration.
3. Windows text-mode stdout translates `\n` to `\r\n`, which corrupts
   byte-exact excerpt assertions. The probe now sets binary stdout
   (`_WIN32`-guarded, driver-only) and the test captures bytes. The
   runtime library itself does no mode or I/O handling beyond `fwrite`
   to an already-open stream.
4. MSVC-target Clang rejects `fopen` under `-Werror` (deprecation).
   Scoped `-D_CRT_SECURE_NO_WARNINGS` applies to the probe driver build
   only; every library file builds warning-clean under identical strict
   flags on both compilers.

## Known gaps (not hidden)

- Null-argument (`BADARG`) paths in the C library have no execution
  coverage; only valid-input and overflow/truncation paths are probed.
  Proposed slice-4 micro-item, not a silent pass.
- Tool-path envelope: v2 front-end invocations fit roughly 450 bytes of
  dense Pep; larger models are interpreter-verified only. Suspected
  quadratic parser buffer, offered to sibling agents as an unconfirmed
  lead — no sibling code touched or diagnosed further.
- Columns are byte columns (matches both span authorities today); a
  future character-column upgrade keeps the call shape.
- The Python `"".join` remains the production join; the native join is
  implemented and probed but unwired pending Agent 2's differential
  gate. No second semantic authority introduced.

## Open questions for others (no response blocks Agent 4)

- Agent 2: confirm/amend `pep_textbuf_join` and `emit_c23_joined`.
- Agent 1/3: the ~450-byte tool-path envelope measurement and the
  parser-buffer lead; the stash-preserved differential-assertion delta
  from slice 1 still awaits its owner.
