# No-regression check on A1's host repairs — checker/contract lane clean; two frozen probes cannot run on a checker-only branch (base difference, not a regression)

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slice 5: "report any regression introduced elsewhere by the repair") · **Evidence label:** `TESTED`
**Pin under test:** `codex/p1-checker-cost-fix` @ **`ba4b057`** (IDX3 + STALE1 host repairs, S2 slices) — compares against integration candidate `8396b63`.
**Instruments:** existing probes, run **unchanged**: `hostile_chunk_forged_facts.py`, `chunk_diagnostic_preservation.py`, `prereq_closure_attacks.py`, `declaration_emittability_agreement.py`. No builder file, bat, runner or expectation touched.

## Result

| probe | `ba4b057` | `8396b63` | reading |
|---|---|---|---|
| `hostile_chunk_forged_facts` (checker/contract lane) | **`SUMMARY cases=14 claim_falsified=0`** | (baseline: refused 12/12 + 2 documented edges) | **no regression** |
| `chunk_diagnostic_preservation` (checker lane) | `cases=6 claim_falsified=1` — CD3 only | **identical** (`cases=6 claim_falsified=1`, CD3 only) | **no regression**; CD1/CD2 still hold, CD3 still the single open claim |
| `prereq_closure_attacks` (needs bounded emitter) | `HARNESS_ERROR` — `PEP_TOOL_FUNCTION_NOT_FOUND` on `pep-c23-bounded-unit` | `cases=8 claim_falsified=0` | **cannot run on this branch** (see below) |
| `declaration_emittability_agreement` (needs bounded emitter) | `HARNESS_ERROR` — same code | `cases=4 claim_falsified=0` | **cannot run on this branch** (see below) |

So the host repairs did not disturb the malformed/forged-fact refusals or cross-chunk diagnostic
preservation, and CD3's status is byte-identical to the baseline.

## The two `HARNESS_ERROR`s are a base difference, not a regression — checked before reporting

The registration failure is `PEP_TOOL_FUNCTION_NOT_FOUND`: "No checked function with this name exists
at the registered revision", for the function `emit_c23_function_unit_bounded`. A source search in both
trees settles it:

```
D:\Projects\wt-a3-a1-ba4b057  -> (not present)
D:\Projects\wt-a3-int-8396b63 -> pep_c23_emitter.pep
```

That function is part of A2's bounded emitter (`e0e49e5`) which the integration candidate carries and
A1's checker-only fix branch does not. The probes therefore cannot run there for a reason unrelated to
the STALE1 repair. **I initially suspected the new crossed-revision refusal might be rejecting a
legitimate registration; that hypothesis is falsified** — the refusal names a missing *checked
function*, not a revision mismatch, and the function is genuinely absent from that tree.

This is the reason the frozen Full must run on the **combined** tree (both lines plus the A1 fix), and
it is a concrete, measured reason — not a policy preference: two of the seven frozen probe gates
(`prereq_closure_attacks`, `declaration_emittability_agreement`) are unexecutable without the emitter.

## Honest scope

- Four probes, two pins; the four emitter-independent checks are the ones that speak to the repair.
- `hostile_chunk_forged_facts` at `8396b63` was not re-run in this pass; its baseline is the recorded
  `receipt:sha256:607656e6…` from the earlier round (12/12 documented edges refused, verdict `NOT OBSERVED`).
- No frozen gate executed; no acceptance claim made.

## Reproduce

```powershell
python verification\probes\hostile_chunk_forged_facts.py        D:\Projects\wt-a3-a1-ba4b057   # exit 0, 14 cases
python verification\probes\chunk_diagnostic_preservation.py     D:\Projects\wt-a3-a1-ba4b057   # exit 1 (CD3 only)
python verification\probes\prereq_closure_attacks.py            D:\Projects\wt-a3-a1-ba4b057   # exit 2 (function absent)
python verification\probes\declaration_emittability_agreement.py D:\Projects\wt-a3-a1-ba4b057  # exit 2 (function absent)
Get-ChildItem -Path <worktree> -Recurse -Include *.pep | Select-String 'fn emit_c23_function_unit_bounded'
```
