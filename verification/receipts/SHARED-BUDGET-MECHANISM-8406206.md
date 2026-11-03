# One obstruction, two symptoms — the A2 driver ceiling (121 tokens) and the A1 checker wall (65–80 nodes) are the same 100k-step budget at ~10³ steps per unit

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slices 4/6: name the obstruction both lanes face, instead of reporting two disconnected symptoms) · **Evidence label:** `TESTED`
**Measured in:** a **scratch measurement tree** containing both lanes — `git merge-tree --write-tree 0c5f12b cf02095` → exit 0, tree `bfe12cd5`, local commit `84062064` (never pushed, no branch, removed after measuring). This tree is a measurement fixture, **not** an integration candidate; `codex/checker-emitter-integration` remains `8396b63`.
**Instrument:** `verification/probes/shared_budget_mechanism.py` (new)

## Method

One source family (`let aN = N;` × n, valid Pep), one fixed tool budget (100,000 steps), both stages
measured on the same tree:

- **driver** — `stdlib/scan.pep` `lex_source` (A2 lane), units = tokens
- **checker** — the Pep-written checker `analyze_parsed` on the parse of the same source (A1 lane), units = AST nodes

## Result

| statements | bytes | driver | tokens | checker | nodes |
|---|---|---|---|---|---|
| 20 | 260 | ok | 101 | ok | 40 |
| **23** | 302 | **ok** | **116** | ok | 46 |
| **24** | 316 | **`PEP_RUNTIME_STEP_LIMIT`** | — | ok | 48 |
| 32 | 428 | `PEP_RUNTIME_STEP_LIMIT` | — | **ok** | **64** |
| 40 | 540 | `PEP_RUNTIME_STEP_LIMIT` | — | **`PEP_RUNTIME_STEP_LIMIT`** | 80 |

- **Driver ceiling: 116 tokens (302 B)** — refuses at 121 tokens (316 B) → **≤862 steps/token**.
- **Checker ceiling: 64 nodes (428 B)** — refuses at 80 nodes (540 B) → **≤1,562 steps/node**.
- Ratio between the two ceilings in units: **1.8×** — same order of magnitude.
- The seed accepts **both** refused sources as `valid` (`O1`), so neither ceiling is a language limit.

**S1/S2/O1 all held** (`SUMMARY claims=3 claim_falsified=0`).

## What this establishes

1. **The obstruction is the fixed 100,000-step budget, not two unrelated bugs.** At ~10³ steps per
   token/node, 100k steps buys ≈10² units in *either* Pep-written stage. The driver runs out at a 316-byte
   program; the checker runs out at a 540-byte program. Both are far below any realistic source — including
   every nontrivial `examples/*.pep` (the largest is 96 KB).
2. **An independent corroboration of the 66-node row.** The checker's node ceiling measured here is
   **between 64 (ok) and 80 (refused)** nodes on plain statements. The frozen regression fixture sits at
   **exactly 66 nodes** and fails at `2454:8`. That is the same boundary, measured from a different
   direction: the row is not an outlier, it is a program sitting on the measured cliff edge. It also
   explains why A1's "flip 66n" attempts moved by tens of steps rather than clearing: the deficit is
   structural, not a few operations.
3. **What would actually move it** is a per-unit cost reduction (fewer interpreter steps per token/node) or
   a budget change — and the latter is explicitly outside my authority and the mission's constraints. The
   honest statement to the roadmap is: *at ~10³ steps/unit, a 100k budget caps the Pep-written pipeline at
   a few hundred bytes, in both lanes, regardless of which one is measured.*

## Honest scope

- One source family (top-level `let` statements). Other mixes (function bodies, matches, records) will move
  the per-unit cost — the checker's 64-node figure is specific to this shape, and the earlier 66-node row's
  cost profile differs. The *order of magnitude* is the claim; exact unit costs are not.
- Steps/unit figures are upper bounds derived from "largest success ≤ 100k", not instrumented step counts.
- The scratch tree lacks the emitter (`e0e49e5`), so this measures the two lanes' own costs, not the
  combined candidate.
- No frozen gate was executed; this is not acceptance evidence.

## Reproduce

```powershell
git merge-tree --write-tree 0c5f12b cf02095                 # tree bfe12cd5…, exit 0
git commit-tree bfe12cd5463b681e833629aebd88a39fb63ae878 -p 0c5f12b -p cf02095 -m "measurement"
python verification\probes\shared_budget_mechanism.py <scratch-tree>    # exit 0
```
