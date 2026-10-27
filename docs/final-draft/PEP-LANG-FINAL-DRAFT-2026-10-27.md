# PEPIN / PEP — Language Design, Final Draft
**Draft ID:** PEP-LANG-FINAL-DRAFT-2026-10-27
**Status:** User-approved consolidated LANGUAGE DESIGN DRAFT. Not a frozen standards specification, proof of implementation, completed compiler, or authorisation to activate provisional implementation packets.
**Project:** Pepin | **Source language:** Pep | **Extension:** .pep | **Target authors:** AI-primary, human-readable and human-verifiable
**Companion files:** IMPLEMENTATION-MISSION.md and ACCEPTANCE-MATRIX.md in this directory.

## 0. Executive contract

Pep is a small, statically typed, AI-first programming language. It is written for intelligent agents as primary operators, while remaining readable and governable by humans. Its compiler, not an AI's confidence or memory, is the authority for parsing, type rules, name resolution, checked trees, safety judgments and runtime eligibility. Source stays plain, versioned text. One authoritative semantic engine serves compilation, tests, tools, queries and edits.

**Founding question:** Does this make a programmer express something genuinely necessary, or could the compiler establish it safely?

**Design balance:** Small language, capable typed standard library, advanced compiler, rich revision-bound semantic interface, explicit host permissions. Sophisticated compiler internals do not justify complicated everyday syntax. An AI model is never required at runtime or for deterministic checking.

**One source file has three complementary information layers:**
1. Executable Pep code and formal checked contracts.
2. Optional structured Semantic Notes requesting verification, recording intent or suggesting safe optimisation priorities.
3. Free-form ordinary comments explaining rationale to a future human or AI.

The compiler never promotes an unverified annotation or model suggestion to a proven fact or runtime authority.

## 1. Provenance and authority: read before implementing

This draft consolidates Matthew's accepted 27 October 2026 decisions: DEC-001, DEC-002, DEC-003A–003H, DEC-004, DEC-005, DEC-006, DEC-007, DEC-008 and DEC-009. These are recorded individually in the Pepin Basic Memory Cloud project. The three-layer Semantic Notes direction is accepted, while its exact tags and parser details live in a separately reviewed design proposal. Built-in testing direction is accepted and its exact grammar/runner details await controlled implementation.

**Never conflate:**
- **Accepted language design:** desired observable semantics and architectural restrictions in this document.
- **Proposed syntax/engineering choices:** candidate grammar forms, runtimes, verification engines and optimisation strategies.
- **Shipped OCaml seed capabilities:** documented by docs/DESIGN.md and demonstrated by actual source and tests.
- **Authorised next development phase:** determined only by docs/packets/CURRENT.md and docs/packets/manifest.json, not by this draft or a development branch.

Canonical existing repo documents:
- docs/FOUNDING_DESIGN_v0.3.md: founding direction, earlier than accepted changes.
- docs/TECHNICAL_RESOLUTION_001.md: bidirectional typing, holes, byte-faithful revisions, JSON and tool boundaries.
- docs/TECHNICAL_RESOLUTION_002.md: modern-by-default policy; intended Pep-written **C23** backend rather than obsolete C11 plan.
- docs/DESIGN.md and docs/SEED_LANGUAGE.md: currently implemented subset and limitations.
- docs/SESSION_PROTOCOL.md and docs/TOOL_PROTOCOL_V2.md: existing actual machine operations.
- docs/packets/CURRENT.md: current phase authority.
- docs/proposals/PEP-SN-001-SEMANTIC-NOTES.md: design branch proposal, not merged as of this draft.
- The-Terror-Bats (separate repo) README and docs/receipt-v0.md: independent adversarial-testing/evidence reference.

**Explicit supersession:** Founding v0.3 suggested reference-like collection semantics. That claim is superseded by accepted DEC-001 and DEC-005: ordinary Pep collections have **independent value semantics**. Founding v0.3 also mentions a forward-looking C11 backend; TR002 supersedes this with a Pep-written **C23** generator. Do not rewrite or erase historical evidence; annotate it and use these newer decisions going forward.

## 2. Target syntax at a glance

These are **proposed final-draft forms**, not a promise that the current seed parses them.

~~~pep
import math
import test
import fs

# Ordinary rationale for next AI or human.
#@ intent: "Scale samples without violating channel assumptions"
#@ verify: channels > 0
#@ prefer: latency

pub type Frame {
    samples: List[Float32]
    channels: Int
}

pub fn scale[T: Numeric](data: List[T], factor: T) -> List[T] {
    return list.map(data, fn(sample: T) -> T {
        return sample * factor
    })
}

fn load(path: Str) -> Result[Str, fs.Error]
    uses fs.read
{
    return fs.read_text(path)
}

fn bump(edit value: Int) -> Unit {
    value = value + 1
}

test "simple arithmetic" {
    test.equal(2 + 2, 4)
}
~~~

**Important:** Numeric is NOT an accepted new generic ability. It is an unresolved *placeholder* demonstrating that arithmetic on type parameter T must require a checked contract; the initial accepted abilities are Equal, Ordered and Hashable. Before including an equivalent example in normative conformance, either use a concrete numeric type or separately decide numeric constraints. list.map, Float32, Result, tests, effects, generic declarations and annotations shown above are future work. This example is descriptive only, not a canonical compiling test.

### Lexical and layout direction

- Familiar braces; explicit named-function parameter and return types.
- Immutable let, mutable var; assignments are explicit.
- Optional semicolon to separate statements; otherwise deterministic newline-based separation, with precisely specified continuation rules in parentheses/brackets and unfinished expressions.
- Explicit return; if statement can omit else; value-producing if expression requires else with compatible result types.
- else if, exhaustive match, for/in, while, break and continue.
- Strings do not need a second AI-specific notation. Ordinary comments may use #; existing // comments should retain compatibility.
- Prefix typed hole ?name / anonymous hole _ remain development-time constructs; postfix ? means checked propagation of Result errors and requires lexical/parser disambiguation.
- One file is one module; modules are path-identified, imports qualified, aliases optional, visibility explicit via pub.
- Other proposed keywords/syntax: edit, take, danger, uses, async fn, await, spawn, test, fn(T)->U function types and anonymous fn(...) -> U { ... }.

Exact precedence, line-continuation grammar, literal forms, numeric suffixes, qualified names, pub placement, error-path syntax and some capture/task constructs require executable grammar fixtures, not intuitive guesses.

## 3. Types, inference and generic behaviour

### 3.1 Bidirectional typing (DEC-003A)
- Named functions explicitly declare parameter and result types. Local bindings infer types where derivable and unambiguous.
- The type checker synthesises a type from expressions and checks against expected types from bindings, arguments and return positions. Ambiguous situations yield constraints or actionable errors, not guessed defaults.
- No implicit conversion between incompatible types, including numeric narrowing or integer-to-float conversions.
- Preserve partial typed trees, typed holes, their expected types, visible symbols and source spans. Incomplete ≠ invalid ≠ valid complete. Execution refuses unresolved holes.

### 3.2 Parametric generics (DEC-003B)
- Type and function declarations can declare parameters such as Pair[A,B] or count[T]. Concrete type arguments inferred at call sites when unique.
- Generic bodies checked independently of the incidental instantiations that happen in a sample program. Unconstrained T does NOT support ordering, equality or arithmetic unless a contract grants it.
- Compiler may specialise or share generic representation/code if and only if semantics and ABI obligations are preserved. No template or macro system hidden behind generics.

### 3.3 Minimal type abilities (DEC-003C)
- Small compiler-known constraints initially: Equal, Ordered (a genuine total order) and Hashable (consistent with Equal). Numeric operations require separately specified capabilities; do not invent an arbitrary Numeric trait hierarchy.
- Compiler may synthesise structural equality for compatible records, but may not infer a meaningful ordering for Person from arbitrarily orderable fields.
- IEEE NaN is not ordinarily totally ordered. Do not automatically grant Float an Ordered guarantee absent an explicit total-order policy.
- No global arbitrary operator overloading.

### 3.4 Programmer-defined behaviour (DEC-003D)
- Express optional behaviours as ordinary generic records of typed functions, passed explicitly (dictionary-as-value) rather than globally registered typeclass instances.
- Multiple formatters/comparators for one type coexist without invisible import-dependent resolution.
- The same contracts can be inspected by AI agents. Avoid a second language/runtime for typeclass resolution.

### 3.5 First-class functions and closures (DEC-003E)
- Functions can be bound, passed, returned and stored as typed values.
- Anonymous closures capture **logical values by default**; the compiler may share underlying read-only storage safely.
- An explicit edit capture temporarily accesses external state exclusively and initially may not escape the permitted synchronous lifetime.
- An explicit take capture transfers ownership and invalidates the source binding.
- Capturing an environment and calling the closure are separate contracts: one-shot or mutating closure invocation must respect the existing access modes. Exact syntactic spelling pending bounded prototype.
- Function types must preserve effect and access contracts.

### 3.6 Lightweight refinements (DEC-003H)
- Small properties such as positive Int, valid index, bounded length and simple Boolean relationships may be established from flow facts or declared value constraints.
- Conditions established by branches or known constants may refine types; mutation/aliasing must invalidate stale facts.
- When static proof cannot establish a refinement, any runtime validation is explicit and typed (for example checked Result conversion), never silently inserted through annotations.
- Known facts, refuted claims, unresolved obligations and runtime-validated conditions are distinct.
- Start with bounded predictable verification and respect checked Int64 overflow semantics; no arbitrary dependent type/proof-assistant requirements.

## 4. Everyday data and observable value semantics (DEC-001, DEC-005)

**Value semantics:** ordinary data and collections are independent logical values. A later edit of one copy must not mutate an earlier logical copy. Compiler/runtime may safely optimise physical representation using registers, stack allocation, shared immutable data, copy-on-write, regions or managed heap.

Proposed essential types:
- Int: checked signed 64-bit
- Float: IEEE 754 64-bit; Float32: IEEE 754 32-bit
- Bool, Unit
- Str: valid Unicode text in UTF-8 encoding; integer byte-style indexing into Str is disallowed/avoided
- Byte, Bytes: raw binary data distinct from Str
- List[T]: ordered, growable logical value collection
- Array[T,N]: fixed-size value collection
- Map[K,V]: typed key/value map; insertion order is observable; keys need Equal and Hashable
- Option[T], Result[T,E]: ordinary generic tagged union families
- Named record and tagged union types with exhaustive pattern matching

All indexed accesses are safe; if bounds are statically proved, runtime checks may be eliminated. Optional get returns Option. Unchecked raw memory access requires danger, not a default indexing operation. Unicode must distinguish UTF-8 units, scalar values and grapheme clusters. Map deletion/reinsertion order and exact APIs require conformance specification. All conversions remain explicit.

Resource identities and shared mutable objects are distinct from ordinary values: only explicitly typed handles/capabilities may expose shared mutable identity. Some resources are non-copyable.

## 5. Function access: read, edit, take (DEC-002)

- **Read (default):** inspect without caller-visible mutation or ownership transfer. May borrow/copy/share based on semantics.
- **edit:** explicit on callee contract and call site; temporary exclusive caller-owned access. Reject overlapping edits if not proved disjoint. The original owner resumes access after the synchronous edit.
- **take:** explicit transfer; previous binding unavailable. For noncopyable handles, this is how ownership and responsibility change.
- A handle's ownership does not prove unique identity of its referent; capability authority and access rights remain distinct.
- No Rust-like lifetime syntax imposed on ordinary source. Compiler derives lifetimes/aliases where sound, otherwise diagnoses unknown or rejects unsafe case.
- Async suspension/cross-task edit initially prohibited without separately specified proof model.

## 6. Errors, effects and host authority (DEC-003F, DEC-003G)

**Errors:**
- Result[T,E] for expected failure, Option[T] for absence.
- Exhaustive match for recovery; postfix ? propagates compatible typed Result errors. No silent translation between unrelated E types.
- Unexamined Result values must not silently disappear; explicit acknowledgement required if deliberately discarded.
- No general exception mechanism initially. Programming defects, checked traps, resource safety and cancellation have separate semantics.

**Effects:**
- Compiler infers effects of ordinary internal functions.
- Exported APIs and restricted execution contexts declare an effect ceiling (proposed uses syntax). Compiler checks transitive effects against it.
- Function values carry effect requirements in their types.
- A function marked as using fs.read does **not** gain permission to read any file. A host/runtime grants and enforces actual authority separately.
- Absence of filesystem/network effects does not prove termination, deterministic result, no allocation, no GC activity, or a real-time deadline.
- Restricted audio callbacks exclude allocation, reclamation, GC activity, and blocking as separately verified properties; timing bounds need distinct evidence.

## 7. Memory, manual allocation and danger (DEC-006)

Compiler-directed hybrid memory:
1. Use direct/static/stack representations and allocation elimination where safe.
2. Infer scoped regions/arenas where lifetime/escape analysis proves safety.
3. Use a managed heap with precise tracing garbage collection as the provisional general fallback for unrestricted graphs/cycles.
4. Use safe immutable sharing and copy-on-write/reuse when semantically equivalent.
5. Keep specialised real-time, GPU, DMA and external resource domains under explicit contract.

**Manual safe control:** user may specify allocator, size, alignment and deallocation timing through typed, noncopyable owned handles (for example OwnedBuffer[Byte]), without entering danger merely to allocate. memory.free(take handle) consumes ownership; second frees, dangling safe borrows and use-after-transfer are rejected. Failure is a typed Result. Custom allocators carry allocation/deallocation identity in the ownership contract. Scope-based cleanup is the preferred fallback where non-deterministic clean-up cost or effects do not violate the execution context; exact destructor/trap/cancellation ordering requires further specification.

**danger:** bounded block or annotated module permits specific raw pointer/foreign-memory operations but does not turn off every checker. Compiler keeps applying provable layout, lifetime, alignment, alias, bounds and effect checks. Unprovable safety premises are explicit **trusted low-level obligations**, never called proved simply because an author or agent asserted them. Safe wrappers must preserve guarantees for all valid safe callers. Raw pointers across GC require rooting/pinning/lifetime control. GPU/DMA resources outlive submitted work until completion/reliable supervision, including cancellation and device failure.

Implementation algorithms and soundness require prototyping and adversarial testing, especially GC/region crossing, cyclic graphs, nested aliasing, FFI, ownership escape and RT/GPU cleanup.

## 8. Modules, imports and packages (DEC-004)

- File == module; module identity derived from project-relative path.
- pub exports named API declarations, private otherwise; opaque/private representation supported.
- import explicit/qualified, optionally alias as. No wildcard imports.
- Reject cyclic module imports. Importing a module cannot start hidden effectful global initialization.
- Small executable scripts may contain top-level executable statements **only in selected entry source**; importable modules may contain allowed declarations and pure initializers under a clearly defined rule.
- Dependency resolution versioning and reproducible manifest are separate packaging specifications; no hidden network fetch through import.
- Compiler generates a revision-bound inspectable public signature for each module including generics, types, error/effect contracts, visibility, dependencies, source spans and trusted status of associated notes. Other agents need not read every implementation file.
- Module identity/case normalization, path collisions and ABI boundaries need cross-platform tests.

## 9. Async, tasks, isolation and cancellation (DEC-007)

- Structured concurrency by default: explicit task scopes own children; spawn starts concurrent work; await is a suspension point.
- Scope exit/failure coordinates cancellation and *awaits safe resource completion/transfer*. No runaway detached children by default.
- Independent values may copy/share immutably; take moves owned values between tasks. Ordinary edit borrows do not silently cross await or task boundaries.
- Shared mutable state requires explicit identity plus isolation, coordination and suitable typed sync facilities.
- Typed channels and supervised state-owning services first. Locks/atomics in typed libraries if needed; raw primitives only in danger.
- Cancellation is cooperative and observable. An abandoned network/GPU action may still own hardware resources; completion and cleanup responsibilities cannot vanish with a canceled task.
- Task outcomes, cancellation, errors, effects and scheduling are explicit inspectable facts. Data-race freedom does not prove freedom from deadlock, logical race or missed deadline.

## 10. Standard library and native testing (DEC-008; testing amendment)

**Stdlib goals:** practical, layered, primarily written in Pep as soon as expressible; stable typed modules with minimal runtime intrinsics. Prefer libraries to new keywords. Group A: pure text/unicode/bytes/list/array/map/math/parsing/json. Group B: host path/fs/io/process/env/time/random/net/task/sync/memory. Group C: compiler semantic APIs, source/edits/tests and development tools.

Every public operation should be AI-discoverable from *actual checker-owned signatures*: generics, effects, permission requirements, errors, platform availability, version, contracts, examples and tests. Stdlib imports do not grant ambient permissions. Build the library in stages, driven by the Pep-written compiler and real programs. API examples are executable demonstrations, not universal proofs.

**Testing is first-class to the development experience:**
- Compiler-discovered test declarations (proposed test "name" { ... }); typed test functions, property-testing helpers and controlled generators via std.test.
- First-party pep test and pep test --json, with source revision, typed assertion failures, inputs/seeds, targets, observed effects, runtime status, artefacts and reproducible receipts. Tests do not execute in production by default.
- Terror Bats provides design principles and an **independent external adversarial adapter** for cross-tool experiments, not a duplicated embedded engine.
- Explicitly separate test execution status, test assertion outcome and what evidence warrants claiming. In the external adversarial framework, PROVEN means an observed falsification under the recorded conditions, NOT proof of overall correctness. NOT OBSERVED, timeout or crash alone do not certify anything.
- Model-authored suggested tests are proposals; deterministic assertions/oracles judge outcomes. All test execution obeys granted host capabilities; a Git worktree is not a security sandbox.

Testing grammar and runner details are to be validated as part of the syntax/acceptance suite; no tests currently claimed for those future features.

## 11. Semantic Notes, comments and semantic program model

**Accepted three-layer design:** code, optional structured notes, ordinary comments coexist in .pep.

The separate **draft** PEP-SN-001 proposes line-start #@ annotations with exactly three initial tags:
- intent: quoted explanatory context, indexed for AI, never proof.
- verify: a pure Boolean proposition requesting a proof/obligation, never an assume or runtime precondition by declaration alone.
- prefer: a bounded optimisation preference (latency, throughput, size, low_memory), not a timing or allocation guarantee.

The authoritative lexer/parser must retain comment trivia and attach notes to compiler-resolved declarations with original UTF-8 byte spans. Compiler-generated machine views distinguish informational/advisory/unresolved/refuted/proved/invalid, with exact revision, checker/evidence identity and reasons. Unknown names and malformed syntax are diagnosed, not ignored. Removing notes changes no executable behaviour, except that advisory choices may change representation within an equivalent semantic contract.

A formal contract whose failure triggers a runtime error or imposes caller duties must come from an explicit separately accepted language contract mechanism, NOT accidental promotion of #@ verify prose into code.

**Semantic Map:** generated from authoritative checked tree and versioned queries; queryable semantic representation, exact source identity and incremental invalidation/rebuild. The original OCaml seed currently has session-local immutable revisions and same-revision analysis cache only; true cross-revision incremental analysis is future work. The map is not a second grammar or a persistent competing truth store.

## 12. AI-first development and extensions

- Machine discoverability: describe supported language syntax, types, effects, stdlib functions, permissions, tests, compiler revisions and available edit/query operations.
- Typed holes and obligations available before complete programs; constrained completion candidates are checker-derived, not guesswork.
- Structural edits target semantic identity + exact immutable revision; preserve untouched UTF-8 bytes and LF/CRLF style; stale/ambiguous edits rejected or re-queried, never guessed.
- Explicit extension registration, validation by checker and real tests, then separate host-authorised activation. A failed revision cannot silently replace an active tool.
- Extensions written in Pep may help inspect/test/edit Pep programs, but may not rewrite grammar, grant permissions or supersede compiler semantics.
- Compiler results distinguish source fact, inferred proof, heuristic, observed test, host capability, human acceptance and unresolved question.
- Context efficiency: agents discover specific symbols and contracts, retrieving more only when needed. Source, semantic results and evidence outlive a particular AI conversation/model.

## 13. Platform, backend and self-hosting

- OCaml 5.5.2 remains the interpreter-first semantic seed for now.
- Planned Pep-written code generator targets **published C23**, with Clang primary and independent GCC cross-check per TR002, subject to real installed feature probes. Do not accidentally reinstate old C11 commitments.
- Native compiler must produce equivalent Pep behaviour under the same type/error/memory contracts as interpreted Pep. Don't describe generated C23 or self-hosting as implemented until verified.
- Future portability and performance may justify other backends via explicit measured decision; semantics are not defined by incidental C backend behaviour.
- Self-extension precedes full self-hosting where feasible. The goal is a Pep compiler that compiles its own source into a working compiler; keep runtime/toolchain boundaries explicit.

## 14. Open detail register (not permission to redesign foundations)

**Normative work before a grammar freeze:**
- Operator precedence/associativity and exact postfix ? versus typed hole tokens.
- Newline continuation, statement/expression block boundary, return type Unit shorthand, if/match arm grammar.
- Generic declaration, type parameter inference and callable function syntax; explicit escaping closure capture modes.
- Named-argument call syntax (shown in manual-memory examples but not yet accepted generally).
- String escapes/Unicode grapheme APIs; Float and Float32 literals, signed bounds, Int checked overflow, NaN equality/order and numeric conversions.
- Type ability derivation, generic arithmetic contracts, Map Hashable/Equal law checking and insertion order on delete/reinsert.
- Modules path rules and signature/visibility/opaque record details.
- Error translation/wrapping and Result discard acknowledgement syntax.
- Refinement proposition fragment and verification effort/cost, external proof assumptions and runtime validation shape.
- Effects vocabulary, host capability transport and safe behavior of function-typed values.
- Scope semantics of danger and trusted foreign contract review, ownership/cleanup for exceptions/traps/cancellation, allocator identity and pointers.
- Concurrent task result/cancellation propagation, supervised detached work, suspension/closure isolation.
- Native test grammar, test runner privileges, evidence schema/privacy and Terror Bats adapter.
- Semantic Note tags, attachment and query schema remain in separate design PR until reviewed.
- Module entry-point top-level statements compatibility with byte-exact parser and import purity.

These are *real engineering specifications and proof obligations*. Do not handwave them away, and do not let agents silently invent externally visible language semantics. Escalate contradictory accepted rules or irreversible interface changes.

## 15. Acceptance philosophy

A feature becomes shipped only when:
- The grammar and type rules are specified, with valid/invalid/incomplete test fixtures.
- Interpreter and compiler backend behaviour, where applicable, agree on observable semantics.
- Source locations, LF/CRLF and exact original byte offsets are correct.
- Machine-readable versioned interfaces describe ONLY supported features and reject unknown schemas.
- Accepted value, ownership, effects, permission and safety contracts are preserved.
- Tests include adversarial counterexamples and do not promote 'not falsified in this run' to 'proved safe'.
- Reports name actual revision, test count, failures, limitations and evidence. Feature branch pushes are checkpoints, not approval/merge triggers.

See the companion acceptance matrix and compact mission contract before executing work. **This file is a design input, not an instruction to implement all features at once.**
