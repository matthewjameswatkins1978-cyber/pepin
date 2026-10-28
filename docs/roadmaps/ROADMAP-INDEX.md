# Pepin Roadmap: Reproducible Bootstrap -> Full Pepin 1.0

**Planning date:** 28 October 2026. **Status:** authored development guidance, not an accepted implementation gate or release.
**Who should read this:** both current Pepin implementation agents, Lucy/independent reviewers, replacement agents after compaction and Matthew checking project direction.

## The two roads

| Road | Deliverable | Definition of done |
| --- | --- | --- |
| **[ROAD 1: Lucy Compiles Lucy](ROAD-1-REPRODUCIBLE-BOOTSTRAP.md)** | A genuinely Pep-written standalone native compiler with reproducible A->B->C self-compilation | No OCaml/Python semantic compiler hidden in later stages, native compiler builds itself and real Pep programs, independent Clang/GCC and reference conformance receipts |
| **[ROAD 2: Pepin 1.0](ROAD-2-PEPIN-1.0.md)** | The **complete accepted** small, AI-first Pep language, runtime, standard library, compiler semantic interface and practical ecosystem | All DEC-001/002/003A-H/004–009 obligations implemented and tested, or explicitly changed with Matthew's approval; safety/compatibility/release gates passed |
| **[FULL-LANGUAGE LEDGER](FULL-LANGUAGE-LEDGER.md)** | One source-linked status inventory, not an agent diary | Every accepted area has truthful implementation, proof, dependency/owner and next milestone; never treat parsing/isolated passing test as full support |

**Critical distinction:** Self-hosted is NOT v1.0. Self-hosting gives Lucy a working compiler built by Lucy; the complete 1.0 includes many further language/runtime contracts. Building safe, useful Pep-first foundational standard libraries must begin **before** the bootstrap closes when dependencies allow, not wait for an artificial phase boundary.

## Reader's current truth and precedence

1. **Actual implementation:** GitHub code, tests, accepted source revision and machine-evidenced compiler/backend artefacts.
2. **Accepted language design:** the individual Basic Memory DEC-001/002/003A-H/004–009 records and final design draft [PR #14](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/14), with later explicit Matthew decisions taking precedence where they conflict.
3. **Latest priority override:** [Basic Memory priority consolidation](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7C563c337a-eb00-4cb4-aa42-95a2ba584a73) and [draft PR #17](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/17). Priority 1 + 5 = one compiler-derived semantic knowledge/checkpoint model. Priority 2 = bottom-up Pep library as main practical priority. Rabbit tutor, wholesale Rust ports and paradigm-freedom research remain deferred. This **supersedes annotation-led #@ implementation** from PR #13 and parts of the older final-draft wording; preserve historical evidence, not a second semantic model.
4. **Accepted integration/release:** docs/packets/CURRENT.md and docs/packets/manifest.json. Last accepted is A8; A15 and full v1.0 are NOT accepted by a roadmap commit.
5. **Live experimental progress:** [compiler campaign checkpoint](../COMPILER_CAMPAIGN_CHECKPOINT.md), [GitHub issue #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16) and exact peer branch SHAs. Do not treat historical checkpoint SHAs in plans as permanent branch HEADs.
6. **Other authoritative requirements:** AGENTS.md, docs/DESIGN.md, TR001/002, session/tool protocols, accepted test matrix and real tests. The historical Tiny Language Design/Founding v0.3 is context, superseded by later collection value semantics and C23 target.

## Current branch-state snapshot (not an acceptance upgrade)

At initial planning, campaign contained Pep-written lexer/parser/A13 checker and a restricted Pep-written C23 emitter coordinated through the OCaml seed and Python. Agent 1's published checker receipt f10d5db3 reports 48/48 focused tests plus 11/11 A14. Agent 2's separate codex/native-collections-loop branch at 7bf4826 reports 17/17 scoped native tests for restricted Int-list for-in. These are builder-reported and independently not rerun for these plans. Current master remains A8. Source code and live branches may have moved by the time you read this.

## First practical actions for current two agents

**Both:** recover live repo/branch and Workshop Board state; confirm current owners; keep existing work. Treat this roadmap as a dependency map and **not as a task reassignment**.

**Agent 1 (checker/semantic owner):** continue A13 real parity, full structural types and nested patterns, branch/flow correctness, stage/revision facts and measurable scaling; prepare an explicit checked-IR ABI for Agent 2 without writing its emitter. Maintain exact original byte spans and first-error differential against OCaml.

**Agent 2 (native/runtime/stdlib owner):** continue isolated real Clang/GCC C23 coverage for collections, loops, ordered expression lowering, nested values and foundational safe buffers/text/bytes. Track which compiler source constructs remain unable to compile natively; emit small reusable Pep stdlib modules when the supported subset permits. Do not alter Agent 1's checker files.

**Named integrator:** ensure one writer per shared path; pin candidate SHAs; integrate with tests and no uncommitted data loss. Once a compiler-source closure inventory exists, prioritise Road 1's blocking runtime semantics rather than unrelated features. Keep full Road 2 ledger visible and steadily advancing.

## Shared coordination and reporting

- [GitHub issue #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16) is the ownership/interface/branch handoff board.
- [Basic Memory Pepin Agent Board](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cff4f6328-dd77-4b0b-8e5a-485e73554d97%7C0da28608-390d-41cb-9d28-b4e8e196c365) contains each agent's own append-only outbox, Lucy notes and collaboration information. Use [Workshop Board private plugin](https://chatgpt.com/plugins/plugins_6ae182625810819192d0acc9761e18e3) if connected, otherwise the existing GitHub/Basic Memory tools directly.
- [Pepin Current Status](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7Cb2ae60a9-86c5-46e4-9c3c-ff61b045b56e) is Matthew/Lucy's one-page operational summary. **Only the designated editor** updates that note; other agents post receipts in their outboxes.
- For each coherent tested slice: commit/push branch, attach exact SHA/tests/limits. After 3 slices obtain adversarial review where possible and **continue**. Record changed ledger rows at real integration gates. Check messages at normal boundaries, not after every command.
- Stop only colliding files/contracts or true irreversible/safety/product-decision issues. No routine approval request, no auto-merge master, no automatic CURRENT/manifest/release publication. A shared note is not a push alert to another live session.

## Navigation and status

This index and both roads are **durable plans**. They do not assert that missing runtime, self-hosting or future v1.0 features are implemented. Use SHA-bound receipts and the updated feature ledger to say what is real. When a dependency changes, revise the relevant short roadmap stage and preserve the accepted goal; do not start over or bury new decisions in repeated chat packets.

**One-sentence product direction:** Bootstrap Lucy early and honestly, then finish every accepted Pep feature with safe native behavior, a bottom-up standard library, one inspectable compiler intelligence system and evidence strong enough for Matthew to approve Pepin 1.0.
