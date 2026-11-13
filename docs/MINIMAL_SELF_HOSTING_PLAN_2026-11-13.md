# Pepin: smallest useful self-hosting compiler
**Proposed direction, 13 November 2026. Status: design/implementation plan, NOT an acceptance receipt.**

## Decision proposed
Build the smallest genuinely usable Pep-written compiler first, then enlarge it by verified slices. Preserve the existing OCaml seed as reference oracle and recovery mechanism. Do not rewrite the current compiler, promote experimental branches wholesale, advance `CURRENT.md`/`manifest.json`, or relabel the A8 accepted baseline. This plan narrows the **first** self-hosting target, not the eventual Pepin 1.0 language.

**Design objective:** rigorous mathematical core; ordinary practical source language; compiler-derived explanations. A mathematical specification creates checkable obligations, not automatic correctness.

## Observed repository baseline
- Accepted `master`: A8 OCaml seed, typed core plus records/unions/lists, holes, semantic queries, tool API; historical acceptance 55 primary and 11 historical tests. No fresh execution in this planning review.
- Experimental development: Pep-written lexer/parser/checker and C23 emitter, substantial separate campaign/candidate branches; not independently certified here.
- The 5 Nov staged-versus-monolithic note on `codex/candidate7-20261105` reports some lexer chunks still hitting the 100k-step budget and one transport limitation; a staged checking proposal is not a completed compiler-source check. Measure current heads before adopting those figures as current.
- Existing Road 1 B0–B7 specifies full bootstrap; this document introduces a smaller vertical milestone before claiming those gates.

## Freeze a minimal core contract (MC0)
Specify a precise subset sufficient for *one* native compiler that can compile that same subset. Choose features from verified seed capabilities, expanding only when the canonical compiler source needs them. Candidate primitives: Int/Bool/Unit; bytes or string input and output; lexical variables and functions; calls/recursion; conditionals; finite loops; records/finite tagged variants or an equally explicit encoded IR; bounded arrays/buffers with checked access; typed result/error propagation; deterministic output. Strings, nested collections and memory need an explicit, tested runtime contract, not arbitrary hand-waving. Implement useful helpers in Pep; restrict host/runtime intrinsics to a published list.

**Mathematical obligations:** define values/types (including Unit and empty Never/bottom), typing judgments, evaluation order, error/termination behavior, and primitive effect boundaries. Define which properties are *proved*, *checked*, *tested*, or simply *assumed*. Do not add full dependent types, broad effect polymorphism, concurrency or general ownership inference to this milestone. Keep the elaborated core small and explicit, with readable syntax lowering into it.

## First vertical compiler (MC1–MC4)
1. **MC1: source inventory and scope freeze.** Inventory every actual Pep compiler source function and dependency across candidate branches; trace a compile request end to end (Pep / OCaml / Python / C runtime / system toolchain). Pick or reduce a *canonical* small Pep compiler source that is itself in the supported subset. List excluded features and why. Choose a single integration branch/worktree; other branches remain read-only inputs until cherry-picked deliberately.
2. **MC2: executable narrow compiler.** From Pep code: read Pep source bytes, lex, parse, resolve/type-check the core subset, emit deterministic C23, reject unsupported code with source-positioned diagnostics. One real external example (not compiler source) must compile and run. Generated output must not rely on a hidden Python/OCaml lexer, checker or emitter. Host orchestration and C compiler are allowed and documented.
3. **MC3: reference and hostile tests.** Freeze a small golden corpus: valid arithmetic/calls/control flow/data, invalid names/types, malformed source/UTF-8, precedence and overflow, erroneous/stale/forged stage facts, and outputs/errors. Compare semantic results to the OCaml reference where it supports the same subset. Test emitted binaries with Clang and GCC, sanitizer runs where available, and bounds/resource limits unchanged. Add independent parser/checker oracle tests; no success based only on self-consistency.
4. **MC4: reproducible native self-hosting.** OCaml seed executes Pep-written stage-0 compiler to generate C23 native A; A builds native B; B builds native C without host semantic delegation. Record source, generated C, runtime, commands, hashes, toolchain and environment. Check native A/B/C on golden and negative corpora. Compare generated C where byte stability is promised; otherwise document deterministic canonicalization and semantic parity. Rebuild from a clean checkout.

## Gate for first acceptance
All canonical compiler functions check in the chosen staged route within unchanged budgets and revision-bound complete facts; uncovered set is **empty**. Do NOT accept merely publishing an uncovered set. Monolithic artificial-scale tests may remain explicitly red *if* the staged route covers all canonical sources and independent tests establish no missing cross-chunk checks; any forged/foreign/stale fact is rejected. The exact test evidence, compiler version, source SHA, target compiler and runtime dependencies must be recorded. Human and independent reviewer approval required before promotion to accepted `master`.

## Growth after first self-host
Grow one feature at a time, keeping core semantics and inference coherent: algebraic types/complete matching, modules/generics, ergonomic errors, effect and capability accounting, resource/ownership guarantees, stdlib and full language. Each slice includes a short specification, implementation in Pep where practical, differential + negative tests, compiler-self-build regression and performance budget receipt. Avoid speculative features and second semantic engines. Semantic Map exposes checked compiler facts; it never invents proof.

## Immediate next agent task (bounded)
Read `AGENTS.md`, `docs/packets/CURRENT.md`, candidate compiler sources and current branch SHAs. Produce the MC1 closure inventory **from actual code**, a proposed smallest compiler source set, a one-page grammar/type/effect core contract, and one executable end-to-end compile fixture. Report precisely which Pep stages and host components ran. No merges, no changes to accepted pointers, no cap raises, no force pushes. When source inventory shows the smallest compiler needs one extra primitive, justify it with a failing minimal fixture rather than broadening the language on speculation.

## Current limits of this review
This plan is based on GitHub repository contents, branch comparisons and revision-bound documents, not a freshly executed test suite or audited working tree. Agent work on other branches or uncommitted local files may be newer. Verify current Git heads, worktrees, test receipts and ownership before altering implementation.
