# PEPIN — A small, living, AI-first programming language

## Founding Design v0.3 — October 2026

> **Status and provenance.** This is the canonical v0.3 design vision. The original writing block referenced in the design conversation was not available in the retained transcript. This document is a careful reconstruction from the accepted commitments supplied for this repository and the existing seed-language and implementation notes; it is not presented as a verbatim recovery. Binding technical decisions are recorded in [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md). The currently implemented subset is listed separately in [DESIGN.md](DESIGN.md).

## 1. Purpose

Pep is a small, statically typed programming language intended to become self-hosting. It is designed for people and AI systems to read, change, inspect, and explain together. Its compiler should expose reliable semantic facts directly, so an editor or agent can work from the language's actual syntax, types, scopes, and diagnostics rather than guessing from text or scraping prose.

AI-first describes the language and tooling boundary, not a requirement to embed a model. Core parsing, checking, execution, diagnostics, and edits are deterministic. AI systems may consume the same versioned interfaces as editors and other tools; they do not get a second semantic authority.

Pep source is ordinary, readable text. The source file remains the durable program a person can review and edit. Compiler services add structured understanding around it without replacing it with an opaque project database.

## 2. Design goals

Pep should:

- remain small enough that its syntax and semantics can be taught and inspected;
- make type information, scope, source locations, incomplete expressions, and errors explicit;
- support a productive edit–inspect–check–run loop, including while a program is incomplete;
- allow tools to make precise, source-preserving structural edits;
- keep compiler queries deterministic and bound to the exact document revision they describe;
- expose a stable, versioned JSON boundary suitable for editors and AI clients;
- grow toward self-hosting through a deliberately staged compiler bootstrap; and
- report implemented behavior separately from intended behavior.

## 3. Language shape

Pep is statically typed. Expressions have types, function parameters and return types are explicit, and the checker owns name resolution and type compatibility. The initial language is intentionally compact: bindings, functions, lexical blocks, arithmetic, conditionals, calls, and a small set of built-ins provide a useful interpreter seed.

The language grows by coherent, specified steps. A feature belongs to the language only when its syntax, typing rules, diagnostics, execution or compilation behavior, and acceptance evidence agree. An idea in this design document is not a claim that the current compiler implements it.

## 4. Bidirectional typing and incomplete programs

Typing uses both synthesis and checking. In synthesis, an expression supplies its type from its own structure and context. In checking, an expected type flows into an expression from a binding annotation, function parameter, return position, or another typed context. The two directions meet at expressions whose type is otherwise ambiguous.

Incomplete expressions are first-class typed holes, not parser failures or magic text substitutions. A hole retains its optional name, expected type when known, visible bindings, scope, and source span. A partially typed tree preserves the known structure and types around holes. The checker distinguishes a valid complete program, a valid but incomplete program, and an invalid program. Incomplete programs may be inspected and queried; execution requires a complete checked program.

Hole queries and any proposed fill are tied to a named hole in a particular document revision. A name is an identity within that revision, not a promise that the same source location or hole survives later edits. Clients must re-query after the revision changes.

## 5. Types and parametric containers

Pep begins with a small set of built-in scalar types. Parametric containers are part of the intended language, but remain built-in compiler forms until the language can express and implement them itself. They are introduced before full self-hosting only through a bounded set of compiler-known container types and operations; they do not imply user-defined generics, a general type-class system, or an extension-defined type system.

The compiler owns the typing rules for these containers. A container value must preserve its element type through construction, use, checking, diagnostics, and the eventual backend. The exact container inventory and surface syntax are to be specified at the implementation gate, not inferred from this vision statement.

## 6. Source identity, revisions, and edits

A document snapshot is immutable and identifies the exact original UTF-8 source bytes. Each edit creates a new revision; previous snapshots remain available for reproducible queries. Diagnostics, typed trees, hole identities, and query results are meaningful only for the revision that produced them.

Source spans and edit positions use offsets into the original UTF-8 byte sequence. LF and CRLF are both supported as line endings. Line and column reporting follows the language's documented convention, while byte offsets continue to refer to the unnormalized original bytes. The compiler must not silently normalize line endings before assigning offsets.

Structural edits preserve untouched source bytes, comments, formatting, and line-ending style. An edit identifies the intended syntax or semantic target, its source revision, and the replacement. If the target is absent, ambiguous, or stale, the edit is rejected rather than relocated by guesswork. Reformatting is a separate, explicit operation and is not an incidental side effect of a structural edit.

## 7. Compiler and tool boundary

The compiler is the authority for parsing, name resolution, typing, hole context, diagnostics, and whether a program may execute. Inspection and checking are read-only. A source edit creates a new snapshot and causes affected semantic results to be recomputed or safely reused only when that reuse is proven equivalent to a fresh analysis.

The machine interface is versioned JSON. Each response identifies its schema/interface version and has explicit states for complete, incomplete, invalid, and runtime-failure results as applicable. Tools must not infer success from human-readable output or treat an unknown version as a compatible contract. Human-oriented CLI output may coexist with JSON, but JSON is the stable automation boundary.

Extensions do not become active merely because a package or declaration is present. Activation is explicit and governed by a declared activation contract. An extension must satisfy its acceptance contract before the host treats it as active. The extension boundary is an immutable message exchange: requests and responses are values, and an extension cannot mutate compiler-owned trees, snapshots, or host state by shared reference. Message schemas and compatibility are versioned. Extension activation, failure, and acceptance remain visible and deterministic.

This boundary is a design commitment, not a statement that an extension runtime or activation system exists in the current compiler.

## 8. Execution and bootstrap

Pep takes an interpreter-first path. The OCaml seed parses and checks Pep, retains a typed representation, and interprets complete checked programs. This keeps the early semantic loop small and makes typed holes and diagnostics useful before a native backend exists.

The long-term bootstrap target is a C11 generator written in Pep. The initial C11 backend is produced by Pep source and is compiled by a host C compiler. The OCaml implementation is bootstrap machinery; it is not the permanent definition of Pep semantics. The transition is staged: first make the interpreter and semantic interfaces trustworthy, then implement and validate the Pep-written generator, then use that generator to build later Pep compiler versions.

The historical MoonBit seed remains available as reference work. It does not define the current primary compiler, the language's semantics, or the future self-hosting path.

## 9. Compatibility and evolution

Surface syntax, typing rules, built-ins, diagnostics, JSON schemas, revision identity, and extension messages are all part of observable behavior. Changes to those contracts require explicit versioning and acceptance evidence. Compiler internals may change without changing these contracts.

Pep should prefer a small number of explicit, stable contracts over hidden inference. Where a decision is not yet fixed, the implementation must not silently turn a provisional design direction into a compatibility promise.

## 10. Acceptance discipline

Every implementation milestone states what is implemented and supplies tests or other reproducible evidence for that claim. At minimum, semantic work should cover success, invalid input, incomplete input, source locations, deterministic machine output, and the relevant edit or execution boundary. Differential comparison against fresh analysis is required when semantic results are reused across revisions.

`describe --json` reports current capabilities only. Design documents may describe the intended language, but the CLI, README implementation summary, and tests must not advertise a planned feature as present.

## 11. Current status

The current OCaml seed is a small interpreter with a source-spanned AST, a checked tree, `Int`, `Bool`, `Str`, and `Unit`, functions, lexical scopes, integer operations, `if` expressions, two monomorphic built-ins, and named or anonymous typed holes. Its CLI exposes `inspect`, `check`, `query`, `run`, and `describe`.

Persistent revisioned documents, incremental reuse, source-preserving structural edit operations, parametric containers, extensions, and the Pep-written C11 generator are design or implementation goals. Consult [DESIGN.md](DESIGN.md), [SEED_LANGUAGE.md](SEED_LANGUAGE.md), and [NEXT_PACKET.md](NEXT_PACKET.md) for the implementation boundary and next work packet.
