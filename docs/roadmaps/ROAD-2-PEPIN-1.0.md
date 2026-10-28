# ROAD 2 — Pepin 1.0: Finish the Entire Accepted Pep Language

**Planning baseline:** 28 October 2026. **Type:** release-quality product roadmap, not code implementation authority or an accepted release tag.
**Prerequisite:** [Road 1: reproducible bootstrap](ROAD-1-REPRODUCIBLE-BOOTSTRAP.md). Work can overlap before its last gate if dependencies permit; bootstrap completion does **not** satisfy this roadmap.
**Inventory:** [FULL-LANGUAGE-LEDGER.md](FULL-LANGUAGE-LEDGER.md). **Companion acceptance:** design PR #14 final-draft matrix. Later precedence: user priority decisions in Basic Memory and draft PR #17.

## Product contract and what 1.0 must mean

**Pepin 1.0 is a complete implementation of the accepted small Pep language and its AI-first programming environment**, with demonstrably correct native execution, dependable library/tool contracts and published limitations. The source language remains compact and conventional; its power comes from the compiler and composable typed Pep libraries. AI agents are the primary intended operators; humans must still be able to read, verify and govern ordinary source and results.

**Lucy** is the intended name of the Pep compiler; **Pep** the language; **Pepin** the environment. Do not assume any proposed executable naming is already implemented.

A working self-hosted compiler proves **independence from the OCaml seed for its compiler source subset**. Pepin 1.0 additionally proves the accepted *user-facing language*, runtime, safety and tooling contract.

**Scope discipline:** no accepted DEC-001/002/003A-H/004–009 feature may be omitted merely because bootstrap does not need it. A hard unresolved design choice must be made explicit and submitted for Matthew's decision; document any owner-approved contract revision before claiming full 1.0. This is not an invitation to add every fashionable language feature.

## Authority and priority reconciliation

1. **Binding semantic direction:** accepted individual Basic Memory decisions DEC-001/002/003A-H/004–009 and accepted consolidated final draft (design PR #14), except where a later explicit Matthew decision supersedes a particular detail.
2. **Later supersession:** compiler-derived semantic knowledge is primary. Annotation-centred #@ Semantic Notes / draft PR #13 is **superseded as the core direction**; do not treat its proposed tags as a 1.0 blocker or implement a hidden annotation language. Plain comments remain. Formal explicit program contracts are allowed only through accepted typed mechanisms and separately specified grammar.
3. **Latest project priorities:** (#1) Lucy's compiler-derived understanding + (#5) read-only stage checkpoints are ONE compiler semantic architecture; (#2) bottom-up **Pep-written standard library** is the primary practical near-term build focus. Rabbit tutor/learn (#3), broad tool ports (#4), and separate multiparadigm/OOP/logic framework exploration (#6) are deferred. Preserve useful UX design ideas without interrupting core compiler work.
4. **Release authority:** master/CURRENT/manifest remain A8 until separate integrated verification and Matthew's approval. Development branches, this roadmap, successful tests and self-hosting do not authorise auto-merges or a 1.0 release.

## Roadmap dependency shape

**Bootstrapped Lucy** + **stable grammar/type declarations and modules** -> **general values/generics/callable types and errors** -> **safe lifetime/ownership/effect contracts** -> **native runtime/FFI/memory and concurrency** -> **complete Pep-first stdlib and tests** -> **AI-first semantic model/edits** -> **feature-complete compiler conformance** -> **RC hardening** -> **Matthew's 1.0 acceptance**.

These overlap vertically: build the smallest useful library early, not at the end; test a feature in interpreter/checker/backend in the same slice rather than accumulating unimplemented paper features. Contract-freeze before RC, not before learning from real programs.

## V0 — Release contract, open questions and conformance inventory

**Goal:** convert the final design **draft** into executable normative grammar and semantic contracts without replacing accepted values.

- Produce a versioned grammar/precedence/line-continuation specification for let/var, blocks, expressions, if/match, loops, declarations, modules, pub, generic brackets, prefix holes vs postfix Result ?, captures, effect ceilings, test, async, danger.
- Decide and pin exact behavior of numeric literal suffixes/casts/NaN, Unicode and grapheme APIs/version, Map hashing/equality/insertion order after deletion, error propagation/discard, module path/case normalization and import purity, externally safe memory/FFI contracts, cancellation/cleanup and test permissions.
- Formalize a stable supported versioned compiler/CLI/JSON schema with explicit compatibility/deprecation rules, avoiding the invention of a second AI-only language.
- Mark all rows in the [full-language ledger](FULL-LANGUAGE-LEDGER.md) **ACCEPTED DESIGN / NEEDS CONTRACT / IMPLEMENTED / TESTED** separately. Do not mark an unimplemented design as implemented.
- Capture product-owner decisions on actual contradictory syntax or irreversible runtime/ABI trade-offs. Agents may choose routine reversible algorithms.

**Gate V0:** grammar and semantic tables can be run as positive/negative/incomplete fixtures; unresolved contradictions are visible with owners. Reviewer confirms no silent incompatible changes to DEC-001, DEC-002, value semantics, checked effects or host authority.

## V1 — Complete the language front end, modules and source model

**Features:** complete lexical forms, deterministic parse tree, recoverable incomplete programs, typed holes, original UTF-8 byte offsets/LF/CRLF/invalid UTF-8; named functions and forward/recursive calls; variable scope and assignment; if/while/for/break/continue, match exhaustiveness and nested patterns; file-based modules, private-by-default pub exports, qualified import and optional as, opaque exports, no effectful hidden initialization, import cycles rejected; separate entry-only top-level execution.

**Required integration:** canonical checked source revision is a hard boundary: no C23 backend, test runner, semantic API or source edit can silently reuse facts for another revision. Support compiler-readable public signatures with declared type/effect/errors and source identity. Make parser/checker performance scale on genuinely larger multi-module programs without inflating budgets.

**Gate V1:** multi-file project compiles and runs, imports are deterministic across supported filesystems, scope/visibility violations are rejected, malformed/incomplete sources produce precise diagnostics and byte-accurate spans. Checks and emitted native behavior agree; incremental reuse is optional until justified, but never stale.

## V2 — General types, inference, callable values and generics

**Features:** bidirectional synthesis/checking; local inference and explicit named function contracts; parametric generic functions and nominal data; type-argument inference where unique; independent checking of generic bodies; minimal compiler-known Equal/Ordered/Hashable with explicit laws, no automatic dishonest Float total order and no general user operator-overload system; explicit behaviour records of typed functions; functions as values; first-class closures with by-value capture default and checked edit/take capture modes, invocation lifetime and effect obligations.

**Gate V2:** generic map/filter-like utilities built from Pep stdlib without special compiler rewrites; two explicit comparator/formatter behaviour values coexist; conflicting imports never silently change behaviour; unsafe escapes/aliases are rejected; type facts and errors are inspectable by an agent and executable on C23.

## V3 — Complete everyday data, Unicode and numeric guarantees

**Features:** checked signed Int64; Float64 and Float32 with explicit conversions; Bool/Unit; Unicode Str valid UTF-8 with clear byte/scalar/grapheme operations; separate Byte/Bytes binary values; ordinary independent value-semantic List[T], fixed Array[T,N], deterministic insertion-ordered Map[K,V], records/recursive unions, Option[T] and Result[T,E]; safe bounds and optional lookup; predictable value copies without accidental shared mutable mutation.

**Gate V3:** run cross-backend corpus for NaN/signed zero/overflow, encoding/invalid UTF-8, raw bytes/NUL, nested values and large collections, bounds, ordered Map insert/update/delete/reinsert, copy/modify independence and memory reclamation. No undefined C behavior used to implement Pep semantics.

## V4 — Typed error propagation, effects and real host authority

**Features:** Result/Option match/recovery; postfix ? with correct typed error propagation; diagnose unexamined results unless explicitly acknowledged; compiler-inferred internal effects; public/restricted uses ceilings including first-class function and generic transitive effects; separate runtime host grants for fs/io/net/process/time/random and any other effects. A declaration of an effect NEVER grants authority.

**Gate V4:** tests show typed propagation and explicit incompatible-error handling; hidden transitive effects are rejected, revoked/denied host grants are enforced at runtime, no ambient operations bypass capability checks, and a fake “pure” signature is insufficient to establish termination, deterministic scheduling, no allocation or real-time timing.

## V5 — Memory safety, read/edit/take, danger, FFI and resource domains

**Features:** compiler-directed efficient stack/direct representation first; scoped regions where proven safe; sound general managed fallback (precise tracing GC remains the *provisional* strategy, collector chosen after evidence); correct roots/barriers across native graphs, closures, packed records and FFI; safe value copying/COW; noncopyable owned handles, safe typed allocation/deallocation, scope cleanup; read default, exclusive edit, explicit take, no use-after-take; danger only for narrowly scoped raw operations with retained checker constraints and clearly labelled trusted obligations; safe FFI/layout/alignment/pinning/custom allocator identity.

**Additional constraints:** no-alloc/no-GC/no-block restricted execution contexts for professional real-time work (not an automatic timing guarantee); explicit GPU/DMA/external resources stay alive through actual work completion or supervised failure.

**Gate V5 (release-critical):** independent adversarial memory-safety review and executable tests for double free, use-after-move/take, dangling aliases, hidden edit escape, regions crossing managed GC, cycles, pinned/rooted FFI, failures/cancellation/cleanup order, wrong allocator, ASan/UBSan or equivalent where available; fresh unsafe examples cannot become safe by wrapping them in danger. If a memory guarantee cannot be supported, do not advertise it or silently relax accepted semantics.

## V6 — Structured concurrency and lifetime supervision

**Features:** async functions, explicit spawn/await, bounded scope ownership of children, typed task outcomes/errors/cancellation, typed channels and services, isolation of ordinary values and explicit shared identity, safe take across task boundaries and no unsafe edit borrow across suspension. Locks/atomics only as typed controlled contracts where needed.

**Gate V6:** deterministic acceptance harnesses plus stress tests for sibling failure, nested scope exit, cancellation races, dropped channels, external I/O/GPU work not yet complete and task-local ownership escape. No leaked detached children, premature releases or false data-race-freedom guarantees. Scheduler behavior documented; no claim of deterministic scheduling or deadlock freedom from a type check alone.

## V7 — Complete the layered Pep-written standard library

**Build bottom-up in Pep as early as possible**, and continue throughout V1–V6; do not save this all for the end. Keep minimal, justified native/host primitives with explicit signatures, effects, ownership, error/result, platform availability and cost notes. Tests and documentation/examples are part of each public module.

- **Foundation / pure:** std.text/str/unicode, bytes/buffers, checked collection builders, list/array/map, iterators/algorithms, math/numeric conversion, parse/format, JSON and common data structures. Avoid O(n²) repeated immutable list append as the universal builder; benchmark the actual workload.
- **Host systems:** path/fs/io/env/process/time/random/net; task/sync/memory and safe foreign/OS facilities only under explicit granted capabilities and correct cleanup.
- **Development:** std.test, semantic inspection, source/edits, diagnostics and developer helpers. Prefer libraries that share the compiler's checked contracts rather than hidden magic.

**Gate V7:** every stable public API is queryable from actual checked source signatures with documented type/error/effect/host grants; real examples and adversarial tests pass across specified interpreter/native targets. Include large enough JSON, file transforms, collection workloads and async service samples to expose ABI/GC/performance bugs. Mark intrinsic count and rationale; do not fake all-Pep implementation for irreducible OS calls.

## V8 — First-party tests and independent adversarial evidence

**Features:** compiler-recognized test declarations, std.test assertions, pep test and pep test --json, selection/filtering, test isolation, accurate source spans, recorded inputs/seeds/environment/host grants and deterministic result schemas. Property testing and bounded shrinking after core runner is stable. Tests are excluded from ordinary production execution. The Terror Bats project remains a separate independent adversarial adapter, not a duplicated embedded framework.

**Gate V8:** reproducible passes, assertion failures, compile errors, timeout, crash, policy denial and infrastructure errors are distinct; source revision is pinned; hostile test runner failures and counterfeit receipts are rejected. A passed sample is evidence for that case, not universal proof; in Terror Bats terminology PROVEN means an observed *falsification* of a claim under specified conditions.

## V9 — Lucy: one continuously useful compiler-derived program model

**Feature direction:** ONE checked semantic authority, not multiple compiler servers, an always-on model or annotation-as-truth. Expose bounded revision-specific queries for types, symbols/references, module signatures, call graph, source spans, holes/expected types, effects, ownership/resource lifetimes, reachable API contracts, compiler stage checkpoints, tests, diagnostics, limitations and native artifacts. Distinguish checker fact/proven obligation vs observed runtime/test event vs unverified author claim/agent suggestion.

**Knowledge reuse:** selectively retain justified facts across source/build revisions through explicit dependency identity and invalidation. Cache must be disposable; a clean rebuild and a warm reuse path have equivalent semantics. Profile whether retention earns its complexity. Preserve verified first-party source editing: semantic identity plus exact source revision, byte-preserving preview/apply, stale/ambiguous edit rejection and post-edit recheck. No inference-based permission or hidden source mutation.

**Gate V9:** an unfamiliar capable agent can query language/library capabilities, understand a module and safely patch a typed hole or targeted construct without rereading all source, with reduced context use *measured*, not assumed. Cache mutation/corruption/stale dependency cases fail closed. Existing v2 FunctionInfo IDs are revision-local unless proven otherwise. No need for #@ intent/verify/prefer as mandatory source syntax.

## V10 — Real use, cross-platform build and packaging

**Programs:** at least one robust multi-module compiler development tool, one real data-processing/JSON/file transformation application and one async/resource-using program that exercises intended guarantees. Do not let shell/Python perform the supposed Pep program's main logic.

**Engineering:** consistent CLI check/run/build/test/query/describe functionality; self-hosted compiler install/upgrade path with clean bootstrap fallback; deterministic artifact descriptions; portable toolchain discovery; documented target/ABI/OS support; reproducible build inputs, dependency pinning and basic package manifest/lock if required by accepted module/dependency design. No magical network fetch through imports; external capability required.

**Gate V10:** fresh checkout/build/test/install on **each explicitly claimed supported platform**. Primary native C23 Clang and independently GCC where target supports them. Test Windows first with existing tooling; define a final platform-support matrix before RC and verify any claimed Linux/macOS support instead of asserting it. Perf and memory envelopes are measured and documented, not vague “faster than C” claims. Document debugging, troubleshooting, version/schema upgrade and standard-library availability.

## V11 — Specification freeze, release candidate and 1.0 acceptance

A release candidate is not accepted just because tests are green. Define a **language contract freeze** after major semantic contradictions are resolved, then collect:
1. Full accepted-feature ledger reconciled against individual design decisions (not merely a chosen list of examples). Every accepted obligation either implemented/tested or explicitly revised with Matthew's approval; no accepted feature silently postponed out of 1.0.
2. Canonical normative grammar, typing/effects/ownership/errors/runtime specification, behavior tables, library/API docs and executable conformance fixtures.
3. Verified end-to-end self-hosted build chain and clean install/upgrade/rollback. A/B/C compiler behavior and source/diagnostic parity supported by stage receipts.
4. Independent security/soundness review for ownership, GC/FFI, danger, capabilities and concurrency; serious defects closed or shown to be outside explicit safe API with an honest specified limitation.
5. Full interpreter vs native differential suite, randomized/metamorphic/adversarial cases, cross-compiler tests, performance/regression and real applications. Every failure/skip counted, triaged and bounded in claims.
6. Verified host permissions and trusted local tool boundary. Never imply the in-process tool host or git worktree is an OS sandbox.
7. Versioned CLI/tool-protocol schemas, machine discoverability, reproducible test receipts and stable user installation. Agent-visible contracts agree with actual implementation.
8. Documentation: concise “first 15 minutes”, reference, standard library, examples, migration/versioning policy and unsupported platform matrix. Rabbit personality and pippin learn remain optional/deferred UX, not a substitute for clear diagnostics.
9. One explicitly reviewed release-candidate manifest recording code SHA, toolchain/runtime SHA, target OS/architectures, exact test proof, binary/artifact hashes, remaining known limits and human acceptance signatures/decision links.
10. **Matthew alone grants final merge/tag/release authority.** Development agents do not auto-update master, CURRENT/manifest, package publication or v1.0 claims. Release checklist may expose blockers rather than invent completion.

## Cross-cutting rules for every slice

- **One semantic engine** serves interpreter, native compiler, library metadata, tests, agent queries and source edits. No parallel unchecked definition of language meaning.
- **Complete source identity:** original UTF-8 and LF/CRLF, immutable source revisions, exact resolved IDs; stale data fails closed.
- **Safety and rights:** accepted value semantics and explicit read/edit/take; danger is narrow; host grants are distinct from declared effects; no unproven memory, timing or scheduling guarantees.
- **Two agents:** existing Agent 1 checker/integrator, Agent 2 backend/runtime; ownership changes only after explicit coordination on [GitHub issue #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16) and relevant Workshop Board outboxes. Prefer non-overlapping slices and independent reviews; no simultaneous edits to shared checkout/files.
- **Evidence:** each coherent slice gets proportional targeted tests, a pushed SHA and concise receipt; every third slice independent adversarial review where available, **nonblocking** by default; full-suite/hardening at consequential integration gates.
- **Memory:** integrator updates the single [Pepin Current Status](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7Cb2ae60a9-86c5-46e4-9c3c-ff61b045b56e) using source-backed receipts; each agent appends only to its own Basic Memory outbox; Lucy can leave cross-lane findings in her outbox. No automatic delivery.
- **No speculative subsystem sprawl:** revisit deferred tutor, wholesale Rust ports and multiparadigm systems only when core features and real user programs justify them or Matthew reprioritises.
- **Stop policy:** no agent stops at a three-slice quota, bootstrap, or first release-like demo. Escalate only irreversible design conflicts, dangerous safety/authority contradictions or true blockers. An agent harness ending means checkpoint and resumption, not fictional asynchronous work.
