# K-A3-4 / K-A3-5: union+match reaches a CAPABILITY wall before the budget; three-slice review

**Date:** 2026-11-05 · **Mission:** LUCY-20261105-001 / Campaign K, A3 card K5 · **Evidence label:** `TESTED`
**PIN: A3 | `codex/bootstrap-agent3-verification` | A1 `727f8af` | clean**
**First next action:** K4 is event-driven (no Candidate7 published → SKIP); next independent card is K6.

## K5 result — a different shape fails for a different reason

Rungs grow a tagged union and its `match` arm count; every rung is **seed-valid** (`pep.ps1 check`).

| arms | bytes | seed | first refusal |
|---|---|---|---|
| 2 | 170 | valid | **EMITTER — capability**: `Pep C23 name lowering requires a direct immutable local let or scalar parameter` |
| 3 | 199 | valid | same emitter capability message |
| 4 | 228 | valid | same emitter capability message |
| 6 | 286 | valid | **CHECKER** `PEP_RUNTIME_STEP_LIMIT` @4157:8 |
| 8 | 344 | valid | **CHECKER** `PEP_RUNTIME_STEP_LIMIT` @2430:30 |

What this adds to the cost picture:

- **On this shape the ceiling is not the first wall.** A union-payload binding (`V0(n) => n + 0`) is simply not lowerable by the current emitter, at 170 bytes — far below the ~408-byte Str-helper budget cliff measured earlier. Stage attribution matters: reporting "budget" here would be wrong for the small rungs.
- **Both limits are real and the visible one depends on size.** Past 6 arms the checker budget refuses *before* the emitter can report the capability gap. So for union/match work the ordering is: capability → budget as the shape grows.
- **Bytes are not cost** (confirmed again): 170 B fails while a 408 B guard-chain program emits and runs.
- Minimal positive below each wall: arms 2–4 emit-refuse with a *specific, actionable* diagnostic; arms 6–8 are budget-refused. A builder fix for union-payload names would move the first refusal back to the budget, not to "working".

Toolchain: OCaml 5.5.2 seed via `pep.ps1`; pipeline = A1 `727f8af` bundle (`pep_c23.emit`, which includes A1's own emitter copy, not A2's prototypes build). Probe: `verification/probes/union_match_ladder_k5.py`.

Limits: one shape family, five rungs, one seed. No claim that the same ordering holds for record/list shapes. `NOT VERIFIED`: whether A2's `123d8b3` emitter (prototypes build) changes the small-rung capability message — it was not in this bundle.

## Three-slice review (K1, K2, K3) — CONTINUE

| slice | SHA | result | independent? |
|---|---|---|---|
| K1 stamp schema | `670395d` | 9 claims, 8 held, 1 falsified (same-target forgery admitted) | TESTED by me at A1 `727f8af` |
| K2 forged → native | `e77c788` | 7 claims, 7 held; Clang **and** GCC refuse the assembled C | TESTED; closes a Campaign-H INFERRED |
| K3 + K7 A2 prototypes | `1f39285` | A2 claim verified; A1 `727f8af` re-pin needs two fields; cold-clone gap persists | TESTED in a fresh disposable clone |

**Workflow cost, first hand:** cold clone + seed rebuild ≈ 4 min; each `pep_c23.emit` on checker-sized input ≈ 10–20 s; the union ladder (5 rungs × check+emit) ≈ 4 min. The dominant cost again was harness plumbing, not measurement: two probe iterations were lost to (a) analysing a whole program so the forged fact collided with the local declaration (duplicate rule fired), and (b) A2's probe crashing on a hand-built dict missing the new stamp fields. Both are now documented so the next session does not repay them.

**One reversible improvement made, not proposed:** every new probe prints the claim table with `HELD`/`FALSIFIED` and a non-zero exit on falsification, so a reader can see which single claim failed rather than re-deriving it from prose.

**Signal v0.1 used for two consequential handoffs** (K1 → A1, K3 → A2), both with `git cat-file -t` + `ls-remote` proof in the claim. Observation for K8: the five-line block fits a *finding* well and a *decision* poorly — the C1/duplicate nuance and the "containment is layering, not design" point both needed prose that the block cannot carry. Net: keep the block as the pointer, keep prose for consequence.

## What is genuinely blocked

- **K4 (Candidate7 acceptance):** no Candidate7 exists. `codex/checker-emitter-integration` is still `46b6712` (Candidate6, immutable, Full-v2 FAIL 14/15). Per the card: SKIP, and **do not** re-run Candidate6.
- Everything else on my queue is independent and remains open (K5 done above; K6 probe corrections available).
