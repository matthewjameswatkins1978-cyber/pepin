# Pep seed language decision (2026-10-25)

## Decision

Use **OCaml 5.5.2** as Pep's seed implementation language. The compiler owns Pep's syntax, typed representation, semantic queries, diagnostics, and eventual self-hosting path. OCaml is implementation machinery; it does not define Pep's surface syntax or semantics.

The machine had OCaml 5.5.0. OCaml 5.5.2 is the current official release, published 2026-10-23. It is installed in a separate Pepin opam root and named switch; the shared OCaml switch used by other projects remains untouched. The isolated compiler reports 5.5.2. See the official [5.5.2 release notes](https://ocaml.org/releases/5.5.2) and [Windows setup guide](https://ocaml.org/docs/ocaml-on-windows).

## What "AI-first" means for Pep

Pep should make the compiler's semantic facts directly inspectable and stable. An AI or editor should not infer types from examples, scrape terminal prose, or invent compiler behavior.

The compiler should provide:
- plaintext `.pep` source as the canonical editable program;
- a source-spanned syntax tree, then a distinct checked Pep tree;
- explicit incomplete-expression nodes that retain their expected type;
- semantic queries against compiler-owned trees and scopes;
- structured diagnostics and typed, actionable suggestions;
- execution only after type checking succeeds;
- deterministic outputs that remain useful without an LLM.

This does not require an LLM in the compiler. The language implementation remains deterministic; an AI can consume its typed interfaces.

## Candidate comparison

| Seed | Fit for typed trees and holes | Incremental/semantic tooling | Windows and self-hosting path | Decision |
|---|---|---|---|---|
| **OCaml 5.5.2** | Algebraic data types make syntax, typed trees, holes, diagnostics, and actions direct data. We implement Pep semantics explicitly. | Mature compiler and editor ecosystem. Pep still needs its own stable query API and incremental document model. We will avoid depending on OCaml's unstable `compiler-libs` APIs. | Installed and native on this Windows machine; supports the small compiler now and a later Pep-written compiler. | **Choose** |
| **Lean 4** | Best built-in example of expected-type holes, metavariables, elaboration, and type-indexed semantic metadata. Its editor information trees are a useful design reference. | Strong interactive infrastructure and incremental diagnostics; internal elaboration would bring proof-engine and kernel concepts into a small standalone language. | No local Lean toolchain was present; a Lean-embedded Pep would make Lean a long-term runtime/semantic dependency. | Borrow hole and query ideas, do not use as the seed. |
| **MoonBit** | Compact typed data and a native backend; existing Pep seed already has a lexer, parser, C generator, and tests. Pep's hole behavior would still be custom. | Its semantic IDE tools help navigate MoonBit itself. Current docs describe future incremental parsing/type checking around block boundaries, not Pep's semantic API. | The machine has MoonBit `0.1.20261023`; the repository's existing MoonBit implementation is preserved as `pep-moonbit.ps1` and its tests remain separate. | Good prototype platform, weaker long-lived compiler base for this scope. |
| **Zig** | Clear low-level data representation and strong native toolchain; it does not provide Pep-style typed holes or a language-server semantic model. | Pep would need to build the entire semantic/query layer. | Official Windows builds are available; no local Zig was installed. | Backend/tooling option, not the best compiler seed. |
| **Koka** | Strong type system, algebraic effects, and research interest; its v3.2.0 notes introduce a `hole` keyword in constructor contexts, which is narrower than Pep expected-type queries. | The official specification describes Koka v3 as a research language still under development, with libraries and package management incomplete. Those features do not solve Pep's query model. | Windows x64 compiler exists, but no local Koka installation was present. | Interesting language-design reference, excess dependency and complexity for the seed. |

Lean documentation demonstrates expected-type holes and separates parsing, elaboration, kernel checking, and compilation. Its elaboration info trees carry types, goals, completion data, and custom action metadata. These are valuable models for Pep's interfaces, without importing Lean's theorem-proving machinery: [Lean holes](https://lean-lang.org/doc/reference/latest/Terms/Holes/) and [elaboration and compilation](https://lean-lang.org/doc/reference/latest/Elaboration-and-Compilation/).

OCaml's compiler frontend provides a mature example of source locations on syntax and typed trees. Its compiler libraries are version-sensitive, so Pep will use its own small frontend instead of tying Pep semantics to internal compiler APIs: [OCaml compiler frontend](https://ocaml.org/docs/compiler-frontend). MoonBit's current docs describe semantic navigation and block markers intended to support future caching and incremental checking: [MoonBit IDE](https://docs.moonbitlang.com/en/stable/toolchain/moonide/index.html) and [block-line documentation](https://docs.moonbitlang.com/en/stable/language/docs.html). Koka's own specification identifies it as research software under development: [Koka specification](https://koka-lang.github.io/koka/doc/kokaspec.html). Zig's official downloads confirm current Windows support: [Zig releases](https://ziglang.org/download/).

## A1 implementation boundary

A1 adds annotated and inferred `let` bindings, `fn` declarations, typed parameters and return types, recursive and forward calls, lexical blocks, integer arithmetic, and the `if condition { value } else { value }` expression needed for recursive functions. Canonical types are `Int` (signed 64-bit), `Bool`, `Str`, and `Unit`. The monomorphic builtins are `say(Str) -> Unit` and `int_text(Int) -> Str`.

The lexer preserves the original UTF-8 source bytes. Spans use byte offsets and one-based starting line and column. The AST, resolved checked tree, and interpreter are distinct representations. Binding and function references in the checked tree use compiler-assigned identities. Function signatures are collected before bodies, so recursion and forward function calls resolve against one type authority.

Typed and named holes retain their expected type when context supplies one. `query --holes --json` returns visible bindings, compatible candidates, scope, and source span; `--offset` selects a hole by byte offset. A hole in an unannotated binding remains unconstrained. `check` marks a program incomplete, and `run` refuses it even when the hole is in an unused function. Runtime integer overflow, division by zero, and excessive call depth produce controlled diagnostics.

This remains a small interpreter seed. Analysis is per CLI process and reparses the whole file; there is no revision identity, incremental reuse, closure, module system, loops, general branching, native Pep backend, or self-hosted compiler. Functions cannot capture top-level values. The checker reports the first invalid-program error rather than accumulating multiple independent errors. The original MoonBit compiler and tests remain available for reference.

## Next design gate

Add an in-process immutable document snapshot and revision-aware semantic queries, then compare every reused result against a fresh full analysis. Start with whole-function invalidation if needed, measure what is actually reused, and do not advertise incremental analysis before that evidence exists. See [NEXT_PACKET.md](NEXT_PACKET.md).
