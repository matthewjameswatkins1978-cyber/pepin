# Pep design and implementation status

This is the implementation-status index. The intended language vision is [Founding Design v0.3](FOUNDING_DESIGN_v0.3.md); the binding accepted technical decisions are in [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md), as amended by [Technical Resolution 002](TECHNICAL_RESOLUTION_002.md). They describe the direction of the language and must not be read as a feature inventory.

## Implemented in the primary OCaml seed
The primary compiler is `pep_ocaml.ml`, invoked by the PowerShell 7 CLI `pep.ps1` and built with the project OCaml 5.5.2 switch. Current implemented behavior includes:

- Built-in scalar types `Int`, `Bool`, `Str`, and `Unit`, plus monomorphic named record and tagged-union types;
- annotated or inferred `let` bindings, typed functions, recursion and forward calls, lexical blocks, integer arithmetic, `<=`, `if … else …`, record construction and field access, variant construction, and `match` expressions with nested constructor and wildcard patterns;
- monomorphic built-ins `say(Str) -> Unit` and `int_text(Int) -> Str`;
- source-spanned ASTs, a separate checked tree, and an interpreter that runs only complete checked programs;
- named and anonymous holes, expected-type checking, visible-binding queries, deterministic fill suggestions, and arm-local typed holes in matches;
- `inspect`, `check`, `query`, `run`, and `describe --json`; and
- an in-process schema-v3 `session --jsonl` with immutable source revisions, SHA-256 identities, revision-specific queries, raw byte edits, same-revision analysis caching, and `fill_hole` preview/application; and
- tool protocol v1 operations for checker-derived registration, real test-vector validation, explicit activation, tool listing, typed scalar invocation, and hot replacement. Tool protocol v2 adds bounded typed List/record transport and a host-authorised semantic snapshot built from checker-resolved function data; `semantic_snapshot()` returns `ProgramInfo` with function declarations, call edges, roots, status, and diagnostics for an explicitly granted retained target revision. Tool functions use their checked immutable source revision and cannot reach `say`; each invocation has a 100,000-step and 128-call-depth budget. The Pep-written [`unused_functions.pep`](../examples/unused_functions.pep) traverses those supplied call facts in Pep and reports functions unreachable under the declared roots;
- built-in `List[T]`, homogeneous/context-checked list literals, `length`, immutable `append`, scalar-only `contains`, mutable `var` bindings and assignment, scoped `for-in`, `while`, statement `if` blocks, scalar equality, and short-circuit Boolean operators. Lists preserve literal order; `length`, `append`, and `contains` are O(n); `contains` searches in order and stops at the first equal scalar. Construction and append charge each allocated list node, traversal and membership charge each visited node, and loops charge each iteration against the runtime budget. The CLI budget is 1,000,000 steps and 512 call depth; the trusted-local tool boundary remains 100,000 steps and 128 call depth. The language has no user-defined generics or mutable list storage.

Hole filling requires a unique scope-qualified target at the current revision, parses one expression, checks the entire candidate, preserves unrelated bytes, and retains historical revisions. Invalid candidates and stale or ambiguous targets do not advance the document. A8's `unused_functions.pep` is a self-development proof: it computes call-graph reachability in Pep from checker-produced facts and reports only functions unreachable under the selected root policy. It is an example registered through the session tool protocol, not a built-in CLI analysis command or a self-hosted compiler. The local tool host is trusted and is not a sandbox.

Edited revisions are fully parsed and checked; this is not cross-revision incremental compilation. See [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md) for the exact interface, [SEED_LANGUAGE.md](SEED_LANGUAGE.md) for the seed limits, and [packets/CURRENT.md](packets/CURRENT.md) for the current implementation task. The [A5](packets/archive/A5-ACCEPTANCE-RECORD.md) and [A6](packets/archive/A6-ACCEPTANCE-RECORD.md) acceptance records preserve their published evidence. The historical MoonBit A0 design remains in [HISTORICAL_DESIGN_A0.md](HISTORICAL_DESIGN_A0.md).
## Designed or planned, not implemented in this seed
The following v0.3 commitments are not current compiler capabilities:

- structural edits beyond the supported named typed-hole fill; there is no general AST-targeted refactoring system;
- cross-revision incremental parsing or type checking; each new source revision is fully analysed;
- user-defined generics, maps, modules, and general mutable references;
- a Pep-written C23 generator (ISO/IEC 9899:2024) or self-hosted compiler.

Same-revision cached analysis is implemented, but it does not constitute incremental compilation. A4 added records, recursive tagged unions, constructors, checked pattern matching, and match-arm holes. A5 added the in-process tool registry, test-vector validation, explicit activation, scalar invocation, side-effect rejection, runtime budgets, and hot replacement. A6 adds compiler-known lists and practical control flow; see the implemented list above. The local tool host is trusted and is not a sandbox. A Pep-written C23 generator and self-hosting remain future work. [Technical Resolution 002](TECHNICAL_RESOLUTION_002.md) establishes the forward-looking C23 target; MoonBit A0's C11 generation is historical only. See [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md) for the versioned message boundary and [packets/CURRENT.md](packets/CURRENT.md) for the next authorised packet.
## Planned implementation packets

The [packet index](packets/README.md) lists A6–A15; [CURRENT](packets/CURRENT.md) identifies the only currently authorised phase. These documents are plans and must **never** be described as implemented capabilities before acceptance and published verification. A9–A15 are provisional pending review after A8.

## Historical A0 slice

A0 was a small MoonBit-based `say("text")`-to-C11 proof of concept. It remains useful historical/reference work through `pep-moonbit.ps1` and the separate MoonBit tests. The current seed and bootstrap direction are OCaml-first; the A0 notes are preserved without merging their feature claims into the current implementation.
