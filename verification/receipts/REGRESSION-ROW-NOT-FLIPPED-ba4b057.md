# A1's "flip 66n regression" claim does not reproduce — the frozen discriminating row still fails at `ba4b057`, and the S2 slices move it zero steps

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slices 2 and 5: challenge a builder claim and distinguish a real fix from a stale one) · **Evidence label:** `TESTED`
**Instrument:** `verification/probes/regression_row_recheck.py` (new) — runs only the two stages that decide the frozen row (Pep-written parser, then Pep-written checker) using the frozen probe's `REGRESSION_FIXTURE` text **verbatim**, copied from `tests/probe_integration_case.py` at `8396b63`. No frozen gate was executed and no builder file was touched.

## Measured trajectory of the row (`regression bytes=440 nodes=66`)

| pin | what it is | row result | refusal point |
|---|---|---|---|
| `8396b63` | integration candidate (baseline) | `check=PEP_RUNTIME_STEP_LIMIT` | `Execution step budget exceeded at 2444:3` |
| `abd372c` | A1 head before the S2 slices | `check=PEP_RUNTIME_STEP_LIMIT` | `… at 2454:8` |
| `611616b` | S2 structural slice 1 ("fuse infer/shape in expression-facts pass") | `check=PEP_RUNTIME_STEP_LIMIT` | `… at 2454:8` |
| `94373fb` | S2 structural slice 2 ("fuse infer/shape for record-field values") | `check=PEP_RUNTIME_STEP_LIMIT` | `… at 2454:8` |
| **`ba4b057`** | S2 slices **+** IDX3/STALE1 host repairs (A1's current head) | **`check=PEP_RUNTIME_STEP_LIMIT`** | **`… at 2454:8`** |

Two conclusions, both measured rather than inferred:

1. **The row is not flipped at any pin on A1's line, including the head of the branch.** The commit
   `e36e67d` is titled "node-passing infer_at for hot paths (flip 66n regression)"; independent
   measurement at `abd372c` — the very next commit — shows the row still refused. A1's own later #16
   comment already reported "66n STILL fails (moved 2444→4870 only)", so this is not a contradiction
   I am manufacturing: the *commit message* is stale relative to the branch it lives on, and an
   integrator reading titles could integrate `ba4b057` expecting the discriminating-rows gate to pass.
2. **The S2 structural slices move this row by exactly zero steps** (`2454:8` identical at `abd372c`,
   `611616b`, `94373fb`, `ba4b057`). The 10-step difference against `8396b63` exists *before* the S2
   work and belongs to the branch-base difference (integration line = `05add76` + P1 + emitter merge),
   not to progress. Whatever the slices improve elsewhere, they do not touch this row.

## Consequence for integration

If A1 integrates `ba4b057` (or anything derived from it) unchanged, the unchanged frozen Full will
still stop at **`first_fail: discriminating rows`**, with `regression` = `PEP_RUNTIME_STEP_LIMIT` — the
same gate and the same stage as the `8396b63` verdict. Gate 15's `PROVEN=0` requirement is separately
blocked by the frozen-probe finding (`FINDING-frozen-probe-false-negative-ba4b057.md`), so both halves
of the next acceptance run are currently unachievable; the budget half is A1's to move, the instrument
half is Matthew's to rule on.

## Non-vacuity / controls

- The fixture text is copied verbatim and byte-counted (`bytes=440`, `nodes=66`) so a silently edited
  fixture cannot be mistaken for a changed result; the node count matches the frozen row's own
  reporting from the `8396b63` receipt (`regression` row, 66 nodes).
- The instrument exits `0` only on `check=valid`, prints the refusal message with its step position,
  and exits `2` on harness failure — a broken harness cannot read as "not flipped".
- Both stages are the same tool invocations the frozen probe's `run_case` performs
  (`pep-c23-parser-start/step`, `pep-c23-checker`), so the row measures the same work.

## Honest scope

- Two stages only: no emitter, no native build, no pack, no frozen Full. `check=valid` here would be
  necessary but not sufficient for the frozen gate.
- Five pins, one run each; no bisection between `8396b63`'s base and `abd372c` (the 2444→2454 shift is
  attributed to branch base by inspection of the branch geometry, not by bisection).
- A1's own S2-minimal experiment (reverted, reported on #16 as "moved 2444→4870") is a *different*
  number from my 2454 → the two attempts are not the same code; I make no claim about it.

## Reproduce

```powershell
python verification\probes\regression_row_recheck.py D:\Projects\wt-a3-int-8396b63   # 2444:3, exit 1
python verification\probes\regression_row_recheck.py D:\Projects\wt-a1-fix           # 2454:8, exit 1  (abd372c)
python verification\probes\regression_row_recheck.py D:\Projects\wt-a3-a1-611616b    # 2454:8, exit 1
python verification\probes\regression_row_recheck.py D:\Projects\wt-a3-a1-94373fb    # 2454:8, exit 1
python verification\probes\regression_row_recheck.py D:\Projects\wt-a3-a1-ba4b057    # 2454:8, exit 1
```
