# Verification receipts index (Agent 3)

One-line status per receipt, grouped by thread. Newest first within
groups. **Current blocker map at the bottom.**

## Lean 4 (DEC-001 value-copy model)

| receipt | status |
|---|---|
| `lean4-kernel-check.md` | **`MODEL_PROVED`** — kernel-checked locally on pinned leanprover/lean4:v4.35.0 (2026-10-30, post-#22): `lake build` green, `BrokenVariant.lean` rejected as required, `#print axioms` = `[propext]` only; two draft defects fixed without touching theorem statements. Third-party reproduced by the report lane. |
| `lean4-build-BLOCKED_SECURITY.md` | **Historical** — the hold-era record; retired by the #22 clearance, kept for provenance. |

## Blocker saga (2026-10-30, chronological — the day's central thread)

| receipt | verdict now |
|---|---|
| `FINDING-a14-stale-expectations-fd5c5d5.md` | Stale length exemplar: **still open** (builder test file, decision theirs). Recursion half **superseded** by the REFINEMENT below. |
| `REFINEMENT-a14-recursion-contract-fd5c5d5.md` | Recursion contract: behavior change not rot; lenient-flag native = interpreter (`PEP_RUNTIME_CALL_DEPTH`); reconciliation with the report lane became mutual. Test update still builder's call. |
| `FINDING-a2-emit-step-budget-regression-8e076e2.md` | **Origin of the emit-cost thread** — window `7bfb819..8e076e2`, attribution across 6 states. |
| `FIX-STATUS-a2-cfa88d2-partial.md` | Fix round 1 partial; countdown class widened (99/100 boundary found). Superseded operationally by later rounds; kept for the oscillation history. |
| `FIX-STATUS-a2-7b69964-boundary.md` | Fix round 2: small-countdown recovered; exact boundary measurement. |
| `RECONCILIATION-emit-walls-two-paths.md` | **Two invocation contracts** (`emit_c23` all-in-one vs `emit_c23_checked` staged); corrected my round-2 value-linear attribution. Still the key triage reference (Keeper decision saved). |
| `FINDING-a1-d64ea2a-bundle-type-mismatch.md` | Bundle `FlatAstNode`/`CheckerNode` break — **RESOLVED** (A1 `7628d6d` adapter + A2 `c9751e5` namespace isolation). |
| `GATE-RESTORED-second-blocker-3d6774e-c9751e5.md` | Bundle restored in combined; second blocker (validation arity) exposed — **superseded by FIX-RECIPE below**. |
| `BLOCKER2-LIVE-a1-7628d6d.md` | Arity blocker live on A1-own as forecast — **RESOLVED** by `46bf1c0`. |
| `FIX-RECIPE-blocker2-verified-wallA-measured.md` | **The tested 5-substitution recipe** (expect constructions were the type defect, not arg1) → `emit OK`; Wall A measured first time (str/cli green, classifier 5× STEP_LIMIT). |
| `RECIPE-LANDED-46bf1c0-blockers-wallA-wallB.md` | Recipe landed+verified on both lines; A1-own green to 2 known. Blockers narrowed to Wall A + Wall B. |
| `HOTSPOT-emitter-pep_c23_child-5114.md` | **Wall A hotspot**: both closures die at emitter L25 (`pep_c23_child` scan; 186 call sites, 72 node loops). |
| `WALLS-AB-distinct-death-regions.md` | **Walls A/B mapped to distinct regions** — one hotspot, two contracts, two fix logics (bucket-index vs contract change). |
| `STATUS-a1-d02a531-a2-dea32c0.md` | Mid-saga status (A1 bundle still broken era); superseded by the FIX-RECIPE chain — kept for chronology. |

## Pinned differential rounds (peer-claim verification)

| receipt | covers |
|---|---|
| `PINNED-ROUND-20261030-b27b247-77aa6b9.md` | 97/97 + merge recipe 9/9 + UBSan spot-check (clang-only; gcc libubsan missing — Keeper gotcha). |
| `PINNED-ROUND-20261030-eb8f7c0-784050c.md` | Recipe change after emitter move; first 15-module baseline: **262 tests / 3 known failures**. |
| `PINNED-ROUND-20261030-f7efa23-7bfb819.md` | A1 claim 109/109 + skipped native arm; SourceBytes seam verified (combined 14/14). |

## Late rounds (turns 23–37 — baselines, cross-lane verification, report-claim audits, `ae91bdc` analysis)

| receipt | one-line |
|---|---|
| `RECOVERY-eda6a0f-depth-axis-cleared.md` | **Depth axis FIXED**: A1's arm-hoisting (direction #1) recovers heavy **26 → 4**, deep suite 22 → **0**; remaining 4 = a14 step-axis set (Wall B track). |
| `REMEASURE-e37218a-persists-26.md` | A1's response `e37218a` (checker overhead): heavy still **26** — parser chains untouched, regression persists; their new driver tests **12/12 OK**; no new defect in heavy set. |
| `MECHANISM-ae91bdc-match-chains.md` | **`ae91bdc` mechanism**: 3 parser dispatchers split into 19/29/19-way fallthrough chains; each hop = 1 host frame; death = `ast_value_span_part_1/part_3` braces (parser L138/152); one mechanism, two budgets (depth 128 + step 100k). |
| `BISECT-ae91bdc-sole-breaker.md` | `bff9dad` = 124/2 green (report's 276/3 independently confirmed); **`ae91bdc` alone breaks** — fix scope = flattening commit only. |
| `REGRESSION-a1-ae91bdc-scale-work.md` | First measurement of `ae91bdc`: heavy 120/2 → **124/26** (deep-suite `CALL_DEPTH` ×22, a14 2→4 = Wall B on A1-own). |
| `FOURPARAM-confirmed-narrow-familyB.md` | Four-param one-liner confirmed; only 2/14 family-B helpers are 4-param; my 3rd probe bug disclosed. |
| `FAMILY-B-reclassified-budget-not-rule.md` | Family B = `STEP_LIMIT` at Wall A hotspot (emitter L24), not a 2nd rule; count_between counter-example = stale message. |
| `CORRECTION-str-fields-work-list-is-the-blocker.md` | **Str record fields EMIT** (my round-31 attribution wrong); List = single type-layer blocker; refusal message proven mislabel; message-text inference banned as method. |
| `CENSUS-verified-1of4-3of9.md` | Census both halves exact: **1/4 types, 3/9 functions** (classifiers); constructors 16/8/11 params confirm four-param rationale. |
| `HANDOFF-verify-listfield-verified-lexprogress-norepro.md` | Report handoff: list-field 3-row table verified; LexProgress mystery natural-form non-reproduction. |
| `RULE-9x9-confirmed-plus-parse-mislabel.md` | Local-binding rule 9/9 confirmed; my 2 R6 probe bugs disclosed (`>` not in seed — Keeper); parse-failure → revision-message mislabel (3rd instance). |
| `CORROBORATE-var-callee-2x2-1b59613.md` | Report's var-in-callee 2×2 reproduced 4/4 with verbatim misreported diagnostic. |
| `CROSSVERIFY-272-and-lean-2443474.md` | 272 baselines match report module-by-module (double-sourced); Lean re-confirmed 3rd time; collections 213-fail consistent. |
| `BASELINE-272-tests-46bf1c0.md` | Full 15-module baseline at `46bf1c0`: **272 / 3 known / 0 new** (reconciles with 262 at `eb8f7c0`). |
| `COLLECTIONS-213-reproduced-coverage-gap-closed.md` | A2-only 129-test collections module run first time: **213 failures / 182 STEP_LIMIT / 31 remainder** — report headlines exact. |

## Bootstrap-era rounds (prior mission, kept for provenance)

`V0-evidence-ledger.md`, `CONSOLIDATION-20261029.md`,
`PEER-REVIEW-ROUND2.md` … `ROUND6.md`, `A2-emitter-rerun-52f1b38.md`,
`B0-CURRENCY-NOTE.md`, `B0-closure-agent1-95ab6c6-READONLY.json`.

## Current blocker map (as of late 2026-10-30, pins A1 `eda6a0f` / A2 `26be4be`)

1. ~~Bundle typecheck~~ — **resolved** (both lines).
2. ~~Validation adapter (blocker 2)~~ — **resolved**, recipe landed and verified.
3. **A1 `ae91bdc` regression — depth axis RESOLVED, step axis OPEN.** `eda6a0f` arm-hoisting (direction #1) recovered heavy **26 → 4** (deep 22 → 0 — `RECOVERY` receipt). Remaining 4 = a14 set: `source_backed`+`depth` (step-axis residue on the shared all-in-one budget) + 2 long-known stale expectations → the Wall B track. Mechanism/bisect/REGRESSION receipts above.
4. **Wall A — classifier/`ascii_continue` staged emit cost: OPEN.** Hotspot `pep_c23_child` L25; fix = bucket-index; A2 parked at `26be4be` (test-only since).
5. **Wall B — a14 all-in-one countdown contract decision: OPEN** — now with named mechanism (match-chain overhead adds to shared spend); owner/builder call (stage budgets or a14 → `emit_c23_checked`).
6. Builder test files: a14 stale-expectation pair + recursion-contract decision (evidence both ways) + arena CRLF (#22 owner item).
7. **List-field emitter gap** — report blocker #1, verified: bounded implementation task; when it lands the type layer unblocks in one step (`Str` works — see CORRECTION receipt).
8. **Watch: design reference corpus** — trigger: past acceptance steps 1–3 → step-4 four-way comparison becomes Agent 3 work (pinned-differential methodology).

**Corpus:** `verification/adversarial/` — 24 case files, replay
**172/172 PASS** at base `805062b` (exit 0; +7 operator-inventory, +1 breadth-budget, +1 root-unavailable probes; grant-identity tightened to exact codes). **Lean:** `MODEL_PROVED`.
