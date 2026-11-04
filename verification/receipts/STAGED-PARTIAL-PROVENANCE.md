# Partial/incomplete staged checking and unverified fact provenance — 9 cells, 8 pass, 0 fail, 1 observation (LUCY-20261104-004)

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-004, A3's single bounded slice ("expand invalid/incomplete staged checking") · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Pins (both measured, identical results):** integrated candidate **`bcfa3c0`** and A1's current head **`97e420b`**
**Instrument:** `verification/probes/staged_partial_provenance.py` (new) — reuses the `staged_typed_attacks.py` harness; no new harness. Every cell compares the **staged verdict against the SEED's verdict class for the same source**, not merely two staged runs against each other.

## Verdict taxonomy kept distinct

`valid` · `invalid` · `incomplete` · `unsupported` · `transport_refusal`. The table below shows the
staged path does **not** collapse these into one "refused" bucket.

## Cells (`SUMMARY cells=9 pass=8 fail=0 observed=1`, identical at both pins)

| cell | contract exercised | seed | staged | expected | verdict |
|---|---|---|---|---|---|
| **C0a** | positive control: no hole, honest facts | `valid` | `valid` | `valid` | **PASS** |
| **C0b** | positive control: both declarations supplied | `valid` | `valid` | `valid` | **PASS** |
| **P1** | typed hole in a body (`return ?hole`) — parse complete, program unresolved | `incomplete` | **`incomplete`** | not `valid` | **PASS** |
| **P2** | named hole (`return ?value`) | `incomplete` | **`incomplete`** | not `valid` | **PASS** |
| **P3** | hole in a let value (`let a: Int = ?filler`) | `incomplete` | **`incomplete`** | not `valid` | **PASS** |
| **G1** | fact asserts a record the source never declares, with **correct** document+revision labels | `invalid` | `invalid` | not `valid` | **PASS** |
| **G2** | phantom field: fact adds `P.ghost` the source does not declare | `invalid` | `invalid` | not `valid` | **PASS** |
| **M1** | complete-looking facts that omit one needed declaration (`Q` missing, body uses `q.y`) | `valid` | `invalid` | not `valid` | **PASS** |
| **G3** | fact **contradicts** the source (`P.x: Bool` while source says `Int`) | `valid` | `invalid` | — | **OBSERVED** |

Notable: the **incomplete class survives staging** (P1–P3 answer `incomplete`, not `valid` and not a
generic refusal), and **provenance is not loosened by correct-looking labels** (G1/G2: a fact stamped with
the right document+revision still cannot introduce a record or a field the source does not have).

## Observation G3 — a contract question, not a defect

A fact that contradicts the source can only come from a corrupt or buggy producer; rejecting it is
**fail-closed**, which the work order explicitly asks for where trust is unproven. What is undefined is
the *contract*:

- **authoritative facts** → staged `invalid` (observed): a program the seed accepts is refused;
- **advisory facts** → the staged path should accept and ignore the contradiction.

I am not calling either behaviour wrong. **A1 should state which semantics the chunk contract intends**;
the observation is recorded so the decision is made deliberately rather than discovered later. Note this
is an availability concern, not a soundness one: nothing here accepts an invalid program.

## Positive/negative control discipline

Each negative is paired with a control that must be `valid` (C0a for P1–P3, G1, G2, G3; C0b for M1), so
"refused" cannot be produced by a broken fixture. Cells whose refusal could be a harness artefact are
distinguished by class: a host refusal would read `transport_refusal`, and none did.

## Honest scope

- Forged/contradictory facts (G1–G3) are not producible by an honest producer; they are corrupt-cache
  scenarios. Honest-input behaviour is covered by the earlier matrix and by C0a/C0b here.
- The hole cells assert the **class**, not a specific code: `incomplete` is a front-end state, and the
  chunked report currently carries no diagnostic for it. A1 may want to name that state explicitly.
- One pin pair, fixed case list; no fuzzing, no generated search.
- Not acceptance evidence. `bcfa3c0` Full verdict remains FAIL 14/15 (`ACCEPT-bcfa3c0-FAIL.md`), and the
  duplicate-declaration defect from `MINIMISED-dup-decl-order-bcfa3c0.md` is still open on A1's side.

## Remaining dependence (stated, per the work order)

This slice is complete. Further progress needs one of: A1's **duplicate-declaration fix** (to re-run the
minimiser and matrix and show the defect changed), or a genuine **integrated successor** (to run the
unchanged Full-v2 first, then this probe). No further matrix expansion is planned.

## Reproduce

```powershell
python verification\probes\staged_partial_provenance.py D:\Projects\wt-a3-int-bcfa3c0   # 8 pass, 0 fail, 1 obs
python verification\probes\staged_partial_provenance.py D:\Projects\wt-a3-a1-97e420b    # identical
```
