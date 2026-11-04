# G-A3-4: boolean-chain cost ladder — second cost shape, boundary 56→72 nodes, cost-only

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-013 / Campaign G A3 G-A3-4 · **Evidence label:** `TESTED`
**Pin:** `codex/checker-emitter-integration@46b6712` (detached `D:\Projects\wt-a3-c6-46b6712`, clean).
**Instrument (new, this commit):** `verification/probes/boolean_chain_ladder.py` (G0/G1/G2; whole-parse single chunk via `analyze_chunk_typed`, same method as the 66n ladder). JSON artifact `_build/boolladder-46b6712.json` (worktree-local, ignored).
REF: A4 Q1 context (per-phase attribution is A1's to instrument); GH #16 (this session, to be posted).

## Result: 3 claims, 0 falsified — boundary last-ok k=12 (56 nodes) / first-refuse k=16 (72 nodes)

| terms | nodes | seed | staged |
|---|---|---|---|
| 2–12 | 16–56 | valid | valid |
| 16–24 | 72–104 | valid | TOOL-ERROR/PEP_RUNTIME_STEP_LIMIT (checker stage) |
| 30 | — | valid | PARSE-PEP_RUNTIME_STEP_LIMIT (parse stage itself refuses) |

G0 held (k=2 valid); G1 observation recorded; G2 held (every rung seed-valid → all refusals cost-only, never semantic).

## Cross-shape read (INFERRED, for A1 G-A1-4 — not a per-phase attribution)

- Refusal band 56→72 nodes sits against the 66n band 62→64: cost scales with node count ~linearly across two unrelated shapes (boolean chains vs the 66n fixture), no shape-specific cliff. Consistent with A1's ablation verdict (no single phase dominates; distributed per-node cost).
- The refusal STAGE moves with size: checker-stage TOOL-ERROR at 72–104 nodes, parse-stage refusal at 480 bytes/30 terms. Two different stages fail closed under the same budget — the ladder measures staged-checker cost; the parse-stage ceiling is a separate (also fail-closed) bound worth naming in budget attribution.
- Per-phase internals remain unmeasurable from outside (probes see verdicts/codes only) — A4 Q1 TO A1 stands as the only fast settler; this ladder is the second boundary datum for it, not a substitute.

## Reproduce

```powershell
python -X utf8 verification\probes\boolean_chain_ladder.py D:\Projects\wt-a3-c6-46b6712  # 3/3
```

## Limits

Single pin, one shape family, whole-parse single-chunk method (matches the 66n ladder's method; one-shot `analyze_parsed` may differ — stated, not assumed identical). Fixture bug caught during build (unbound variable made rungs seed-invalid; fixed before measuring — first run discarded). No builder files touched; no master/CURRENT/manifest/budget changes.
