# BOOT-A4-20261106-001 — compiler-source dependency frontier (slice 1)

SOURCE-READ at campaign `57fe424`, A2 `123d8b3`, A1 `1aaead7`. No native run
claimed; native execution is A2/A3's lane. Grades: ESTABLISHED = I ran it,
SOURCE-READ = I read the exact bytes, INFERRED = reasonable reading.

## 1. Canonical bundle (ESTABLISHED, `pep_c23.py:10-15` at `57fe424`)

Stage-0 SOURCES order: `examples/pep_lexer.pep` → `examples/pep_parser.pep`
→ `tests/pep_checker_a13.pep` → `tests/pep_c23_emitter.pep`. `emit()` opens the
4-file bundle in one session, registers `pep-c23-parser/parser_parse_program`,
`pep-c23-checker/analyze_parsed`, `pep-c23-emitter/emit_c23_checked`, then
invokes parse → check → emit with a host-authorised `semanticTarget`.

## 2. Static component census (SOURCE-READ, `57fe424`; emitter delta at `123d8b3`)

| Component | fns | types/records/unions | consumes | produces |
|---|---|---|---|---|
| lexer | 10 | 5 / 0 / 0 | SourceBytes (ambient `source_bytes()`) | LexCursor/LexProgress |
| parser | 80 | 12 / 1 (`AstValue`, 36-ctor union, ~243 uses per E1) | LexCursor/LexToken | ParserCursor/ParserChunk → List[FlatAstNode] |
| checker | 103 | 25 / 0 | List[FlatAstNode] | CheckerReport (functions/bindings/references/calls/expressionTypes/holes/diagnostics) |
| emitter@57fe424 | 13 | 2 / 0 | ParserProgress + CheckerReport | PepC23Emission |
| emitter@123d8b3 | 110 | — (A2 native verticals) | same | same + C runtime prelude |

Lexer fns: `ascii_letter/digit/continue`, `utf8_check`, `advance_position`
(K4-tested P1), `make_cursor/token/progress`, `lexer_start`, `lexer_step`.
Builtin surface used by lexer: `source_bytes`, `byte_at`, `byte_length`,
`utf8_slice`, `prepend`, `reverse`, `length` (+ `int_text` in emitter).

## 3. Cross-file call edges (SOURCE-READ, direct sites only)

- E1: `parser_stream(lexer_start())` (`pep_parser.pep`, single construction
  site) — the parser→lexer seam. No other parser construction of LexCursor.
- E2: `stream_fill` → `lexer_step(current.lexCursor)` — the only steady-state
  cross-file call; every token flows through it.
- E3: checker consumes ONLY `List[FlatAstNode]` (via `flatten_ast` output
  shape); no checker→lexer/parser call found (103 fns scanned for
  `lexer_step/flatten_ast/SourceBytes` — only type refs, zero calls).
- E4: `emit_c23()` → `emit_c23_checked(parsed, checked)` — the only
  full-pipeline Pep entrypoint (see §4). Emitter reads `FlatAstNode` fields
  plus node `startByte/endByte` spans; its interpreted-side self-use of
  `source_bytes()/byte_at/byte_length/utf8_slice` (e.g. string-literal span
  check at A2 `123d8b3`) runs under the seed session, not native.
- E5: `utf8_check(source, offset, length)` is lexer-internal; `lexer_step`
  re-fetches `let source = source_bytes()` locally (line 152) and threads it
  as a let-bound local — never as a function parameter.

## 4. Smallest complete entrypoint (INFERRED, falsifiable)

`emit_c23()` (zero-arg) is the ONLY function that performs all semantic phases
(parse→check→emit) in one Pep program (E2-B3, seed-executed). Every other
named entry (`parser_parse_program`, `analyze_parsed`, `emit_c23_checked`) is a
partial phase requiring host-supplied facts. Demonstrated shrinkage preserving
all phases: UNKNOWN — no smaller complete entrypoint has been shown; the
phase-split tools are composition, not shrinkage. Falsifier: a named Pep
program smaller than the 4-file bundle that still refuses invalid input with
identical diagnostics and emits identical C23.

## 5. Dynamic/unknown edges (explicitly NOT static)

D1 tool-protocol dispatch (`tool_register/invoke` by Str name) — D2 `match` on
the 36-ctor `AstValue` union (payload routing is data-dependent) — D3 recursion
(`parse_expression` depth, `quick_sort_nodes`) and `while` loops with mutable
state (`lexer_step` scan loop, ~4 nested whiles) — D4 ambient authorities
(`source_bytes()` grant, `byte_length` transport cap 65536 per E1). None of
D1–D4 is claimed as a static edge; staged-checker coverage must treat them as
opaque until A1/A3 measure otherwise.

Falsifier of THIS doc: any fn/type/call count above that does not reproduce via
the stated `Select-String` counts at the pinned SHAs, or a cross-file call site
I missed (name it with file:line).
