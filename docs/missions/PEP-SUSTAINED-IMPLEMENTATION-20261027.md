# PEPIN — Sustained Implementation Campaign: Working Pep Toolchain

**Mission ID:** PEP-CAMPAIGN-V01-20261027
**Role:** Luna (High thinking), acting as implementation lead
**State:** AUTHORISED BY MATTHEW for prolonged work on **development/workshop branches**.
**Base:** codex/pep-a13-list-checking, commit 54a08f311117fe020db916286aa863b42d5151a1
**Campaign branch:** campaign/pep-v01-sustained-build-20261027
**Product direction:** implement the accepted Pep language final draft incrementally, with a real native compiler, native testing, a useful standard library and a credible path to self-hosting.
**Not authorised:** automatic merge to master, modifying an accepted release/tag, force-pushing, enabling network/secret access, or changing docs/packets/CURRENT.md plus manifest.json without separately verified integration acceptance.

## PRODUCT END-STATE OVERRIDE: FULL PEP, NOT BOOTSTRAP ONLY

**Read and follow [FULL-LANGUAGE-ENDSTATE-AND-TWO-AGENT-PLAN.md](FULL-LANGUAGE-ENDSTATE-AND-TWO-AGENT-PLAN.md) at every mission start, next slice/review checkpoint and handoff.** Matthew has explicitly clarified: the **complete accepted Pep language** is the final product. Self-hosting and the supported C23 subset are milestones **on the way**, not a substitute or new finish line. Continue after A→B→C bootstrap into every accepted type, language safety, memory, effects, concurrency, stdlib, native testing and AI-first compiler feature. Maintain a full-language completion/gap ledger showing all gaps and exact supported/tested states; do not silently declare a final-draft feature out of scope because the compiler doesn't need it to self-host.

**Two workers, complementary paths:** require each current agent to declare actual branch/worktree/SHA/current slice/files and ownership on [coordination issue #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16). Suggested division: one owns checker/semantics and machine-query interfaces, the other owns native runtime/C23/stdlib/testing, adjusted to real expertise and current ownership. One writer per overlapping path per slice, separate worktrees and explicit integration receipts. Check Lantern's Pepin Agent Coordination Board. Do not infer the second agent's identity; no automatic notification is implied.

## OBJECTIVE: AN END-TO-END PRODUCT, NOT THREE MORE PATCHES

This is an extended implementation campaign. **Do not stop because you finished three slices, one phase, a review or one pull request.** The user explicitly said that three coherent slices took ten minutes and wants a **far larger goal so they can leave you working**. Continue across multiple coherent slices and review cycles without routine approval prompts.

**North star:** a verified, usable Pep toolchain where a programmer can author meaningful typed Pep source, check it with a Pep-written front end, run it, compile a supported language subset into strict C23 and native executables, test it with a first-party Pep test runner, and inspect honest compiler-produced semantic facts. Keep extending that subset toward the full user-approved design and eventually a demonstrable self-hosting bootstrap.

**Minimum substantial integrated milestone:** complete the existing A13 Pep-written checker to behavioral/diagnostic parity over the OCaml seed language, expose version-bound checked semantics through the existing authorised interface, and get at least one real Pep program through a Pep-written C23 generator and independently executed native executable under actual verified Clang/GCC toolchains. A paper proposal, handwritten static C fixture, OCaml-only compilation or a codegen stub does not meet this target. **Once this milestone is achieved, CONTINUE** into standard-library, language-completeness and self-hosting work rather than ending solely because the first native binary exists.

The full accepted language target is documented separately. Work progressively; do not claim complete language conformance merely because a feature's syntax parses. No fake proof of soundness, native availability or self-hosting.

## CURRENT TRUTH / INHERITED EVIDENCE

Verified through the GitHub connector on 27 October 2026:
- The checkpoint commit exists: 54a08f311117fe020db916286aa863b42d5151a1, subject "feat(checker): type control flow conditions".
- Branch codex/pep-a13-list-checking is **3 commits ahead** of a13/pep-written-checker and **22 commits ahead** of master, not behind those bases at the time compared.
- The three most recent commits added builtin call validation for say/int_text, source-byte builtin contracts, and Bool-checking for if/while (including expected Bool types for holes). Tests and checker changed; unsupported List/nominal semantics remain admitted gaps.
- **Builder-reported**, NOT independently repeated in this mission document: entire suite 129 passing, focused A13 suite 14 passing, git diff --check clean. Re-run actual tests in your environment and report exact outcome, test discovery and versions.
- A12 flat AST contracts require **fully owned** parser cursor consumption; cursor.done is not an attestation. All lexer/parser/checker results must bind target document and exact source revision.
- Original repository master still records A8 accepted, manifest.current null, and A9–A15 as provisional. This is legacy integration policy, NOT a measure of development-branch capability.
- There are independent performance, conformance and C23 feasibility branches and design PR #14 and Semantic Notes PR #13. Check what is actually reusable. Do not copy experiments with false claims, silently squash branch history or overwrite their work.
- The user's previous mission ZIP was reportedly unavailable to Luna inside the checkout. **This mission lives in the repository; no ZIP attachment is required.** Read this file and the repository docs by reference.

Read on demand: docs/final-draft/PEP-LANG-FINAL-DRAFT-2026-10-27.md and docs/final-draft/ACCEPTANCE-MATRIX.md on design/final-language-draft-20261027; docs/TECHNICAL_RESOLUTION_001.md, 002; AGENTS.md; docs/packets/A12-A13-FLAT-AST-CONTRACT.md; docs/packets/CURRENT.md; tests/test_a13.py; tests/pep_checker_a13.pep. The final draft is approved **design**, not evidence of existing compiler capabilities. Later independent value semantics supersede founding reference-like collections; C23 supersedes historical C11 plans.

## AUTHORITY & OPERATING MODE

You are expressly authorised to implement across the entire campaign **on development branches** and to make routine reversible engineering choices independently. Do not ask for permission after every slice, fix, package, small API or test. The 3-Slice Review Cycle is a **nonblocking visibility and adversarial feedback mechanism**, not a completion quota.

After each coherent working slice: run proportional tests, commit, push, and leave a compact receipt (repo, branch, SHA, capability, test outcomes, limitation, review index). At slice 1/3 carry on, at 2/3 flag review after next, at 3/3 provide cumulative review materials, invite or perform independent review if actually available, incorporate blocking safety defects, **then proceed to slice 4**. Repeat 4–6, 7–9, etc. If independent reviewer unavailable, log that fact, do not manufacture approval and continue reversible work. No agent may self-certify security/soundness on its own evidence.

Prefer one working development branch for sequential slices unless an independent sibling experiment or reviewer requires isolation. Check current remote HEAD before each push; preserve local edits and other agents' work; never force-push or silently change master. Avoid unnecessary PR/CI/approval overhead after every commit; deep verification at real integration boundaries.

This does NOT authorise bypassing an actual safety failure, changing public accepted language semantics, blindly merging unreviewed sibling branches, auto-publishing a release, acquiring external credentials or live permissions, or advancing CURRENT/manifest. Make those decisions visible for separate review while continuing independent safe work.

**Self-management:** Work in coherent capabilities, not arbitrarily sliced commits or a timer-based quota. Use existing tools and standards, avoid bureaucracy. If 2 consecutive attempts at the same approach fail or stagnate, stop that approach, record why and pivot to a different viable subproblem. Preserve a compact resume record after each major milestone and before any context compaction. If the runtime truly ends, leave a durable next-action pointer rather than claiming to keep running in the background.

## MISSION SUCCESS LEVELS: KEEP ADVANCING

### Gate G1: Credible Pep-written semantic front end

Conclude only with reproducible evidence of substantial OCaml-seed parity:
- Correct checking of named and recursive functions, scalar and builtin signatures, lexical scopes and shadowing, return types, records/field access, tagged unions/constructors and exhaustive pattern matching, Lists and operations, expressions/conditions/loops and typed holes.
- Finish A13's acknowledged unsupported List and nominal typing rather than masking them with fail-closed diagnostics forever. Generic future syntax is *not* required to declare seed parity; differentiate monomorphic seed from future generic design.
- Distinguish valid, incomplete and invalid; deterministic codes/source spans, expected types, candidate bindings and revision-local semantic identity.
- Differential tests against the OCaml checker comparing semantic facts and expected errors, not just printed output. For disagreements with expected language rules, record a reproducible counterexample and repair the spec/bug deliberately rather than treating the OCaml seed as infallible.
- Test LF/CRLF, UTF-8, malformed input, stalled parser cursor, forged terminal cursor, source > current supported 65,536-byte limit, strict tool message/step bounds, and stale revision rejection. Do not silently raise limits to make demos pass.

### Gate G2: One coherent compiler semantic service

- Reuse the OCaml host and existing A7/A8 schema-v3 session / v2 tool infrastructure during the transition, rather than building a second permanent checker/server.
- Pep-written lexer, parser and checker compose through real owned, revision-bound steps. If the checker is exposed as an extension/tool, it remains clearly experimental until parity evidence and integration are accepted.
- Expose stable queryable checked facts: functions, type facts, bindings/references, call graph, typed holes, diagnostics; exactly describe query support and limitations. Make source-spanned editor operations safe for stale revisions and untouched bytes.
- Progress toward checker-independent production semantics only with strong differential gates, not by assuming two language implementations magically agree.
- Discover stdlib operations and compiler features via machine-facing contracts. Preserve schema versioning and truth status.

### Gate G3: First real native C23 compiler vertical slice

Work from the Pep-written checker and existing C23 feasibility experiment, preserving tested design choices:
- Define a small explicitly **supported** Pep subset and typed IR sufficient for several real programs containing arithmetic, functions, branching and one useful aggregate/control-flow form.
- Implement a **Pep-written** generator that emits strict C23 for that supported subset; use verified toolchain invocation. First Clang as primary, GCC independent check when actually installed. On absent toolchains, keep generator/code-review/tests moving but mark native-execution gate BLOCKED until evidence exists.
- Build executable(s) from emitted source and independently **run** them. Compare results and errors with the OCaml reference on valid, invalid and adversarial cases; check signed overflow, bounds, Unicode or target-specific ABI concerns only when subset says it supports them. Reject unsupported AST nodes with typed diagnostic, not plausible-but-wrong C code.
- Provide a usable build command or documented CLI route with source/target/output path and toolchain diagnostics, integrating with existing pep.ps1 rather than discarding it.
- Compile and run an **actual source-backed test corpus**, not only one hello-world hardcoded emitter.
- Keep runtime dependencies explicit. An emitted C source text file by itself is NOT a native compiler milestone.

### Gate G4: Complete practical language v0.1 core

Advance the accepted final draft through coherent, independently runnable thin slices:
- One-file/one-module resolver, import/visibility/public interface; selected entry-file semantics without side-effecting import initialization.
- Generic functions/types with bidirectional checking, basic Equal/Ordered/Hashable constraints, explicit typed behaviour-as-values (no unreviewed typeclass or arbitrary operator overload engine).
- Typed Option and Result, exhaustive match, postfix error propagation distinguishable from prefix typed-hole question marks; no silently discarded Result.
- Numeric Float/Float32/Byte/Bytes, Str Unicode rules, safe List and Array APIs, ordered Map; independent logical value semantics across copies/edits. Never change existing observable semantics to optimise representation.
- First-class function values and closures, then read/edit/take capture/access modes; reject borrow/escape/transfer cases until soundness is established. Keep transitive ownership and resource identities explicit.
- Surface grammar unification: optional else for statement if, required else for expression if, deterministic newline continuation, break/continue, qualified calls, generic constraints, public effect declarations, test blocks and danger. Each syntax extension requires positive and hostile grammar fixtures and checked AST. Don't implement every unproved construct as syntax only.

**Integration route:** extend parser, checker, interpreter, semantic query and native generator together per coherent feature or mark interpreter-only/native-unsupported honestly. Don't create a vast target-only grammar with no executable semantic rules.

### Gate G5: Built-in test experience and bootstrap stdlib

- Deliver pep test for source-discovered native test declarations once their grammar is accepted; typed test assertions, selected tests, structured JSON results and source spans. Tests excluded from ordinary production execution.
- Emit replayable versioned test receipts with source/compiler identity, runner/target, input or random seed, execution status, deterministic assertion/oracle findings, effects/capabilities **actually enforced**, evidence and limitations. Never promote a pass or NOT OBSERVED into universal proof.
- Build a useful Pep-written foundation library by actual dogfooding, first collection helpers, Unicode/bytes, parsing/serialization and JSON, paths/fs where host-authorised, and typed test utilities. APIs must expose effects/errors/availability.
- Add bounded property cases and differential comparisons. Reuse the separate Terror Bats framework as an **external adapter**, not a second embedded YAML runner. Test scripts, spawned processes and Git worktrees must not claim sandbox enforcement without evidence.
- Demonstrate at least one multi-file Pep sample that reads/writes appropriate authorised data, processes it with reusable stdlib functions, produces deterministic structured output, and has repeatable Pep tests.

### Gate G6: Effects, refinements and Semantic Notes

- Compiler-inferred effects for functions and function values; public effect ceilings with checked transitive calls. Distinguish type-level ability from host security authority.
- Negative tests where a declared fs.read effect is present but host denies filesystem permission. Explicitly capture declared/granted/enforced differences.
- Lightweight flow-based refinements for simple integers, bounds and boolean conditions with mutation/alias invalidation. Explicit Result-based dynamic checks where static proof unavailable; no trusted generic assume.
- Three source information layers; if adopting #@ Semantic Notes, reconcile against design PR #13. Start with trivia preservation and revision-bound metadata queries, then typed verification requests, then bounded proof/checker. A note NEVER proves what it asserts or permits dangerous operations, and may not silently change runtime behaviour.
- Compiler query separates proved/refuted/unresolved/runtime checked/observed, source facts vs author statements, and AI suggestions vs deterministic decisions.

### Gate G7: Memory-control prototype and hardened safe boundary

Do not attempt to ship a production GC or claim memory soundness based on a one-run unit test.
- Safe explicit allocation via noncopyable owned handles, allocator identity, explicit transfer/free and scope cleanup, typed allocation failures.
- Prototype stack/region inference plus a **precise tracing managed heap fallback** for cyclic general graphs. Evaluate real runtime cost, roots and mixed graph references in the planned C23 runtime; choose implementation algorithms by evidence. Preserve ordinary value semantics.
- danger permits explicitly named raw operations only; regular typing and provable alignment, length, lifetime, alias/effect checks stay on. Unknown foreign/raw conditions require exposed trusted obligations, not a fake compiler proof.
- Failure cases: double free, use after take, region/GC reference escape in both directions, cycles, C FFI rooting/pinning, destructor/callback restrictions, GPU/DMA completion/cancel before release, allocation failure and mismatched allocators.
- Keep hard real-time no-alloc/no-GC/no-block paths separately verified. Do not assert a worst-case latency bound from absent effects alone.
- If a sound GC/raw API boundary cannot be established in this campaign, preserve a **safe supported subset** and a proof/prototype branch; do not silently declare unsafe features done.

### Gate G8: Structured concurrency, explicit failures and isolation

- Task scopes own child lifetimes; explicit spawn/await; typed cancellation and error propagation; bounded event supervision.
- Independent values may transfer or share immutably; transitive aliased mutable identity must not cross tasks without explicit isolation/synchronisation.
- Provide typed channels/state-owning coordination. Validate nested cancellation, tasks waiting on external I/O or hardware, owned cleanup after parent exit, resource handling in timeout/failure paths.
- Tests seek races, misordered cancellation, leaked children, deadlocks, premature frees and unauthorised host effects. Data-race-free is not a proof of deadlock-free or deterministic scheduling.
- Implement only capabilities whose runtime safety can be justified; don't let speculative concurrency stall checker/stdlib/native progress.

### Gate G9: Actual bootstrap and self-hosting milestone

When the supported Pep semantics/library and native C23 generator are sufficient:
- Build a Pep source compiler composed of Pep-written lexer, parser, checker and code generator.
- Demonstrate stage-0 compiler produces stage-1; stage-1 compiles equivalent Pep compiler sources again into stage-2; run stage-1 and stage-2 against fixed source/diagnostic corpus.
- Identify external C23 compiler and runtime as real external dependencies. A self-compiled static executable with a hidden OCaml interpreter link is NOT self-hosting.
- Document bootstrapping inputs, reproducible build commands, hashes, runtime/compiler limitations and remaining work toward full final-language conformance.

G9 is a **north star**, not a pass claim simply because Pep sources for a parser and checker exist.

### Gate G10: Harden and prepare an honest development preview

- Cross-platform verification where target toolchains available; OCaml/Pep/C23 native differential corpus; negative/error/UTF-8/CRLF/protocol tests; bounded performance and memory measurements.
- Real sample projects and stdlib APIs, test discovery + receipts, machine-readable capability descriptions, no secret leakage, documented package/run/build usage.
- Publish **only review-ready branch/tag candidate** until explicit release/merge authority granted. User's standard is production-quality evidence, not a weekend demonstrator.
- Inventory what remains missing from the complete final draft, especially generic inference, effects, tracing GC, danger contracts, async and native compatibility, with honest readiness classifications.

## EXPERIMENTS AND PARALLEL WORK

Reuse existing experiments proportionately:
- a11/complete-pep-lexer → a12/pep-written-parser → a13/pep-written-checker → codex/pep-a13-list-checking.
- exp/c23-feasibility and exp/c23-artifact-05 as evidence for C23 capability/ABI, **not authoritative integrated production code**.
- exp/pep-conformance-* and exp/pep-performance-* as reproducible labs for black-box, performance and instrumentation. Never treat absence of observed bugs as proof of correctness.
- design/final-language-draft-20261027 is the accepted draft documentation baseline; design/semantic-notes-20261027 is a separate parser/proof proposal, not automatically merged.
- The Terror Bats repository may run adversarial tests of Pep via an adapter and an independent oracle.

Start by reading only the files needed for the next coherent slice; avoid dumping full repositories and all documentation into model context.

## VERIFICATION ECONOMY AND 3-SLICE REVIEW

**Every slice:** targeted valid/invalid regressions and relevant protocol/source-span tests; compile actual changed Pep source; git diff --check; commit/push/check remote equality. Record real counts and tool versions, distinguish builder-reported and independently rerun tests.

**Every 3 completed slices:** independent adversarial review of the prior three deltas when available, captured as review note with actual evidence; resolve any verified severe unsoundness before progressing through that safety seam. **Do not stop the campaign after review.**

**At each gate:** full discovered suite, real Pep CLI smoke, differential reference results, cost/size limits, UTF-8/CRLF and stale revision checks, exact branch SHA and exposure of known unsoundness. For native gates also verified C23 toolchain and independently executed outputs. For memory/task gates also hostile resource-lifetime tests. Defer expensive checks until consequential integration unless needed to diagnose a failing slice.

**Evidence required:** list of exact run commands, toolchain, commits, successful/failed/skipped counts, artefact hashes when relevant, sample program behaviour, accepted/unaccepted scope and what remains blocked. Do not infer green from no CI signal.

## STOP / PIVOT / ESCALATION RULES

**Continue autonomously** after normal achievements. A proposed design issue is NOT automatically a stopping event if there is another independently useful slice.

**Stop only the affected seam** if a demonstrable safety unsoundness, irreconcilable accepted semantics, unreviewed irreversible public API choice, missing external authority, leaked secret, illegal external operation, or unavailable irreplaceable tool is discovered. Record an exact reproduction; continue an unrelated safe and useful phase if possible.

**If actual entire mission becomes blocked:** provide a clean repo, pushed evidence, concise next-action packet, unresolved decision with reasonable alternatives, and explicit HUMAN ATTENTION. Never pad the outcome with tiny refactors to simulate progress, and never claim to work in the background after the tool session stops.

**No automatic master merge; no auto-release; no force pushes; no broad network deployment; no changing CURRENT/manifest without independent acceptance.**

## FINISH CRITERIA (NOT A TIME OR SLICE QUOTA)

Do **not** report "Completed" simply because 3, 6, 9 or 30 commits landed, nor because the first milestone is reached. This mission is complete only when:
1. The agreed supported target is demonstrated as a cohesive usable toolchain, including meaningful Pep source -> checked program -> native executable, real stdlib and native tests.
2. All reachable gates above have actual evidence or explicitly recorded, scoped BLOCKED/DEFERRED results with why they cannot be progressed responsibly.
3. Self-hosting is demonstrated with proper provenance **or** an evidenced dependency barrier plus a concrete continuation backlog. If blocked, be clear that the north-star milestone remains unfinished.
4. The code branch, documentation, tests and receipts permit a new agent to resume cheaply, without relying on private chat context.
5. An independent integration/release review can examine the output without trusting the builder's narrative.

There is no fixed number of slices. The correct scope is measured in **integrated compiler capabilities**, not time or quantity of commits.

## DEFAULT REPORTING (COMPACT)

After each slice:
RESULT · CAPABILITY · branch/SHA · TESTS with counts and exact commands · LIMITS · review counter · NEXT SLICE.
After each milestone gate:
GATE / supported language surface / benchmark and test evidence / deviations / safety risks / actual toolchains / highest-value next phase.
When stopped by hard blocker:
BLOCKER with exact reproduction / already tried / safe options / impact / what may continue / HUMAN DECISION needed.

**Priority if context is limited:** preserve facts and continue meaningful implementation; do not repeat the entire packet, produce another grand proposal, or wait for routine approval. The mission exists specifically because the user wants Luna to work independently for a sustained period.

## NEXT ACTION NOW (NOT ANOTHER PLAN)

1. Confirm remote branch ancestry and SHA 54a08f311117fe020db916286aa863b42d5151a1; verify current toolchain and actual 129/14 reported suites independently.
2. Read the A13 checker and OCaml typed reference. Build an evidence-backed **missing feature matrix**, with seed List typing and nominal record/union typing ranked first.
3. Implement the highest-value missing A13 feature end-to-end, with typed facts, negative tests, byte spans and a checked run.
4. Commit + push; continue into the next coherent feature. At 3/3 create review evidence and **keep working**.
5. Drive toward G1 and then G2/G3 without asking for routine approval. The next done signal is a verified **integrated capability**, not a three-commit receipt.

**User mandate, in plain English:** Make real sustained progress toward a complete Pep language. Do not treat a small batch of local type-checking fixes as the finished assignment.
