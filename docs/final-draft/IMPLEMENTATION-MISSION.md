# PEPIN — Implementation Mission Contract (Final Draft Design)
**Packet ID:** PEP-LANG-FD-20261027
**Parent:** PEP-LANG-FINAL-DRAFT-2026-10-27
**Status:** DESIGN/HANDOFF READY. Not a blanket authorisation to implement all features or publish a language release.
**Owner of product intent:** Matthew. **Preferred worker:** a capable high-reasoning coding agent (Luna acceptable); independent review at consequential gates.

## OBJECTIVE
Turn the accepted Pep language final draft into a **coherent, small, independently verifiable compiler/runtime roadmap**, then implement approved bounded slices without deviating from accepted semantics. Preserve an AI-first compiler with one deterministic semantic authority, an inspectable versioned semantic API and ordinary readable .pep source. The milestone is not "add every keyword"; it is *prove a cohesive working subset that can support Pep's own development*.

**Read before planning:** [full accepted draft](PEP-LANG-FINAL-DRAFT-2026-10-27.md), [acceptance matrix](ACCEPTANCE-MATRIX.md), docs/packets/CURRENT.md, docs/DESIGN.md, docs/FOUNDING_DESIGN_v0.3.md, docs/TECHNICAL_RESOLUTION_001.md and 002, docs/SESSION_PROTOCOL.md, docs/TOOL_PROTOCOL_V2.md, AGENTS.md. For the Semantic Notes proposal, inspect separately the design/semantic-notes-20261027 branch and draft PR #13; do not assume it is merged. For testing, inspect independent The-Terror-Bats repository and its receipt/architecture docs, reusing existing tools.

## SCOPE / CURRENT TRUTH
Baseline at draft creation (verify live repo before acting): primary OCaml 5.5.2 seed with Int/Bool/Str/Unit, named monomorphic records/unions, exhaustive match, typed holes, functions, lists, let/var, loops, in-process schema-v3 session and local v1/v2 extension protocols. The only published historical implementation campaign in docs/packets/CURRENT.md is A6–A8, with A8 accepted and A9–A15 marked provisional; worker branches may contain later experiments. Do NOT infer master or working directory from the newest pull request or memory summary.

The previously accepted 2026-10-27 language decisions DEC-001/002/003A-H/004-009 are target *design*, not implementation state. One document contains their consolidated meaning and flags open grammar choices.

## AUTHORITY
**This packet itself authorises documentation inspection, architecture review and reproducible low-risk planning. It is not permission to merge, change CURRENT/manifest, rewrite compiler code or deploy anything.** For implementation, first obtain an explicitly accepted bounded implementation phase consistent with current repository status and active agent work.

When implementation IS authorised, code on a named feature/workshop branch. Commit and push after every coherent working slice, with minimal receipts; pushes provide visibility, **not approval or permission to stop**. Keep implementation moving. Never auto-merge to master, force-push or overwrite another worker's work. Use the existing three-slice review cycle: after first slice continue; after second announce review after next; after third expose cumulative evidence for independent review, nonblocking unless a real safety/compatibility blocker is found.

**Do not assume an existing pull request is mergeable.** Work on the latest verified branch and respect active compiler development topology.

## CONSTRAINTS
1. **One semantics:** no AI-driven compiler truth, separate unofficial typechecker, competing annotation interpreter, or language-changing macros.
2. **Source fidelity:** UTF-8 byte offsets, LF/CRLF preservation, source and revision-bound actions, stale-safe structural edits.
3. **Safety:** accepted read/edit/take/value semantics, explicit effects/host authority, checked errors, safe memory and danger obligations; do not claim soundness or sandboxing without evidence.
4. **Modern baseline:** interpreter-first OCaml seed; future Pep-written C23 backend per TR002, not historic C11. Native codegen needs full interpreter differential tests.
5. **Truthful statuses:** imported draft syntax is NOT automatically legal Pep; partial/incomplete/invalid are distinct, tests vs proofs vs acceptance distinct.
6. **Reuse before build:** study active A11/A12/A13 branches, existing typed semantic API, test harnesses, line-ending tools, and external Terror Bats adapter possibilities before creating another stack.
7. **Cost and context:** narrow source and machine queries, deterministic small tests after each coherent slice, broader differential tests at integration gates; compact receipts, no bloated agent history.

## NON-SCOPE
- No implementation of the entire final language in one agent run.
- No production garbage collector or parallel runtime merely because the design approves them.
- No global macros, arbitrary operator overloads, general typeclasses, new AI-specific source language, unrestricted verification axioms or unauthorised capability grants.
- No premature CI/PR approval requirement after every small commit.
- No claims of implemented native testing, Semantic Notes, refining solver, effect checker, structured concurrency or C23 until corresponding tests demonstrate them.

## DEPENDENCY ORDER — candidate waves, not automatic authorisation

**Wave 0: Discover and reconcile.**
- Read actual repository state, all active branches/owners, seed grammar and test suite.
- Produce a checked status matrix: shipped vs accepted target vs draft open question vs active experimental work.
- Identify conflicts: founding reference-like collection note vs value semantics; C11 historical vs C23 target; selected-entry top-level effects vs library import purity; prefix ?hole vs postfix ?; effect declaration vs runtime permission; and the Semantic Notes verifier boundary.
- Specify *one* narrow first authorised slice and measurable gate, grounded in repo reality.

**Wave 1: Grammar and exact conformance.**
- Produce one normative grammar source and source fixtures for implemented syntax and future syntax separately.
- Handle newline continuation, semicolons, if statement/expression, else-if, break/continue, precedence, postfix ?, generics/qualified names, function types, named arguments, test/danger/uses/task constructs.
- Tokenisation, diagnostics, malformed and partial constructs, original-byte spans and source editing acceptance.
- **Choose minimal implementation deltas** preserving the OCaml seed and any accepted Pep-written parser. Don't force all syntax into one compiler milestone.

**Wave 2: Semantic core and everyday data.**
- Generic functions/records with bidirectional checking, minimal type abilities and typed behaviour records.
- Option/Result and ? propagation; checked conversions and no silent unused Result.
- Values, Array/Map/Str/Bytes/Float per conformance, explicitly safe indexing and source-visible sharing/transfer semantics.
- File-based modules and checked public signatures/qualified imports to enable multi-file tooling. Prove basic self-hosting enabling programs.

**Wave 3: Functions, effects, refinement and annotations.**
- First-class functions/closures and read/edit/take capture/call semantics with escape and alias checks.
- Effect tracking and public effect ceilings; runtime host grants remain separate.
- Lightweight flow/refinement contracts and unproved obligations with honest statuses.
- Build Semantic Notes in **separate bounded slices** starting with metadata-only read/query; independent note grammar review (draft PR #13), then typed verify requests, then bounded proof with provenance. No optimisation on unproved annotations.

**Wave 4: Explicit memory and safe native boundary.**
- Safe owned memory handles and allocator contracts, scope cleanup and typed failure.
- Mixed region/GC graph prototype, escape roots/pinning, FFI, cyclic lifetime, cancellation and DMA completion adversaries.
- danger per-operation obligations and safe wrapper assurance. No release claim until cross-domain safety proof/evidence and empirical measurement.

**Wave 5: Structured concurrency and native testing.**
- Task scopes, typed outcomes, cancellation and isolation without cross-task alias unsoundness.
- Built-in test declarations and pep test JSON, then deterministic evidence receipts, selected runs, seeds/property testing and Terror Bats adapter.
- Compile-time effect and real-time exclusions require transitive closure, not syntax-label promises.

**Wave 6: C23 and self-hosting.**
- Implement only after required compiler/runtime functionality and conformance gates exist.
- Pep-written C23 generator with Clang/GCC independent validation and interpreter equivalence.
- Self-hosting proof = new Pep compiler can compile its own source into another working compiler, without OCaml in ordinary successful build path (external C toolchain/runtime boundary explicitly acknowledged).

**Do not follow this order blindly** if live project evidence shows a different minimal dependency path. Record deviations, reuse existing accepted work and preserve product decisions.

## ACCEPTANCE
For each authorised slice:
- Exact repo, base branch, commit SHA and source revision.
- Success and failure fixtures exercising *real* parser/typechecker/runtime, not synthetic reference data.
- Existing tests remain green; new deterministic tests pass; relevant UTF-8 LF/CRLF and session schemas preserved.
- Changed observable semantics captured by a reviewed design decision, not merely compiler convenience.
- Evidence type and limits: checked, observed, unverified and human-accepted never conflated.
- Minimal compact receipt: **RESULT · branch/SHA · tests/results · new public contracts · unresolved proof/risk · next slice · HUMAN ATTENTION if actually required**.
- At third slice, cumulative independent adversarial review targeting assumptions and regressions; continue on subsequent work unless gate fails or product decision needed.

See ACCEPTANCE-MATRIX.md for individual feature gates and hostile tests.

## ATTENTION
Escalate only: contradiction between accepted public semantics and working compiler, unsound memory/effect/capability behaviour, irreversible module/ABI change, unknown external trust boundary, unreproducible evidence, or actual missing implementation authority. Do **not** escalate routine code formatting, reversible internal representation choice or ordinary compiler refactor.

## DELIVERABLE
Upon acceptance of an implementation phase, deliver checked code on a feature branch, revision-bound structured evidence and a compact truthful handoff. Preserve the full draft and matrix as references, not context to paste into every agent turn.

**Next legitimate action now:** preflight repository/status review and proposal for one concrete bounded implementation phase. No compiler edits are authorised by this design packet alone.
