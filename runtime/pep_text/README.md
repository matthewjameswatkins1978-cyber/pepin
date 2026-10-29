# Agent-4 native text runtime (`runtime/pep_text/`)

Minimal C23 primitives for the bytes Pep cannot express (raw storage,
allocation, byte access, `Str` concatenation), plus the Pep-side policy
models that pin their behavior. The OCaml seed checker and the
Pep-written emitter/parser remain the semantic authorities; nothing
here invents language semantics.

## Files

- `pep_textbuf.{h,c}` — growable byte builder: checked doubling growth,
  `append_bytes/cstr/i64/u64`, fragment join (`join` for C strings,
  `join_n` length-tagged, see INTEGRATION.md for the NUL contract),
  file read/write, sticky-error cleanup.
- `pep_textbuf_core.pep` — saturating-double step + self-test `main`,
  lowered through the Pep-written C23 emitter (282 bytes; the v2
  tool-host front end fits only ~450 bytes per invocation).
- `pep_textbuf_model.pep` — full policy (clamped growth, looping
  driver, `int_width` cascade), interpreter-executed.
- `pep_utf8.{h,c}` + `pep_utf8_{core,model}.pep` — validate/decode/
  encode transcribed from the lexer `utf8_error` model.
- `pep_span.{h,c}` — byte-column span locate + seed-form diagnostic
  render (`file:line:col: CODE: message` + excerpt + caret).
- `pep_json.{h,c}` — string escaping mirroring the seed `json_string`.
- `pep_jsonval.{h,c}` — explicit-shape JSON value writer (compact,
  no spaces, no DOM).
- `pep_num.{h,c}` + `pep_utf8_core.pep`-style coverage — signed
  decimal parse mirroring the tool-protocol Int format, round-trip
  half of `append_i64`.
- `pep_cstr.{h,c}` — C string-literal emission (unconditional `\?`,
  fixed 3-digit octal, no trigraphs or octal-merge hazards).
- `*_probe.c`, `demo_textbuf.c`, `utf8check.c` — test drivers and the
  first real tools on the library (probes print deterministic output;
  `utf8check FILE...` validates UTF-8).
- `INTEGRATION.md` — smallest Agent-2 handoff for the fragment join,
  including the NUL-fragment contract and the differential gate.
- `REVIEW_SLICE{3,6,9}.md` — cumulative review notes with openly
  logged gaps. `AGENT4_OUTBOX.md` — append-only coordination log.
- `SECURITY_2026-10-29_DEFENDER.md` — incident record (hold active).

## Build rules

Strict C23 everywhere: `-std=c23 -Wall -Wextra -Wpedantic -Werror`
on Clang 23.1.4 (MSVC target, primary) and GCC 16.2.0 (cross-check).
One exception, build-environment only: MSVC-target Clang deprecates
`fopen` under `-Werror`, so those builds add
`-D_CRT_SECURE_NO_WARNINGS`. The define silences only that vendor
diagnostic; probe drivers that never touch files build with the
identical flag set on both compilers.

Stdout is forced to binary mode (`_WIN32`-guarded `_setmode`) in
probes whose asserted output contains raw bytes (span excerpts with
`\r`, file round-trips); text-mode CRT translation would otherwise
corrupt byte-exact assertions. Library code never touches modes.

## Verification state

`tests/test_textbuf_native.py`: 19/19 green on both toolchains before
the 2026-10-29 security hold (byte-identical outputs, OCaml
differentials, compiler-oracle round-trips). While the hold stands:
no native builds, no execution, no new test runs. Source edits made
under the hold are syntax-checked only (`clang -fsyntax-only`,
`python -m py_compile`) and marked implemented-but-untested; the
suite must be re-run green before any further commit that depends
on behavior.
