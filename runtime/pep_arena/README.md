# Agent-4 native AST arena (`runtime/pep_arena/`)

Explicit-lifetime, chunked, growable C23 allocation for one compilation
operation's temporary recursive data (AST nodes, node lists, scratch
trees). The arena owns BYTES only: tags, arities, child counts, types
and every semantic distinction stay with Pep and the checker. An arena
is neither a garbage collector nor a comment on memory policy — it is
one malloc-backed handle with explicit init and whole-arena cleanup.

## API (`pep_arena.h`)

- `pep_arena_init(&arena, chunk_hint)` — 0 for the default 4 KiB
  first chunk; larger hints only tune growth, never correctness.
- `pep_arena_alloc(arena, size, align)` — checked size, power-of-two
  alignment required (`size != 0`, `align != 0`). Returns NULL on any
  failure and records a sticky error; callers MUST null-check.
- `pep_arena_status(arena)` — `OK` / `ALLOC` / `OVERFLOW` / `BADARG`
  (component-local codes, same convention as `pep_textbuf`).
- `pep_arena_free(&arena)` — releases every chunk and nulls the
  caller's handle. Safe on NULL, safe twice.

Growth: each fresh chunk at least doubles the previous target
(saturating, overflow-checked); chunks are never moved or
reallocated, so every returned pointer stays valid until the
single `free`. Threading: none — one arena per compilation unit.

## Example (`arena_demo.c`)

Builds `Add(Int 19, Int 23)` plus nested `Add(Int 1, Add(Int 2,
Int 3))` from arena-allocated linked nodes, evaluates both
(`42`, `6`), and frees everything with one call. A deliberately
small first chunk forces multiple chunks, so pointer stability
across growth is exercised rather than asserted.

## Verification state

Built and executed in the 2026-10-29 post-hold re-run.
`tests/test_textbuf_native.py::test_arena_demo_builds_and_runs` compiles the demo
with Clang 23.1.4 and GCC 16.2.0 and runs it. The Clang build prints `42` then
`6`, so the post-hold gate stated here previously is met in substance.

One test defect remains and it is not an arena bug: the assertions at
`tests/test_textbuf_native.py:777,783` expect `b"42\n6\n"` while the Windows CRT
translates the demo `\n` to `\r\n` on stdout, so Clang fails on the CRLF
mismatch and the GCC half never runs. Fix the expectation or write through a
binary handle; do not normalise away the byte-exact comparison.
