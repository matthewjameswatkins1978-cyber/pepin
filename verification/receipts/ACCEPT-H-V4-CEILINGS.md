# H-V4: a valid program becomes unexecutable after ~1–8 extra declarations — Str result costs the most

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-015 / Campaign H, Workstream V4 · **Evidence label:** `TESTED`
**PIN:** A3 `codex/bootstrap-agent3-verification@226bb22` (+this commit) · clean · tested A2 `58fc9bf` tree, A1 `2ad750b` seed
**Boundary is NOT the frozen 66-node fixture.** Every rung below is `seed`-valid, so no refusal can be blamed on source invalidity, and no budget, cap, fixture or frozen instrument was changed.

## Ladder 1 — the REAL two-guard `lex_error_code` prefix + N trivial fillers

Filler = `fn filler_N(v: Int) -> Int { return v + N }` (valid, unused). Source sha256 of the prefix: `0c9888aae4a1fe8aa722550255561a40b5ef5188503cd53a638d554a4b7d987f`.

| fillers | bytes | seed | pipeline |
|---|---|---|---|
| 0 | 408 | valid | **OK**, emits 6206 B, native `PEP_INT_LITERAL_RANGE` |
| **1** | **454** | valid | **REFUSED checker `PEP_RUNTIME_STEP_LIMIT`** @3525:21 |
| 2 | 500 | valid | REFUSED checker @2441:37 |
| 3 | 546 | valid | REFUSED checker @2451:8 |
| 4–6, 10, 15, 20, 25, 30, 40, 50 | 592–2788 | valid | REFUSED checker (positions vary: 2512:23, 2441:26, 3633:9, 2450:3 …) |

**One extra three-line function is enough.** The first failing stage is always the **checker tool invocation** (`check parsed source`), code `PEP_RUNTIME_STEP_LIMIT`; never the parser, never the emitter, never the C compiler, never host transport.

## Ladder 2 — controls that isolate the cause

| shape | 0 fillers | 1 | 3 | 8 |
|---|---|---|---|---|
| **S0** Str guard-chain helper | OK 408 B | **REFUSED 454 B** | REFUSED 546 B | REFUSED 776 B |
| **S1** Int guard-chain helper (same guard shape) | OK 179 B | OK 225 B | OK 317 B | **REFUSED 547 B** |
| **S2** `main` only (no helper) | OK 33 B | OK 79 B | OK 171 B | **REFUSED 401 B** |

Reading the three rows together:

1. **It is not byte count.** S2 at 401 B is refused while S0 at 408 B is accepted, and S1 at 547 B is refused while S0 at 454 B is refused but S1 at 317 B is fine. Cost is per-declaration and shape-dependent.
2. **A `Str`-returning guard chain is the expensive item.** With identical guard structure, `Str` result costs enough that the *very next* declaration crosses the ceiling, while the `Int` version absorbs three extra declarations before failing.
3. **Even a bare program with no helper functions** crosses the ceiling at ~9 declarations (main + 8 fillers, 401 B source).

## Guard-count ladder (from V2, same pin, kept here for the same conclusion)

Prefix rungs of the real five-guard function, record-field arguments as at `scan.pep:845`:

| guards | Str result | Int result |
|---|---|---|
| 1 | emitted, native OK | — |
| 2 | emitted, native `PEP_INT_LITERAL_RANGE` | emitted, exit 2 |
| 3 | **REFUSED** (emitter @5471:5) | emitted, exit 2 |
| 5 | **REFUSED** (checker @2451:8) | **REFUSED** (checker @2933:32) |

**Minimum positive below the boundary and a valid input above it:** rung 2 (emitted, runs, matches seed) vs rung 3 (refused, seed still valid). Nesting is not the trigger — a flat five-guard `Str` variant is refused at the same `2451:8`, and a nested three-guard variant with one inner guard is refused too.

## Why this is actionable for A1 (Q1 instrumentation)

- The frozen gate's 66-node row is one symptom; this is a **second, independent, much tighter boundary on ordinary valid source**: ~400–550 bytes of Pep with 2–9 declarations. Any real bootstrap unit (the checker alone is 188 KB) is orders of magnitude beyond it, so this is not a corner case — it is the wall the self-hosting path hits next.
- The **Str result is measurably more expensive than the Int result** on identical control flow. If per-phase step accounting becomes available, the first question worth asking is where a `Str`-returning guard chain spends its steps relative to the `Int` twin.
- Positions reported (`2451:8`, `3525:21`, `3633:9`, …) move with shape and are step-counter loci, not source lines. They are recorded verbatim for A1 rather than interpreted.

## Admitted unknowns / limits

- Ladder 1's rungs above 6 fillers reuse the same shape, so they add nothing beyond "still refused"; kept to show it never recovers.
- Growth is by **declaration count**, not by the frozen fixture's node count — deliberately a different shape from the 62/64 ladder, which is A1's lane and was not replayed.
- Checker vs emitter vs parser attribution is by the pipeline's own stage message (`check parsed source` / `emit checked source`); per-phase step counts are not exposed to A3.
- No budget/cap/fixture/manifest/runner change by A3; `verification/**` only.

## Reproduce

```powershell
python -X utf8 verification\probes\size_ladder.py    D:\Projects\wt-a3-h1-cold
python -X utf8 verification\probes\size_controls.py  D:\Projects\wt-a3-h1-cold
```
