# Pepin Full-Language Feature and Acceptance Ledger

**Initial planning inventory:** 28 October 2026. This is a **gap register**, NOT a test report or a machine-verified implementation inventory.
**Road 1:** [Reproducible bootstrap](ROAD-1-REPRODUCIBLE-BOOTSTRAP.md). **Road 2:** [Pepin 1.0](ROAD-2-PEPIN-1.0.md). **Entry point:** [ROADMAP-INDEX.md](ROADMAP-INDEX.md).
**Normative target:** accepted Pep decisions DEC-001/002/003A-H/004–009, later compiler-derived knowledge priority; design draft PR #14, newest priority PR #17, evidence matrix.
**Source of truth for code:** exact GitHub revision + tests, not this file.

## How to maintain

The **design status** column is distinct from **implementation status**. Accepted design ≠ implemented code. Record an exact SHA, test invocation, counts, target/toolchain and limitation before changing a status to VERIFIED. A passing parser test does not establish checker/native parity; a single successful C23 program does not imply the whole type is native. An accepted decision with syntax still to settle stays NEEDS CONTRACT in the relevant grammar/API row.

- **NOT STARTED:** no verified implementation known; do not assert absent code without inspecting repository.
- **PARTIAL:** a known implemented subset with named unsupported cases.
- **IMPLEMENTED UNVERIFIED:** code exists but target conformance/evidence incomplete.
- **VERIFIED SUBSET:** named cases pass at pinned SHA/target; NOT full accepted semantics.
- **VERIFIED COMPLETE:** normative positive, negative, invalid/incomplete, native/interpreter, adversarial and appropriate cross-platform test gates met.
- **BLOCKED:** record the concrete missing prerequisite and smallest next action.
- **DEFERRED:** priority only; accepted product obligation persists unless Matthew explicitly revises it.

Single editor/integrator updates this document from evidence and peer receipts at meaningful milestones; agents may propose ledger patches on own branches. Preserve provenance and avoid parallel edits to this shared file. No master/CURRENT/manifest/release pointer changes without separate acceptance.

## Current evidence anchors (snapshot, not perpetually latest)

- **Accepted master:** A8; manifest current null. docs/DESIGN.md describes the OCaml seed; docs/packets/CURRENT.md and manifest.json define accepted pointer.
- **A13 checker:** f10d5db3fe6eeac19565e4d8db0be19720878a29, agent-reported 48/48 checker and 11/11 A14 tests; semantic parity still partial and fail-closed outside implemented slice.
- **Native branch:** codex/native-collections-loop at 7bf4826184f70e5cf2cd45644ba1189e75bde021, agent-reported 17/17 scoped Clang/GCC/interpreter tests for a restricted Int-list loop. Not integrated into active campaign at this baseline.
- **Staged native CLI:** Pep-written parser/checker/emitter invoked with OCaml seed and Python orchestration; native output verified for restricted subset. NOT independent native compiler, NOT self-hosting.
- **Bootstrap:** Stage 0->A->B->C never demonstrated in verified GitHub receipt reviewed for this plan.
- **Evidence labels:** counts above are **builder reports from identified commits**, not independently re-executed as part of writing this roadmap.

## Front end, modules and typing

| Feature / design source | Initial evidence / state | Road gate | Primary stream |
| --- | --- | --- | --- |
| Exact UTF-8/LF/CRLF source and revision identity (TR001) | Implemented in OCaml seed; Pep lexer/parser stage and source-byte bounds present; full independent compiler parity PARTIAL | B1, V1 | Compiler |
| Small conventional grammar, precedence, newline/semicolon, all accepted statements (DEC-009) | Seed subset implemented; final target grammar NEEDS CONTRACT | V0, V1 | Compiler |
| Lexical scopes, let/var/assignment, functions/recursion (seed) | Seed yes; A13 PARTIAL and native subset PARTIAL | B1-B2, V1 | Compiler + native |
| if expression/statement, for/while/break/continue, nested match/exhaustiveness | Seed substantial; A13 and native coverage PARTIAL, deeper patterns/flow open | B1-B2, V1 | Compiler + native |
| Bidirectional checking/holes and exact incomplete/invalid/valid state (DEC-003A) | Seed yes; A13 checker partial parity; native fail-closed | B1, V2 | Compiler |
| One file = module, pub/private, qualified import/alias, no cycles/init effects (DEC-004) | Target only relative to seed baseline; NEEDS CONTRACT for path rules | B4 as needed, V1 | Compiler |
| Generic functions and nominal types; inferred unique instantiations (DEC-003B) | Accepted design; not seed-shipped; no evidence of general native parity | V2 | Compiler + native |
| Equal/Ordered/Hashable laws, derived abilities (DEC-003C) | Accepted direction, laws/Float semantics NEEDS CONTRACT | V0, V2 | Compiler |
| Explicit behaviour-record values, no global implicit instance lookup (DEC-003D) | Target; depends on function values and generics | V2 | Compiler + stdlib |
| First-class functions, closures, read/edit/take capture rules (DEC-003E) | Target; exact capture/invocation grammar NEEDS CONTRACT | V0, V2/V5 | Compiler + native |

## Data, effects and access

| Feature / design source | Initial evidence / state | Road gate | Primary stream |
| --- | --- | --- | --- |
| Int checked overflow, Bool, Unit and scalar calls | Seed yes; Clang/GCC native verified subset; broad parity PARTIAL | B2, V3 | Native + compiler |
| Float64/Float32/NaN/conversions (DEC-005) | Accepted target; no established seed/native implementation | V0, V3 | Compiler + native |
| Valid Unicode Str and distinct Byte/Bytes; grapheme/scalar/byte API (DEC-005) | Seed Str plus SourceBytes tooling; general target PARTIAL/NEEDS CONTRACT | B3, V3 | Native + stdlib |
| Independent ordinary value semantics (DEC-001) | Immutable seed Lists compatible; full mutable/complex value-copy and ABI unverified | B3, V3/V5 | Native + compiler |
| List[T] generic/nested, Array[T,N] value data (DEC-005) | Seed List; restricted native Int literal loop only; Array target | B3, V3 | Native + stdlib |
| Map[K,V] with stable insertion order and key abilities (DEC-005) | Target; ordering/equality API needs contract | V0, V3 | Compiler + stdlib |
| Named record, recursive tagged unions and exhaustive match | Seed supported; A13 and C23 PARTIAL | B1-B3, V3 | Compiler + native |
| Option[T] and Result[T,E], typed error recovery (DEC-003G) | Accepted target; no complete implementation evidence | V3-V4 | Compiler + stdlib |
| Postfix Result ? and unexamined-result diagnostics (DEC-003G) | Accepted syntax direction; grammar + full implementation open | V0, V4 | Compiler |
| Inferred effects; public uses ceilings; effects through callables (DEC-003F) | Target; no semantic/compiler enforcement claim | V4 | Compiler |
| Host capability grants separate from uses declarations (DEC-003F/TR001) | Seed checked tool host supports explicit grants for existing scope; full OS/native host grants open | V4/V7 | Runtime + compiler |
| Read/default, exclusive edit, transfer take; no use-after-take (DEC-002) | Accepted semantics; final source/alias/escape analysis open | V2/V5 | Compiler + runtime |
| Lightweight bounded refinements and flow-fact invalidation (DEC-003H) | Accepted target; proposition grammar/proof-status contract open | V0, V9 | Compiler |

## Memory and concurrency

| Feature / design source | Initial evidence / state | Road gate | Primary stream |
| --- | --- | --- | --- |
| Compiler-directed safe direct/stack/region/managed memory (DEC-006) | Provisional precise tracing GC fallback, not independently proven final runtime | B3 minimal, V5 full | Runtime + checker |
| Noncopyable safe owned allocation and free with allocator identity (DEC-006) | Accepted target; no complete ABI/soundness evidence | V5 | Runtime + checker |
| Auditable narrow danger/FFI/rooting/pinning and safe wrappers (DEC-006) | Target; exact grammar, obligations and proofs open | V0, V5 | Runtime + checker |
| No allocation/GC/block in real-time contexts and GPU/DMA lifetime safety (DEC-006) | Accepted safety direction, proof/runtime details NOT established | V5 | Checker + runtime |
| Structured task scopes, async/spawn/await and child supervision (DEC-007) | Accepted target; implementation not established | V6 | Runtime + compiler |
| Isolation, typed channels/services, task transfer, cancellation and cleanup (DEC-007) | Target; depends on access/memory/effect contracts | V6 | Runtime + compiler |

## Standard library, testing, semantic environment and release

| Feature / design source | Initial evidence / state | Road gate | Primary stream |
| --- | --- | --- | --- |
| Compiler-needed Pep-written byte/buffer/text/collection foundations (DEC-008) | Pep compiler components exist; full composable library still open | B3, V7 | Native/stdlib |
| Pure stdlib: unicode/bytes/collections/math/parse/json (DEC-008) | Accepted layered target; only scattered seed builtins/examples currently established | V7 | Native/stdlib |
| Host stdlib: path/fs/io/env/process/net/time/random/task/sync/memory (DEC-008) | Target with explicit effects and grants; library completeness unverified | V7 | Native/stdlib |
| Native first-party pep test / std.test / JSON receipts (DEC-008T) | Accepted direction; grammar/runner open | V8 | Native/testing |
| Terror Bats independent adversarial adapter (DEC-008T) | Existing separate Terror Bats design/evidence; Pep adapter still future | V8 | Testing |
| Lucy one revision-bound semantic model; typed queries and stage checkpoints | Seed session/semantic_snapshot exists; unified native/retained query model PARTIAL | B1 minimal, V9 full | Compiler |
| Selective compiler-derived knowledge retained across builds (later decision 28 Oct) | Research approved direction; cross-build safe reuse not evidenced | V9 | Compiler |
| Precise revision-guarded structural edits, typed holes, stale-proof invalidation (TR001) | Seed fill_hole exists; general structural edits not implemented | V9 | Compiler |
| Optional source annotations #@ intent/verify/prefer (older draft PR #13) | **SUPERSEDED as architectural priority**; not required for 1.0 without new decision | Not a release blocker | Do not assign |
| Real native multi-module applications and cross-toolchain conformance | Restricted Int/Bool native programs verified; broader applications target | B4-B6, V10 | Both |
| Stage0->A->B->C Lucy self-hosting (A15) | **NOT VERIFIED** | B4-B7 | Integrator |
| Small documented platform matrix, deterministic artifacts, package/install/update | Future release engineering; existing Windows development is not cross-platform certification | V10-V11 | Integrator |
| Documentation, public 1.0 contract, independent safety review and Matthew acceptance | **NOT RELEASED**; accepted master A8 | V11 | Integrator + human |

## Deferred but remembered (not a silent 1.0 core deletion)

Matthew's 28 October selected priorities explicitly defer a whimsical rabbit CLI and interactive learn experience, wholesale Sartorial/Rust-tool migration and new multiparadigm/logic/OOP exploration. These are product backlog ideas, **not newly accepted semantic requirements**. Keep recoverable references in Basic Memory. New accepted semantics may only change through Matthew's deliberate decision; do not accidentally let a deferred research theme override DEC-001/002/003A-H/004–009.

## Update receipt format

At a major integration milestone, record a bounded revision entry:
- Changed rows and their old/new status.
- Source repo/branch/SHA, generator/compiler/runtime and toolchain versions.
- Exact positive, negative, invalid/incomplete, differential and adversarial commands and pass/fail/skip counts.
- A real previously unsupported example that now runs; any newly rejected program; known limits.
- Peer owner/reviewer, issue #16 handoff, any contract compatibility break and owner action.
- What remains blocked, minimal next dependency and next release gate.
- Whether evidence was independently rerun, builder-reported or only a design claim.

One single editor maintains this ledger; the two agents submit their delta receipts through Workshop Board and their GitHub branches. This avoids duplicate “truth” documents and lets Matthew/Lucy read the latest Basic Memory Current Status, then drill into this ledger when desired.
