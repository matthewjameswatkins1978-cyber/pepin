# Next packet: Pep document snapshots and revision-aware queries

This packet advances [Founding Design v0.3](FOUNDING_DESIGN_v0.3.md) under [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md). Queries and named holes must be bound to immutable document revisions; offsets remain original UTF-8 byte offsets for both LF and CRLF input.

## Objective

Build the smallest persistent document-analysis layer that lets an editor or AI query Pep by source identity and revision, while preserving the current compiler as the semantic authority. Establish observable parse/type reuse and invalidation before claiming incremental analysis.

## Current verified language

- Primary compiler: pep_ocaml.ml; CLI: pep.ps1; seed: OCaml 5.5.2 in the opam default root (override with PEPIN_OPAM_ROOT when the switch is elsewhere).
- Types: Int, Bool, Str, and Unit. Syntax: annotated or inferred let, fn declarations with typed parameters and return types, return, lexical blocks, integer arithmetic, <=, if … else … expressions, calls, named and anonymous holes.
- Builtins are monomorphic: say(Str) -> Unit and int_text(Int) -> Str.
- Function signatures are collected before checking bodies, so recursion and forward calls work.
- inspect, check, query --holes --json [--offset N], run, and describe --json are available. Query offsets and source spans count original UTF-8 bytes.
- Check and run reject incomplete programs, including holes in unused functions. The interpreter consumes the checked tree and has a bounded call depth.
- Tests cover runtime output, recursion, scopes, type failures, holes, query determinism, line endings, overflow and division by zero.
- No persistent document service, revision identity, incremental parse/type reuse, closures, modules, loops, general control flow, or native backend exists.

## Required change

Introduce an in-process document snapshot with a stable document identity and revision tied to the exact source bytes. Keep it small and explicit; no server protocol or agent orchestration.

Add the minimum edit-and-requery path needed to compare:

1. cold parse and type check;
2. query at a byte offset in one revision;
3. apply an edit to create a new revision;
4. query again using the new revision.

The existing full parse-and-check result is the correctness oracle. Any reused syntax or typing result must be observationally identical to a fresh analysis. Keep snapshots immutable so old query results remain reproducible.

## Acceptance

- Queries identify the document and exact source revision they describe.
- Repeating the same query against the same revision is byte-for-byte deterministic.
- Edits produce a new revision; the prior snapshot remains queryable.
- Query offsets and spans remain byte-based and preserve LF/CRLF source bytes.
- Reuse counters or equivalent evidence show what was reused and invalidated.
- Differential tests compare incremental results against a fresh full analysis over representative edits, including edits before and inside a function.
- Invalid and incomplete states remain distinct, and no incomplete checked tree can execute.
- Windows tests pass; describe advertises only implemented snapshot capabilities.

## Boundaries

Do not add language syntax in this milestone. Do not add a network service, persistence layer, plugin system, model dependency, parser framework, or speculative dependency graph. Begin with whole-function invalidation if finer dependency tracking is not yet justified; report that granularity honestly.
