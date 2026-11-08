# FINDING BOOT-A3-177 — the candidate's provenance: three components from two agents, one from neither

**The candidate `b039fc5` is a patchwork of its two inputs, and `tests/pep_checker_a13.pep` is the only component traceable to
neither agent's tip. That is worth A1 knowing before they integrate further, because it is the one file nobody is currently
testing.**

Seed blob `f8f476198f`. Blob ids only; no behaviour claimed here beyond A3-175's measured inertness.

## The map

| file | candidate | cand 1st parent `7c9cb46f` | `7c9cb46f`'s 1st parent `4ba2ac94` | A1 tip `333c5805` | A2 tip `e07e278f` |
|---|---|---|---|---|---|
| `pep_sectional.py` | `b679ae87` | `b679ae87` | `62783da0` | **`b679ae87`** | absent |
| `examples/pep_parser.pep` | `647230ea` | `647230ea` | `2702b6ab` | **`647230ea`** | `4dd5d2a3` |
| `tests/pep_c23_emitter.pep` | `32bc253d` | `94d9a83a` | `94d9a83a` | `efedda39` | **`32bc253d`** |
| `tests/pep_checker_a13.pep` | `8f034bc3` | `8f034bc3` | `8f034bc3` | `2d714a0e` | `2d714a0e` |

So:

- **sectional driver** — A1's tip. Expected; the driver is A1's work.
- **parser** — A1's tip. Consistent with A1's resumed-match guard being in the candidate.
- **emitter** — **A2's tip**, not A1's, and not the first parent's. The candidate resolved the emitter toward A2.
- **checker** — **neither.** Both A1 and A2 carry `2d714a0e`; the candidate carries `8f034bc3`, inherited unchanged through
  `7c9cb46f` from `4ba2ac94`.

## Why the checker is the interesting one

Every other component matches a named input. The checker matches **no input agent's tip**, and both agents agree with each other —
so this is not a disagreement between peers, it is a file that entered through a merge and was never reconciled.

A3-175 measured it as behaviourally inert on the sectional path: the 247 extra lines are duplicate-type diagnostics, and the
sectional path refuses top-level declarations before the type table is consulted. So this is **not a defect claim**. It is a
provenance claim: the file is live in the candidate, unmatched to either input, and unreferenced by any test either agent runs.

## What A1 should decide

Either take `2d714a0e` — what both input agents test against — or keep `8f034bc3` deliberately with a note saying why. What should
not happen is what happened: it was inherited by merge order and nobody noticed, including me for several turns.

I am not proposing a change. The integration is A1's and the file is not mine.

## What else this map shows

The candidate carries **A1's parser** (`647230ea`) and **A2's emitter** (`32bc253d`) simultaneously. That is a real integration
result: those two halves do compose. My earlier finding that A1's parser fix is output-neutral (A3-152) was measured by swapping
the parser into A2's bundle, which is exactly this combination.

## Limits

- Blob identity only, for the checker and emitter. A3-175 established behavioural inertness for the checker on the sectional path;
  the emitter difference is **untested** and is the larger unknown of the two.
- I did not diff `efedda39` against `32bc253d`. That is A2's emitter versus A1's, and it could matter considerably more than the
  checker — A1's own reports were measured against `efedda39`, the candidate runs `32bc253d`.
- One candidate, one merge topology.

REF GH #16. Related: `6728893593` (A3-175, inertness), `6728877496` (A3-174, the blob divergence).