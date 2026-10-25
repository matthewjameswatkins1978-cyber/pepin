# Pep design and implementation status

This is the implementation-status index. The intended language vision is [Founding Design v0.3](FOUNDING_DESIGN_v0.3.md); the binding accepted technical decisions are in [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md). They describe the direction of the language and must not be read as a feature inventory.

## Implemented in the primary OCaml seed
The primary compiler is `pep_ocaml.ml`, invoked by the PowerShell 7 CLI `pep.ps1` and built with the project OCaml 5.5.2 switch. Current implemented behavior includes:

- `Int`, `Bool`, `Str`, and `Unit`;
- annotated or inferred `let` bindings, functions with typed parameters and return types, recursion and forward calls, lexical blocks, integer arithmetic, `<=`, and `if … else …` expressions;
- monomorphic built-ins `say(Str) -> Unit` and `int_text(Int) -> Str`;
- source-spanned ASTs, a separate checked tree, and an interpreter that runs only complete checked programs;
- named and anonymous holes, expected-type checking where context supplies a type, visible-binding queries, and deterministic fill suggestions;
- `inspect`, `check`, `query`, `run`, and `describe --json`; and
- an in-process `session --jsonl` protocol (schema v3) with immutable source revisions, SHA-256 identities, revision-specific semantic queries, half-open UTF-8 byte edits, retained historical analyses, malformed-request recovery, and same-revision analysis caching. Edited revisions are fully parsed and checked; this is not incremental compilation.

See [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md) for the exact JSONL contract, [SEED_LANGUAGE.md](SEED_LANGUAGE.md) for the seed decision and precise limits, and [NEXT_PACKET.md](NEXT_PACKET.md) for the next milestone. The historical MoonBit A0 design is retained in [HISTORICAL_DESIGN_A0.md](HISTORICAL_DESIGN_A0.md); its feature inventory does not describe the primary Pep CLI.
## Designed or planned, not implemented in this seed
The following v0.3 commitments are not current compiler capabilities:

- compiler-backed structural edits and refactorings; `session --jsonl` currently applies only revision-checked raw byte-range edits;
- cross-revision incremental parsing or type checking; each new source revision is fully analysed;
- built-in parametric containers;
- an immutable extension message runtime, activation flow, and acceptance-contract enforcement; and
- a Pep-written C11 generator or self-hosted compiler.

Same-revision cached analysis is implemented, but it does not constitute incremental compilation. See [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md) for the exact A2 boundary.
## Historical A0 slice

A0 was a small MoonBit-based `say("text")`-to-C11 proof of concept. It remains useful historical/reference work through `pep-moonbit.ps1` and the separate MoonBit tests. The current seed and bootstrap direction are OCaml-first; the A0 notes are preserved without merging their feature claims into the current implementation.
