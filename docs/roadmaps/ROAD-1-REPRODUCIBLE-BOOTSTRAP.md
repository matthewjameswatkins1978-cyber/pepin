# ROAD 1 — Lucy Compiles Lucy: Reproducible Native Self-Hosting

**Planning baseline:** 28 October 2026. **Status:** product roadmap / execution guidance, not release acceptance, a change to accepted Pep semantics, or authority to merge.
**Project:** Pepin | **Language:** Pep (.pep) | **Compiler name:** Lucy (chosen in Basic Memory; CLI command remains subject to implementation).
**Source of design:** final draft PR #14, its acceptance matrix, A15 packet, technical resolutions TR001/TR002, current Pepin decisions in Basic Memory and newer priority amendment PR #17.
**Next road:** [ROAD-2-PEPIN-1.0.md](ROAD-2-PEPIN-1.0.md). **Progress ledger:** [FULL-LANGUAGE-LEDGER.md](FULL-LANGUAGE-LEDGER.md).

## Exact goal and definition

A self-hosted **native compiler**, not merely a Pep program that emits C, is a Pep-implemented compiler that can compile its own canonical Pep compiler source into a usable successor **without invoking OCaml lexer/parser/checker/interpreter or a hidden non-Pep compiler at its later stages**. A documented host C23 toolchain and minimal runtime/OS support are legitimate dependencies. They must be visible rather than disguised.

**Canonical reproducible proof:**
- **Stage 0 / seed:** trusted OCaml 5.5.2 checks and executes the canonical Pep-written compiler source; its Pep-written emitter produces C23; independently verified Clang builds native compiler A. Record all source, generated C, runtime, toolchain and options hashes.
- **Stage A -> B:** native A accepts the same canonical compiler sources and emits C23 for native compiler B; build B using documented C23 tools. No OCaml seed or OCaml compilation inside this stage.
- **Stage B -> C:** native B repeats the operation to build C, also with no OCaml compiler dependency.
- **Agreement:** A/B/C handle the conformance corpus equivalently, including valid/invalid/incomplete programs, precise diagnostic code/byte spans, type and semantic queries and native output. Compare canonical generated C byte-for-byte if guaranteed; otherwise define and test a justified semantic normalization with traceable differences. Binary bitwise equality is not assumed across differing compilers, paths or nondeterministic metadata.
- **Independent check:** rebuild candidate generated C23 with GCC in addition to primary Clang; execute real binaries and verify observable behavior/errors. Run in a fresh checkout without preexisting build products or accidental dependence on local OCaml executables.

**Passing this road is the bootstrap milestone, NOT Pepin 1.0.** The accepted full language remains binding, as tracked by [ROAD-2-PEPIN-1.0.md](ROAD-2-PEPIN-1.0.md).

## Observed starting point; verify on live refs before action

- Accepted master/manifest remains **A8**; CURRENT lists no newly accepted A9-A15 phase. A15 is provisional as an acceptance packet. The already-authorised long campaign is a **separate experimental implementation line**, not a licence to promote provisional work to master.
- Active compiler/integration line: campaign/pep-v01-sustained-build-20261027. Last source-checked A13 implementation receipt: f10d5db3fe6eeac19565e4d8db0be19720878a29, 48/48 checker differential and 11/11 A14 scoped tests **reported by builder**, not rerun as part of drafting this plan.
- Separate native branch: codex/native-collections-loop at 7bf4826184f70e5cf2cd45644ba1189e75bde021, reporting 17/17 scoped native tests using Clang/GCC, including limited integer-list for-in. Not yet integrated into campaign. Do not treat this as general List support.
- Pep lexer, parser, checker and C23 emitter exist in Pep. The staged Python coordinator currently invokes those through OCaml seed/session; generated native binaries run only a restricted Pep subset. Checked AST/semantic facts and original revision identity are key; do not invent a second semantic authority.
- Compiler test/tool invocation budget stays 100,000 steps/128 call depth; normal CLI differs. No increasing caps to conceal repeated full-tree scans. The current work split is Agent 1 checker/semantic ownership and Agent 2 isolated C23/backend ownership; confirm live ownership on issue #16.

## Critical dependency graph

**Semantic parity / structural checked IR** + **ordered native lowering** + **runtime for compiler-used types** + **reusable Pep stdlib and I/O** -> **standalone native A** -> **A compiles B** -> **B compiles C** -> **fresh-checkout independent conformance** -> **bootstrap gate accepted** -> **entire Pepin 1.0 road continues**.

Dependencies can be built in parallel when they do not share files. Do not wait until one whole lane is complete to begin the other's compatible work.

## Milestone B0: baseline and compiler closure inventory

**Deliverable:** a machine-checkable inventory of every canonical compiler source module, compiler intrinsic, host callback, runtime dependency, source format, input/output requirement, type, effect and ownership requirement. Map each to (implemented/partial/unsupported) in interpreter and C23. Track source-byte input, error paths, stage boundaries, authoritative checked facts, compiler invocation and C23 build entry points.

**Gate:** trace a compile request end-to-end. Every step is identified as Pep code, OCaml seed, Python orchestration, C runtime/OS/compiler toolchain or test-only oracle. Define precisely which dependencies are allowed in A/B/C. Record performance baseline with both small and larger input. Keep A15's semantic/evidence obligations.

**Likely owned by:** integrator for inventory + Agent 2 runtime closure; Agent 1 consulted on checker/IR contracts.

## Milestone B1: complete native-required syntax, checker and source identity

**Implementation:** finish Pep-written checker equivalence on the **entire compiler-used seed subset**, including arbitrary nested structural List types, nominal record/union graphs and patterns, locals and assignment, for/while and flow, recursion, source-byte built-ins, match exhaustiveness, typed holes, correct invalid/incomplete/valid distinction, precise diagnostic codes and original UTF-8 byte spans. Include parser progress invariants, malformed cursor/AST input and stale revisions.

**Gate:** version-bound checked AST/IR is accepted only for the exact parsed source revision; tests compare code/span/status and semantic facts against OCaml over valid, invalid and incomplete corpora. Fix actual performance scaling using measurement (AST indexes, shared analysis, bounded staging) without raising the runtime budget. A larger multi-function compiler module must be analysable within documented resource bounds.

**Owner:** Agent 1 on its dedicated checker worktree. Agent 2 can contribute adversarial tests or non-overlapping backend contracts.

## Milestone B2: typed, ordered C23 backend for the compiler's own used subset

**Implementation:** single checked semantic authority -> explicit typed lowering -> ordered native operations -> deterministic strict C23. Handle calls, nested calls, returns, mutable locals, short-circuit Boolean and evaluation/error precedence, recursive code, loops, records/field access, unions/constructors/match, text/byte operations, lists of structured values and function/module boundaries *as required by compiler source*. Do not compile unverified/unsupported constructs. Use controlled temporaries; do not rely on unspecified C argument evaluation or undefined signed overflow.

**Gate:** interpreter-vs-native differential corpus with first-error/result parity under Clang and GCC; reject forged/stale semantic facts and bad input before emitting C; stable generated output against pinned inputs; no handwritten fixture masquerading as Pep emission.

**Owner:** Agent 2/backend (separate branch and worktree). Agent 1 owns checker semantics and contracts; integrate only through named integrator and pinned SHA.

## Milestone B3: safe runtime and bottom-up Pep library needed by Lucy

**Implementation:** minimal safe C23 ABI/runtime for Int/Bool/Unit, valid UTF-8 Str distinct from Bytes, checked indexing, owned/growing buffers, value-semantic Lists, nested record/union data, failure propagation and allocation/cleanup needed for compiler-produced programs. Choose and validate a safe heap/ownership strategy capable of compiler graphs; do not overpromise that a prototype is the final hybrid allocator/GC design. Interoperability and exact layout/cleanup behavior must be defined and tested.

Build reusable foundations **in Pep whenever expressible**: byte scanning/UTF-8, builder and collection helpers, formatting, diagnostics, parsing support, and eventually code-text emission. Introduce an intrinsic only for irreducible OS/runtime needs or measured safe performance. Preserve clean typed contracts.

**Gate:** compile and run nontrivial Pep data transformation and parser/checker-like fixtures using strings, lists, records/unions, errors and controlled allocation; test invalid UTF-8, embedded NUL, bounds, copy independence, allocation failure, cleanup, recursion and error paths with sanitizers where available. Report what memory-safety claim is supported and what remains unproven.

**Owner:** Agent 2/runtime + stdlib; Agent 1 for borrowed checker-facing type/ABI contracts. No unrelated library catalogue before the compiler needs it.

## Milestone B4: standalone compiler A (first seedless normal operation)

**Implementation:** using stage 0, build a **real native binary** containing Pep-written lexer/parser/checker/lowering/C23 generator and the required runtime. Define an ordinary file input/compiler CLI, multi-source compiler assembly as needed, explicit C23 output and errors, and no hidden dependence on OCaml/Python for A's *semantic compilation*.

Python or shell may orchestrate outer CI/build commands, but **A itself** must execute the required Pep compiler phases natively. If a wrapper invokes OCaml or a Python parser/typechecker/emitter, gate FAILS.

**Gate:** in a clean directory without an OCaml runtime on PATH, A compiles an unrelated ordinary Pep source to C23, reports correct negative diagnostics, and generated C23 builds and executes. Trace process ancestry and file provenance; verify stage A's actual compiler source and native ABI.

**Owner:** joint integration milestone with one named integrator.

## Milestone B5: independent A -> B -> C rebuild

**Implementation:** pin one canonical source set and deterministic build recipe. Use A to compile and build B; B to compile and build C. Archive stage-specific source/generated C/runtime/compiler executable hashes, build flags/versions/host platform, environment controls, build invocations and stdout/stderr/exit codes. Prove the compiler sources used by A/B/C agree. Ensure no stage silently pulls an OCaml artifact.

**Gate:** at least one full independent A→B and B→C cycle with actual executable successors and conformance. Compare semantic outputs on golden valid, invalid and incomplete programs (including UTF-8/LF/CRLF and typed holes), plus real end-user executable programs. Require consistent build results from Clang and an independent GCC build where supported. Document any normalization needed for reproducibility, not just a screenshot of three binaries.

**Owner:** integrator with independent adversarial reviewer; Agent 1 validates semantics, Agent 2 validates runtime/artifacts.

## Milestone B6: reproducibility, resource and security hardening

**Implementation:** clean fresh-worktree bootstrap script; machine-readable stage receipts and failure classification; locked compiler/source/runtime inputs; generated C hash/content checks; portable compiler discovery rather than only hard-coded Scoop paths; fail-closed tool invocation; resource ceilings; no persistent state dependency in bootstrap; tests for missing/bad compiler, malformed source, stale checked IR, path collisions, temp-file races, interrupted build, poisoned generated code and counterfeit receipts. Real OS/tool sandboxing is separate; a Git worktree isn't containment.

**Gate:** a second clean environment reproduces bootstrap according to documented target matrix, or reports an exact unsupported-platform boundary. All tests name real target/toolchain versions. Benchmark growth and memory costs for compiler-sized source; a stage that only works on a trivial file is not complete.

## Milestone B7: bootstrap acceptance and handoff to Road 2

A15 can be reviewed for **bootstrap acceptance** only if all of the following are backed by durable evidence:
1. Canonical Pep compiler source is complete, versioned and compiler-checkable; supported subset explicitly stated.
2. Native A is built from Pep compiler source via trusted seed and actual C23 toolchain.
3. A→B and B→C run without any OCaml semantic compilation or hidden host compiler implementation.
4. Generated compiler B and C execute and pass corpus/diagnostics/tests, with independent Clang/GCC receipts and reproducibility policy.
5. A/C can compile real applications; failures have typed/status/byte-span diagnostics and no unsafe C execution.
6. Exact source/runtime/flags/toolchains/build receipts, regression commands, dependencies and known limitations are preserved; hostile tests include forgery and stale-revision paths.
7. No unsupported whole-language, memory, performance or portability claim is inferred from bootstrap success.
8. Independent review and **Matthew's acceptance** authorise changing A15/accepted pointers or mainline; no worker auto-merges.

After acceptance, **continue directly into Road 2** with the bootstrap subset as reusable infrastructure. Full Pepin v1.0 is a distinct much larger gate, not A15 by another name.

## Work allocation, progress and attention

At each natural three-slice checkpoint both agents read [GitHub coordination #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16) and [Workshop Board](https://chatgpt.com/plugins/plugins_6ae182625810819192d0acc9761e18e3) if installed, otherwise the existing Basic Memory board. Agents retain their existing assigned files and report branch/commit/actual test receipts; one writer for shared integration paths. The named integrator maintains [Pepin Current Status](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7Cb2ae60a9-86c5-46e4-9c3c-ff61b045b56e). Messages are asynchronous and do not notify sessions automatically.

Do **not** stop at three slices, change the master acceptance pointer, increase host budgets, merge PRs, make release claims or reassign the peer's task without proper evidence/authority. Escalate real incompatible semantics, unsafe memory contracts, ABI changes, host grants and irreversible decisions. If a subarea is blocked, continue safe independent work elsewhere.

## Non-goals for reaching bootstrap

Do not make self-hosting wait for the entire final language's Float/Float32, Map, public generics, structured concurrency, manual memory/danger API, effects/refinements, advanced AI query system, interactive tutorial or wholesale tool ports **unless the canonical compiler genuinely depends on them**. Equally, do not permanently drop these features: all accepted obligations stay open in Road 2. Do not add an OS kernel, arbitrary macro system, permanent AI runtime dependency, second semantic engine or broad multiparadigm framework just to close bootstrap.
