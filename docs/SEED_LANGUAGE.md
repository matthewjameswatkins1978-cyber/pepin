# Pep seed language decision (2026-10-25)

The seed choice implements part of the broader [Founding Design v0.3](FOUNDING_DESIGN_v0.3.md). Binding future technical constraints are in [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md), as amended by [Technical Resolution 002](TECHNICAL_RESOLUTION_002.md); this file records current seed facts and limits.

## Provisional file modules

The provisional core branch supports function modules in file-based CLI projects. The entry file's physical parent directory is the project root. An import such as `import math.scale as scale` resolves the case-exact path `math/scale.pep` underneath that root. Imported declarations are private by default. Export a function with `pub fn` and call it through an explicit qualifier. Imported files can declare functions, private records and tagged unions, and import other files. Private type and constructor names are scoped to their declaring file. Cycles, noncanonical paths, private types in public signatures, and top-level execution in imported files are diagnosed.

`math/scale.pep`

```pep
fn adjust(value: Int) -> Int { return value + 1 }
pub fn twice(value: Int) -> Int { return adjust(value) * 2 }
```

`main.pep`

```pep
import math.scale as scale
say(int_text(scale.twice(20)))
```

From the repository root, use `.\pep.ps1 run PATH_TO_MAIN.pep` or `.\pep.ps1 run-c23 PATH_TO_MAIN.pep --direct`. Both should print `42`. Use `.\pep.ps1 check PATH_TO_MAIN.pep --json` to inspect the checked tree and the content-addressed `moduleGraph`. Use `python pep_semantic_map.py context PATH_TO_MAIN.pep --symbol math/scale.pep::twice --json` to retrieve the exported function's source and dependencies. Context refuses to use a graph after any module source changes. The direct C23 driver also refuses output paths that name any source in the checked module graph, including transitive imports and existing hard links. See `tests.test_c23_correctness` (module source/output collision).

When a module declares `pub type Counter { value: Int }`, importers can name the type as `alias.Counter` and pass values through public functions. Record fields and tagged-union constructors stay private. Define public construction and inspection functions within the declaring module. The checked module graph lists public type identities in `typeExports`.

Session-based module editing, module-aware repairs and lane approval, and packages remain outside this slice.

## Provisional statement control flow

**PEP-DEC-009 / V1 (statement conditionals).** A statement `if condition { … }` may omit the else branch. An `else if` is a nested statement in the false branch, with the same lexical scoping and lazy selection as a braced `else`. In a function returning a non-`Unit` value, a conditional terminates the block only when every branch terminates. An expression `if` also supports `else if` and requires a compatible final else value. Checked programs expose the nested branch as an `if_statement` in the typed tree used by the interpreter and direct C23 backend.

Evidence: `tests.test_a6.A6CollectionsAndControlTests.test_loop_binding_is_immutable_and_loop_return_flow_is_conservative` and `tests.test_c23_correctness` (optional else and else-if parity).

**PEP-DEC-009 / V1 (loop transfers).** `break` exits the nearest enclosing `while` or `for` body. `continue` rechecks the nearest `while` condition or advances the nearest `for` iterator. Branch and block scopes are exited normally. The checker rejects either keyword outside a loop and rejects statements after unconditional transfers in the same block. Loops still do not establish a function's return completeness. The checked tree exposes source-spanned `break` and `continue` statements. This slice has no Pep-owned resources or managed native cleanup.

Evidence: `tests.test_a6.A6CollectionsAndControlTests.test_loop_control_is_contextual_and_terminates_the_current_block` and `tests.test_c23_correctness` (nearest-loop transfer parity).

**PEP-DEC-005 / V1 (integer ordering).** The signed `Int` comparisons `<`, `<=`, `>`, and `>=` return `Bool` and bind more tightly than equality and less tightly than addition. Operands are evaluated left to right. Other types require an explicit supported operation. The [module demo](../examples/module_demo/main.pep) uses these comparisons, checked indexing, and loop control to sum squares over a bounded prefix. See `tests.test_c23_correctness` (signed ordering, precedence, side effects and module demo) and `tests.test_a6` (invalid operand types).

## Provisional checked list indexing

**PEP-DEC-005 / V1 (indexed reads).** `values[index]` reads an immutable `List[T]` and produces `T`, using zero-based `Int` indices. A bracket on the same line as the preceding token continues the expression. Postfix indexing composes with field access and other indices. The receiver is evaluated before the index, once each. A negative or out-of-range index traps with `PEP_RUNTIME_INDEX_BOUNDS` before subsequent effects. The interpreter traverses the list up to the requested element and charges step budget during traversal. Direct C23 checks the bounds and reads its existing contiguous list storage. The typed tree reports the operands, element type, source span, and required runtime bounds check. Indexed writes, `get` returning `Option`, and indexing other collections remain future work.

Evidence: `tests.test_a6.A6CollectionsAndControlTests.test_list_index_is_typed_and_bounds_checked` and `tests.test_c23_correctness` (indexed read ordering, bounds and nominal, nested and Boolean value parity).

## Provisional generic functions

**PEP-DEC-003B / V2.** Declare type parameters with `fn first[T](values: List[T]) -> T { return values[0] }`. The checker checks the body with abstract type parameters, even when the function is unused. Calls infer type arguments from arguments and the expected result when available. The interpreter and direct C23 consume the same concrete checked instances, deduplicated by source function and concrete types. The typed tree links each instance to its template and exposes the checked template separately. Public generic signatures retain their type parameters in the checked module graph and Semantic Map.

This slice supports unconstrained, nonrecursive generic functions declared locally or exported from a file module. Nested calls to generic functions from a monomorphic caller are allowed. Calls from generic bodies to other generic functions (including recursion), explicit type arguments, constraints and generic nominal type declarations require follow-up. Ambiguous calls and programs requiring more than 256 distinct instances receive diagnostics.

Evidence: `tests.test_a6` (template checking and inference), `tests.test_a7` (source function identities and call edges), and `tests.test_c23_correctness` (concrete native parity and public module interfaces).

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

A1 adds annotated and inferred `let` bindings, `fn` declarations, typed parameters and return types, recursive and forward calls, lexical blocks, integer arithmetic, and the `if condition { value } else { value }` expression needed for recursive functions. Canonical built-in types are `Int` (signed 64-bit), `Bool`, `Str`, and `Unit`. A4 adds immutable nominal records, recursive tagged unions, constructor expressions, field access, and exhaustive `match` expressions with nested constructor, binding, and wildcard patterns. These forms use the same parser, checked tree, query model, and interpreter. The monomorphic builtins are `say(Str) -> Unit` and `int_text(Int) -> Str`.

The lexer preserves the original UTF-8 source bytes. Spans use byte offsets and one-based starting line and column. The AST, resolved checked tree, and interpreter are distinct representations. Binding and function references in the checked tree use compiler-assigned identities. Function signatures are collected before bodies, so recursion and forward function calls resolve against one type authority.

Typed and named holes retain their expected type when context supplies one. `query --holes --json` returns visible bindings, compatible candidates, scope, and source span; `--offset` selects a hole by byte offset. A hole in an unannotated binding remains unconstrained. `check` marks a program incomplete, and `run` refuses it even when the hole is in an unused function. Runtime integer overflow, division by zero, and excessive call depth produce controlled diagnostics.

The unaccepted A10 review branch adds exact-byte inspection, `open_bytes`, a v2 host-granted `source_bytes()`, checked byte slicing, and O(1) `prepend` plus linear `reverse`; see [the typed lexer fragment](../examples/lexer_fragment.pep). These are candidate branch capabilities, not an accepted full lexer or self-hosting milestone.

This remains a small interpreter seed. A6 adds compiler-known immutable `List[T]`, homogeneous list literals, contextual empty lists and typed element holes, `length`, immutable `append`, scalar-only `contains`, `var` assignment, `for-in`, `while`, statement `if` blocks, scalar equality, and short-circuit Boolean operators. Loop iterations, list construction, traversal, copying, and membership work consume the interpreter step budget; the trusted-local A5 tool host retains its smaller 100,000-step and 128-call-depth limits. File-oriented analysis reparses the whole file; the in-process session retains ephemeral revisions and reuses analysis only for the same exact revision. Changed revisions are fully re-analysed, so cross-revision incremental reuse is not implemented. Closures, modules, a native Pep backend, and a self-hosted compiler are absent. Functions cannot capture top-level values. The checker reports the first invalid-program error rather than accumulating multiple independent errors. The original MoonBit compiler and tests remain available for reference.

## Revision-aware session and local tool boundary
The revision-aware semantic session is implemented in-process in schema-v3 `session --jsonl`; it retains immutable document revisions, revision-bound queries, same-revision cached analyses, and scope-qualified named-hole preview/application. Changed revisions are fully parsed and checked. Cross-revision incremental analysis and general structural refactoring are not implemented. A4 adds records, recursive unions, match, and arm-local typed holes. A5 adds explicit local-tool registration, interpreter test-vector validation, activation, typed scalar invocation, and hot replacement. A6 adds typed lists and control flow; the file-oriented CLI and session use the same checker and interpreter. Tool protocol v1 accepts scalar parameters and results. Protocol v2 adds bounded typed List and record transport plus a host-authorised semantic snapshot of a retained target revision. The protocol is versioned independently within session schema v3. The tool host is trusted-local, not sandboxed, and enforces 100,000 execution steps and 128 function-call depth, including loops and collection work. See [NEXT_PACKET.md](NEXT_PACKET.md), [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md), [TOOL_PROTOCOL_V2.md](TOOL_PROTOCOL_V2.md), and [packets/CURRENT.md](packets/CURRENT.md).
