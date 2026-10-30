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

## Pinned differential rounds (peer-claim verification)

| receipt | covers |
|---|---|
| `PINNED-ROUND-20261030-b27b247-77aa6b9.md` | 97/97 + merge recipe 9/9 + UBSan spot-check (clang-only; gcc libubsan missing — Keeper gotcha). |
| `PINNED-ROUND-20261030-eb8f7c0-784050c.md` | Recipe change after emitter move; first 15-module baseline: **262 tests / 3 known failures**. |
| `PINNED-ROUND-20261030-f7efa23-7bfb819.md` | A1 claim 109/109 + skipped native arm; SourceBytes seam verified (combined 14/14). |

## Bootstrap-era rounds (prior mission, kept for provenance)

`V0-evidence-ledger.md`, `CONSOLIDATION-20261029.md`,
`PEER-REVIEW-ROUND2.md` … `ROUND6.md`, `A2-emitter-rerun-52f1b38.md`,
`B0-CURRENCY-NOTE.md`, `B0-closure-agent1-95ab6c6-READONLY.json`.

## Current blocker map (as of 2026-10-30, pins A1 `46bf1c0` / A2 `26be4be`)

1. ~~Bundle typecheck~~ — **resolved** (both lines).
2. ~~Validation adapter (blocker 2)~~ — **resolved**, recipe landed and verified.
3. **Wall A — classifier/`ascii_continue` staged emit cost: OPEN.** Hotspot pinned (`pep_c23_child` L25); fix = bucket-index; awaiting A2 emitter cost work (test-only since `26be4be`).
4. **Wall B — a14 all-in-one countdown: OPEN** (combined a14 = 4). Contract-change decision (stage budgets or a14 → `emit_c23_checked`) awaited; cost cuts only move its boundary.
5. a14 stale-expectation test updates + recursion-contract decision — builder's file, evidence delivered both ways.

**Corpus:** `verification/adversarial/` — 24 case files, replay
**163/163 PASS** at base `805062b` (exit 0). **Lean:** `MODEL_PROVED`.
