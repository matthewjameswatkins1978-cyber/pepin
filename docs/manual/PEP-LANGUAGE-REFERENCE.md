# Pep Language Reference

*Design-contract reference derived from the approved 27 October 2026 Pepin language draft*

**Reference edition:** 28 October 2026  
**Design source ID:** `PEP-LANG-FINAL-DRAFT-2026-10-27`  
**Status:** **Accepted design direction; normative grammar and implementation coverage remain incomplete.**  
**Scope:** Pep source language, compiler semantic contracts, host/runtime boundaries, and intended developer interfaces.

This document is a **structured reference for the final design draft**, not an independent new specification. It reorganises the draft for readers and implementers; it does not freeze undecided spelling, choose unaccepted runtime algorithms, or promote code examples to conformance evidence. When a grammar fragment below is marked **proposed**, its final syntax is not yet an executable contract. Where the 28 October priority correction changed the earlier draft's emphasis, that correction is stated explicitly.

**Citation shorthand:** `FD §n` refers to the numbered sections of the [consolidated final draft](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/design/final-language-draft-20261027/docs/final-draft/PEP-LANG-FINAL-DRAFT-2026-10-27.md). `DEC` refers to the accepted decisions it consolidates. `TR001/TR002` refer to technical resolutions. `V0–V11` refer to planned completion milestones, **not released versions**.

## Reference map

1. [Status, source, and authority](#1-status-source-and-authority)
2. [Source units, lexical form, and layout](#2-source-units-lexical-form-and-layout)
3. [Declarations and naming](#3-declarations-and-naming)
4. [Expressions, statements, and control flow](#4-expressions-statements-and-control-flow)
5. [Static types and inference](#5-static-types-and-inference)
6. [Data and value semantics](#6-data-and-value-semantics)
7. [Function values and access contracts](#7-function-values-and-access-contracts)
8. [Error handling, effects, and authority](#8-error-handling-effects-and-authority)
9. [Memory, resources, and danger](#9-memory-resources-and-danger)
10. [Modules, visibility, and packages](#10-modules-visibility-and-packages)
11. [Structured concurrency](#11-structured-concurrency)
12. [Standard library organisation](#12-standard-library-organisation)
13. [Testing and evidence](#13-testing-and-evidence)
14. [Compiler semantic interface and source revisions](#14-compiler-semantic-interface-and-source-revisions)
15. [Runtime, native backend, and portability](#15-runtime-native-backend-and-portability)
16. [Open normative decisions](#16-open-normative-decisions)
17. [Implementation coverage and conformance](#17-implementation-coverage-and-conformance)
18. [Design provenance](#18-design-provenance)

---

## 1. Status, source, and authority

Pep is the **small statically typed language**; `.pep` is its file extension. Pepin is the project/environment. Lucy is the intended name of its eventual compiler. Pep is AI-first because its authoritative checker provides machine-readable, revision-bound information and safe edits, not because execution calls an LLM. Plain Pep source and deterministic checks remain the program's authority. *(FD §§0–1, 12.)*

### Evidence and status classes

The following states are not interchangeable:

| State | Meaning |
| --- | --- |
| **Accepted design direction** | The language behaviour or architecture Matthew approved as the target |
| **Proposed syntax/contract** | A spelling or detail illustrated in the draft but awaiting grammar/conformance acceptance |
| **Implemented seed feature** | Present in the accepted OCaml seed, for the documented subset |
| **Development branch feature** | Code and tests exist on a branch; may not have been integrated or accepted |
| **Verified at a revision** | Exact source/backend/test evidence exists for a named SHA and scope |
| **Released** | Explicit release acceptance and packaging; not implied by a pushed branch |

A language example, an AI assertion, a test result, a compiler proof, and a human release approval are different kinds of evidence. This reference never treats one as another. `master` remains accepted only through A8 in the cited baseline. *(FD §§1, 15; Road 2.)*

### Design precedence

- **DEC-001 and DEC-005 supersede earlier reference-like collection guidance:** ordinary collections are independent logical values.
- **TR002 supersedes historical C11 planning:** the intended native code generator targets **C23**.
- **28 October priority correction:** compiler-derived knowledge and read-only stage checkpoints are one architecture; early Pep-written standard-library work is the practical priority. Optional `#@` Semantic Notes, although present in the 27 October design text, are **not the central architecture or an unconditional 1.0 release blocker**. No claim written in comments is authoritative.

## 2. Source units, lexical form, and layout

### Source files and revisions

Each `.pep` source file is canonical editable plaintext. Source identity and semantic outputs are bound to exact immutable revisions. A source-preserving edit must retain untouched original bytes, including LF/CRLF style, and refuse stale or ambiguous targets. UTF-8 byte offsets must be distinguished from user-facing line/column coordinates. The parser/checker can report a program as **valid**, **invalid**, or **incomplete**. Incompleteness arising from typed holes is not permission to execute. *(FD §§0, 2, 12, 15; TR001.)*

### Lexical surface: accepted direction

| Surface | Intended meaning | Status |
| --- | --- | --- |
| `{ ... }` | Lexical blocks and declarations | Existing style, draft-approved |
| `fn name(...) -> Type { ... }` | Named typed functions | Seed-style syntax |
| `let name = expression` | Immutable binding | Seed |
| `var name = expression` | Mutable binding | Seed |
| `name = expression` | Assignment to suitable mutable binding | Seed |
| `# explanation` | Ordinary source comment | Draft direction; existing `//` compatibility preserved |
| `;` | Optional explicit statement separator | Proposed; newline grammar pending |
| `?name` and `_` | Named or anonymous development-time holes | Seed principle; token grammar evolving |
| `expression?` | Propagate a compatible `Result` error | Design; postfix disambiguation pending |
| `pub`, `import`, `as` | Module visibility/imports | Accepted direction; path grammar pending |
| `edit`, `take`, `danger`, `uses` | Access, low-level, effect syntax | Accepted direction; details pending |
| `async fn`, `await`, `spawn`, `test` | Structured tasks and tests | Proposed surface grammar |

**No mandatory semicolons** is accepted. Newlines should separate ordinary statements unless a precisely recognised continuation applies. Continuation inside parentheses/brackets and unfinished expressions is intended. *The exact lexical and parser rules have not been frozen.* Avoid asserting precise precedence, indentation significance, numeric suffixes, or automatic line joining where no tested grammar exists. *(FD §2; DEC-009.)*

### Exclusions

The accepted design intentionally avoids classes and inheritance as core language features, macros that redefine language semantics, arbitrary operator overloading, wildcard imports, implicit conversions, a second AI-only source syntax, and global implicit behaviour resolution. *(FD §§2–3, 8; DEC-009.)*

## 3. Declarations and naming

### Variable declarations

`let` binds an immutable value. `var` binds a value that may be reassigned consistently with its type. Local annotations can be omitted when the checker uniquely determines a type. Named function parameter and result types are explicit. *(FD §§2–3; DEC-003A.)*

**Seed-form illustration:**

```pep
let count: Int = 3
var next = count + 1
next = next + 1
```

No general ambient mutation is implied by `var`: it governs the binding and the type's access rules.

### Type declarations

The design contains nominal record declarations and tagged unions. Examples of proposed accepted source forms:

```pep
type Point {
    x: Int
    y: Int
}

type Answer = Yes() | No()
```

The seed supports monomorphic named records and tagged unions, constructors, field access, and exhaustive matching. Visibility and opaque representation of module exports are additional design obligations. *(FD §§3–4; DEC-005.)*

### Function declarations

```pep
fn twice(x: Int) -> Int {
    return x + x
}
```

Function signatures are checked independently of incidental call sites. Recursion and forward calls are part of the seed. `pub fn` is the proposed exported declaration form; a module remains private by default. Generic declarations and explicit effect ceilings extend the same concept without requiring a different source language. *(FD §§2–3, 8.)*

### Declaration form still open

Exact function-type syntax, generic constraints, visibility placement in every declaration, callable captures, module-root top-level statement rules and other production grammar need conformance fixtures. The design favours a compact grammar, not a collection of equally privileged alternative spellings.

## 4. Expressions, statements, and control flow

### Blocks and returns

A named function has an explicit result type. The draft accepts explicit `return`. Its precise rules for statement blocks versus value-producing blocks are not fully frozen. `Unit` is the logical no-value result type; any shorthand for omitted `-> Unit` needs a real grammar decision. *(FD §§2, 14.)*

### Conditions

A value-producing `if` **requires an `else`** whose branch has a compatible result type. A statement-form `if` may omit `else`. `else if` belongs to the final design. The condition must have `Bool` type. The exact expression/statement parser boundary remains to be finalised. *(DEC-009.)*

```pep
let larger = if left <= right { right } else { left }
```

**Seed-form illustrative expression.** This is not an independent proof of exact grammar precedence.

### Pattern matching

`match` checks tagged alternatives and nested patterns. Exhaustiveness is a static obligation for expressions over a closed union; wildcard and binding patterns are allowed in the seed. An unmatched required branch must not silently succeed. Numeric and record pattern coverage and precise arm grammar need versioned tests. *(FD §§2, 4.)*

### Loops

`while` and `for value in collection` belong to the seed's documented control flow. `break` and `continue` are accepted draft extensions with parser details to verify. Short-circuit Boolean operators and scalar equality are documented seed operations; full generic equality must respect the `Equal` ability contract. *(FD §§2–3; DESIGN.md.)*

### Evaluation guarantees not to invent

Do not infer undocumented operator precedence, exact evaluation order for all future constructs, implicit casts, automatic error coercions, or allocation effects from the examples. Those require explicit rules and negative tests before a normative grammar freeze.

## 5. Static types and inference

### Core typing: DEC-003A

The checker uses **bidirectional typing**: it synthesises types where possible and checks expressions against expected types from contexts. Incompatible types cannot be reconciled by invented implicit conversions. Unresolved typed holes preserve context and expected type but prevent execution. A program with an invalid type must fail closed. Named function signatures contain explicit parameter and result types. *(FD §3.1.)*

### Generic types: DEC-003B

Generic functions and nominal types support type parameters. The proposed surface includes `fn identity[T](value: T) -> T` and constrained parameters such as `[T: Ordered]`. Type arguments may be inferred only when the solution is unique. A generic body is checked by its declared constraints, **not** merely by observing the concrete types used in a few test programs.

Unconstrained `T` is not automatically numeric, equatable or orderable. The compiler may monomorphise, specialise, or share representation where semantics and ABI remain equivalent; no template-style macro system is added. *(FD §3.2.)*

### Abilities: DEC-003C

| Ability | Contract |
| --- | --- |
| `Equal` | Meaningful equality on the type |
| `Ordered` | A genuine **total order** consistent with its specification |
| `Hashable` | Hash equality compatible with `Equal` |

The final derivation rules and laws must be specified. Structural equality may be synthesised for suitable records. Order is **not** automatically synthesised for every record, and IEEE floating values with NaN do **not** receive an ordinary total ordering without a separately defined policy. Arithmetic constraints are a separate open design question, not an invitation to invent a general `Numeric` trait hierarchy. *(FD §3.3.)*

### Behaviour values: DEC-003D

Rich behaviour is represented by explicitly passed, typed values such as records of functions. There is no invisible global typeclass-instance lookup dependent on imports. This permits multiple comparators or formatters for one type and makes dependencies inspectable. Exact library types remain to be settled with the first-class function facility. *(FD §3.4.)*

### Refinements: DEC-003H

Small value propositions (e.g. positive integer, bounded length, valid index) may be inferred from checked flow facts or supplied through an explicit language contract. Mutation and aliasing must invalidate stale facts. When static proof fails, an explicit typed runtime validation may be used; the compiler must distinguish **proved**, **refuted**, **unresolved** and **runtime-validated** claims. There is no promise of an unrestricted theorem prover or arbitrary dependent typing. *(FD §3.6.)*

## 6. Data and value semantics

### Primary type inventory

| Type or family | Target contract | Seed evidence boundary |
| --- | --- | --- |
| `Int` | Checked signed 64-bit integer | Seed supports checked arithmetic |
| `Bool` | Boolean logical value | Seed |
| `Unit` | No-value result | Seed |
| `Str` | Valid Unicode text encoded with UTF-8 | Seed `Str`; full Unicode API pending |
| `Float`, `Float32` | IEEE 754 64-/32-bit floats | Target, not established complete |
| `Byte`, `Bytes` | Raw binary distinct from text | Target; seed has separate source-byte tooling on branches |
| `List[T]` | Ordered, growable logical collection | Restricted seed lists with `append`/`length`/`contains` |
| `Array[T,N]` | Fixed-size typed collection | Target |
| `Map[K,V]` | Typed map; observable insertion order | Target, API/order details unresolved |
| `Option[T]` | Value or absence | Target generic family |
| `Result[T,E]` | Success or expected typed error | Target generic family |
| Named records and tagged unions | Statically checked nominal data | Seed monomorphic subset |

*(FD §4; DEC-001/005.)*

### Independence of ordinary values

The externally observable rule is that **editing one ordinary value must not mutate another independent logical value**. A compiler can use alias-free physical copies, shared immutable backing storage, copy-on-write, regions, direct value layouts, or a managed heap when safe. Physical sharing must never leak a mutation into a different logical value. This rule supersedes the earlier founding v0.3 reference-like collection language. *(FD §§1, 4.)*

### Indexing

Every ordinary indexed access is safe. Statically proven in-bounds access may omit runtime checks; an out-of-range access must not cause raw memory corruption. An optional access can return `Option`. Unchecked raw access requires a deliberately approved `danger` operation, not the default indexing syntax. Final APIs and boundary conditions remain to be frozen. *(FD §4.)*

### Text

`Str` must contain valid text. API contracts should distinguish UTF-8 bytes, Unicode scalar values and grapheme clusters. Literal escapes, segmentation version and exact indexing/iteration operations remain open. Binary `Bytes` cannot silently be reinterpreted as `Str`. *(FD §§4, 14.)*

### Map ordering

Insertion order is observable and deterministic. Updates, deletion and reinsertion behaviour are an explicit unresolved conformance table; do not silently inherit incidental host-language hash table order. Keys must meet appropriate `Equal`/`Hashable` requirements. *(FD §§4, 14.)*

### Numeric special cases

Checked `Int64` overflow is a runtime safety contract. Floating NaN/negative zero/infinities, conversions, integer bounds, literals and roundings require normative fixtures. The C23 backend may not quietly adopt undefined overflow or otherwise change Pep's arithmetic semantics. *(FD §§3, 4; acceptance matrix §3.)*

## 7. Function values and access contracts

### Parameter access: DEC-002

Every function parameter has an explicit or default access mode:

- **read**, the default: inspect without caller-visible mutation or ownership transfer.
- **edit**: exclusive temporary access to an existing caller-owned value; exclusivity and lifetime must be proven; original owner resumes afterwards.
- **take**: explicit ownership transfer; the source binding is no longer available.

The access mode appears in the callee's contract and, when applicable, at the call site. The final spelling for all call-site forms is still subject to tested grammar. Overlapping exclusive edits must be refused unless provably disjoint. Captures and aliases cannot be silently used to subvert exclusivity. *(FD §5.)*

### First-class functions and closures: DEC-003E

Functions may eventually be stored, passed and returned as typed values, using a proposed shape `fn(T) -> U` and anonymous `fn(...) -> U { ... }`. Logical values are captured by default. An explicit edit capture is exclusive, temporary and initially nonescaping from its permitted synchronous scope; a take capture transfers ownership. Exact capture syntax, escaping, one-shot calls and effect-bearing function types remain unfinished grammar/safety contracts. *(FD §3.5.)*

### Lifetimes

The compiler should infer safe lifetime/alias relations without routine programmer-authored lifetime annotations. An unsupported or unprovable escape must be diagnosed or rejected rather than permitted speculatively. Asynchronous suspension with an outstanding ordinary edit borrow is not generally permitted in the initial access model. *(FD §§3.5, 5, 9.)*

## 8. Error handling, effects, and authority

### Expected failure: DEC-003G

`Result[T,E]` represents success (`T`) or typed expected error (`E`). `Option[T]` represents presence or absence, not general failure. Recovery can use exhaustive `match`. Postfix `?` is intended to extract the success value and propagate a compatible `Result` error from the current function. Implicit conversion between unrelated error types is forbidden; explicit mapping/wrapping must have a separately specified mechanism. Unexamined `Result` cannot be silently discarded. The acknowledgement syntax remains open. General exceptions are not the initial error model. *(FD §6.)*

The tokenizer must distinguish postfix propagation `?` from named prefix typed holes `?name` and anonymous `_` holes. No released source grammar should accept an ambiguous case by accident.

### Effects: DEC-003F

Internal functions infer effects. Public functions and restricted execution contexts declare a transitive **effect ceiling**, provisionally spelled with `uses`. Calls through helpers, generic instantiations and function values must respect the caller's ceiling. Type signatures of first-class functions carry relevant effect requirements. The full effect vocabulary and grammar remain open. *(FD §6.)*

### Authority is external

An effect declaration describes a requirement, **not a grant**. `uses fs.read` cannot authorise reading a file. The host separately grants and enforces filesystem, network, process or other authority. Importing a library also cannot grant a capability. Capabilities and resource ownership are independent notions: owning a handle does not necessarily give arbitrary access to what the handle denotes. *(FD §§5, 6, 8, 10.)*

### Non-effects are not stronger proofs

“No external effect” does not mean termination, deterministic scheduling, no allocation, no GC activity, no blocking, or a bounded latency. Restricting real-time code requires additional verified transitive properties. *(FD §§6, 7.)*

## 9. Memory, resources, and danger

### Compiler-directed hybrid memory: DEC-006

The intended safe implementation chooses between stack/direct storage, inferred regions/arenas, immutable sharing/COW, and a managed heap where necessary. A **precise tracing GC is the provisional fallback design**, not a fully verified accepted runtime algorithm. Optimisation does not relax Pep's observable value, access, lifetime or ownership rules. *(FD §7.)*

### Safe explicit allocation

A programmer may request an allocator, size, alignment and deallocation timing through **typed, noncopyable owned handles** without entering `danger` solely for allocation. An illustrative type is `OwnedBuffer[Byte]`, and illustrative consumption is `memory.free(take handle)`; these are **design examples**, not currently established stdlib signatures. Double-free, use after take, illegal borrows, allocator mismatch and dangling safe references must be prevented or diagnosed by the accepted ownership contract. Scope-based cleanup may be used where its timing/effects fit the context. The exact destructor, cancellation, panic/trap and allocator failure rules remain to be settled. *(FD §7.)*

### Danger and trusted obligations

A `danger` block or appropriately scoped module permits specific low-level/foreign-memory operations. It does **not** suspend all checker rules. Checkable bounds, alignment, lifetime, layout, aliasing and effect constraints must still be enforced. Any remaining premise outside the compiler's proof capabilities is an **explicit trusted low-level obligation**. A wrapper cannot claim safety merely by surrounding operations with `danger`. The exact scopes and trust/FFI contracts remain an open normative item. *(FD §§7, 14.)*

### GC roots, real-time execution and hardware

Raw foreign pointers crossing GC boundaries need rooting, pinning and a validated lifetime policy. GPU/DMA buffers remain owned or supervised until device work actually completes, even on cancellation or device failure. Protected real-time code may require separately enforced **no-allocation, no-GC, no-reclamation and no-blocking** contracts. Worst-case timing must be independently evidenced; it is not inferred from ordinary type correctness. *(FD §7; matrix §6.)*

## 10. Modules, visibility, and packages

The target is **one file, one module**, identity derived from a project-relative path. `pub` exports declarations; others are private. Qualified `import` and optional alias `as` are accepted directions. Wildcard imports are excluded. Public opaque types may conceal representation. Imports must reject cycles and may not silently run effectful global initialisation. Entry files may execute top-level statements; importable modules use declarations and permitted pure initialisation. Precise path/case collision and export semantics need cross-platform conformance. *(FD §8; DEC-004.)*

### Machine-readable module contracts

The compiler should provide a revision-bound checked public signature containing exported types, functions, generics, access modes, effects/errors, source spans, dependencies, visibility and supported status. Manual duplicate interface files should not become a competing authority. Package manifests/locks must be reproducible; `import` alone does not permit an implicit network fetch. *(FD §8.)*

## 11. Structured concurrency

### The task model: DEC-007

The accepted principle is **structured** asynchronous work: an owning scope supervises children. Proposed spellings include `async fn`, `spawn`, `await` and an unfinalised `task.scope` construct. Children are not detached without explicit supervision; scope exit coordinates cancellation and safe completion/resource ownership. *(FD §9.)*

### Safe transfer

Independent values may be copied or shared immutably. Ownership transfer uses `take`; an ordinary temporary `edit` does not silently cross task or await boundaries. Shared mutable state needs explicit identity/isolation and suitable typed coordination. Typed channels and supervised services are the initial preferred facilities; locks and atomics may live in verified typed libraries, raw variants under bounded `danger`. *(FD §9.)*

### Cancellation and safety

Cancellation is cooperative and observable. Task outcomes and child errors must be supervised. Cancelling foreign I/O or a GPU submission does not prove hardware stopped using its resources. A data-race-free program is not automatically deadlock-free, logically race-free or deadline-safe. Exact task result, cancellation, cleanup and scheduling contracts remain open. *(FD §§9, 14.)*

## 12. Standard library organisation

The target library is **layered and primarily written in Pep as soon as the language supports it**, using narrow native intrinsics only where irreducible or justified by evidence. Prefer a checked library function over a new keyword. *(FD §10; DEC-008; later priority.)*

| Layer | Intended responsibilities | Status |
| --- | --- | --- |
| Pure foundations | `Byte`/`Bytes`, UTF-8 and Unicode text, buffers, list/array/map, math, parsing, JSON | Accepted target; partial seeds and Pep-written collections development |
| Host facilities | path/fs/io/process/env/time/random/network/task/sync/memory | Accepted target; grants/effects required; not guaranteed implemented |
| Development | semantic queries, source/edit APIs, tests, compiler tools | Accepted target; several seed operations and test runner exist in subsets |

Public stdlib functions should expose actual checker-derived, machine-queryable contracts: generic parameters, access mode, types, errors, effects, granted-capability requirements, platform availability, examples and real tests. **Documentation and comments may describe intent but cannot replace checked signatures.** The latest owner priority moves foundational Pep-written stdlib development earlier in the practical plan, not after all runtime features. *(28 October priority decision.)*

## 13. Testing and evidence

### Accepted testing direction

Compiler-discovered `test "description" { ... }` blocks, typed test helpers in `std.test`, `pep test`, JSON receipts, bounded property testing and independent adversarial adapters are design targets. Test declarations should not execute as normal production entry code by default. Exact test grammar and test-runner privilege/isolation rules remain open. *(FD §10; testing amendment.)*

### Working but separate development capability

At GitHub SHA [`52a75d6`](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/52a75d668b6b3158c603accb757674f26114c75d), a development branch contains a **manifest-driven** first-party `pep test` runner and additive CLI dispatch, without compiler-recognised test syntax. Agent-reported Windows verification: 17/17 adversarial Python tests; actual `pep.ps1 test --json` reports 12 passing source fixtures and one intentional skip with zero unexpected failures. The exact remote SHA is confirmed, but this edition does **not** independently rerun those tests. Do not infer `std.test`, property testing, multi-backend coverage, or a security sandbox from this milestone.

### Honest outcomes

Tests need distinct statuses for the process's **execution outcome**, assertion/oracle result, and evidence. They should record exact revisions, target/toolchain, permissions (declared, requested, granted, enforced), seeds, duration/limits, and saved artifacts where available. Missing evidence, denied permission, crashes, hangs and inconsistent output must not be mistaken for passing assertions. A test corpus does not prove all programs correct. *(FD §10; matrix §8.)*

**External Terror Bats terminology:** `PROVEN` means the trial has established a particular falsification, not that a program is universally safe. `NOT OBSERVED` and inconclusive outcomes likewise must be interpreted only within the reported experiment.

### Sandbox boundary

A Git branch or worktree isolates source edits, **not** malicious filesystem/network/process effects. Hostile tests require genuine process/OS containment and granted-capability policy. No test tool should claim security properties it did not enforce. *(Acceptance matrix §6.)*

## 14. Compiler semantic interface and source revisions

### One checked authority

Parsing, source scopes, types, checked trees, access/effect judgments, runtime eligibility, queries, edits, and test discovery must derive from **one deterministic compiler semantic authority**. An LLM cannot create a verified type/proof by assertion; an independent persistent “semantic map” cannot secretly drift into a second typechecker. The authoritative program model may expose stages and checkpoint queries over the **same** checked information. *(FD §§0, 11–12; later priority.)*

### Partial programs and typed holes

The parser/checker retains incomplete trees and expected types at holes, plus visible bindings and source spans. Incomplete programs are inspectable, but execution refuses unresolved holes. Proposed fill candidates are checked; ambiguous scope/revision targets are rejected. The seed supports named-hole fill against an immutable in-process revision; full arbitrary structural edits are a future contract. *(TR001; FD §12.)*

### Revision-bound semantics

A semantic response must specify the exact source revision and checker/proof/test identity. Stale data cannot silently be applied after the program changes. Changes should preserve untouched original source bytes and line endings. The seed currently retains in-process immutable revisions and a same-revision analysis cache; robust incremental reuse across *different* builds/revisions is not yet established. *(FD §§11–12.)*

### Source notes

The 27 October draft described optional `#@ intent`, `#@ verify`, `#@ prefer` in a **separate draft proposal**, as descriptive/advisory/verification-request material, never proof or permission. The **28 October owner priority explicitly superseded annotation-centred semantics as core architecture**. The 1.0 compiler-knowledge architecture should derive facts from checked code and stage checkpoints; ordinary comments remain appropriate. Do not interpret unapproved note syntax as an executable language feature or make annotations a release gate without a new accepted decision.

### Extensions

Pep-written extensions may be checker-validated and tested, then **separately activated by the authorised host**. They cannot redefine Pep grammar, evade semantic contracts, or grant permissions. The seed already has local tool registration, test-vector validation, activation, hot replacement and bounded typed transport in specific versions; it is trusted-local, **not** an untrusted sandbox. *(FD §12; seed tool protocol.)*

## 15. Runtime, native backend, and portability

### Seed and target

The current foundational compiler is an OCaml 5.5.2 seed. A future Pep-written Lucy compiler aims to generate **C23** and ultimately compile itself, with Clang as the primary and GCC as an independent native check. The exact supported C23 feature subset and toolchain behaviour require tests; an OCaml-led Pep-written stage is not an independent fully self-hosted compiler. C code generation may not change Pep's checked arithmetic, data, error or ownership semantics. *(FD §13; TR002.)*

### Self-hosting proof

An A→B→C bootstrap must demonstrate a Pep-written compiler producing a working compiler that can compile itself again without the OCaml seed as a normal compiler dependency. Document the remaining external C23 toolchain/runtime clearly. Self-hosting alone is **not** full Pepin 1.0: the accepted language type, memory, effects, concurrency, stdlib and semantic tool contracts still need conformance. *(Road 1 / Road 2.)*

### Portability

No platform is supported by assertion. Stable source semantics must survive interpreter/backend and cross-toolchain differential testing. Package availability, operating systems/architectures, filesystem path rules, numeric edge cases, Unicode behaviour, memory safety, and feature gaps need an explicit published matrix. *(FD §§13, 15; matrix.)*

## 16. Open normative decisions

The signed-off design **deliberately leaves the following detail work for real grammar and conformance decisions**. This list is an accuracy safeguard, not permission to alter accepted foundations. *(FD §14; Road 2 V0.)*

| Area | Required contract before normative freeze |
| --- | --- |
| Lexing and layout | Operator precedence/associativity; multiline/newline continuation; optional semicolon; expression vs statement blocks; holes vs postfix `?` |
| Names and functions | Generic declaration/constraint grammar; inferred type arguments; capture mode/call syntax; function-value effect/access type syntax; `Unit` shorthand |
| Data and numbers | Float/Float32 literals, numeric conversions, NaN/zero/overflow rules; string escaping; Unicode version and grapheme APIs |
| Collection laws | `Equal`/`Ordered`/`Hashable` derivation; Map deletion/reinsertion order; exact indexing APIs |
| Modules | Module path/case identity; aliases; visibility and opaque types; entry-file execution and import purity |
| Errors and effects | Error conversion/wrapping; explicit Result discard; `uses` vocabulary and transitivity; host grant transport |
| Refinements | Bounded proposition grammar; proof statuses; runtime validation forms and costs |
| Memory | `danger` scope, allocator/owned-pointer types, cleanup/trap/cancellation order, FFI rooting and pinning |
| Concurrency | Task scope/result spelling, propagation and cancellation semantics, closure isolation and supervision |
| Testing | Test declaration grammar, discovery, assertion/library contracts, permissions, JSON privacy/evidence schema |
| Semantic system | Revision queries, proof validity/invalidation, stage checkpoints; explicit contracts replacing speculative annotations |

**Not acceptable:** quietly adding a type class, new implicit conversion, ambient host grant, hidden unsafe escape, or ad hoc grammar production to fill one of these gaps. Open semantic conflicts require a deliberate reviewed owner decision and conformance tests.

## 17. Implementation coverage and conformance

### Status snapshot for 28 October 2026

| Family | State at documented baseline |
| --- | --- |
| Scalars, functions, records/unions, lists, loops, typed holes, source spans and session queries | Accepted seed **subset** |
| Pep-written parser/checker, restricted C23 backend and stdlib primitives | Experimental campaign **partial**; actual backend parity varies by feature |
| External-manifest `pep test` | Development lane at `52a75d6`, **agent-verified mission**; review/integration separate |
| General generics, closures, ability system, modules, effect/error algebra and full text/data families | Final design target; not established complete |
| Ownership/memory soundness, foreign resources, task supervision, security grants | Final design target with outstanding proof obligations |
| Full Pep-written Lucy + A→B→C self-bootstrap + Pepin 1.0 | Not verified or released |

### Acceptance checklist

Before claiming a language feature complete, the implementation needs: a specified grammar; positive/negative/incomplete fixtures; exact spans and source revisions; interpreter/native parity where relevant; wrong-type, wrong-effect, wrong-grant, ownership, and boundary adversarial tests; an accurate machine-readable capability contract; and SHA-bound test records. Runtime safety cannot be inferred just from a compiling happy path. *(FD §15; acceptance matrix.)*

The documentation itself must be updated from real evidence once features are accepted. Do not mechanically turn a plan or development-branch result into an official supported-feature table.

## 18. Design provenance

### Primary authority, in intended reading order

1. [Pep final design draft, 27 October 2026](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/design/final-language-draft-20261027/docs/final-draft/PEP-LANG-FINAL-DRAFT-2026-10-27.md), source ID `PEP-LANG-FINAL-DRAFT-2026-10-27`, docs-only design branch / PR #14.
2. [PEP-DEC-009 surface syntax sign-off](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7Caf91b899-62b4-4c8f-8a1e-429bda9d4fa3).
3. [28 October owner priority correction](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7C563c337a-eb00-4cb4-aa42-95a2ba584a73) and [Road 2 release scope](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/ROAD-2-PEPIN-1.0.md).
4. [Final draft acceptance and adversarial matrix](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/design/final-language-draft-20261027/docs/final-draft/ACCEPTANCE-MATRIX.md).
5. [Current OCaml seed implementation index](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/DESIGN.md), [seed bounds](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/SEED_LANGUAGE.md), [full-language evidence ledger](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/FULL-LANGUAGE-LEDGER.md).
6. [First-party test runner's final development SHA](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/52a75d668b6b3158c603accb757674f26114c75d).

### Editorial policy for future versions

Revise the reference when the project accepts a normative grammar/semantic rule or verifies a released feature, **not** merely because a worker experimented with a spelling or a test passed in an isolated branch. Record the decision ID, implementation SHA and relevant positive/negative conformance evidence for each change. Preserve human-readable Pep source as the program's truth and Lucy's checked semantic output as its machine interpretation.

---

*This is the reference companion to [The Pepin Manual](PEPIN-MANUAL.md). It is deliberately faithful to the accepted draft's unresolved questions: accuracy is more valuable than a confident but invented rule.*