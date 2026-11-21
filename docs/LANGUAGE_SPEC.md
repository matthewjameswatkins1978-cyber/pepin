# Pepin — living language specification

**PEP-SPEC-20261121 · 21 November 2026 · consolidated target specification, not a grammar freeze or release certificate.**

Pepin is the project; Pep (`.pep`) is its small, statically typed general-purpose language; Lucy is its compiler and semantic development environment. Agents and humans use the same source, language rules and deterministic compiler. No LLM is required to build or run Pep programs.

## Authority and scope

This sheet consolidates the accepted DEC-001/002/003A–H/004–009 design, the 20 November practical-language priority change, and the 21 November memory, data-oriented and core language plans. It does not replace the underlying decisions or invent unresolved syntax. See [the 27 October final draft](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/14), [28 October priorities](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/17), [native/core coordination](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16), [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md), [002](TECHNICAL_RESOLUTION_002.md), and [Road to 1.0](ROADMAP_TO_1_0.md).

Status vocabulary:
- **Accepted baseline (A):** implemented on accepted master, only to the documented extent.
- **Provisional (P):** candidate implementation, not accepted or release-certified.
- **Target (T):** accepted design intent requiring implementation/conformance; exact unsettled details are listed below.
- **Open (O):** design choice still to be settled deliberately. A target is not a claim that its syntax runs today.

Current integration pointer: [CURRENT](packets/CURRENT.md), [manifest](packets/manifest.json), [implemented subset](DESIGN.md), [seed reference](SEED_LANGUAGE.md). As inspected on 21 November, master `e70693938e530177b793b5219addf3d797210e6d` remains A8. The A8 recorded receipt is 55 primary OCaml and 11 historical MoonBit tests; subsequent branch counts do not transfer to it. Illustrative provisional compiler pin: [e737cead](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/e737cead9e5194d7f785b4ceb5e53f72913abf62). No tests were run for this documentation update.

## 1. Design rules

- Express the problem in the smallest natural Pep form. Prefer library functions and normal data over new keywords, duplicated infrastructure or speculative generality.
- The compiler should establish machine-knowable facts, not force an agent to repeat them. Make type, lifetime, layout, effect and dependency facts inspectable; emit actionable diagnostics with precise source spans.
- Source stays canonical readable UTF-8 text, byte-preserving edits, ordinary comments. A model's guess, intent, test outcome or annotation is not a compiler proof.
- Deterministic observable behaviour is independent of interpreter, C23 compiler, optimisation and allocator choices.
- Safety by default; explicit authority and narrowly bounded low-level control. No hidden conversions, implicit ownership moves, ambient host access or silent changes to observable value semantics.
- The compiler/runtime may be sophisticated; the language surface should remain small. No classes/inheritance, macro language, global arbitrary overloads, wildcard imports or AI-only dialect in the 1.0 core.

## 2. Core language inventory and acceptance ledger

IDs below are stable requirement anchors for the living specification; they are not claims of already registered machine evidence. A/P entries mean a subset is present. Every target must have valid, invalid and where applicable incomplete fixtures, checker-owned facts and native parity before acceptance.

| ID | Contract | Status on 21 Nov |
| --- | --- | --- |
| PEP-L01 | UTF-8 source, deterministic tokens/layout, braces, comments, exact byte spans and revisions | A subset; full grammar T |
| PEP-L02 | `let`, `var`, assignment, explicit typed named `fn`, `return`, recursion, lexical scope, top-level immutable values | A subset; top-level access P |
| PEP-L03 | `if`, `else if`, statement-if without else, expression-if with else; short circuit, exhaustive `match`, `for/in`, `while`, nearest-loop `break/continue` | A subset; statement/loop completion T |
| PEP-L04 | Named records, tagged unions, nominal identity, constructors, field access and pattern matching | A subset; cross-module opaque nominal types P |
| PEP-L05 | One file per module; `import`, qualified access, `as`, `pub`, private-by-default and opaque declarations; no cycles/hidden effectful initialisation | P file imports and signatures; complete session/graph parity T |
| PEP-L06 | Bidirectional typing, partial checked trees and named/anonymous holes (`?name`, `_`); refuse execution of incomplete code | A subset; fuller constraints T |
| PEP-L07 | User-defined type/function generics, inferred type arguments, Equal/Ordered/Hashable, explicit behaviour values | T |
| PEP-L08 | Int64 checked, Float (64-bit IEEE), Float32, Bool, Unit, explicit numeric conversions | A Int/Bool/Unit subset; float and conversion contract T |
| PEP-L09 | Unicode Str, Byte/Bytes, ordered List[T], fixed Array[T,N], insertion-ordered Map[K,V], safe indexing and iteration | A Str/List subset; typed nested/native lists P; general collections T |
| PEP-L10 | Independent logical values; explicit shared identity, noncopyable owned resources; `edit` and `take` | T |
| PEP-L11 | Option[T], Result[T,E], exhaustive recovery, postfix `?`, explicit error discard | T |
| PEP-L12 | First-class typed functions, closures, value capture by default, explicit edit/take captures and callable effects | T |
| PEP-L13 | Flow-sensitive bounded refinements; invalidate on mutation/alias change; proof vs runtime validation | T |
| PEP-L14 | Inferred internal effects, declared public `uses` ceilings, separate granted host capabilities | T |
| PEP-L15 | Compiler-directed hybrid memory and safe explicit allocators; precise roots and resource lifetime | T (memory foundation mission active) |
| PEP-L16 | Data-oriented buffers/views, layout/capacity control, narrowly scoped `danger`, checked foreign boundary | T; exact layout/API O |
| PEP-L17 | Structured concurrency, `async fn`, `await`, scoped children, typed transfer/communication/cancellation | T; exact task syntax O |
| PEP-L18 | Native `test` declarations, first-party runner, properties and revision-bound evidence | T; exact grammar O |
| PEP-L19 | Tiered Pep-first stdlib, explicit capabilities and inspectable public contracts | A seed primitive subset; T |
| PEP-L20 | Compiler-derived Semantic Map, requirements/test links, context packets, mechanical repairs, safe multi-agent work | A semantic/session/guarded-edit subset; extended map P |
| PEP-L21 | Native C23 lowering, deterministic semantics, tested runtime/ABI, reproducible Pep-written compiler | P direct native subset; T full backend/self-host |

### 2.1 Surface syntax (target illustration, not a seed fixture)

```pep
import test

pub type Pair[A, B] {
    first: A
    second: B
}

pub fn identity[T](value: T) -> T {
    return value
}

fn bump(edit value: Int) -> Unit {
    value = value + 1
}

test "identity preserves its argument" {
    test.equal(identity(42), 42)
}
```

Familiar brace syntax, deterministic newline separation with optional semicolons, locally inferred types where unambiguous. Named fn parameters and result types explicit. No new reservation of keywords simply because a future library needs an operation. Prefix holes and postfix error propagation must be unambiguously distinct.

## 3. Type, evaluation and data semantics

- Generics are parametric, checked independently of examples. Unconstrained T does not gain arbitrary operations. Minimal abilities: Equal, Ordered (total order), Hashable consistent with Equal; optional behaviours are explicit records of typed functions. No implicit global dictionary selection. Specialisation is an implementation strategy, not a change to semantics.
- Eager evaluation order is deterministic, including operands, calls, constructors, fields and collection elements; conditional/match/short-circuit branches are lazy. Stop at the first error in language-defined order. C argument evaluation order must not leak into Pep.
- Int is signed 64-bit, checked overflow including edge operations; floats have explicit representation/conversion rules, NaN and ordering policy under conformance. Do not infer total order for IEEE floats. Str is valid UTF-8 Unicode text; Byte/Bytes are binary. Separate scalar/grapheme/byte APIs; no ambiguous integer Str indexing.
- Ordinary values (including nested aggregates) are independent: editing a copy cannot mutate the original. Compiler may eliminate copies/share immutable storage where observationally equivalent. List is ordered, Array fixed-size, Map insertion-ordered with Equal/Hashable keys. Bounds checks unless proved; optional get returns Option. Unchecked raw indexing is not default indexing.
- Read is the default access mode. An explicit edit temporarily grants exclusive access; overlap rejected unless proved disjoint. Explicit take transfers ownership and invalidates the old binding. No implicit source moves. Shared mutable identity requires explicit typed representation. Closure default capture is logical value; edit capture cannot escape its permitted synchronous lifetime; take capture transfers ownership. Function types retain access/effect requirements.
- Lightweight refinements derive from constrained flow facts; invalidated by writes/alias changes. Report proved, refuted, unresolved or runtime-validated separately. No arbitrary dependent proof burden.

## 4. Memory and data-oriented systems

The approved direction is **compiler-directed placement with explicit control where needed** (DEC-006, PEP-MEM-20261121-01, PEP-DATA-20261121). The compiler should choose the simplest safe representation: registers/direct values/stack, then bounded regions where escape/lifetime proof warrants it, then a precise managed heap for general graphs and cycles. Initial managed fallback is a simple nonmoving tracing implementation; alternative collection, reference counting, reuse and copy-on-write are measured candidates, not language semantics. The user does not need Rust-like lifetime syntax for ordinary values.

| Level | Contract |
| --- | --- |
| Automatic | Sound layout, escape, roots, reclamation, independent logical values; no ordinary pointer bookkeeping |
| Explicit checked | Typed noncopyable owned buffers, allocator identity, size, alignment, fixed capacity, lifetime-checked views, explicit release/reset, failure as Result |
| Bounded danger | Narrow raw address/foreign memory/other hazardous operations with explicit reviewed obligations; ordinary checks still apply where possible |

Safe allocation/free should not require danger. Consuming release, non-copyable ownership, correct allocator identity and scope cleanup must hold across success, early return, errors and cancellation. Exact trap/cleanup protocol remains to be specified. Managed references at FFI must be rooted/pinned or copied according to contract; GPU/DMA/async buffers stay live until genuine completion or safe responsibility transfer, not just cancellation request.

Data-oriented programming is a first-class design target, not a separate language:
- Typed contiguous buffers and bounded views; aligned storage, fixed capacity, caller-supplied allocation capability, bounded arenas/pools. Reject stale views, overflow, hidden growth or silent fallback allocation.
- Explicit array-of-structs (AoS) and structure-of-arrays (SoA) representations; checked columns/indexing, alias/disjointness reasoning, layout and ABI facts from the compiler. Design exact API only after measuring workloads.
- Permit scalar-to-vector lowering and bounds-check elimination when valid; retain correct C23 scalar fallback and do not silently enable fast math. No ECS framework in the core.
- Independently express and check no dynamic allocation, no managed allocation, no GC entry/activity, no blocking, no reclamation as applicable. None alone proves real-time safety, worst-case latency or deadline. Protected audio/real-time paths need explicit isolation and measurements.
- Benchmarks: particle update AoS/SoA, frame arena/pool, allocation-free audio mixing; compare equivalent C baselines, report throughput/tail latency/memory/allocations/flags/target; no speed claim until measured.

## 5. Modules, errors, effects and concurrency

Modules are project-relative file identities, qualified imports, explicit public signatures, private-by-default, opaque representation and acyclic graph. Imported modules may not trigger hidden effectful initialisation; executable top-level statements only in the selected entry under specified rules. Package manifests and dependency identity are reproducible, never implicit network fetches.

Option represents absence; Result expected failure. Match recovery, compatible typed postfix propagation, explicitly acknowledged discard. No general exception mechanism initially; traps, cancellation and expected typed errors remain distinct. Effects are inferred internally; public APIs/restricted contexts declare ceilings; transitive calls and function values retain their requirements. Declaring fs.read does not grant access: host grants and enforcement are independent.

Structured scopes own child tasks, cancel on specified failure and await safe completion/transfer before exit. Async suspension is explicit; edit cannot silently cross await, nor mutable state cross tasks. Copy/immutable share ordinary values and take owned values; explicitly coordinated identities, typed channels and supervised services for shared state. Exact task syntax, outcomes/scheduler semantics and FFI cancellation remain formalisation tasks. Data-race freedom is not deadlock freedom.

## 6. Living program specification, tests and AI collaboration

One compiler-derived Semantic Map supplies compilation, queries, tests, editing and agents; no parallel guessed semantic database. A project specification records problem/purpose, requirements and non-goals, public contracts, architecture, constraints, decisions, ownership and acceptance evidence. Authors update it alongside affected code. Stable requirement IDs link explicitly to checker-owned symbols, dependency edges, test assertions and evidence receipts; a prose requirement is not proof. Native test declarations can live near behaviour or separate files and link to contracts, without mandatory boilerplate in every function. The compiler identifies missing/dangling links and invalidates evidence when relevant source/dependency/contract/toolchain changes. Unknown impact is conservative, not silently certified.

A receipt records requirement/symbol/test IDs, exact revision and compiler/toolchain, target/flags/input/seed, result/output/exit, assertion outcome, limits and evidence state. Distinguish checked fact, proof obligation, human decision, observed test, suggestion and stale/unknown. A pass is not a universal proof; an observed falsification is not a proof of all other behaviour. Independent adversarial adapters (including Terror Bats) may challenge receipts.

Context packets are minimal dependency-complete, budgeted views of signatures, source, effects, invariants, requirements, callers/callees, tests and revision. If a mandatory dependency cannot fit, report the missing context, never pretend complete. Mechanical repairs have explicit safety tiers: deterministic safe automatic edits versus choices needing review. Structural edits preserve untouched source bytes and reject stale revisions. Diagnostic accumulation should report independent useful errors while suppressing cascades.

Built-in multi-agent *development* support is distinct from runtime parallelism: declare lanes, base revisions, symbol/requirement write ownership and dependencies; agents may propose different solutions for the same symbol on isolated branches, exchange evidence and review one another, but the integrator selects/composes checked changes. Detect signature, effect, invariant, requirement, dependency and test conflicts even if Git merges text cleanly. Never auto-accept a competing edit, grant permissions or run an untrusted extension merely because it is Pep. Shared semantic truth, independent review, guarded integration.

## 7. Library, native backend and release contract

Grow the Pep-written library bottom-up: bytes/text/Unicode, builders/buffers, core collections, math, algorithms, parsing/JSON; then authorised path/files/IO/process/env/time/random/network, memory/task/sync, native tests, semantic tools. Use minimal runtime intrinsics with explicit behaviour. Every public API exposes types, generics, errors, effects, platform availability, tests/contract links and permissions. Prefer ordinary modules to language magic.

Keep OCaml 5.5.2 as reference seed and use the direct checked-IR-to-C23 backend as the immediate practical path, Clang primary and GCC independent cross-check. Python orchestration/lowering is a provisional implementation choice, not Pep semantics. Native code must agree with interpreter results/errors/order/cleanup, reject unsupported features explicitly, preserve typed layout/ABI and avoid undefined behaviour. Self-hosting follows a usable native language and library; stage A→B→C proof must not conceal the old semantic compiler.

## 8. Open normative details and change control

Freeze through executable fixtures rather than arbitrary new syntax: precedence, newlines, hole/propagation tokens, comments, generic/constraint/closure grammar, numeric literals/conversions/NaN, Unicode version/API and Map reinsertion, module path/case/initialisers, proven bounds vs optional get, discard/error translation, refinements, effect vocabulary and capability transport, cleanup/error/trap/cancellation, region/GC invariants and FFI ABI, exact allocator/view/layout/danger syntax, task signatures, native test runner/receipts, specification format and semantic query schema. Compatibility rule: no change of an accepted externally visible guarantee without explicit decision and updated conformance. Candidate optimisations can be accepted only after evidence.

## 9. Evidence snapshot (not live release state)

- A8: [accepted integration pointer](packets/CURRENT.md); meaningful typed interpreter, typed holes, byte/revision-aware session and trusted-local Pep tool extension. 
- Provisional: [native-order repair 88f2bfb](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/88f2bfb9b38a0f7eeb9fe7aa1de829fab24a16d8) fixes the reported argument-order mismatch by explicit sequencing; author reported 71/72 broader tests (one pre-existing Windows LF/CRLF failure), focused differential Clang/GCC checks. Independent acceptance not established by this sheet.
- Provisional: [e737cead](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/e737cead9e5194d7f785b4ceb5e53f72913abf62) has file import/public/private/opaque nominal work, checked public signatures, ordered C layout and typed nested list storage; no claim of session import, general generics or memory completion. The [core campaign handoff](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16#issuecomment-7057390901) names next constructs.
- PEP-MEM/PEP-DATA are approved direction/engineering plans, not implementation evidence. Always recheck exact head, CURRENT, acceptance and tests before advancing labels.

Update this sheet and the [roadmap](ROADMAP_TO_1_0.md) when accepted requirements, milestones or verified status change. Detailed implementation evidence belongs in its owning packets and review receipts; do not advance those from a documentation edit.
