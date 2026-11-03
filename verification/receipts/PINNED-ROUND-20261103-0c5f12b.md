# Pinned round at A1 `0c5f12b` — CD3 closed, gate-15 pack reaches `NOT OBSERVED=3 / PROVEN=0`; the 66-node row is now the sole known red gate

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slices 2/5: recheck repairs, no-regression, and pre-integration readiness) · **Evidence label:** `TESTED`
**Pin:** `codex/p1-checker-cost-fix` @ **`0c5f12b92ffe78297171337b467c714d949f9b9b`** ("checker-certified external type facts producer (slice 4a)"), pinned detached worktree `D:\Projects\wt-a3-a1-0c5f12b`, clean, untouched.
**Baseline in force:** acceptance baseline **v2** (runner `b464e00e`, probe `688042d7`); v1 preserved in `verification/acceptance/v1/`.
**Important:** this is **not** an acceptance run. There is no integrated successor of `8396b63`, so the frozen Full was **not** executed and no pass is claimed.

## 1. CD3 is closed — verified twice, independently

A1's `844c8b0` ("str_concat builtin closes CD3 diagnostic-message parity") holds up:

| instrument | result |
|---|---|
| frozen probe `chunk_diagnostic_preservation.py` (unchanged) | **`SUMMARY cases=6 claim_falsified=0`** — VAC, CD1 (no loss), CD2 (no extras), **CD3 (message parity)** all held |
| my independent minimal repro (`repro_host_defects.py CD3`, one fixture) | **`[CD3] HELD`** — whole-source and chunked messages now identical for the same `(code, span)` |

So the owner chose *align*, not *declare out of scope*: the chunked wording now matches the seed
("Unknown type 'Nope'" where it previously read "Record field type is outside the implemented checker
subset"). That is the stronger of the two closes I offered, and it retires the open question I
escalated on #16.

## 2. Gate 15's pack reaches its target state at this pin

Unchanged pack, run standalone on the A1 tree (gate-15 instrument only; not the Full procedure):

```
terrorbats pack run verification\bats\agent3-index-gates.yaml --repo <0c5f12b> --json
  summary: NOT OBSERVED=3  PROVEN=0  INCONCLUSIVE=0
  child receipts: 95f4275f…, 1d0f68db…, ac225a7b…
```

All three children — `index-cache-claims` (IDX3/STALE1), `chunk-diagnostic-claims` (CD3), and the
unchanged P1 `regression-hole-guard-passes` — are **NOT OBSERVED**. Under baseline v2 the first child
is measurable (at v1 it could not be, see `FINDING-frozen-probe-false-negative-ba4b057.md`), and all
three are now genuinely green.

## 3. No regression from the slice-4a checker work

| probe (unchanged) | `0c5f12b` |
|---|---|
| `index_cache_adversarial.py` | `cases=9 claim_falsified=0` |
| `edge_identity_boundary.py` (over-refusal guard) | `cases=7 claim_falsified=0` — all parseable examples still build an index |
| `hostile_chunk_forged_facts.py` | `cases=14 claim_falsified=0` |

## 4. The remaining red gate is the 66-node row, and it has not moved

```
regression_row_recheck.py <0c5f12b>
  checker_refusal_code=PEP_RUNTIME_STEP_LIMIT message=Execution step budget exceeded at 2454:8
  regression bytes=440 nodes=66 check=PEP_RUNTIME_STEP_LIMIT
```

Identical to `abd372c`, `611616b`, `94373fb` and `ba4b057` (`2454:8`). The slice-4a type-facts
producer changes nothing on this row either.

**Projected state of the next combined candidate** (evidence-based, to be measured when it exists):
gate 15 satisfiable (`NOT OBSERVED=3 / PROVEN=0` demonstrated here on the A1 tree, must be re-measured
after the emitter merge), gates 1–4 and 6–14 green as at `8396b63` unless the merge disturbs them,
and **gate 5 red on the 66-node row** unless it flips. So integration readiness now reduces to one
measurable question, which is exactly the question LUCY-20261103-004 routed to A1.

## Honest scope

- The pack run is the gate-15 instrument, not the acceptance procedure; no Full-mode gate was executed
  and no candidate was accepted.
- CD3 verification is message-text equality for the three single-error fixtures plus one minimal
  fixture; it does not claim parity for every diagnostic message in the checker.
- The 66-node number is one row; other composition walls remain as recorded
  (`COMPOSITION-STRESS-ba4b057-8396b63.md`).
- A2's driver (`cf02095`) is not measured here; it is the next slice.

## Reproduce

```powershell
cd D:\Projects\wt-a3-a1-0c5f12b
python ..\..\pepin\_build\bootstrap-agent3-verification\verification\probes\chunk_diagnostic_preservation.py .
python ..\..\pepin\_build\bootstrap-agent3-verification\verification\probes\regression_row_recheck.py .
terrorbats pack run <verifyRoot>\verification\bats\agent3-index-gates.yaml --repo . --json
```
