# Pepin research note: AI-first execution and resource boundaries

**Date:** 2026-10-26  
**Status:** **Provisional design research, not a technical resolution or implementation authorisation.**  
**Branch context:** architecture review after accepted A8. No A9–A15 packet is authorised by this note.

This note extends [Founding Design v0.3](FOUNDING_DESIGN_v0.3.md) without changing it. [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md) and [Technical Resolution 002](TECHNICAL_RESOLUTION_002.md) remain binding. Consult [DESIGN.md](DESIGN.md) for implemented capabilities and [packets/CURRENT.md](packets/CURRENT.md) for authorised work.

## 1. Design intent

**A beautiful, compact, general-purpose Pep surface with an unusually capable, inspectable compiler and runtime.** Its primary intended programmer/operator is a *capable AI agent*; skilled human programmers use **the same Pep language and the same semantic authority**, with different presentations where appropriate. AI-first means compiler-backed discovery, diagnosis, planning and checked actions, **not** hidden prompt-based semantics or a second AI-only grammar.

The desired experience is: state essential requirements once; the compiler establishes safe opportunities and refuses invalid ones; libraries expose verifiable contracts; the runtime makes implementation choices within those contracts; humans and agents can inspect the choice, cost and evidence. A complex compiler is acceptable. Unpredictable *program semantics* are not.

This research was motivated by the October 2026 Lucy–Argon discussions of a DAW's UI/audio/GPU pipeline, generic parallel tasks, prepared immutable resources, cancellation and standard-library composition. Their code fragments and kind systems are **design sketches**, not working Pep features.

## 2. Grounded observations from existing systems

| Area | Established precedent | Implication for Pep |
| --- | --- | --- |
| Deep isolation and immutable sharing | Pony distinguishes transferable isolated object graphs from shareable immutable graphs; isolation is about **all reachable aliases**, not merely a variable captured by a task. [Pony tutorial](https://tutorial.ponylang.io/reference-capabilities/reference-capabilities) | Concurrent boundary checks must account for the reachable graph and any external alias, or make a verifiable copy/snapshot. |
| Structural transfer properties | Rust's `Send`/`Sync` properties are derived through constituent types; interior mutability can defeat naive sharing rules. [Rust Nomicon](https://doc.rust-lang.org/nightly/nomicon/send-and-sync.html) | Structural checking is promising, but safety also depends on aliasing and operations, not shallow type labels. |
| Concurrency crossing | Swift requires sendability across actor boundaries and provides checked transfers for certain non-sendable values. [Swift concurrency guide](https://docs.swift.org/swift-book/LanguageGuide/Concurrency.html), [Swift diagnostics](https://docs.swift.org/latest/documentation/diagnostics/non-sendable-types-and-objective-c-interoperability/) | Prefer local sequential ergonomics and explicit consequences at boundaries. |
| Scoped consumption | Swift's `borrowing` and `consuming` conventions demonstrate noncopyable values without requiring explicit call-site syntax on every call. [Swift declarations](https://docs.swift.org/latest/documentation/the-swift-programming-language/declarations/) | Check whether resource handles can be borrowed/consumed by a modest, compositional set of rules. |
| Deferred reclamation | Crossbeam's epoch reclamation delays destruction until prior readers can no longer hold references. [Crossbeam epoch](https://docs.rs/crossbeam/latest/crossbeam/epoch/) | Reader lifetime and reclamation must be designed together; a stalled reader can delay reclamation indefinitely. |
| Real-time restrictions | JACK's callback contract excludes blocking I/O, allocation, `free`, and ordinary locking from real-time code. [JACK process threads](https://jackaudio.org/api/group__NonCallbackAPI.html) | A `realtime` execution contract should reject known or unknown blocking/allocation/destruction effects, subject to verified host contracts. No keyword alone proves a deadline. |
| GPU ownership | Direct3D 12 requires applications to protect in-flight resource contents and residency until fences establish completion. [Microsoft D3D12 synchronization](https://learn.microsoft.com/en-us/windows/win32/direct3d12/porting-from-direct3d-11-to-direct3d-12), [fence-based resource management](https://learn.microsoft.com/en-us/windows/win32/direct3d12/fence-based-resource-management) | Submission must give the device/runtime a durable resource claim before the initiating task can be cancelled. |
| Task cancellation | Tokio cancellation is asynchronous/cooperative at await points and destroys task locals; it does **not** imply that separately submitted hardware work has finished. [Tokio tasks](https://docs.rs/tokio/latest/tokio/task/index.html) | Cancellation of an observer is not cancellation/completion of a submitted job. |

**Research limitation:** These are precedents and constraints, not evidence that a particular Pep implementation is correct or faster. No design here has been prototyped or benchmarked in Pep.

## 3. Proposed factorisation: access, lifetime, domain, effects

Treat the following as **different questions**:

1. **Access:** who can read, mutate, exclusively own, or temporarily borrow an object?
2. **Lifetime:** what event permits its storage or underlying external resource to be reclaimed?
3. **Domain/location:** managed heap, real-time-prepared pool, CPU staging, device-local GPU allocation, external handle, etc.
4. **Effects:** which work can a function (including implicit cleanup and foreign calls) actually perform?
5. **Execution contract:** what is forbidden or bounded for this context (structured task, parallel mapping, real-time callback, frame pipeline)?

The source language should expose only the *essential* distinctions. Libraries can offer ergonomic operations (`prepare`, `submit`, `parallel.map`, bounded mailbox) backed by compiler-known contracts. Never infer authority from availability.

**Do not freeze** the proposed `Data / Lease / Linear` classification, `FrozenView[T]` syntax, universal ARC, region-only GC, or a particular keyword family yet. Their soundness and usability are unproven. Typed resource handles and shape-preserving prepared views remain strong candidates.

## 4. Ordinary managed values and resource ownership are not the same

The appealing candidate is **automatically managed ordinary Pep values + explicit resource domains at consequential boundaries**. Ordinary compiler ASTs, UI state, maps and lists should not require Rust-style lifetime annotations as a default.

But a resource handle can appear deep inside a record, container, closure or cyclic graph. That immediately raises an unresolved trilemma:

- unrestricted mutable aliasing and cycles in ordinary managed containers;
- deterministic final release of embedded external leases;
- zero additional restrictions or management rules.

**These cannot all be promised simultaneously by inserting a `Drop` at lexical scope exit.** A scope can release one *reference* while other aliases remain; tracing-GC reachability does not guarantee prompt finalization; reference counting does not automatically reclaim strong cycles. A compile-time ban on every type *capable* of forming a cycle is unnecessarily restrictive and is not equivalent to proving an arbitrary graph acyclic at runtime.

**Candidates to test rather than silently select:**

- **Explicit resource owner/registry:** authoritative resource domains own external assets; ordinary data stores non-owning or validated access handles; scope/registry lifetime is explicit. Failure mode: stale handles or retaining resources too long.
- **Owned resource-aware containers:** containers that preserve move/lease constraints and defined cleanup, while ordinary `List[T]` remains uncomplicated. Failure mode: extra API surface; composition becomes awkward.
- **ARC leases under constrained graph rules:** reference counting for resource nodes with weak edges or explicit cycle handling, not generic source-type cycle bans. Failure mode: cycle retention, atomic overhead, unbounded destructor chains.

Choose only after specifying how aliases, cycles, early returns, shutdown, and long-lived owners behave. The location and time of finalization must be visible, especially for real-time contexts.

## 5. Concurrent capture requires deep isolation, not just capture names

This is **not enough**:

```pep
// Proposed syntax only
let a = state.left
let b = state.right
task {
    spawn update(a)
    spawn update(b)
}
```

`a` and `b` may reach the same mutable graph node. Checking that variable names differ is meaningless. Safe options include:

- compiler-established *deep exclusive transfer* of an isolated reachable graph;
- independently copied snapshots, with cost made visible;
- deep immutable snapshots shared under protected lifetime;
- explicit synchronized/serialized channels or shared-memory primitives with tracked effects.

Pony and Swift are useful precedent for choosing a manageable boundary model. No claim is made that deep uniqueness is simple to infer for arbitrary mutable references. If it cannot be proved, Pep must ask for explicit conversion or reject the crossing, not secretly race.

## 6. Prepared read-only views are promising but need a precise conversion contract

**Provisional concept:** `prepare<T>(source)` creates a resource-domain-owned `PreparedView<T>`/equivalent with a separate read-only interface. It can copy ordinary data into stable storage, or retain already-prepared shared assets under protected leases, on a non-real-time path.

Required questions before any `FrozenView[T]` mechanism becomes normative:

- **Aliasing:** if a graph has shared subnodes, preserve meaningful sharing/identity or reject the projection. Naive tree copies may change a diamond graph's semantics.
- **Cycles:** determine which can be represented safely and which must be rejected by an explicit, bounded conversion. Do not mistake `CycleDetected` at runtime for a compiler proof.
- **Closures and resources:** checked transitive effects, compatible captured environments, known foreign-function contracts and resource dispositions.
- **Costs and bounds:** copying, allocation, transfer size, pool capacity, representation changes and failure results must be discoverable *before* consequential execution where practicable.
- **Views:** mutable `List[T]` does not magically become deeply immutable because its binding uses `let`. Published views must not expose an alias that allows source-side mutation.
- **Large assets:** support composing a tiny fresh snapshot with prepared shared wavetable/texture assets rather than copying a 20 MB asset for every knob movement.
- **Hot updates:** snapshotting an entire multi-megabyte buffer every edit is not a universal solution; investigate chunked/tiled update protocols with explicit consistency requirements.

No specific `FrozenMap` layout, contiguous-graph format or free conversion can be assumed.

## 7. Real-time audio: bounded behaviour and honest guarantees

A real-time entry-point contract should exclude known/unproven allocation, freeing, ordinary locks, blocking I/O and unbounded destruction from reachable operations (including implicit cleanup). Foreign operations are **unknown by default**, with explicitly audited trusted contracts tracked as assumptions. An immutable object may still expose a lazy operation with unsafe effects.

A safe *candidate* control/audio exchange:

1. Prepare immutable patch data on a control thread, using bounded preallocated pool capacity.
2. Publish at a safe point via a bounded latest-state exchange.
3. Audio reads a protected snapshot and never runs its final destructor or lease release.
4. The non-real-time side reclaims retired snapshots only when no reader can use them.
5. Reserve/reason about retirement capacity **before** permitting a replacement; when capacity is exhausted, keep valid current state and refuse/coalesce pending updates. Never block or allocate to cope with exhaustion on the callback.

A ring-buffer or epoch scheme needs a **concrete proof of safety and progress assumptions**; "wait-free" is not a label earned by using atomics. Distinguish queue-full, consumer stall, shutdown, ownership handoff and reclamation. Page residency, deadlines, cache effects, OS scheduling, and plugin/driver behaviour remain empirical/host concerns.

Compiler checking can certify some *forbidden-effect* properties but **not** a universal worst-case execution time or glitch-free performance. Use callback deadline distributions and fault-injection tests to validate observed behaviour.

## 8. GPU: execution lifetime outlives observer lifetime

**Recommendation to test:** on accepted submission the *device queue/runtime* takes an authoritative claim on all referenced resources and a **pre-reserved in-flight slot**. The caller receives a completion/cancellation-observation ticket. Dropping/cancelling the waiting task does not prematurely release submitted resources; completion, device loss, and shutdown govern their safe disposition.

This is stronger than a hypothetical orphan queue that first tries to accept resources only *after* cancellation (the queue may already be full). Prevent unsafe reuse by generation-checked handles and known completion fences. Admission can fail **before** submission under backpressure. Lost/hung device handling must be explicit; never invent fence completion.

A game frame could coalesce optional visualisation updates while preserving essential audio processing. Those are declared application policies, not implicit quality reduction.

## 9. AI-first libraries and the semantic interface

Keep library **execution contracts** attached to actual checked declarations and versions, not manually duplicated prose. The same underlying semantic model should serve CLI text, editor interfaces and agent JSON queries.

Proposed query subjects (all **not implemented**):

- `what_operations`: available typed operations and legal target domains.
- `why_not_send`: exact offending path(s) in a reachable object graph and permitted conversion mechanisms.
- `prepare_plan`: source revision, source/target representations, alias-preservation guarantee, cost class and capacity requirements.
- `effect_report`: inferred versus trusted versus unknown effects, including implicit drop/destruction.
- `submission_plan`: required authority, referenced resources, admission cost, in-flight lifetime and failure behaviour.
- `obligations`: mechanically established facts versus unverified timing, safety or acceptance requirements.

Each reply should carry a documented schema version, an exact source/library/runtime revision identity, and evidence level. A suggestion is not an accepted edit; a build is not a performance proof; an invoked operation is not automatically authorised.

Illustrative, **future-only** query result:

```json
{
  "schema_version": "pepin.execution-research/0",
  "implemented": false,
  "subject": "rt.prepare(patch)",
  "source_revision": "<revision>",
  "decision": "requires_conversion",
  "conversion": ["copy_mutable_envelope", "retain_prepared_wavetable"],
  "known_cost": ["copies_envelope_elements"],
  "unverified": ["pool_capacity", "deadline_budget"],
  "authority": "separate_runtime_grant_required"
}
```

The sample schema is illustrative and **must not** be shipped as an actual supported command or API without its own acceptance.

## 10. Prototype gates before a binding architecture

The existing A8 milestone is accepted; implementation is **paused for design/priority review**. This note **does not advance CURRENT.md or manifest.json**, and it does not authorise A9–A15.

A small *future-authorised* research prototype should run adversarial cases with explicit acceptance tests:

1. **Compiler AST:** recursive graph with aliases and cycles; ordinary operations remain ergonomic. Test embedded resource/lease reachability and cleanup separately.
2. **Concurrent task capture:** two different roots share one mutable descendant; spawn must reject, safely copy, or explicitly serialize. Include immutability and transfer controls.
3. **Live synth:** editable 16-point envelope, undo history, shared large wavetable, pool full, stalled control reader, retirement saturation and shutdown. No callback allocations/releases; measure timing distribution.
4. **GPU pipeline:** submit multiple jobs, cancel all observers, saturate in-flight capacity, delay fence forever, device loss, and attempt premature CPU access/reuse. Resource correctness precedes throughput.
5. **Graph projection:** diamond alias DAG and true cycles. Show that preparation preserves documented identity semantics or fails explicitly.
6. **Semantic inspection:** independently verify machine results match compiler facts and effects; distinguish runtime measurements and trust assumptions.

Benchmarks should report throughput, worst-observed latency, peak memory, queue saturation, total copies/bytes, diagnostic locality, programmer code size, and AI-agent repair success/cost using equivalent tasks. Treat Argon's "95% ordinary code" and "bulletproof" claims as **unmeasured hypotheses**.

## 11. Questions to resolve before technical resolution v0.4

1. **Who owns embedded resources when managed objects are aliased or cyclic?** Is a resource registry/owner scope preferable to per-object ARC?
2. **What is the minimum sound deep-isolation/send rule** with ordinary managed containers and no global explicit lifetime annotations?
3. **What does a prepared view preserve:** identity, graph sharing, address stability, and exact operation/effect contracts?
4. **What is the admission/completion model for async hardware?** In-flight resources must survive task cancellation, including queue exhaustion and device loss.
5. **How can constraints stay inspectable and compositional** while the surface syntax remains small? A compiler-generated plan is better than a hidden heuristic.
6. **Which semantics must be stable before self-hosting**, and which optimisations belong exclusively in the runtime/backend?

**Recommendation:** keep the v0.3 semantics and accepted A8 scope intact; retain managed-code + explicit domain boundaries as a *leading hypothesis*, but do not bless universal ARC, compile-time banning of cycles, a three-kind type system or specific `FrozenView` rules before tests and review. This is a research dependency, not an implementation packet.
