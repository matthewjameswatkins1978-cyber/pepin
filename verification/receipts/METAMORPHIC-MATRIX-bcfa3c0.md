# Metamorphic/differential matrix (LUCY-20261104-002 slice 2) — 13 cells at `bcfa3c0`: 12 pass, 1 fail, and the failing invariant is sharper than I first reported

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-002 slice 2 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Pin:** `codex/checker-emitter-integration` @ **`bcfa3c011c67f25142c2866755a525bc3817a42a`** (pinned worktree, clean)
**Instrument:** `verification/probes/staged_metamorphic_matrix.py` — deterministic and bounded (a fixed case × relation table, no search), **reusing** the harness, typed-record builders and seed oracle from `staged_typed_attacks.py` rather than standing up a second harness.

## Matrix (13 cells: **pass 12, fail 1, skip 0**)

| case | relation | verdict | evidence |
|---|---|---|---|
| `valid_use` (`type P{x:Int}` + `f(p: P) -> p.x`) | R1 whole baseline | PASS | whole=`valid`, seed `valid` |
| `valid_use` | R1 chunk agrees with whole | PASS | chunk=`valid` |
| `valid_use` | R4 fact-order invariance | PASS | `valid` → `valid` |
| `valid_use` | R5 missing-fact closure | PASS | dropping `P` facts → `invalid` |
| `valid_use` | R6 foreign-fact closure | PASS | adding a foreign-revision fact → `invalid` |
| `decl_order` (two independent types, swapped) | R2 declaration-order invariance | PASS | swapped whole=`valid`, chunk=`valid`, original whole=`valid` |
| `dup_decl` (81-byte counterexample) | R1 whole baseline | PASS | whole=`invalid`, seed `invalid` |
| **`dup_decl`** | **R4 fact-order + seed agreement** | **FAIL** | **forward=`valid`, reversed=`valid`, whole=`invalid`, seed=`invalid`** |
| `dup_let` (duplicate scope binding `let a` twice) | R1 chunk agrees with whole | PASS | whole=`invalid`, chunk=`invalid`, seed `invalid` |
| `invalid_program` (body **using** a record with an unknown field type) | R1 body refused like the seed | PASS | whole=`invalid`, chunk=`invalid`, seed `invalid` |
| `chunk_boundary` (3-statement body) | R3 boundary invariance (body vs full group) | PASS | body=`valid`, group[0,1,2]=`valid` |
| `chunk_boundary` | R3 partial group refuses (dependency discipline) | PASS | partial group[2]=`invalid` |
| `incomplete` (`return` with no expression) | R1 both paths fail closed | PASS | parse refused (`ContractRefusal`), seed `invalid` |

## The failing cell — and a refinement of the finding

The old wording ("order-dependent") was too narrow. With `expectReturns=false` **both orders return `valid`**, and the whole path and seed both say `invalid`. The invariant actually violated is:

> **duplicate declarations must not let a chunked check agree with an invalid program** — order-dependence is one symptom of it (visible with `expectReturns=true`, where forward=`valid`/reversed=`invalid`), and order-independent acceptance is another (visible here).

Both point at the same root cause already minimised: `external_records` (`tests/pep_checker_a13.pep:2532`) hardcodes `duplicateType: false`, dedupes nothing, and takes the first matching record. **Shortest counterexample remains the 81-byte fixture** `verification/fixtures/dup-decl-order.flip.pep` (blob `8466adf6…`).

## What the passing cells tell us

- **Declaration order is safe for independent types** (R2) — the fail is specific to *duplicate* names, not to reordering in general.
- **Chunk boundaries are safe when dependencies travel with the group** (R3 both directions), and an under-carried group still refuses — the 4c dependency discipline is intact.
- **Trusted-fact closure works in both directions** (R5 missing → refuse, R6 foreign → refuse), so the guard surface around the defect is sound; the hole is the duplicate-name case specifically.
- **Duplicate scope bindings** in source (`let a` twice) behave like the whole path.
- **Invalid and incomplete programs** fail closed rather than being silently accepted.

## Own-instrument corrections (three, all before recording)

1. First version scored `dup_decl / R4` **PASS** because it only compared forward vs reversed — both `valid`, so "order-stable". That is a weaker relation than soundness and would have hidden the defect. Replaced with *fact-order **and** seed agreement*.
2. First version scored `invalid_program` **PASS** while the chunk said `valid` — the body was `main` (which never touches the bad record), so `valid` was legitimate. Replaced with a body that actually uses the record.
3. First version compared two *under-carried* groups for R3, so both were trivially `invalid`. Replaced with a complete body/superset-group comparison plus a separate partial-group refusal cell.

## Honest scope

- 13 enumerated cells, one pin; this is a bounded regression matrix, not a fuzz campaign. Every cell prints its evidence, so a "PASS" here is checkable rather than asserted.
- The matrix asserts relations, not full equivalence: no claim is made about chunk *plans* (id remapping, shared roots) beyond what slices 4b/4c expose.
- `expectReturns` changes which symptom of the duplicate-declaration defect is visible; both symptoms are recorded rather than one being chosen.
- Not acceptance evidence: the Full verdict for `bcfa3c0` remains FAIL 14/15 (`ACCEPT-bcfa3c0-FAIL.md`).

## Reproduce

```powershell
python verification\probes\staged_metamorphic_matrix.py D:\Projects\wt-a3-int-bcfa3c0   # exit 1: 12 pass, 1 fail
python verification\probes\dup_decl_minimiser.py        D:\Projects\wt-a3-int-bcfa3c0   # exit 0: 81-byte counterexample
```
