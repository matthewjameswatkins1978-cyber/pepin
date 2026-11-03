# Cost profile by source shape — the 100k budget buys 36–104 checker nodes and ~90–120 driver tokens, depending on shape

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slices 4/6: turn one ceiling into a cost profile the roadmap can act on) · **Evidence label:** `TESTED`
**Measured in:** the scratch measurement tree `84062064` (`0c5f12b` + `cf02095`, both lanes, **no emitter**), local only — never pushed, no branch, removed after measuring. Not an integration candidate; `codex/checker-emitter-integration` remains `8396b63`.
**Instrument:** `verification/probes/budget_cost_profile.py` (new)

## Profile — 100,000 steps per stage, six source shapes

| shape (generator) | driver: last ok | driver: first refusal | checker: last ok | checker: first refusal |
|---|---|---|---|---|
| `lets` (`let aN = N;`) | **101 tokens** (260 B) | 316 B | **64 nodes** (428 B) | 540 B |
| `bool_chains` (`x == a && x == b \|\| …`) | **119 tokens** (322 B) | 615 B | **44 nodes** (176 B) | 322 B |
| `records` (`type RN { a: Int b: Int }`) | 91 tokens (310 B) | 452 B | **104 nodes** (740 B) | 884 B |
| `functions` (`fn fN() -> Int { return N }`) | 91 tokens (262 B) | 382 B | **52 nodes** (382 B) | 506 B |
| `match_arms` (union with n arms) | 117 tokens (387 B) | 539 B | **36 nodes** (239 B) | 387 B |
| `strings` (`say("sN")`) | 113 tokens (298 B) | 342 B | **72 nodes** (254 B) | 298 B |

Every refusal is `PEP_RUNTIME_STEP_LIMIT` on a source the seed accepts as valid (`O1`).

## Three claims, all held (`SUMMARY claims=4 claim_falsified=0`)

- **S1 — every shape is bounded.** No shape family is free: the best case (records) reaches 884 B, the worst (match arms, bool chains) under 400 B.
- **S2 — the driver's cost is per token, not per shape.** Ceilings 91–119 tokens, **spread 1.31×**. That is a genuinely useful engineering fact: the driver's cost model is uniform, so its ceiling can be predicted from token count alone.
- **S3 — the checker's cost is shape-dependent.** 36–104 nodes, **ratio 2.89×**. The cheapest shape (record declarations, 104 nodes) buys ~3× the units of the most expensive (match arms, 36 nodes).

## What this adds beyond the single ceiling

1. **The 66-node regression fixture is past its shape's ceiling, not merely near one.** `bool_chains` — the family the fixture belongs to — tops out at **44 nodes** (176 B) in this generator. The frozen row sits at **66 nodes** and fails at `2454:8`. So the row is not "a fixture we happen not to have fixed yet"; on this evidence it is a program in a shape family whose measured budget is roughly two-thirds of its size.
2. **The most expensive shapes are the expression- and arm-heavy ones** (match arms 36, bool chains 44, functions 52), which is exactly where A1's S2 expression-facts work aims. That makes the target measurable: moving match-arm or boolean-chain cost per node is worth ~2–3× more than the same effort on record declarations.
3. **A third stage shares the wall.** The Pep-written **parser** refuses at **18 match arms** (`PEP_RUNTIME_STEP_LIMIT`; 16 arms / 108 nodes still parse). So parser, checker and lexer driver all exhaust the same fixed budget at comparable unit counts — the profile is not a checker-specific story.
4. **A second, different limit appears**: `bool_chains` at 804 nodes hits **`PEP_TOOL_VALUE_LIMIT`**, not the step budget — a transport/value-size ceiling that becomes reachable before the step budget on node-dense sources. Recorded so a future failure at that scale is not misattributed.

## Honest scope

- Six hand-written generators. The absolute numbers are artefacts of those shapes; the *ordering* (match arms/booleans expensive, records cheap) and the order of magnitude are the claims.
- Steps/unit are upper bounds from "largest success ≤ 100k", not instrumented step counts; the driver's `spread` figure is a ratio of unit counts, not of measured steps.
- The scratch tree has no emitter, so emission is out of scope here.
- `match_arms` rungs ≥ 18 arms fail in the **collector's** parse step with the parser's own refusal; I recorded the code (`PEP_RUNTIME_STEP_LIMIT`) rather than reporting a harness error, and the earlier truncated state text was repaired for that reason.
- No frozen gate executed; not acceptance evidence.

## Reproduce

```powershell
python verification\probes\budget_cost_profile.py <scratch-tree-with-both-lanes>   # exit 0
```
