# K-A3-7: A1's new step accounting — the counter is real, and it cannot see the capability class

**Date:** 2026-11-05 · **Mission:** LUCY-20261105-001 / Campaign K (follow-on: A1 advanced to `3ff3bf1`) · **Evidence label:** `TESTED`
**PIN: A3 | `codex/bootstrap-agent3-verification` | tested A1 `3ff3bf1` (detached `D:/Projects/wt-a3-a1-3ff3bf1`) | clean**
**Why this slice:** A1 shipped `3ff3bf1` "read-only step accounting + measured per-phase checker cost" — the instrument three campaigns said was missing. The independent job is not to repeat A1's numbers but to ask whether my own earlier attributions survive it, and whether the counter is real.

## Result: 3 claims, 3 held (after two of my expectations were corrected)

| rung | bytes | outcome | code | last_execute_steps |
|---|---|---|---|---|
| S1 Str 1 guard | 342 | host-side refusal | — | none |
| S2 Str 2 guards | 408 | host-side refusal | — | none |
| S3 Str 3 guards | 720 | CHECKER | `PEP_RUNTIME_STEP_LIMIT` | **100001** |
| S5 Str 5 guards | 848 | CHECKER | `PEP_RUNTIME_STEP_LIMIT` | **100001** |
| U2 union 2 arms | 170 | host-side refusal | — | none |
| U4 union 4 arms | 228 | host-side refusal | — | none |
| U6 union 6 arms | 286 | CHECKER | `PEP_RUNTIME_STEP_LIMIT` | **100001** |
| U8 union 8 arms | 344 | CHECKER | `PEP_RUNTIME_STEP_LIMIT` | **100001** |

- **C1 HELD — the counter is real.** Every budget refusal reports exactly `100001` (one past the 100 000 limit, consistent with tick-then-check). It is not a constant stub and not a rounded report.
- **C0 HELD (revised) — the metric appears on tool-invocation failures only.** 4 of 8 rows carry `last_execute_steps`; the other 4 are **host-side pre-emission** refusals raised as Python `ValueError` inside `pep_c23.emit`, before any tool `execute` runs.
- **C2 HELD (revised) — non-budget refusals consume no counted execute at all**, so per-phase accounting cannot attribute them. My first draft claimed "every non-budget refusal reports steps below 50% of the limit"; that was untestable and is recorded as a corrected expectation, not a passing test.

## Two corrections to my own earlier reporting

1. **My K5 stage label was imprecise.** I reported the union small-rung failure as an "EMITTER capability" refusal. On `3ff3bf1` it is a **host-side pre-emission gate** (`ValueError: Pep C23 name lowering requires a direct immutable local let or scalar parameter`) that fires before the emitter tool executes. The *finding* (capability, not budget) stands; the *layer* is the host driver, not the emitter tool.
2. **"The emitter" differs across trees, and my H-V4 numbers belong to A2's bundle.** On A1's bundled emitter, a Str-result function is refused at 342–408 B with `Pep C23 functions require supported parameters and scalar or record results`. On A2's emitter (H-V4, `58fc9bf` tree) the *same 408-byte program* emitted 6206 B and ran natively. Not a regression — a bundle difference — but it matters for composition: if a candidate bundles A1's emitter copy instead of A2's, Str-result support disappears.

## Why this is actionable for A1 (K2 instrumentation)

- The new counter is trustworthy where it fires, and it *does* settle the budget class exactly.
- **It is blind to the whole capability class**, which is where a large share of refusals actually live (4 of 8 rungs here; the small-rung union work in K5; the Str-result gate). Counting steps cannot distinguish "too expensive" from "never started" — and the second is what most small real programs hit.
- Cheap closure if A1 wants it: the host driver already knows it refused; a one-field `refusal_layer` ("host" | "checker-tool" | "emitter-tool") on the failure envelope would let a verifier attribute without re-deriving from message text. I am not asking for it — the current message text was enough for this receipt.

## Reproduce

```powershell
python -X utf8 verification\probes\cost_accounting_k7.py D:\Projects\wt-a3-a1-3ff3bf1
# 8 rungs, 3 claims, all held; rows printed with steps and execute# counters
```

Toolchain: OCaml 5.5.2 seed built from the worktree's own `pep_ocaml.ml` (the accounting revision). Peer worktree read-only; only its ignored `_build/a3-k7` was written.

## Limits

- Eight rungs, two fixture families, one tree. No claim about how steps distribute *within* an execute (the counter is per-execute, not per-phase, despite the "per-phase" framing in the commit subject — the phase split A1 reports comes from their probe's sequencing, not from a per-phase counter).
- `S1/S2` host-side refusals here reflect A1's bundled emitter gate, not A2's; do not read them as a capability regression.
- I did not re-run A1's own `tests/probe_checker_phase_cost.py`; this is independent measurement, not a review of their harness.

## Signal v0.1 handoff to A1

```text
PIN: A3 | codex/bootstrap-agent3-verification | 33494b1 (+this commit) | pushed+remote-verified | clean
RESULT: your step counter verified real (100001 at every STEP_LIMIT refusal) but it is per-execute and blind to host-side pre-emission refusals (4/8 rungs). TESTED.
REPRO: python verification\probes\cost_accounting_k7.py D:\Projects\wt-a3-a1-3ff3bf1
FALSIFIER: any STEP_LIMIT refusal reporting steps well below 100000 would disprove the counter; none observed.
NEEDS: A1 — if you want attribution for the capability class, expose a refusal_layer field; note also that your bundled emitter copy refuses Str-result functions that A2's emits, which matters when composing Candidate7.
```
