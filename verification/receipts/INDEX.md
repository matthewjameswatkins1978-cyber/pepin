# Verification receipts index (Agent 3)

One-line status per receipt, grouped by thread. Newest first within
groups. **Current blocker map at the bottom.**

## Checked-chunk contract (2026-11-02 — A1 `pep-checked-chunk-v1`)

| receipt | one-line |
|---|---|
| `CHECKED-CHUNK-malformed-scalars-8130276.md` | **8/11 malformed-input claim cases falsified** at A1 `81302766` (7 malformed scalars accepted as `valid`, 1 raw `ValueError` instead of `ContractRefusal`): Terror Bats `receipt:sha256:e2d49d13eec842f71ad3721efe36a7e89b27cf04930802145a4e0f79d4d7da07`, verdict `PROVEN` (claim falsified under recorded conditions; execution `d0702492`). Test commit `45f0ee0` (probe + bat spec). Repro: `terrorbats run verification/bats/checked-chunk-malformed-scalars.yaml --repo <pinned-A1-worktree>`. Owner: Agent 1 — checker contract repair; Agent 3 does not edit builder files. |
| `CHECKED-CHUNK-fix-verified-05add76.md` | **D1/D2 repaired, re-verified** at A1 `05add76`: same bat unchanged → probe exit 0, verdict `NOT OBSERVED` (`receipt:sha256:cd5195b5e38e4d43e0e52e47dc19f7bff59000cf001b3baf4b7a33b939ecd9a8`, exec `0647bb92`); builder's own 42 tests independently rerun OK. |
| `A2-SECTION-c70d5eb-bounded-no-main.md` | A2 bounded-emitter slice verified at `c70d5eb`: builder suite **6 OK / 1 documented skip** rerun; own probe C1–C5 (one-shot guard intact, header/function/unit emit without main) **claim_falsified=0**; reconciliation probe at A1 `05add76` → no-main `valid`, +reconstructed caller `PEP_RUNTIME_STEP_LIMIT 2443:23` (corroborates A2's 2428:3). Native `make_token` compile `NOT_RUN` (integration-gated). |
| `CHUNK-FORGED-FACTS-05add76.md` | Forged-facts campaign at A1 `05add76`: **12/12 documented edges refused** with exact codes (bool `False==0` signatures, cross-document report/envelope, ascending/unique `coveredNodeIds`, plan-time empty/open-parent, type tags, status edges); Terror Bats `receipt:sha256:607656e6c4435e7c9a195b78b7b31afa7b21574b53eb5d0507db95f700fa056a` verdict `NOT OBSERVED` (exec `d54c9d1b`). Additive to A1's 27-case suite. |
| `A1-HEAD-SPOTCHECK-05add76.md` | A1 head spot-check: ledger **4/4**, node-cost **2/2**, budgets+contract+scalar **59/59** rerun green (65 tests total at `05add76` this session); `open_bytes` cap re-pinned — 65,536 `ok` / 65,537 `PEP_SOURCE_BYTE_LIMIT` (`verification/probes/open_bytes_limit.py`, exit 0). |
| `REGRESSION-a1-d158044-hole-guard-step-limit.md` | **CONFIRMED NEW REGRESSION (A1 line):** bisect `6aadc4f..05add76` (53 commits) pins first-bad `d158044` (checker perf, `pep_checker_a13.pep` only); hole-guard native test OK at parent `61f1d33` / FAILED at `d158044..05add76` / OK on A2-own `c70d5eb`; `PEP_RUNTIME_STEP_LIMIT 2514:26` = checker L143 `is_constructor` scan. Terror Bats `receipt:sha256:67661e8d0e7da557dad52126b3d3a14163a81cea286f15fef57469bfa9cf8488` verdict `PROVEN`. Owner: A1. |
| `VOLUME-CORRELATION-real-lexer-05add76.md` | Real-lexer ledger correlation (15 chunks): function outcomes **ordered by node count** (pass@55 / fail@59 → cost/node in **(1694, 1818]**), declaration regime ≤1315/node — volume thesis corroborated **within kind**, but **no universal node ceiling** (76-node decl passes while 59-node fn fails); A1 `node_cost` ~100-node headline understates function bodies. Probe exit 0, `claim_falsified=0`; docstring-currency note to A1. |
| `PINNED-ROUND-20261102-05add76.md` | Full current-head inventory: **503 tests**, failing records 198 all classified — collections **195** (178 `PEP_RUNTIME_STEP_LIMIT` in the all-in-one emit path — deaths **154 checker / 24 emitter**, hot line `lookup_node` L72 → **shared-budget/Wall B family, both walls open**, 17 known refusal-misblame, 0 wrong answers; total matches A2's corrected 195), a14 = documented pair only, str = the reported `d158044` regression. 0 unexplained failures. |

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
| `WALLB-headroom-collapse-ladder.md` | **All-in-one countdown headroom → zero**: pre-series emits countdown(0/6/100), current fails 0..99 (same death point = emitter L499, host budget unchanged); staged path green — migration now the only green route. |
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
