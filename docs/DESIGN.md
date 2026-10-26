# Pep design and implementation status

This is the implementation-status index. The intended language vision is [Founding Design v0.3](FOUNDING_DESIGN_v0.3.md); the binding accepted technical decisions are in [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md). They describe the direction of the language and must not be read as a feature inventory.

## Implemented in the primary OCaml seed
The primary compiler is `pep_ocaml.ml`, invoked by the PowerShell 7 CLI `pep.ps1` and built with the project OCaml 5.5.2 switch. Current implemented behavior includes:

- Built-in scalar types `Int`, `Bool`, `Str`, and `Unit`, plus monomorphic named record and tagged-union types;
- annotated or inferred `let` bindings, typed functions, recursion and forward calls, lexical blocks, integer arithmetic, `<=`, `if … else …`, record construction and field access, variant construction, and `match` expressions with nested constructor and wildcard patterns;
- monomorphic built-ins `say(Str) -> Unit` and `int_text(Int) -> Str`;
- source-spanned ASTs, a separate checked tree, and an interpreter that runs only complete checked programs;
- named and anonymous holes, expected-type checking, visible-binding queries, deterministic fill suggestions, and arm-local typed holes in matches;
- `inspect`, `check`, `query`, `run`, and `describe --json`; and
- an in-process schema-v3 `session --jsonl` with immutable source revisions, SHA-256 identities, revision-specific queries, raw byte edits, same-revision analysis caching, and `fill_hole` preview/application. Hole filling requires a unique scope-qualified target at the current revision, parses one expression, checks the entire candidate, preserves unrelated bytes, and retains historical revisions. Invalid candidates and stale or ambiguous targets do not advance the document.

Edited revisions are fully parsed and checked; this is not cross-revision incremental compilation. See [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md) for the exact interface, [SEED_LANGUAGE.md](SEED_LANGUAGE.md) for the seed limits, and [NEXT_PACKET.md](NEXT_PACKET.md) for the next milestone. The historical MoonBit A0 design remains in [HISTORICAL_DESIGN_A0.md](HISTORICAL_DESIGN_A0.md).
## Designed or planned, not implemented in this seed
The following v0.3 commitments are not current compiler capabilities:

- structural edits beyond the supported named typed-hole fill; there is no general AST-targeted refactoring system;
- cross-revision incremental parsing or type checking; each new source revision is fully analysed;
- built-in parametric containers;
- an immutable extension message runtime, activation flow, and acceptance-contract enforcement; and
- a Pep-written C11 generator or self-hosted compiler.

Same-revision cached analysis is implemented, but it does not constitute incremental compilation. Records, recursive tagged unions, constructors, checked pattern matching, and match-arm holes passed A4. Extensions, a Pep-written C11 generator, and self-hosting remain future work. See [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md) for the A3 protocol boundary and [NEXT_PACKET.md](NEXT_PACKET.md) for A5.
## Historical A0 slice

A0 was a small MoonBit-based `say("text")`-to-C11 proof of concept. It remains useful historical/reference work through `pep-moonbit.ps1` and the separate MoonBit tests. The current seed and bootstrap direction are OCaml-first; the A0 notes are preserved without merging their feature claims into the current implementation.
