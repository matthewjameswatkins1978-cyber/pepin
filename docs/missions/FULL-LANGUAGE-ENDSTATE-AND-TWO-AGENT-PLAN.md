# PEPIN — Complete Language End-State and Two-Agent Collaboration Contract

**Product owner directive:** Matthew, 28 October 2026. **Status:** binding goal for implementation missions, not a claim of shipped features or change to accepted semantics.
**Design authority:** [Accepted Pep Final Draft](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/design/final-language-draft-20261027/docs/final-draft/PEP-LANG-FINAL-DRAFT-2026-10-27.md), PEP-DEC-001/002/003A–H/004–009, built-in testing amendment.
**Coordination:** [GitHub #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16), [Basic Memory board](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cff4f6328-dd77-4b0b-8e5a-485e73554d97%7C0da28608-390d-41cb-9d28-b4e8e196c365).

## THE NON-NEGOTIABLE PRODUCT GOAL

**Build and finish ALL of the complete, small, AI-first Pep language accepted by Matthew, not just the subset needed to bootstrap its compiler.**

Bootstrapping (a Pep compiler builds an independent successor that can compile itself) is a major **intermediate milestone** to speed continued development. It is **not the project finish line**. Once native compiler A builds compiler B, and B builds C under verified tests, continue implementing and validating every accepted language, runtime, library, testing and AI-first semantic capability. Do NOT declare the language done because its compiler self-hosts, three slices pass, native code prints 42, or the existing A13 checker matches the OCaml seed.

A small and clear language surface does not imply that sound memory handling, a rich practical standard library, formal compiler contracts or runtime correctness can be skipped. A feature may be staged later with a named owner/dependency/gate; it must not be silently removed from scope. Accepted final-draft details that still need formal grammar or implementation evidence remain explicit OPEN items; Matthew decides any irreversible change to accepted semantics. All capabilities must have honest implemented/unsupported/tested status.

## TWO COMPLEMENTARY AGENTS, ONE PRODUCT

Matthew reports two active Pepin agents. Their **actual** live identities, branches and owned files must be verified; historical PARSER/CONFORMANCE/C23 labels are NOT assumed to identify them. At the next natural slice boundary each agent registers actual role, worktree, branch/HEAD, active task, exact intended files/symbols, uncommitted edits and dependencies on [issue #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16). Read peer declaration and relevant Basic Memory board/outbox messages.

Preferred division after both agree:

**Stream A — Compiler and semantic authority:** Pep lexer/parser/checker, final grammar, bidirectional types/generics, name resolution, access/effects/refinement checks, checked source/query APIs, Semantic Map, real compiler performance and differential reference evidence.

**Stream B — Native runtime and practical language:** Pep-written C23 backend/lowering, strict evaluation and error order, Strings/Bytes/List/Array/Map/records/unions, memory/runtime ABI, practical standard-library functions in Pep, built-in pep test with evidence receipts, independent native conformance, actual applications and bootstrap harness.

This is a suggested split, not unilateral reassignment. The campaign integrator remains one writer of each integration path. All other agents use separate branches/worktrees; **one writer per overlapping file/symbol per coherent slice**. Exchange pinned SHAs, interface contracts and clear ownership changes before touching the same checker/emitter/test paths. Never rewrite, stash, reset, rebase, force-push or overwrite someone else's uncommitted work. When a collision occurs pause only that seam and continue independent useful work; no routine wait for approval. The board cannot automatically notify live agent sessions.

Coordination boundary contracts include checked AST and types, semantic IR, source byte offsets/revisions, function and error/effect metadata, runtime ABI and tool interface versions. Review these shared contracts before irreversible change.

## FULL-LANGUAGE DELIVERY LEDGER

Maintain a durable **full-language feature ledger** in the repo, linked from the campaign checkpoint and Basic Memory project status. Columns: Area; accepted contract/reference; parser; checker; interpreter; native C23/runtime; library/CLI; tests/evidence; status; blocker/owner. Not every column applies to every feature. Use NOT STARTED / PARTIAL / IMPLEMENTED / VERIFIED / BLOCKED / DEFERRED with accurate revision/target details. "Verified" needs executing meaningful positive, negative and adversarial tests at supported target and real toolchain; a passing parser or isolated unit test alone is insufficient.

The accepted draft, not the list below, is the exhaustive source of requirements. The minimum categories that MUST remain tracked:

1. **Syntax and modules:** braces/newline rules, let/var/assignment, if statement/expression, while/for/break/continue, match, functions and closures, file modules, imports/alias/pub, visibility, entry execution vs effect-free imports, typed holes, postfix error ?, effects uses, async/spawn/await, narrow danger, comments and compiler Semantic Notes.
2. **Types and logic:** Int/Float/Float32/Bool/Unit/Str/Unicode/Byte/Bytes, fixed Array, value List and ordered Map, records/tagged unions, Option/Result, bidirectional inference, generics, minimal Equal/Ordered/Hashable, explicit typed behaviour values, function types/captures, conversions, typed errors, refinements and exhaustive matches.
3. **Semantic safety:** independent value copies, read/edit/take ownership, safe indexing/alias/access, explicit host authority separate from inferred effects, checked error propagation, scoped resource cleanup, precise proof/refuted/unresolved/runtime validation and untrusted Semantic Notes.
4. **Memory and systems:** compiler-directed stack/region/managed heap, safe manual owned allocation/free, bounded danger/FFI/pointers/pinning/rooting, no-alloc/no-GC/no-block realtime contracts, genuine GPU/external resource lifetimes, host I/O and capabilities.
5. **Concurrency:** task scopes, await/spawn, typed outcomes and cancellation, isolated mutable identity, channels/services, supervised external work.
6. **Standard library and tooling:** text/bytes/collections/math/json/path/fs/io/env/process/time/random/net/task/sync/memory/semantic, first-party pep test, replayable evidence and property testing, optional Terror Bats adapter, AI-queryable source semantics, revision-bound structural edits, practical CLI and tutorial UX.
7. **Native and self-hosting:** full accepted semantics under strict C23 and interpreter/native differential tests, Clang/GCC independent checks, multi-file real applications, stage0→A→B→C self-hosting and continued implementation after bootstrap.

A feature that is not required to compile the compiler is NOT automatically unnecessary to complete Pep.

## SEQUENCE, REVIEW AND FINISH CONDITIONS

**Near term:** measured checker/emitter scaling and safe stage-boundary reuse, language-seed parity, ordered native lowering, native core values/control/data, real applications and Pep tests.
**Intermediate:** standalone native Pep compiler; complete stage-0→A→B→C bootstrap with exact hashes/toolchains, no hidden OCaml compiler on A→B or B→C; review evidence. **Continue after this.**
**Beyond bootstrap:** complete *every* remaining final-draft language family, including generics, ownership/effects/refinements, memory/danger, structured concurrency, layered standard library, native tests and AI semantic interface; verify across actual supported targets.
**Final-language completion:** feature ledger fully accounted for; accepted features implemented and tested, or an explicit Matthew-approved revision recorded for any changed/removed obligation. A preview may document a supported subset but may not be advertised as whole Pep. No unilateral reducing final language scope to achieve a bootstrap milestone.

Use **3-slice reviews as nonblocking feedback**, push tested development commits, keep direct evidence. Independent reviewers do not magically approve their own work. Preserve master, releases, CURRENT.md and manifest without appropriate acceptance. Keep Basic Memory main/projects/pepin current and use the Lantern coordination board and owned append-only outboxes; do not alter peer outboxes. At session/context end record exact resumable work and gaps, without pretending background work continues.

**One-line standing directive to every Pepin agent:** *Bootstrap Pep as soon as practical, because it helps us finish Pep; then continue until the entire accepted language is actually built and verified. Two complementary agents, one coherent compiler and product.*
