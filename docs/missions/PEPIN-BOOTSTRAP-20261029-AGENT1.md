# PEPIN-BOOTSTRAP-2A-20261029 / AGENT 1
## Compiler Semantics + Single Integrator (future appointed worker)

**PRECONDITION: USER REPORTS NO AGENTS CURRENTLY RUNNING.** Begin only when Matthew launches/assigns you as Agent 1. Read [common mission](PEPIN-TWO-AGENT-SELF-HOSTING-20261029.md) first; its security hold and authority rules control. Mission is the complete Road 1 bootstrap, continuing into Road 2 after acceptance. This packet is not a blanket instruction to merge or redesign.

### OBJECTIVE
Preserve and complete the **Pep-written semantic compiler** needed for reproducible A→B→C self-hosting, with revision-safe typed facts, correct status, source spans and measured scaling. Act as the **sole integration owner and Current Status editor**, keeping Agent 2 on an independent native/runtime branch.

### CURRENT TRUTH / INHERITED EVIDENCE
- Accepted `master` A8 (55 primary + 11 historical tests, old builder-reported acceptance). Experimental campaign `campaign/pep-v01-sustained-build-20261027` has `examples/pep_lexer.pep`, `examples/pep_parser.pep`, `tests/pep_checker_a13.pep`, `tests/pep_c23_emitter.pep`; `pep_c23.py` invokes stages in one persistent OCaml JSONL session. This does **not** prove self-hosting.
- A12 flat `FlatAstNode` / `ParserProgress` is real. Parser input limit documented at 65,536 bytes via host `open_bytes`, not 16-bit token offsets. The 100,000-step tool fuel and transport size limits are separate. Native stages may have different bounds. Never infer a source split fixes fuel.
- A13 has substantial checker/OCaml differentials but is partial; no unconditional `valid` certificates outside checked subset. Exact live HEAD and accepted/tested SHAs must be recovered at restart. Do not quote old test counts as fresh.
- Security hold: `runtime/pep_text/SECURITY_2026-10-29_DEFENDER.md`. Severe Defender alert on generated native binaries; no native build/execution on affected Windows host until explicit security clearance. Do not change protections or assume false positive.

### SCOPE / OWNERSHIP
Default owned paths: `examples/pep_parser.pep`, `tests/pep_checker_a13.pep`, `tests/test_a12.py`, `tests/test_a13.py`, `tests/test_a13_nested_records.py`, schema/source revision metadata, and new semantic/integration planning files. Canonical compiler driver/source composition and `pep_c23.py` are **Agent 1-owned if changes needed**; confirm with Agent 2 before touching shared/generated code. The lexer `examples/pep_lexer.pep` and `pep_ocaml.ml` require explicit collision check. Agent 2 owns C23 emitter, native runtime, native-specific tests. No shared checkout.

### DEPENDENCY-ORDERED SLICES (continue after 3-slice review)
**1 / B0: Source closure.** Enumerate the exact Pep compiler modules and their current source-language constructs, required intrinsics, typed records, host calls, canonical assembly, versioned interfaces. Trace `pep_c23.py` down to actual Pep/OCaml/Python operations and mark semantic vs deterministic transport/concatenation. Record actual SHA, feature coverage, tests, unsupported examples; do not copy unverified Gemini inventory. Produce compact closure-matrix rows in your owned planning/ledger path after pinning baseline.

**2 / B0-B1: Separate resource bottlenecks.** Reproduce `open_bytes` cap, interpreter fuel, output/message limits and multi-file composition independently. Use a small source near each boundary, then the real compiler source as a reproducer. Choose the least intrusive correction: measured traversal/indexing changes, stage partition, or carefully scoped compiler-only I/O capability proposal with explicit authority. Do not globally raise cap, disable budgets or weaken tool host without Matthew's consequential approval. A >64 KiB module is a symptom, not proof that the native compiler must be split.

**3 / B1: Semantic closure.** Build compiler-used syntax/type matrix and mark `valid` only when checked. Preserve original byte LF/CRLF spans, named holes and `incomplete` distinct from `invalid`; reject forged/stale `ParserCursor`, unverified `CheckerReport`, unsupported patterns, type errors and changed revisions. Include nested records/union payloads, function calls/returns, assignment, loops, lists as actual source uses. Use OCaml vs Pep differential fixtures, independently specified invalid cases and explicit interpreter-step records. Keep OCaml reference as a recovery/differential oracle, not a second permanent production compiler.

**4 / B1-B4: Canonical driver and integration.** Define reproducible Pep compiler source set, source/module identity and stage interface. Prefer working staged native pipeline to forced premature monolithic binary. Integrate pinned Agent 2 emitter/runtime after independent review and compatibility checks; no silent overwrite. A must compile unrelated Pep programs and produce checked negative diagnostics natively without hidden seed semantics. The integrator owns exact source/artefact/toolchain receipts and A→B→C process proof when the security hold is cleared.

**5 / B5-B7: Bootstrap proof and Road 2 continuity.** Run A/B/C protocol in approved safe environment, preserve all hashes/commands/output and independent QA, update full-language feature ledger accurately. Self-hosted ≠ full Pep 1.0. No master, CURRENT, manifest or release promotion without Matthew's acceptance.

### ACCEPTANCE PER SLICE
One coherent tested capability; commit/push your OWN branch; record exact tests and counts, PASS/FAIL/SKIP/SECURITY-BLOCKED, SHA, spec source, limitation, next test and review counter. Use targeted tests during development, broader dependent tests at substantial gates. Negative cases and proper status matter more than vanity counts. Any new checked IR exported to native must carry exact source/revision identity and fail-closed verification. Do not trust a parse cursor merely because `done=true` was supplied.

### WORKSHOP BOARD COLLABORATION (mandatory)
Follow [Workshop Board](https://chatgpt.com/plugins/plugins_6ae182625810819192d0acc9761e18e3); if unavailable use connected Basic Memory Cloud and GitHub. Announce actual role/worktree/branch/HEAD/current slice/file ownership and uncommitted changes on [issue #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16). Read hub, Current Status and relevant peer outbox at natural slice boundaries. Append meaningful observations ONLY to your Agent 1 outbox using read/checksum/conditional append, never to Agent 2's outbox. Agent 1 alone updates shared Current Status, and the feature ledger at significant gates, with source-backed as-of dates. GitHub commits/test evidence remain authoritative. Coordination is pull-based, not live notifications.

### ATTENTION AND STOP RULES
Do NOT stop for routine review or approval. Continue reversible independent work after three slices. Stop only affected seam for memory safety/authority contract change, security alert, schema/source semantics conflict, dirty-worktree collision, destructive git action or acceptance promotion. If Agent 2 has not yet joined, continue isolated source/semantic work and leave a handoff contract for later. Never widen native execution rights, whitelist binaries or increase host budgets quietly. Tell Matthew only what needs consequential judgement.

### RECEIPT
`AGENT1 | repo/branch/base/new SHA | exact source/semantic change | commands PASS/FAIL/SKIP/BLOCKED | OCaml reference differential evidence | compiler-used subset row | peer dependency | review 1/3–3/3 | next independent slice | HUMAN ATTENTION (only if real)`

**Next legitimate action on launch:** Verify live branch/dirty state/security hold, post role declaration, complete B0 semantic closure and reproducible source-limit/fuel classification. Do not start with a rewrite.
