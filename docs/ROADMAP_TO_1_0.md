# Pepin: the road to 1.0

**Product roadmap · 21 November 2026 · updated execution order, not a release or implementation certificate.**

The finish line is a useful, independently buildable AI-first general-purpose language, not merely a compiler that compiles itself. The [living language specification](LANGUAGE_SPEC.md) defines the target inventory and separates accepted, provisional, target and open items.

**Priority decision (20–21 November):** get Pep usable with reliable native C23 compilation, real memory semantics, core language constructs, a bottom-up standard library and one compiler-derived Semantic Map. Do not hold that work hostage to the restricted self-hosting interpreter. Keep OCaml as reference and use the C toolchain now. Self-hosting remains an eventual 1.0 acceptance requirement, not the next bottleneck.

## Starting point

A8 is the accepted baseline, as shown in [CURRENT](packets/CURRENT.md), [manifest](packets/manifest.json) and [implementation status](DESIGN.md). Master observed at `e70693938e530177b793b5219addf3d797210e6d`. A8 receipt: 55 primary OCaml and 11 historical MoonBit tests. On provisional branches, direct C23 execution, semantic evidence work, eager-order repair and file-module/opaque-type/typed-list work exist. [Pinned core review e737cead](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/e737cead9e5194d7f785b4ceb5e53f72913abf62); [native order repair 88f2bfb](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/88f2bfb9b38a0f7eeb9fe7aa1de829fab24a16d8); [issue #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16). These are not accepted milestones. No new compiler tests were run for this roadmap.

## Dependency-led sequence

The numbers below are planning milestones, not new packet IDs or claims of acceptance. Each has an exit gate. Multiple lanes may proceed when they have explicit non-overlapping ownership and a verified dependency seam.

| Milestone | Deliverable | Exit gate |
| --- | --- | --- |
| M0 — Integrate reliable native foundation | Resolve known direct-C23 defects; checked IR authoritative; evaluation order, error/status, typed nominal layouts | Immutable reviewed pins; interpreter/Clang/GCC parity, all relevant accepted regression checks green or documented pre-existing failures |
| M1 — Core usable syntax and modules | Finish file module graph, pub/private/opaque imports and session parity; top-level constants, statement-if/else-if, break/continue, cleanup, safe indexing | Real multi-file application; negative visibility/cycle/branch/bounds fixtures; matching native results and diagnostics; no unsupported constructs advertised |
| M2 — General types and data | Parametric functions/types, Equal/Ordered/Hashable, concrete instances; Float/Float32, Byte/Bytes, Array/List/ordered Map, Option/Result | Generic-body checking, inference and rejection of invalid constraints; typed layout; integer/float/Unicode/bounds/collection and nested-value parity |
| M3 — Native safe memory and ownership | Hybrid placement/regions/managed fallback, explicit read/edit/take, independent data, noncopyable handles and allocator identity | Precise root/layout/escape tests, cycle reclamation, stale-view/alias/transfer rejection, cleanup under failure, sanitizer-backed stress evidence |
| M4 — Functions, typed errors and effects | First-class functions/closures; compatible postfix ?, exhaustive handling, effect ceilings and independent host permissions, bounded refinements | Closure escape/capture/access tests; transitive effect checking; permission denial tests; deterministic error order, no silently discarded Result |
| M5 — Practical native alpha | Pep-first text/bytes/collections/math/parse/JSON and host basics; first-party test runner; compiler-derived Semantic Map; usable CLI | Build/run/test/query real programs on published supported target(s); linked specs/tests, bounded packets, negative tests and reproducible install instructions |
| M6 — Data-oriented systems | Checked contiguous buffers/views/pools/arena, AoS/SoA, capacity/alignment/allocator controls, narrow danger/FFI | Safety under stale views, overlap, capacity, allocator mismatch and foreign lifetime; controlled C-comparable benchmarks; independently verified no-allocation/no-block/reclamation contracts |
| M7 — Structured concurrency and advanced resources | Scope-owned async/await, typed channels, cancellation and safe ownership transfer, supervised external work | Race/suspension/cleanup tests, cancellation completion, resource pin/transfer proof; no implicit detachment; documented host/FFI scope |
| M8 — Complete library and AI-native workflow | Finish accepted core stdlib/API contracts; stable test/evidence/query/edit protocols; semantic conflict detection and spec-driven agent collaboration | Provenance/capability contracts, dependency invalidation and guarded edits; independent concurrent-edit tests; real external applications |
| M9 — Self-host Lucy | Pep-written lexer/parser/checker/runtime interface and C23 emitter; no concealed semantic seed in later stages | Reproducible Stage0→A→B→C builds with source/artifact identities and independent conformance; reference OCaml retained for recovery |
| M10 — 1.0 acceptance | Freeze semantic contracts, APIs, protocols, release/distribution and supported-platform matrix | Every accepted requirement disposition, conformance/adversarial tests, safety review, practical applications, reproducible build/install and explicit human approval |

M0 and M1 start immediately on current authorised lanes. **M3 foundational work starts alongside M1/M2, not after them:** settle concrete layout, value/ownership boundaries, root representation, runtime calls and error/cleanup interfaces early; finish generics and collections against that seam. Do not pretend advanced lifetime/GC support is complete in order to ship an elementary construct. M4 typed Result and errors may begin as soon as unions/generics support them; closure and effect work builds on ownership. First-party test discovery, specification/evidence links and library foundations start in M1/M2 and grow continuously; M5 is the usability gate, not their starting point.

## Immediate execution lanes

- **CORE (PEP-CORE-20261121-02):** continue the existing provisional seed/checker/direct-backend lane. Modules → control flow → safe indexed access → general generics/type instances → numeric/containers → typed errors/ownership → closures/effects. Use reusable language features to eliminate one-off compiler intrinsics. Do not build a competing parser or rewrite the seed. 
- **MEM (PEP-MEM-20261121-01):** implement sound, typed native allocation/lifetime foundation in coordination with CORE. Direct/stack placement, proof-bounded regions, precise nonmoving tracing fallback; measure reuse strategies later. Publish ABI/layout/root/ownership/cleanup seam before other lanes commit incompatible representations.
- **DATA (PEP-DATA-20261121):** specify and prototype checked explicit storage and layout contracts after the enabling ownership/buffer interfaces; compare C baselines. Do not make every program use danger or introduce an ECS/runtime rewrite. Keep advanced GPU/DMA/RT/parallel expansion behind proven lifetime boundaries.
- **Semantic tools, tests and stdlib:** serve one checked engine. Establish stable requirement-symbol-test IDs and evidence invalidation, multi-diagnostic reporting, context packets and mechanical safe repairs; build reusable Pep libraries with the core. Independent semantic conflict review of concurrent work; ordinary Git merge cleanliness is insufficient.

The [21 November coordination record](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16#issuecomment-7057390901) is the implementation handoff. This roadmap grants no new merge, release or packet authority.

## What the first useful alpha should actually do

A multi-file typed Pep program can import a collection and math library, parse text/JSON, perform checked numeric calculations on data, handle errors, run linked tests, compile to native executable and expose exact symbol/contract information to an agent. Include a realistic CLI data-processing program; later a particle workload and audio mix exercise data-oriented capability. A small practical alpha explicitly advertises limitations, not 1.0 completeness. No benchmark or target-performance claim until reproducibly measured. Measure cold-start agent comprehension, implementation and maintenance against a comparable conventional-language workflow: task correctness, independent tests, tokens, time, wrong/stale edits and repair rounds. Specialist Pep-model training follows stable semantics and measured evidence, not the other way around.

## Verification and integration discipline

For each coherent slice:
1. Specify stable requirement ID, intended semantics, non-goals, dependencies, grammar/IR/ABI changes and test obligations before implementation. Preserve ordinary source as truth.
2. Execute valid, invalid, incomplete, edge and regression fixtures; compare interpreter and native stdout, stderr/error class (document permitted location differences), exit status and observable side effects. Use strict C23 Clang/GCC, -O0/-O2/-O3 where relevant, ASan/UBSan, stress collection and property/adversarial cases; later race checks with TSan where supported. Record exact compiler/revision/flags/target/test outcomes and limitations, never just count successes.
3. Keep tests linked to requirement and symbol dependencies in the Semantic Map; invalidate stale receipts on source, toolchain or contract change. Unknown evidence is not pass. Verify LF/CRLF and exact byte spans.
4. Isolated branches/worktrees, one writer per conflicting path or symbol, agreed seams, immutable pushed checkpoints; exchange alternative proposals and fresh adversarial cases. Request independent review after three slices or at safety-critical gates; keep independent bounded implementation moving when it does not depend on blocked acceptance. Designated integration owner composes reviewed pins; Lucy retains acceptance. No automatic merge or release-state advance.
5. Check real performance separately from correctness: reproducible workloads and C reference, compiler flags/target/hardware, throughput, latency distributions, allocations and peak/live memory. No unqualified zero-cost, memory-safe, hard-real-time or faster-than-C claim.

## 1.0 release gate

A release is a standard, not an arbitrary date:
- All accepted design requirements in the [living spec](LANGUAGE_SPEC.md) and underlying [full-language ledger](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/FULL-LANGUAGE-LEDGER.md) implemented and independently accepted, or explicitly changed by Matthew; no silent narrowing. Versioned normative grammar plus executable conformance fixtures.
- Full native C23 semantics and reproducible self-hosting proof, including supported toolchain and artifact identities. General memory, ownership, errors, effects, capability/FFI and concurrency guarantees adversarially tested within stated boundaries.
- Pep-first library APIs, native tests and deterministic semantic development protocols usable by humans and agents, stable upgrade/version policy, independently tested multi-agent semantic edits and evidence invalidation.
- Real externally useful applications, documentation, installation, tested platform matrix and repeatable release/distribution process; no blanket portability or security promises.
- Independent review and explicit Matthew approval of release. Keep CURRENT/manifest as operational truth; a documentation change never advances accepted state.

## Historical plans and precedence

The [November 2 roadmap at the prior accepted revision](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/e70693938e530177b793b5219addf3d797210e6d/docs/ROADMAP_TO_1_0.md), detailed [Road 1 bootstrap](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/ROAD-1-REPRODUCIBLE-BOOTSTRAP.md), [Road 2 full-language](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/ROAD-2-PEPIN-1.0.md) and [gap ledger](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/FULL-LANGUAGE-LEDGER.md) remain valuable detailed history. This sheet supersedes their sequencing where it conflicts with the 20–21 November priority decision, not the accepted language or evidence requirements. Programmer-authored #@ Semantic Notes are superseded as the architectural centre by compiler-derived facts and linked living specifications. Rabbit tutor, broad tool ports, graphics/audio lab and alternative backends remain later projects rather than release prerequisites. See [documentation guide](README.md).
