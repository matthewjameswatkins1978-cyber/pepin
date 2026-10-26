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
- an in-process schema-v3 `session --jsonl` with immutable source revisions, SHA-256 identities, revision-specific queries, raw byte edits, same-revision analysis caching, and `fill_hole` preview/application; and
- tool protocol v1 operations for checker-derived registration, real test-vector validation, explicit activation, tool listing, typed scalar invocation, and hot replacement. Tool functions use the checked immutable source revision and cannot reach `say`; each invocation has a 100,000-step and 128-call-depth budget.

Hole filling requires a unique scope-qualified target at the current revision, parses one expression, checks the entire candidate, preserves unrelated bytes, and retains historical revisions. Invalid candidates and stale or ambiguous targets do not advance the document. The local tool host is trusted and is not a sandbox.

Edited revisions are fully parsed and checked; this is not cross-revision incremental compilation. See [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md) for the exact interface, [SEED_LANGUAGE.md](SEED_LANGUAGE.md) for the seed limits, and [packets/CURRENT.md](packets/CURRENT.md) for the current implementation task, and [packets/archive/A5-ACCEPTANCE-RECORD.md](packets/archive/A5-ACCEPTANCE-RECORD.md) for the A5 acceptance record. The historical MoonBit A0 design remains in [HISTORICAL_DESIGN_A0.md](HISTORICAL_DESIGN_A0.md).
## Designed or planned, not implemented in this seed
The following v0.3 commitments are not current compiler capabilities:

- structural edits beyond the supported named typed-hole fill; there is no general AST-targeted refactoring system;
- cross-revision incremental parsing or type checking; each new source revision is fully analysed;
- built-in parametric containers;
- a Pep-written C23 generator (ISO/IEC 9899:2024) or self-hosted compiler.

Same-revision cached analysis is implemented, but it does not constitute incremental compilation. Records, recursive tagged unions, constructors, checked pattern matching, and match-arm holes passed A4. A5 adds the in-process tool registry, test-vector validation, explicit activation, scalar invocation, side-effect rejection, runtime budgets, and hot replacement. The local tool host is trusted and is not a sandbox. A Pep-written C23 generator and self-hosting remain future work. [Technical Resolution 002](TECHNICAL_RESOLUTION_002.md) establishes the forward-looking C23 target; MoonBit A0's C11 generation is historical only. See [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md) for the versioned message boundary and [packets/CURRENT.md](packets/CURRENT.md) for the next authorised packet.
## Planned implementation packets

The [packet index](packets/README.md) lists A6–A15; [CURRENT](packets/CURRENT.md) identifies the only currently authorised phase. These documents are plans and must **never** be described as implemented capabilities before acceptance and published verification. A9–A15 are provisional pending review after A8.

## Historical A0 slice

A0 was a small MoonBit-based `say("text")`-to-C11 proof of concept. It remains useful historical/reference work through `pep-moonbit.ps1` and the separate MoonBit tests. The current seed and bootstrap direction are OCaml-first; the A0 notes are preserved without merging their feature claims into the current implementation.
