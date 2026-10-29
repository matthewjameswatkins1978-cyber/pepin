> **STAFFING UPDATE, 29 OCT 2026:** Matthew added a THIRD independent verification agent. Read [three-agent operating overlay](PEPIN-THREE-AGENT-OVERLAY-20261029.md) and [Agent 3 Lean 4 mission](PEPIN-BOOTSTRAP-20261029-AGENT3.md). This existing full engineering plan remains the Road 1/2 source; wherever it specifies **exactly two workers** or assigns the optional Lean proof pilot to Agent 1, the new overlay supersedes that STAFFING and PROOF ownership only. Agent 1 and Agent 2 have since posted B0 receipts on [issue #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16), so earlier stopped-agent snapshots are historical. **Do not stop or reassign existing workers.** Agent 1 stays single integrator. Native security hold remains unchanged.\n\n# PEPIN / LUCY — TWO-AGENT SELF-HOSTING MISSION, 29 OCTOBER 2026

**State:** Approved planning handoff for TWO future implementation agents; **no agents are running at publication**. The user stopped all prior sessions pending this plan. This document does not start an agent, approve a release, merge code, change accepted Pep semantics, or lift a security hold.

**Mission identity:** PEPIN-BOOTSTRAP-2A-20261029 v1.
**Repository:** https://github.com/matthewjameswatkins1978-cyber/pepin
**Implementation baseline:** `campaign/pep-v01-sustained-build-20261027`, re-check remote HEAD and dirty worktrees at join time.
**Planning branch:** `planning/two-agent-self-hosting-20261029`. **Accepted master:** A8; `docs/packets/CURRENT.md` and manifest remain acceptance-controlled. NEVER infer the campaign was merged or accepted.
**Existing authority:** `docs/roadmaps/ROAD-1-REPRODUCIBLE-BOOTSTRAP.md`, `docs/roadmaps/ROAD-2-PEPIN-1.0.md`, `docs/roadmaps/FULL-LANGUAGE-LEDGER.md`, `docs/missions/FULL-LANGUAGE-ENDSTATE-AND-TWO-AGENT-PLAN.md`, TR001/TR002 and the accepted Pep decision set. The later 28 October priority note supersedes the optional annotation-first research emphasis; compiler-derived knowledge and Pep-first stdlib are priorities.
**Coordination:** [issue #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16), [review #15](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/15), Basic Memory [Pepin Agent Coordination Board](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cff4f6328-dd77-4b0b-8e5a-485e73554d97%7C0da28608-390d-41cb-9d28-b4e8e196c365), [Pepin Current Status](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7Cb2ae60a9-86c5-46e4-9c3c-ff61b045b56e). The board is asynchronous pull-based, not an agent launcher or notification system.

## 1. Success means a real compiler, not a demonstration

**Road 1:** Existing OCaml 5.5.2 seed checks/executes Pep-written lexer, parser, checker and C23 generator to produce native **A**. Native A compiles the exact canonical Pep compiler source into **B**, then B into **C**, with no OCaml/Python *semantic parsing, checking, lowering or emission* in A→B and B→C. Shell/Python may run external build orchestration, verify hashes and launch C23 toolchains; an external tool may NOT supply missing Pep compiler semantics disguised as a helper. An initially multi-executable **native** Pep compiler pipeline is acceptable when every semantic stage runs natively with a specified, verified interface; one binary is an eventual convenience, not the definition of self-hosting.

**Proof:** Clang and GCC strict C23 feature probes; real native conformance, valid/invalid/incomplete status and exact required diagnostic codes/UTF-8 byte spans; memory safety on tested paths; A/B/C compiled at pinned sources/runtime/flags; reproducible C output when specified (or documented normalization); clean second environment without seed/compiler artefacts; independent adversarial review; acceptance only by Matthew. Stage equality is consistency evidence, not a compiler correctness proof.

**Road 2:** Self-hosting is an INTERMEDIATE milestone. The full accepted Pep 1.0 scope remains in the feature ledger: source language, types/generics, ownership/effects/refinements, memory/danger, concurrency, layered Pep-first stdlib, native tests, and one AI-first semantic system. No feature is dropped because the compiler does not use it.

## 2. Ground truth and unresolved assumptions

| Topic | What repository documentation/code inspection supports | What remains unproven |
| --- | --- | --- |
| Accepted state | `master` accepted A8; campaign experimental; no newer acceptance pointer | A13/A14 production parity |
| Pep passes | `examples/pep_lexer.pep`, `examples/pep_parser.pep`, `tests/pep_checker_a13.pep`, `tests/pep_c23_emitter.pep`; `pep_c23.py` opens one persistent OCaml JSONL session and invokes Pep-written stages | Whether every compiler-used construct can execute as native Pep |
| A12 data | Existing `FlatAstNode`/chunked `ParserProgress` with parent/role/source spans; no general AST rewrite justified | Complete checked-IR / native ownership contract and transport integrity |
| Source ingestion | A12 contract states `open_bytes` 65,536-byte host guard and parser source larger than that. Pep spans already use `Int`. | Whether an attempted real bootstrap is blocked by source cap, interpreter fuel, message limits, or all three; smallest safe repair |
| Fuel/performance | Reported 100,000-step tool ceiling; staged calls made some nested cases pass; other cases still hit it | Compiler-sized scaling/independent performance profile |
| Native | Restricted C23 compiler and collection tests reported passing on development SHAs. All numbers are *builder-reported* until independently rerun. | Complete emitter/runtime coverage, clean A→B→C and cross-host portability |
| Security | `runtime/pep_text/SECURITY_2026-10-29_DEFENDER.md`: Severe Defender quarantine of two generated native test binaries; investigation read-only; security hold not lifted | Whether detection is false positive, and safe conditions to resume affected native runs |

**Do NOT copy Gemini's invented `src/lexer.pep` names, 16-bit index root cause, 150-line host-ABI estimate, automatic 90% reuse, claim of four OCaml processes, or unproven native leaks.** Gemini's latest proposals are hypotheses: partition parser into modules only if source analysis proves benefit; do not global-widen host tool permissions. `Result`, `edit`, `take`, ARC/CoW, drop flags and PepMIR are future contracts unless code inventory shows current compiler dependence. Keep accepted memory design's provisional tracing-GC fallback for unrestricted graphs; an acyclic bootstrap runtime is a subset, not permanent semantics.

## 3. Exactly TWO workers, independent worktrees

- **Agent 1: SEMANTICS + INTEGRATOR.** Own Pep-written parser/checker, source/typed IR and revision contracts, OCaml differentials, source-size/fuel investigation, canonical source/driver definition and **single integrator** role. Own `examples/pep_parser.pep`, `tests/pep_checker_a13.pep`, `tests/test_a12.py`, `tests/test_a13*.py`, and new non-overlapping checker tests by default; coordinate `examples/pep_lexer.pep`, `pep_ocaml.ml`, `pep_c23.py` if their changes are actually necessary. Sole writer of shared Pepin Current Status and full-language ledger at meaningful integration boundaries.
- **Agent 2: NATIVE + RUNTIME.** Own Pep-written C23 emitter, native lowering/order, runtime/host/stdlib substrate for compiler-used types, Clang/GCC differential and native resource tests, independent conformance adversary. Own `tests/pep_c23_emitter.pep`, `tests/test_a14_c23.py`, `tests/test_c23_cli.py`, and new native/runtime test paths by default. Existing `codex/native-collections-loop` work remains evidence to inspect; DO NOT silently merge or overwrite it. Coordinate on generated C glue and `pep_c23.py` (Agent 1 default owner).
- **No third worker.** Both review each other's meaningful contracts without self-grading. No previously named agent is presumed currently running. At restart, each declares actual role/branch/worktree/HEAD/uncommitted changes/owned file set on #16 and its OWN BM outbox. One writable worktree per agent; existing dirty work must be preserved. A branch name is not proof of a live worker.

Cross-lane seams: checked semantic facts and versioned schema (Agent 1 owns) → native emitter/runtime representation (Agent 2 owns); diagnostic/result protocol jointly reviewed; canonical Pep compiler inputs and outer coordination (Agent 1 owns) → complete generated native C and build entry point (Agent 2 owns). Where collision occurs, stop only that overlapping file/contract, pin peer SHA and negotiate one writer; continue other safe slices. The named integrator alone performs revision-pinned integration after peer receipts, without master merge.

**Mission packets:**
- [Agent 1, compiler/semantic integrator](PEPIN-BOOTSTRAP-20261029-AGENT1.md)
- [Agent 2, native/backend/runtime](PEPIN-BOOTSTRAP-20261029-AGENT2.md)

## 4. Dependency-led road, not a rigid waterfall

### B0. Evidence and closure inventory (first coherent slices, parallel)

Agent 1 inventories every canonical Pep compiler input by exact path and source SHA, grammar use, type/checked fact use, `open_bytes` and session operations; records actual `pep_c23.py` stage flow and which code runs in Pep vs OCaml vs Python. Agent 2 inventories every emitter operation and all required native types, native library functions, toolchain commands, C assembly/forward types and observable errors. Joint deliverable: one small machine-readable **compiler closure matrix** by feature, implemented/partial/unsupported, owner, evidence SHA and next minimal test. Prefer existing feature ledger to a rival truth store. No replacement AST or new ABI by assumption. Tests only where safe.

**Exit:** exact pinned end-to-end trace for at least one successful compile and one unsupported/invalid case; independent first-error source; separate source-cap, fuel, JSON transport and output-artifact limits; test provenance clearly identified.

### B1. Seed-side semantic closure + scalability (Agent 1 leads)

Preserve `FlatAstNode`/typed holes/original-byte LF/CRLF invariants, valid/incomplete/invalid distinction, source revision checks and fail-closed unsupported cases. Derive actual subset from canonical compiler source. Repair parser/checker gaps through targeted OCaml-vs-Pep positive/negative/typed-hole tests. For oversized source, measure source cap, bundle size, execution fuel and transport independently; favour staged source/multi-file ingestion, indexed traversals or explicitly isolated compiler-authority contract when justified. A source split alone does not guarantee less total interpreter fuel. Never silently relax tool-host limits, host grants or access controls.

**Exit:** compiler-used subset checked with exact source identity; representative compiler-sized input tested or a recorded blocker with minimal reproducer; no invalid source certified valid; stage protocol cannot trust forged/stale cursor/checked report.

### B2. Typed native lowering (Agent 2 leads, in parallel)

For features genuinely used by the compiler, implement strict C23 ordered evaluation and correct Int64 overflow, Bool/short-circuit, calls, returns, locals, loops, records/unions/patterns, strings/bytes, lists and any required host calls. Prefer reuse of existing emitter; add a typed intermediate layer only where the **actual** native lowering/cleanup contract requires it, not by redesign edict. Make evaluation order explicit with temporaries, reject stale/forged/unsupported IR before emission, avoid UB and GCC/Clang extensions not sanctioned by TR002. Document semantic assembly in Python: moving it into Pep is required only if Python currently supplies compiler meaning; deterministic concatenation/build orchestration can remain outside semantic compiler.

**Exit:** compiler-used feature rows supported, native checks and OCaml parity (including invalid cases); no hand-written fixture masquerading as Pep-generated code. For any owned aggregate, define copy/move/drop and verify failure/exit paths; do not assume ARC/CoW or universal header until evidence.

### B3. Narrow native runtime + Pep-written foundation (Agent 2 leads)

Provide only runtime/host operations actually needed for compiler A: raw Bytes vs valid UTF-8 Str and length-aware C boundary, file read/write, argv/exit, checked allocations/size arithmetic/alignment, owned buffers, container representation and cleanup, explicit OOM/traps, failure propagation and source identity. Write reusable higher-level helpers in Pep whenever supported. Track native pointer/length/owner provenance, static literals, NUL in text, aggregate/variant payload destruction, CoW independence as applicable. Runtime ABI is implementation-private until intentionally frozen. Respect accepted value semantics: physically shared data may never yield caller-visible aliasing.

**Security hard stop:** A 29 Oct Defender Severe/Trojan quarantine on generated test executables is documented in `runtime/pep_text/SECURITY_2026-10-29_DEFENDER.md`. Do not restore, whitelist, suppress Defender, regenerate flagged samples, or run/build new native binaries on the affected host in the held lane until explicit security review and authorization. This plan does NOT authorize native execution. Source inspection, docs, non-native verification and independent validation of test provenance can continue. For clean independent build hosts, confirm separate security approval; do not bypass the hold by moving suspected artefacts. Record every blocked test as BLOCKED-BY-SECURITY, not PASS. Escalate suspect toolchain/credential safety to Matthew, without casually declaring false positive.

**Exit:** safe tested subset in an environment cleared for native execution, Clang/GCC strict C23 with sanitizer checks where supported, negative cases and documented ABI/runtime dependencies. If hold remains, only source-level preparedness can be claimed.

### B4. Native A, integration (Agent 1 integrator with Agent 2 deliverables)

Compile canonical Pep-written compiler source through OCaml-hosted Pep pipeline and the permitted C23 toolchain; native A must itself execute the Pep lexer/parser/checker/emitter over an ordinary unrelated Pep program with no hidden OCaml/Python semantic work. Allow multi-executable native phases if specified I/O contract, exit/error propagation and authenticated revision/provenance hold. Explicit args/files/diagnostics; no hidden "magic" host compiler. Verify a real invalid-program rejection, independent positive native output and inspect native process and artefact provenance.

**Exit:** A executable demonstrated once on separately cleared environment, all constituent native stages Pep-authored, exact inputs/toolchain flags/build receipts preserved.

### B5. A → B → C reproducible self-compilation

A compiles canonical sources into B, then B compiles same into C. Build and run all stages; pin source set, runtime, flags, platform/toolchain and generated C hashes. Compare canonical B/C generated C exactly if output contract demands it, otherwise justify normalization and test behavior; do not pretend binaries must match across arbitrary C toolchains. Run independent valid/invalid/incomplete conformance, exact spans/diagnostic status, and separate Clang/GCC versions; fresh checkout with no OCaml/Python semantic compiler in successor stages.

**Exit:** independent reviewer reruns critical path and adversarial counterexamples, no unexplained hidden dependencies, full receipt and limitations. Self-hosting proof does NOT prove compiler correct.

### B6/B7. Hardening and acceptance, then continue Road 2

Second clean environment or explicit unsupported platform; deterministic provenance, path collisions, malformed bytes/AST/IR, unsigned overflow and OOM, forged cursor/revision, injected generated C, interrupted build, stale tools and wrong stage binaries; no hidden unstable caches. Agent 1 maintains full-language ledger, Agent 2 supplies independently checkable native evidence. Matthew alone approves milestone promotion, public master/CURRENT/manifest updates, releases and consequential semantic/ABI changes. After accepted self-hosting, proceed on Road 2 until complete accepted language and tests, rather than stopping.

## 5. Operational rules when Matthew is away

- **Start state:** STOPPED until Matthew actually launches/assigns two agents. Publishing this document is not an invocation or permission to impersonate a running session. They receive their individual packet + common plan.
- **No routine check-in waits.** Work independently through coherent reversible, targeted-tested slices. Commit and push only their own feature/workshop branches after each slice with minimal SHA/command/test/limitation receipt. The 3-Slice Review Cycle is nonblocking: 1/3 continue; 2/3 announce pending review; 3/3 post independent-review-ready evidence and continue safely. Reviews never silently approve own work.
- **At natural boundaries:** read issue #16, BM hub, relevant peers' outboxes. Write only to YOUR outbox using read/checksum/conditional append. Agent 1 (integrator only) updates BM Current Status and feature ledger from committed evidence. If BM unavailable, retain GitHub SHA-bound receipt and reconcile later, not invent memory writes.
- **Stop/escalate only:** severe security risk; accepted semantic conflict; runtime ownership soundness unknown for a consequential change; host permission expansion; irreconcilable stage/protocol mismatch; overlapping mutable files; destructive git operation; necessary mainline/manifest/accepted ABI or scope change. Continue unaffected safe work and leave exact next-action packet. No force-push, unsafe reset/stash, unreviewed PR merge, Windows Defender exclusion, silent budget increase or misleading success claim.
- **No new work queues without need.** Existing #16, BM board/outboxes and Road 1 are sufficient. No dependence on periodic human check-in to make routine progress.

## 6. Verification and receipts (per slice and gate)

Every receipt includes: mission+role; repo/branch/base SHA/new SHA; actual paths; statement of which semantics changed; precise test commands, target/toolchain, PASS/FAIL/SKIP/BLOCKED and counts; independent vs builder evidence; first failing reproducer and classified cause (source size vs fuel vs transport vs unsupported syntax vs runtime vs security); effect on existing evidence; next dependency; review counter; HUMAN ATTENTION only if consequential.

Conformance categories: lexer/parser originals UTF-8 LF/CRLF/invalid encoding, source-byte offsets, holes and incomplete/invalid/valid; scopes, nested records/unions, generic containers only as actually supported; recursion, assignment/for/match and negative diagnostic ordering; interpreter/native behavioral parity including checked overflow/bounds/string NUL; value independence/aliasing and cleanup for every reachable owned operation; host I/O permission and error exits; wrong C compiler/flags, emitted-source provenance, import/file path collisions; stage A/B/C deterministic artifacts. Test shared oracle assumptions independently; OCaml is an implementation oracle, not specification authority.

## 7. Handoff checklist

1. Read this plan, your role packet, Road 1, feature ledger, latest campaign checkpoint and 29 Oct security incident.
2. Confirm you are one of TWO appointed agents; declare current branch/worktree/HEAD and exact ownership on #16 and your own BM outbox before touching overlapping source.
3. Produce B0 closure row(s) from the **live** code, not Gemini's guessed file paths; compare with existing tests.
4. Take the smallest source-safe useful slice. Keep working through independent milestones without a routine approval pause; record exact evidence.
5. Integrator publishes one human-readable current status with explicit security hold and owner state after actual restart; never imply agents are currently running merely because plan exists.

**Launch readiness:** GO to evidence-led B0/source-safe work once agents are appointed. NO-GO to native execution on the affected held Windows host, speculative runtime ABI freeze, wholesale rewrite, and accepted-master promotion without further authorization.

## 8. Optional Lean 4 proof pilot (Matthew decision, 29 October 2026)

**Selected proof assistant: Lean 4, NOT Coq/Rocq for this pilot.** This is an evidence-gathering side track, not an additional bootstrap prerequisite and not a claim that formal verification is complete. An earlier Rocq extracted-OCaml lab on a separate project demonstrated tiny cases but scaled poorly (e.g. ~5.7 s at a 1,000-link chain), so avoid extracting production compiler code from proof-first representations. Rocq's maturity is not the issue; the prior workflow was the wrong shape for a fast implementation.

**Smallest useful pilot (source-only planning while the affected native test lane remains held):**
1. Pin a Lean 4 stable toolchain and Lake project after confirming a safe execution environment; no dynamic `latest` dependency in proof CI.
2. Specify *a tiny subset* of Pep values with lists and independent copying, a small-step or big-step interpreter model, and the effect of editing one logical value. Give each definition a correspondence note to accepted DEC-001 source semantics; never silently redefine Pep.
3. Machine-check a concrete theorem: after copying an ordinary value into `b`, a legal edit to `a` cannot change the observable value of `b`. Mark proof green **only** after actual Lean kernel acceptance with no `sorry`, `admit`, unreviewed axioms or `native_decide` used as an unexplained trust bypass.
4. The first theorem is about the **model**, not Lucy. Next optional experiment: compare a tiny actual compiled Pep implementation against the model, then prove/refine an abstract CoW implementation if worthwhile. Report the unverified bridge and runtime/FFI assumptions prominently.
5. Allow minimal proof-task proposals as bounded *Agent 1 semantic specification* work and Agent 2 counterexample/review input only when they do not delay B0/B1/B2/B3 native self-hosting or breach ownership/security holds. Do not pull both agents into a large Lean formalization campaign. If repeated proof engineering yields no implementation insight, park the pilot with a reproducible receipt.

**Acceptance vocabulary:** TESTED (observed), MODEL-PROVED (kernel checked under stated axioms/model), IMPLEMENTATION-REFINED (verified correspondence to actual Pep/Lucy), UNVERIFIED. Self-hosting A→B→C alone is consistency evidence and must not be described as MODEL-PROVED.
