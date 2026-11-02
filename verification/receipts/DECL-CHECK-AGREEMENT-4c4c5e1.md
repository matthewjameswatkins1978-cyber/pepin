# Declaration-check vs real emission — agreement probe at A2 `4c4c5e1` (one text disagreement found)

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Why:** A2's self-correction `4c4c5e1` claims prerequisite emittability is answerable
without emitting, "returning the first refusal with **the same diagnostic text emission
would use**", and explicitly asked A3 to attack classification/emission disagreements.
**Target:** `codex/a2-bounded-emission` @ `4c4c5e18e5d70c93bac3612d21f43f0c42824660`
(clean pinned worktree `D:\Projects\wt-a3-a2b-4c4c5e1`).

## Reruns

- `tests.test_c23_bounded_emission` → **15/15 OK (11.65s)** — A2's four pinned facts
  (supported→ok, empty→unsupported "empty records", closure ok, unit still emits the
  dangling reference) verified under independent execution.

## Agreement probe — `verification/probes/declaration_emittability_agreement.py`

Six fixtures, all with `main` so whole-program refusal can only come from declaration
support. Run: **exit 1, `SUMMARY cases=4 claim_falsified=1`** (3 claims + 1 observation).

| fixture | checker | check verdict / text | whole verdict / text | verdict agree? | text agree? |
|---|---|---|---|---|---|
| CTRL (Point record) | valid | `ok` / — | `emitted` | ✓ | n/a |
| EMPTY (`type Empty { }`) | valid | `unsupported` / `Pep C23 does not lower empty records` | `unsupported` / **identical** | ✓ | ✓ (CR1 held) |
| **UNION_EMPTY** (`type E2 { }` + `type U = W(E2)`) | valid | `unsupported` / **`Pep C23 tagged union has an unsupported layout`** | `unsupported` / **`Pep C23 does not lower empty records`** | ✓ | **✗ DISAGREEMENT (CR3 falsified)** |
| REC_UNION (`type R { u: U2 }` with `U2` union) | valid | `unsupported` / `…record fields require Int, Bool, or a preceding record declaration` | identical | ✓ | ✓ |
| MUTUAL (`Ping`⟷`Pong`) | valid | `unsupported` / `…tagged union has an unsupported layout` | identical | ✓ | ✓ |
| ORDER (record before the record it nests) | valid | `unsupported` / `…preceding record declaration` | identical | ✓ | ✓ |

## Finding (reported to A2, no builder edit made)

**CR3 falsified — first-refusal text/attribution disagreement on UNION_EMPTY.** For
`type E2 { }` + `type U = W(E2)`, the declarations-check reports the *union's* refusal
(`tagged union has an unsupported layout`) while whole emission reports the *empty
record's* refusal (`does not lower empty records`). Both sides refuse (fail-closed —
the dangling-reference hazard is still caught), but A2's stated guarantee —
*"the first refusal with the same diagnostic text emission would use"* — does not hold
here: the two traversals order/pick different first refusals. A caller relaying the
check's diagnostic to a user would name the wrong declaration (and the wrong rule) for
this shape. Likely mechanism: emission lowers declarations in source order (reaches `E2`
first) while the check's closure traversal reaches/classifies `U` first (or classifies a
union without recursing into its payload record) — builder's call.

**What held (stated fairly):** verdict-level agreement everywhere (check `ok` ⇔ whole
emitted; check `unsupported` ⇒ whole `unsupported`) across all six fixtures; exact-text
agreement on EMPTY, REC_UNION, MUTUAL and ORDER — so the disagreement is narrow
(first-refusal selection under multiple unemittable declarations), not a fail-open gap.

## Disclosures (my harness, this slice)

- First REC_UNION fixture was invalid: **nullary union variants require `A2()`** — bare
  `A2` parse-fails `PEP_PARSE_EXPECTED: Expected '('` (grammar fact measured on three
  candidates; pinned as a comment in the probe; fixed via one Threadmoth-certified edit).
- Probe exit 2 remains reserved for harness failure; exit 1 here is a genuine claim
  falsification with the disagreement payload printed.

## Honest scope

One head; checker/session emit layer only (no native build); agreement measured on six
deliberate fixtures, not an exhaustive declaration grammar; `REC_UNION`/`ORDER`/`MUTUAL`
texts compared by exact string equality as A2's claim states.

## Reproduction

```powershell
python -m unittest tests.test_c23_bounded_emission -v          # 15/15
python verification\probes\declaration_emittability_agreement.py <wt-4c4c5e1>   # exit 1 (CR3)
```
