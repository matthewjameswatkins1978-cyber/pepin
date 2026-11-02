# Pepin: the road to 1.0

**Product roadmap · 2 November 2026 · planning document, not a release or implementation certificate**

Pepin's destination is a **useful, independently buildable, AI-first general-purpose programming language**. Its source language is Pep; Lucy is the intended compiler and semantic development environment.

The goal is not merely to get a tiny compiler compiling itself. **Self-hosting proves a major engineering capability. Pepin 1.0 must additionally deliver the accepted language semantics, practical libraries, dependable tooling and evidence-backed safety.**

## First, how to read progress

There are three distinct states, and none automatically implies another:

- **Accepted on `master`:** an implemented milestone with a recorded acceptance boundary. The current accepted baseline is **A8**; see [implementation status](DESIGN.md) and the [authoritative packet pointer](packets/CURRENT.md).
- **Working on another branch:** experimental or ongoing implementation. Successful focused tests on a branch do **not** establish integration into accepted `master`, general language coverage or release readiness.
- **Designed / proposed:** a desired language feature or engineering contract. It remains unshipped until separately implemented, verified and accepted.

The detailed [Road 1 bootstrap plan](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/ROAD-1-REPRODUCIBLE-BOOTSTRAP.md), [Road 2 full-language plan](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/ROAD-2-PEPIN-1.0.md) and [feature gap ledger](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/FULL-LANGUAGE-LEDGER.md) live on a **development branch**. They are detailed working plans, not an accepted release manifest. This stable overview deliberately does not duplicate their continually changing test receipts.

## The milestones

| Phase | Outcome | Status at accepted `master` |
| --- | --- | --- |
| **Foundation (A0–A8)** | Typed seed, introspectable source, semantic sessions, guarded typed-hole edits, living Pep tools and a Pep-written analysis proof | **Completed through A8** |
| **Road 1: compiler foundations** | Pep-written reusable substrate, byte/text support, real lexer, parser and checker with oracle/differential tests | **Not accepted**; development branches contain candidate slices |
| **Road 1: native bootstrap** | Real Pep-written C23 emitter/runtime and staged A → B → C self-compilation that no longer hides an OCaml/Python semantic compiler in later stages | **Not accepted** |
| **Road 2: complete Pep** | Full accepted surface language, values, ownership, safe memory, errors/effects/capabilities, tasks and interoperability with verified native parity | **Not accepted** |
| **Road 2: libraries and intelligence** | Pep-first standard library, first-party tests, semantic queries, evidence, revision-safe modifications and usable real applications | **Partly prototyped**, mostly planned |
| **1.0 release gate** | Frozen tested contracts, self-hosting proof, security review, real applications, installable documented supported platforms and explicit approval | **Not met** |

Phases overlap when it is technically sensible. For example, the standard library should grow alongside compiler work rather than be left until the final phase. The numbering is an orientation aid, not authorisation to skip dependencies or declare a release.

## What we've already proved

The current OCaml 5.5.2 seed has established:

1. **Pep source can be parsed, resolved, checked and executed** for a meaningful typed subset, including records, unions, list operations and structured control flow.
2. **Incomplete programs can still be useful.** Typed holes expose expected types and visible bindings, and unresolved holes cannot be run as complete programs.
3. **The compiler can serve tools.** File commands and a schema-v3 JSONL session provide machine-readable facts, byte-faithful revisions and guarded hole filling.
4. **Pep can extend its own workshop.** A bounded, trusted-local tool protocol registers checked functions; a real Pep-written unused-function analyser uses authorised checker-derived facts.

These are working architectural proofs, not a complete general-purpose language. Published A8 acceptance reports 55 primary OCaml tests and 11 historical MoonBit tests at their recorded baseline. Do not reuse those counts for newer branches.

## Road 1: Lucy compiles Lucy

The first major mountain is **Pepin in Pepin**.

**Compiler foundations.** Build a small useful Pep-written substrate, choosing compiler primitives only for genuinely irreducible or demonstrably necessary operations. Original-byte handling, correct UTF-8 and safe efficient token builders are practical prerequisites for a real lexer.

**Lexer → parser → checker.** Have Pep-written components consume real Pep source and produce compiler-owned, source-revision-bound syntax and typed information. Differential-test them against the accepted OCaml seed; reject unsupported cases explicitly rather than claiming parity.

**C23 and runtime.** Move from interpreted seed execution to real Pep-generated C23 and verified native executables. Use Clang as the primary target toolchain and GCC for independent checks where available. Test actual semantics, failures, cleanup and ABI compatibility, not only emitted text.

**Reproducible self-build.** Demonstrate compiler-stage A → B → C with source and artifact identities, independent test executions and no OCaml/Python semantic compiler silently performing the work of the purported Pep compiler after bootstrap. The OCaml seed can remain a recovery/reference tool.

The development campaign contains experimental Pep-written compiler and restricted native paths. Those are valuable work, **not** evidence that this final gate has been passed. See the [working bootstrap plan](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/ROAD-1-REPRODUCIBLE-BOOTSTRAP.md).

## Road 2: the complete language people can use

Road 2 finishes the intended product instead of stopping at the bootstrap demonstration.

**The language contract.** Settle exact grammar, name resolution, modules and visibility, bidirectional typing, generics, first-class functions and closures, checked operators, records/unions and exhaustive control flow.

**Independent data and predictable errors.** Implement the agreed value semantics for ordinary data, collections, checked integers, floating-point, Unicode strings versus raw bytes, array/map behaviour, Option/Result and explicit error propagation. Efficient storage is the compiler's job, not a change to source-language meaning.

**Safety without needless ceremony.** Infer safe behaviour when possible; provide explicit `read` / `edit` / `take` access, carefully bounded `danger`, resource lifetime rules, and separately enforced host capabilities. Compiler effect inference does **not** grant filesystem or network authority. Reconcile native memory reclamation, ownership, FFI, cancellation and concurrency with adversarial tests before claiming strong safety properties.

**Libraries built upwards.** Prefer small Pep-written reusable foundations (text, bytes, safe buffers/builders, collections, algorithms, parsing, JSON), then files/IO/process/network/time, testing and development utilities, using narrow host primitives where actually required. Avoid growing dozens of special compiler intrinsics as a substitute for a standard library.

**Lucy as an authority on code, not a chatbot.** One checked semantic engine should serve CLI, compiler, tests, editors and agents. Expose bounded exact-source queries and read-only checkpoints first; add durable, invalidation-safe reuse only when it proves useful. Keep checked facts, recorded observations, test outcomes, human decisions and AI suggestions distinct. General structural editing should use revision guards and checked previews.

**Usable outside its own repository.** Run real programs, provide consistent check/run/build/test/query/describe interfaces, report supported targets and effects, document versioned APIs and ship a practical install path. A language that only compiles its own toy demonstrations has not earned 1.0.

The complete intended feature inventory and acceptance gates are detailed in the [Road 2 plan](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/ROAD-2-PEPIN-1.0.md) and [full-language ledger](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/FULL-LANGUAGE-LEDGER.md). They represent the complete accepted ambition, not a promise that every design example already parses.

## What wins priority now?

The most recent product-priority clarification (28 October, [review PR #17](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/17)) makes two complementary investments central:

1. **A bottom-up Pep-written standard library** whose useful parts become real before building an enormous package ecosystem.
2. **One compiler-derived semantic understanding system**, including inspected checkpoints and revision-bound evidence. The compiler establishes facts; caches, notes and models cannot silently define new language meaning.

The alternative idea of making programmer-authored `#@` Semantic Notes the centre of the architecture is **superseded**. The rabbit tutor, large-scale ports of existing tools and a graphics/audio Pep Lab remain interesting later directions, not 1.0 implementation prerequisites. Compiler/runtime correctness, safety and hard integration work continue in parallel.

## 1.0 is an acceptance standard, not a date

Before the project can call itself **1.0**, we need credible evidence for all of these:

- A written, versioned language and standard-library contract with executable conformance fixtures and an explicit disposition for each accepted requirement.
- A genuinely reproduced self-hosted compiler chain and a tested supported native C23 path.
- Cross-implementation and adversarial tests of language behaviour, memory, effects, concurrency, FFI and failure/cleanup paths; errors and skips clearly reported.
- Safe host authority boundaries in the supported deployment model, not an unproven assertion that trusted in-process extensions are sandboxed.
- Real-world Pep applications that exercise the language beyond compiler fixtures.
- A coherent CLI, query/edit protocols, user documentation, installation, supported-platform matrix and reproducible release artifacts.
- Independent review and explicit human approval for the final 1.0 release.

No release date, performance superiority claim, complete memory-safety claim or cross-platform support claim is justified until verified.

## Navigating implementation safely

For an implementation assignment, **start with [packets/CURRENT.md](packets/CURRENT.md)** and [packets/manifest.json](packets/manifest.json). The accepted integration pointer is deliberately separate from feature work on development branches. A roadmap is a dependency and acceptance map, **not** an instruction to auto-merge experimental work or advance release metadata.

Use [DESIGN.md](DESIGN.md) for the supported seed, [the documentation guide](README.md) for more detail, and the exact source/tests of any development branch when discussing experimental progress.
