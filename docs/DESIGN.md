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
- original UTF-8 byte offsets, LF/CRLF-aware line reporting, and versioned JSON responses.

See [SEED_LANGUAGE.md](SEED_LANGUAGE.md) for the seed decision and precise limits. [NEXT_PACKET.md](NEXT_PACKET.md) is the current implementation work packet. The historical MoonBit A0 design is retained in [HISTORICAL_DESIGN_A0.md](HISTORICAL_DESIGN_A0.md); its feature inventory does not describe the primary Pep CLI.

## Designed or planned, not implemented in this seed

The following v0.3 commitments are not current compiler capabilities:

- immutable, revisioned document snapshots and query results bound to document revisions;
- named-hole identities that include the source revision;
- source-preserving structural edit operations;
- built-in parametric containers;
- an immutable extension message boundary and explicit activation/acceptance contracts; and
- a C11 generator written in Pep, followed by a self-hosting compiler.

The technical resolution defines constraints for this future work. Do not list these as implemented in `describe --json`, README feature claims, or release notes until code and acceptance evidence establish them.

## Historical A0 slice

A0 was a small MoonBit-based `say("text")`-to-C11 proof of concept. It remains useful historical/reference work through `pep-moonbit.ps1` and the separate MoonBit tests. The current seed and bootstrap direction are OCaml-first; the A0 notes are preserved without merging their feature claims into the current implementation.
