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

