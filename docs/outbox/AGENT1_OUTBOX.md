# Agent 1 — Outbox (append-only)

Receipts are appended newest-last and each is bound to a pushed commit.
Established 2026-11-06 following the A2 (`docs/outbox/AGENT2_OUTBOX.md`) and
A4 (`runtime/pep_text/AGENT4_OUTBOX.md`) convention: the historical Basic Memory
agent outbox note (`…ff4f6328…`) is not reachable from the 6 Nov Pi sessions'
MCP connection, so peer-facing receipts live in-repo.

---

## BOOT-A1-20261106-009 | Candidate7 PUBLISHED `codex/candidate7-20261105@6dce37d` | bound commit: 6dce37da8930bdb4b0f5ba410c8042f23110545d

**Date:** 2026-11-06 · **Dispatch:** PEP-BOOT-20261106-01 (A1 = sole integrator) · **Status: PUBLISHED, awaiting A3 independent gate.**

**SEAT CORRECTION (disclosed, bounded).** At pickup this seat mis-identified as
Agent 3 from launch-order inference; one commit `5adb893` landed in A3's
`verification/**` lane (wt-a3-gate) while the real A3 seat was active. Withdrawn
before any peer impact beyond history noise: branch reset to A3's own `b76aa19`
(remote-equal again), artifacts relocated to `D:/Projects/wt-a3-handoff-staging/
(a2_repin_verifier.py, ACCEPT-BOOT-A3-1-A2-REPIN-READINESS-A1.md) as adopt/decline
handoff; the dangling `5adb893` exists only in local reflog, never pushed.
Correct identity: **Agent 1 sole integrator**, one active writer, wt-c7 + wt-a1-fix.

**Inputs (both pushed, remote-verified):** A1 `1aaead7` (via local baseline
`c4bdec5` = `46b6712` + `727f8af` + `1aaead7`, kept unpublished per K8); A2
`495e6b1` (three-line re-pin committed inside, plus K4 record-return and
SourceBytes probes and receipts BOOT-A2-20261106-03/04).

**Publication:** `git merge 495e6b1` onto `c4bdec5` — clean, zero conflicts →
**`6dce37d`**, branch pushed (`6dce37da…845d` verified on remote). Candidate6
`46b6712` untouched (byte-identical in ancestry).

**In-tree measurement (builder-run; A3 to independently confirm):**
- `python tests/probe_seam_chunked.py` → **exit 0**; 4 chunks valid (decl 18 /
  make_token 55 / add_one 8 / main 5); 11 enumerated negatives exact; strict
  Clang 23.1.4 + GCC 16.2.0 `-Wall -Wextra -Wpedantic -Werror -O2`, 42 both
  orders, both chunk orders; seed 42.
- Bundle digest **`7fc7bb4ab909265eee5c125bf398a4ab73eb5faabc96f6ada692bdf3be12b846`**
  (NEW — the candidate's emitter is A2's `495e6b1` version, blob `5d8e41c5…`,
  larger than A2 `123d8b3`). `80c28ef5…` was the pre-A2-emitter-delta value and
  is NOT the candidate's digest.
- Stale-pin guards (mechanised in the handoff verifier, staging dir): marker
  `seed_source_pin.txt` = `727f8af4…` ✓; **tree ships the pinned checker** —
  tree `tests/pep_checker_a13.pep` blob `2d714a0e…` == `727f8af`:… blob ✓;
  printed digest == recomputed digest from pin blobs + tree emitter ✓.
- 65-target battery: `test_a14_c23` 12/12 OK (63.3 s) + `test_chunk_cross_call_facts`
  + `test_checked_chunk_contract` + `test_c23_arity` + `test_c23_str_result`
  53/53 OK (51.6 s). 65/65 at `6dce37d`.
- Disclosed semantic boundary from A2's vertical (unchanged by integration):
  native `str_concat` uses a 4 KiB fail-closed bump pool
  (`PEP_RUNTIME_STR_CONCAT_RANGE`, capacity negative green) vs seed-unbounded —
  A2's disclosed divergenced decision, not an integration change.

**GATE REQUEST to A3:** the candidate is published; asking for the unmodified
frozen instrument exactly as pre-registered (K-A3-8):
1. `verification/probes/verify_frozen_manifest.py` against a fresh candidate
   checkout → 15 pins, drift 0.
2. `verification/tools/run_acceptance_gates.ps1 (blob b464e00e…)` with
   `-Mode Full -CombinedWorktree <checkout of 6dce37d>` from A3's own
   verification files. Report ALL 15 rows; the 66-node row is expected RED
   (no cap raise, no frozen-test change) — per Matthew's Policy-B ruling
   (LUCY-20261106-001) that does not relabel 14/15; the strict staged
   zero-uncovered gate is run separately.
3. Optionally adopt/decline the verified false-green oracle (merged-scratch
   reproduction measured this session: unpatched probe exit 0 with digest
   `19a56ef…`/marker `2ad750b…` in a candidate-shaped tree while the tree ships
   `2d714a0e…`; verifier emits GENUINE_GREEN / FALSE_GREEN_STALE_PIN with
   `--candidate-mode` blob parity).

**Boundaries:** No master/CURRENT/manifest/acceptance-pointer change; no cap or
frozen-test edit; A2's branch untouched; A3's branch untouched after RESTORE
(see seat correction). Frozen Full-v2 NOT run by A1; verdict belongs to A3.

---

## BOOT-A1-20261106-010 | utf8_check helper-extraction trial: measured NEGATIVE (no gain) | bound commit: codex/a1-utf8-headroom-trial@1019234f80b51af7d3cbb653b20c15800ce7ea2c

**Date:** 2026-11-06 · **Dispatch:** PEP-BOOT-20261106-01 (A1 while-waiting slice) · **Evidence label:** `TESTED` · **Canonical `examples/pep_lexer.pep` unchanged.**

**Baseline (read-only probe, machinery from tests/test_lexer_chunk_ledger.py + READ-ONLY `metrics.last_execute_steps`), measured at A1 `1aaead7`:** all 15 lexer ledger labels reproduced (utf8_check/make_cursor/make_progress/lexer_start `PEP_RUNTIME_STEP_LIMIT`, lexer_step transport-limited, others `valid`) plus per-chunk step counts: make_token 55n = 98,228 (1.8% headroom), advance_position 33n = 51,291, ascii_letter 34,476; declaration chunks alone cost 9,020–74,689 (LexProgress declaration = 74,689). Baseline JSON: `_build/utf8_baseline.json` (ignored artifact).

**Trial (isolated scratch, `tests/fixtures/utf8_extracted_trial.pep`, seed `check --json` VALID / 0 diagnostics):** `utf8_check` rewritten with four pure helpers (`utf8_width`, `utf8_minimum`, `utf8_base`, `utf8_continue_byte`) in the same document. Staged result (`python tests/probe_utf8_headroom.py --source tests/fixtures/utf8_extracted_trial.pep`): helpers each check `valid` as their own chunks (`utf8_width` 45,745 steps, `utf8_minimum`/`utf8_base` 21,823, `utf8_continue_byte` 15,083 — one-liners with call cost), but **the rewritten body chunk still dies `PEP_RUNTIME_STEP_LIMIT` at 100,001 — identical to the original**. Node arithmetic: the family's affordability boundary is ~55 nodes/~100k steps (make_token), and the statement machinery (while loop, carried mutable state, guard ifs with `byte_at` re-reads) keeps the body ~4× over that line; the extracted chains were never the binding cost.

**Verdict:** helper extraction is NOT a zero-uncovered route for `utf8_check`. Per the dispatch fallback, restructuring stops here; the priced next route is **inner-function (statement-group) checking** — already proven at 21/21 statement coverage on `utf8_check` by `tests/test_chained_bindings.py` via `analyze_chunk_typed_bound` with scope-anchored carried bindings at this same lineage. The open integration question for the next slice is making the canonical chunk pipeline sequence typed-bound statement chunks with carried facts under the contract ledger (totality proof), not moving source around.

**Repro:** probe + fixture committed on the trial branch (`tests/probe_utf8_headroom.py`, `tests/fixtures/utf8_extracted_trial.pep`); baseline JSON regenerates via `python tests/probe_utf8_headroom.py` at any A1-lineage checkout. No canonical source, no budget, no frozen test changed; Candidate7 `6dce37d` unaffected (checker sources byte-identical).

---

## BOOT-A1-20261106-011 | typed+bound statement-group pipeline measured: utf8_check COVERED | bound commit: codex/a1-typed-bound-pipeline@04573c9c4108a1bd7368f4149cae1304af5db797

**Date:** 2026-11-06 (LUCY-20261106-004 A1 slice) · **Evidence label:** `TESTED` · **Canonical `examples/pep_lexer.pep` unchanged; budgets unchanged.**

New probe `tests/probe_typed_bound_pipeline.py` (reuses `test_chunk_typed` + `test_chained_bindings` + `pep_chunk_contract` machinery verbatim; read-only, per-invocation steps from the read-only `metrics` counter) drives the canonical staged flow per hot function: (1) body-only TYPED chunk (`analyze_chunk_typed`) with scope-fact closure, (2) else the BOUND statement-group chain (`analyze_chunk_typed_bound` = `bound-chunk`) with `BindingPool` same-revision carried facts, totality = every top-level statement group `valid` with zero diagnostics and accepted == statement count.

| function | body-only typed (scoped / unscoped) | bound chain | verdict |
|---|---|---|---|
| lexer_start | valid / valid | not needed | **COVERED** (typed body chunk; host `semantic_snapshot` facts) |
| make_progress | valid / `PEP_RUNTIME_STEP_LIMIT` | not needed | **COVERED** (typed body chunk + scope facts; scoped is the production pattern) |
| utf8_check | `PEP_RUNTIME_STEP_LIMIT` both | **21/21 groups valid, zero diagnostics**; steps 15,896–89,918 per group, all inside the 100k budget; 9 bindings carried at the end | **COVERED-BOUND** |
| make_cursor | `PEP_RUNTIME_STEP_LIMIT` both | group 0 (the only statement) itself `PEP_RUNTIME_STEP_LIMIT` | NOT-COVERED — single-statement body (69n giant record literal) needs expression-level staging, not statement grouping |
| lexer_step | transport-refusal (1 MiB) both | group 0 valid (11,704 steps); group 1 `PEP_RUNTIME_STEP_LIMIT` | NOT-COVERED — needs interior/loop-body staging above statement granularity |

**Meaning for the gap:** the typed+bound route closes `utf8_check` (the 268-node worst cost case) AND keeps `lexer_start`/`make_progress` covered, all under unchanged 100k/1MiB budgets, same document/revision/semantic target, scope-anchored renumbered facts with stale/foreign/malformed refusal. The per-invocation evidence is deterministic and source-anchored; no tool/suite/cap changed.

**What is NOT yet true (fail-closed, honestly):** this is a MEASURED BUILDER CAPABILITY, not a contract change. The canonical `ChunkLedger`/`plan_ids` flow still models one chunk per function; accepting a decomposed function (N statement groups) as ONE covered unit needs an explicit contract amendment (group coverage equals function subtree, carried-fact provenance per group, first-failing-group refusal) — separately reviewable, not smuggled into the accepted instrument. `make_cursor` (single giant statement) and `lexer_step` (giant statement) are priced as NEW mechanisms (expression-level / interior staging), not variants of chain(). Until that contract lands, zero-uncovered cannot be honestly claimed.

**Next A1 slice:** draft the contract amendment shape (typed-bound unit records with group coverage facts) for A3/Matthew review, then make_cursor/lexer_step pricing; A3 independent gate of Candidate7 `6dce37d` remains the acceptance dependency and is untouched by this slice.

---

## BOOT-A1-20261106-012 | typed-bound contract AMENDMENT DRAFTED + stay-gap pricing measured | bound commit: codex/a1-typed-bound-pipeline@135118d

**Date:** 2026-11-06 (LUCY-20261106-004 A1 continuation) · **Evidence label:** `TESTED` (pricing) + `DRAFT` (amendment) · **Canonical lexer source untouched; budgets unchanged.**

Deliverable 1 — `docs/CHECKED_CHUNK_CONTRACT_TYPED_BOUND_DRAFT.md` @ `135118d`: a reviewable amendment proposal (explicitly NOT part of the accepted instrument), grounded in `pep_chunk_contract.py`: typed-bound function-unit records with (a) exact statement-range tiling of `statement_children` (`UNIT_COVERAGE_MISMATCH` otherwise), (b) pool-renumbered same-revision carried facts (raw pooling is the measured 14/21 aliasing failure), (c) per-unit valid+zero-diagnostics with recorded first-failing unit (`UNIT_NOT_VALID`), (d) terminality only on the last range. Ledger integration: Option A (additive plan tier, recommended) vs Option B (report-carried for emitter consumption, prototype in scratch first).

Deliverable 2 — measured pricing of the two stay-gaps (`tests/probe_cursor_lexerstep_pricing.py`, JSON at `_build/pricing_cursor_lexerstep.json`):
- `make_cursor`: exactly **1** top-level statement (single giant return record literal, 69n); bound group 0 refuses `PEP_RUNTIME_STEP_LIMIT` — statement grouping has nothing to split; needs **expression-level staging** (new mechanism).
- `lexer_step`: **36** top-level statements; no interior unit exists at the failing statement (`statement[1]` has no body-role children) so one-level `bounded_units` interiors do not engage; group 1 remains `PEP_RUNTIME_STEP_LIMIT` — needs statement-kind-aware **staged descent** or separately-reviewed canonical decomposition.
- With the amendment accepted, covered set = lexer_start, make_progress (typed body), utf8_check (bound groups); uncovered after this slice = make_cursor, lexer_step (both priced, both measured).

**For A3:** the amendment is review input for the strict staged-zero-uncovered gate design; it deliberately does NOT relabel the accepted contract or the frozen Full-v2 rows. **For Matthew:** accept/decline the amendment direction (Option A) before it becomes pin-able.

---

## BOOT-A1-20261106-013 | Option A IMPLEMENTED as additive module: utf8_check chain recorded COVERED through the new unit record | bound commit: codex/a1-typed-bound-pipeline@3f3da65

**Date:** 2026-11-06 (after A3's BOOT-A3-002 hand-back; same session) · **Evidence label:** `TESTED` · **Frozen contract file and budgets untouched (new module `pep_chunk_units.py`).**

Consumed A3's verdict (Full-v2 on `6dce37d` FAIL 14/15, sole red `regression=PEP_RUNTIME_STEP_LIMIT`, staged gate FAIL with utf8_check uncovered — receipt `ACCEPT-BOOT-A3-002-CAND7-FULLV2-VERDICT.md`) and implemented the recommended lever exactly: `pep_chunk_units.py` implements the typed-bound function-unit record layer on top of existing machinery — exact statement-range tiling (`CHUNK_COVERAGE_MISMATCH` on overlap/bounds), pool-renumbered fail-closed carry (bindings admitted only from units reporting `valid` with zero diagnostics), sticky `first_refusal` (position/status/codes), structural last-unit closure, totality via `CHUNK_INCOMPLETE`. ONLY EXISTING refusal codes reused; zero edits to `pep_chunk_contract.py` (its header rule respected: no scope growth in the frozen module).

**Pins (`tests/test_chunk_units.py`, 7/7 OK, chained harness's own session):** overlap/bounds refused; first-refusal sticks and blocks carry; whole-body unit completes `valid`; terminal must end at body; none-closes-body refusal; AND end-to-end **utf8_check via the real 21-unit bound chain records `status=valid`, `unitCount=21`, `bindingsCarried>=9`** through the new record. `tests.test_chained_bindings` still 10/10 (no regression).

**One measured correction to the draft (recorded, not hidden):** driving the checker with `expect_returns=True` on a squeezed terminal slice costs more and crossed the 100k ceiling for utf8_check group 20 — so the record requires STRUCTURAL last-unit closure, and the missing-return semantic residual (whole-check absent-return diagnostic not reproduced by slices) is disclosed in the draft (`Terminality` section) and pinned via `checker_expect_returns=False` on the recording unit. Closing that residual is priced separately (whole-body sweep when affordable); never a budget change.

**State after this slice:** covered (measured, machine-checkable): lexer_start, make_progress (typed body chunks), utf8_check (typed-bound unit record, 21/21). Uncovered: `make_cursor` (expression-level staging missing — measured 1-statement body), `lexer_step` (staged descent missing — measured 36 statements, no interior unit at the failing one). Both priced in receipt 012; neither claim is accepted-usable until A3 independently gates a candidate that carries the amendment.

**Next:** A3 review of the amendment + module (gate design input); on approval, Option A plan-tier integration into the canonical pipeline so `zero-uncovered` becomes ledger-checkable; A2's computed-call-args slice and the str_concat 4KiB decision remain their lane.

---

## BOOT-A1-20261106-014 | A3 conditions satisfied: hostile pooled-carry gate GREEN + residual disclosed | bound commit: codex/a1-typed-bound-pipeline@4d2166a

**Date:** 2026-11-06 · **Evidence label:** `TESTED` (21/21 across units+hostile+chained suites) · **Consume:** A3 `BOOT-A3-007` (endorse Option A with 2 conditions) + `BOOT-A3-008`.

**Condition 1 closed — hostile pooled-carry gate** (`tests/test_chunk_units_hostile.py`, 4 pins, all on the real chained-harness session):
1. foreign-document stamped fact → pool's explicit `ValueError` propagates through `accept`; record state unchanged (nothing appended, nothing carried);
2. stale-revision stamp → same, fail-closed;
3. aliased duplicate ids across two units' reports → pool renumbers to distinct ids, no widening; partial record still refuses `CHUNK_INCOMPLETE`;
4. **forged same-anchor parameter type (`width: Bool` at the real scope anchor, capured from the checker's own report in a clean chain) is admitted by the consistency-only pool, then SURFACES at the checker on the unit that uses it → recorded as the record's `first_refusal` at that unit** — pooling never launders a forged fact into a green unit. Complements A3's K1/K1b/K1c exactly at the units layer.
Condition-1 caveat honestly recorded: the injector order matters — the pool REFUSES a same-anchor type conflict against already-admitted real facts (`conflicting BindingFact`), so the measured widening surface is confined to anchors whose real fact has not yet been pooled; both shapes are pinned.

**Condition 2 closed — draft §6.1 added**: inherited residual (same-target forged PARAMETER type admitted; forged result/arity refused) now disclosed in `docs/CHECKED_CHUNK_CONTRACT_TYPED_BOUND_DRAFT.md`; pooling widens nothing; repair is the checker-level K1-A3 residual, out of scope.

A3's declined-adopt note on the handoff-staging verifier acknowledged — staging dir removal pending at end of slice; my amendment report references the concept only where re-proven by A3's own BOOT-A3-001/002.

**Coverage state unchanged and machine-checkable:** covered lexer_start, make_progress (typed body), utf8_check (21/21 through the unit record); priced-uncovered make_cursor, lexer_step. Candidate7 `6dce37d` untouched; awaiting Matthew's accept/decline on the amendment + A3 re-gate trigger decision.

---

## BOOT-A1-20261106-015 | lexer_step full 36-statement bound map — staged-descent pricing made precise | bound commit: codex/a1-typed-bound-pipeline@0be1af0

**Date:** 2026-11-06 · **Evidence label:** `TESTED`. Continuation slice while awaiting the amendment decision; A3/Matthew asks unchanged.

`tests/probe_lexerstep_fullmap.py` runs ALL 36 statement groups of `lexer_step` through the bound chain with an EMPTY pool (continue-past-failure variant; the carried chain stops fail-closed at its first refusal): **23/36 valid; 13 failing — 9× `PEP_UNKNOWN_VARIABLE` (positions 1,3,7,8,9,33,34,35 = carriable via bindings, the utf8_check-proven mechanism), 4× `PEP_RUNTIME_STEP_LIMIT` (positions 4,5,6,10 = individually over the 100k ceiling even alone), 1× `PEP_TOOL_VALUE_LIMIT` (position 32).**

Consequence for the priced mechanism: binding carry alone closes at most the unknown-variable rows; the 4 STEP_LIMIT rows and the TOOL_VALUE_LIMIT row need **sub-statement carving** (the amendment's staged descent) regardless of carry. `make_cursor` measured again in the same run: 0/1 (its single statement is the ceiling case). Exact failing-position sets recorded in `_build/lexerstep_fullmap.json` (regenerable via the probe). Staging handoff dir `wt-a3-handoff-staging` removed per A3's declined-adopt note.

**Still awaiting:** Matthew accept/decline on the amendment; A3 re-gate trigger decision. No candidate, budget, frozen-test, or canonical-source change in this slice.

---

## BOOT-A1-20261106-016 | native SourceBytes grant contract DRAFTED (entry-bound, revision-attested) | bound commit: codex/a1-typed-bound-pipeline@a802290

**Date:** 2026-11-06 · **Evidence label:** `DRAFT` (host boundary design, grounded in measured peer findings) · **Candidate7/budgets untouched.**

Lucy's item 3 (A1+A2 coordinate the host-owned `source_bytes()` target-grant contract) delivered as `docs/NATIVE_SOURCE_GRANT_CONTRACT_DRAFT.md`: optional host-authored `sourceGrant {mode: entry-parameter}` on the existing `semanticTarget.v2`; the host native `main` wrapper passes the opened target's own bytes as the entry's first `SourceBytes` parameter (the exactly-already-lowering shape, runtime substrate present per A2); `source_bytes()` as a CALL stays refused — single semantic source, revision-bound wrapper abort, no ambient authority, refusals unchanged without the grant. Exit criteria: granted vertical end-to-end (strict Clang+GCC + seed oracle incl NUL/UTF-8), negative without grant, A3 re-gate trigger = published candidate carrying it; hostile ingress probes re-run on the new host surface.

Handoffs: A2 reviews the wrapper-shape responsibility split (host wrapper vs emitter branch); A4's frontier S1–S3 shapes map onto the contract directly; Matthew accept/decline open on both drafts (typed-bound amendment + this grant contract). #16 comment 6690088045.

---

## BOOT-A1-20261106-017 | staged-descent SIZING: failing lexer_step groups are small and context-driven, not node-driven | bound commit: codex/a1-typed-bound-pipeline@6d406cd

**Date:** 2026-11-06 · **Evidence label:** `TESTED`.

`tests/probe_staged_descent_sizing.py` measures per-statement node counts and per-invocation steps for every failing lexer_step group (empty pool, continue-past-failure):

| statement | nodes | outcome | steps |
|---|---|---|---|
| 4, 5, 6 (width/minimum chain ifs) | 39 / 45 / 35 | STEP_LIMIT | 100,001 |
| 10 (codepoint chain if) | 51 | STEP_LIMIT | 100,001 |
| 1, 3, 7, 8, 9, 33, 34, 35 (unknown-var rows) | 3–28 | invalid | 12,629–93,928 |
| 32 | **1,033** | `PEP_TOOL_VALUE_LIMIT` | 10,502 |
| make_cursor pos 0 | **34** | STEP_LIMIT | 100,001 |

**Three design facts this fixes for the staged-descent mechanism (receipts 012/015 refined):**
1. The STEP_LIMIT statement groups are SMALL (35–51n) — per-invocation cost is **context/carry-driven** (ext-fact closure + carried bindings weight), not node-count-driven; carving must cut invocation context weight, not merely split counts. (With carry, group 1 crossed from 93,928-invalid to >100k-valid — measured both sides.)
2. lexer_step position 32 is a genuine **1,033-node single statement** — the transport problem's core; sub-statement carving there is mandatory and mechanical.
3. make_cursor's whole body is **34n and still dies** — expression-level staging must reduce per-invocation overhead (or drop carried weight), not just slice smaller pieces; its typed record literal is the cost center at any granularity.

JSON: `_build/staged_descent_sizing.json` (regenerable). Candidate7/budgets untouched; still awaiting Matthew on the two drafts + A3 trigger.







---

---

## BOOT-A1-20261106-018 | LUCY-20261106-006 pickup: peers synced, both required A1 replies sent, v1 grant contract finalised | bound commit: codex/a1-typed-bound-pipeline@0640bee

**Date:** 2026-11-06 · **Dispatch:** LUCY-20261106-006 (cooperative bootstrap push) · **Evidence label:** `TESTED` + `SOURCE-READ`.

**Peer state consumed at coordination check:** A2 `935c331` (implemented the grant vertical against my a802290 draft; probe_source_grant_entry.py; A3 BOOT-A3-016 verified PASS clang+gcc NUL/UTF-8, negatives exact, seed-oracle SKIP correctly analyzed); A3 `5c07072` (BOOT-A3-009..019: my pricing/sizing/taxonomy reproduced, 65-battery split confirmed, K1c pooled forgery refused on Candidate7); A4 `d6ed6fa` (mc-seam role census + oracle pair, literal trial honestly marked pre-empted by my interior-availability probe).

**Reply 1 - A2 (Signal #16 6698085798):** their simpler shape ACCEPTED as v1 grant contract (derived, not declared - no new semanticTarget field in v1): grant iff checked entry declares a SourceBytes parameter AND name in entryFunctions; bytes = open_bytes payload of document/revision only; unlisted-entry SourceBytes keeps today's refusal; listed-entry-no-param emits normally; source_bytes() call lowering stays refused. Formalised in docs/NATIVE_SOURCE_GRANT_CONTRACT_DRAFT.md section 6 @ 0640bee; v2 reserved (explicit declared sourceGrant field, strict no-extra-fields, new review line required). G1 host-acceptance named: emit() must pass real entryFunctions (currently []); integration test asserts granted NUL/UTF-8/ASCII + both fail-closed shapes at the merged host+emitter SHA. Question to A2: where the C wrapper reads granted bytes at runtime (driver-defined pep_source_data vs argv/file).

**Reply 2 - A4 (Signal #16 6698086281):** the exact blocking invariants for their mc-seam question: (1) bounded_units interiors come only from role='body' children; make_cursor pos 0 is kind=return with zero such parts (measured at a9e9e2f, reproducible via tests/probe_interior_availability.py); record-field values are children of the RECORD node, unreachable by statement grouping. (2) the checker validates a record-construction node as ONE construct against its declaration - a fields-0..7 slice needs a NEW partial-record fact kind (field-range admission, stamped document/revision). A4 authorised: ONE isolated test-only extractor/fixture in their lane (record node header identity + original spans preserved, referenced param bindings + LexCursor decl fact + revision stamp, mc_seam_oracle halves valid, mc_seam_neg still refuses MISMATCH at same span), no checker/host edits; A1 consumes the fixture for the carver design (G2).

**Also consumed:** A3's retracted A2-scalability-claim note honored (no redesign on that basis); A3's BOOT-A3-018 (K1c refused on Candidate7) closes my hostile-gate acceptance condition with shared-machinery evidence.

**Next A1 slice (G1):** implement host acceptance in pep_c23.py emit() (real entryFunctions + integration test) once A2's runtime-bytes answer lands; then G2 carver design from A4's fixture; then G3 new experimental integration candidate + A3 strict gate.}`

---

## BOOT-A1-20261106-019 | G1 host acceptance DELIVERED: emit_granted green at merged host+emitter SHA | bound commit: codex/a1-typed-bound-pipeline@0866530

**Date:** 2026-11-06 (LUCY-20261106-006 G1) · **Evidence label:** TESTED · Merged A2 935c331 into codex/a1-typed-bound-pipeline (no conflicts) at 68026fc.

New pep_c23.py emit_granted() implements grant contract v1 (derived mode) end to end: open_bytes target (status valid), parse+check with entryFunctions=[entry] if granted else [], entry shape from pep-c23-checker-sigs (MEASURED: the checker REPORT elides entry params - params==[] for the entry; discovered and pinned), host validation BEFORE any emitter invoke, then emit via pep-c23-emitter (A2 emit_c23_checked). Refusals all pre-emitter and typed: GRANT_DENIED (ungranted SourceBytes entry), GRANT_SHAPE_MISMATCH (granted entry without SourceBytes param), GRANT_ENTRY_MISSING (checker PEP_SEMANTIC_ROOT_NOT_FOUND mapped, or signature absent). tests/test_grant_host_acceptance.py 4/4 OK (~1s) at the merged SHA: granted wrapper binds pep_source_data (assertion mirrors A2 probe), plus the three refusals. A3 layering: K1/K1b/K1c matrix maps onto this host surface; runtime parity (Clang+GCC NUL/UTF-8) already verified by A3 at A2 935c331.

A2 questions answered: (a) host refuses pre-emitter (authoritative); (b) not needed in v1 (their semanticTarget.entryFunctions flow remains defence-in-depth). Awaiting A2 ACK + runtime-bytes mechanism answer, then the merged integration test runs the actual file (G1 close) and G2 consumes A4 fixture. #16 6698271768.

---

## BOOT-A1-20261106-020 | G2 slice contract pinned from A4 extractor | bound commit: codex/a1-typed-bound-pipeline@7d58003

**Date:** 2026-11-06 · **Evidence label:** TESTED.

A4 test-only field-range extractor consumed (spec/agent4-spec-lab@1577aa3): mc_seam_slice_0_7/8_15 descriptor pairs copied to tests/fixtures (data, provenance annotated); new pep_record_slices.py validate_field_slices() pins the contract - identical headers (recordType LexCursor, recordSpan, declSpan), fieldIds tile 0..15 exactly, field spans inside the record span (descriptor span naming endOffset handled), carried bindings cover field bindingIds, provenance required; overlap refused by test. tests/test_record_field_slices.py 2/2 OK. This is the executable target for the checker-side partial-record admission (next G2 A1 slice); A3 asked to pre-register the wrong-field-type counterexample at the pinned span before that lands. A4 STOP honored. #16 6698365390.

---

## BOOT-A1-20261106-021 | grant handshake RESOLVED: (i) argv/file adopted, v1 ownership rule revised | bound commit: codex/a1-typed-bound-pipeline@11e1294

**Date:** 2026-11-06 · **Evidence label:** DECIDED + TESTED (merged host tests already pass with the payload-operand shape).

A2's divergence (BOOT-A2-20261106-40) resolved: v1 adopts (i) argv/file - the wrapper reads ONE host-named operand once, fail-closed pre-entry on argc<2, no second byte source / cached global / scanner; equality of operand contents to the opened payload is host-verified at integration level; emitter-enforced identity binding reserved for v2 (declared field). Draft s6 revised accordingly (@11e1294). A2's implemented wrapper at 935c331 is now contract-conforming as-built; per mission item 4 A2 may proceed to the next closure feature. A3 hostiles onto the argv surface mapped (operand swap/duplicate read). #16 6698433832.

---

## BOOT-A1-20261106-022 | G2 field-slice verdict reported: expressible, bounded by record-validation cost | probe scratch `_build/probe_v4.py`, branch @11e1294

**Date:** 2026-11-06 · **Evidence label:** TESTED (probe chain, regenerable) · Verdict Signal #16 6698667122 to A4/A3.

Experiment chain completed across turns 5-9: parent-chain-preserving field-range keep-sets (function root + return + record node + fields[lo:hi], parent=-1 terminus) — the original remap parent-chain break fixed; LexCursor declaration travels as a ResolvedTypeDecl FACT (slice-4b typed pattern) instead of source nodes; scoped fact_closure signatures. Both halves (fields 0-7 / 8-15) still refuse `PEP_RUNTIME_STEP_LIMIT`.

**Conclusion (measured at field granularity):** make_cursor record-field slices are EXPRESSIBLE through the existing typed path; the residual cost is the checker's record-construction validation itself (per-field type check against the declaration). The only remaining route to make_cursor coverage is the partial-record fact kind — checker Pep source work, requiring A3's pre-registered hostile matrix (field duplication / phantom field / missing field / wrong type at pinned span) and Matthew's approval, per the standing amendment boundary. A4's STOP was honored; their census/oracle pair formed the basis of this verdict.

**Standing peer-gated items:** A2 — consume `emit_granted()` at the merged SHA + runtime-bytes ACK (G1 close); A3 — partial-record hostile matrix pre-registration; Matthew — accept/decline typed-bound amendment + SourceBytes grant contract.
