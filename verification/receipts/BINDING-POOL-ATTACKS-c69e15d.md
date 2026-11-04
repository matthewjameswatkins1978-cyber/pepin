# BindingPool / external binding-fact attacks at `c69e15d` — a stale binding fact changes a verdict (fail-open), and the pool cannot report a conflict

**Date:** 2026-11-04 · **Mission:** PEP-WB-A3-20261104-B priority 3 ("challenge A1's new BindingPool: cross-chunk identities, shadowing and stale facts") · **Evidence label:** `TESTED`
**Candidate:** `codex/checker-emitter-integration` @ **`c69e15d3cf9a7aeb56e84a35c43733347fd820c8`**
**Instrument:** `verification/probes/binding_pool_attacks.py` (new, 13 cases) — pure-Python attacks on `pep_chunk_contract.BindingPool` plus transport attacks on the new `analyze_chunk_typed_bound(…, externalBindings, …)`.

## FINDING 1 (high) — a stale binding fact decides a verdict

A1's chained design lets a later statement be checked without its prefix, using caller-supplied
`List[BindingFact]`. Those facts carry **no document and no revision** (`type BindingFact { semanticId,
syntaxId, name, ownerFunctionId, scopeId, visibleFrom, mutable, typeName, typeShape }`), and
`analyze_chunk_typed_bound` guards **only `externalTypes`** for identity
(`tests/pep_checker_a13.pep:2589–2593`). Type facts of another revision are refused with
`PEP_STALE_REVISION`; binding facts cannot be, because there is nothing to compare.

Measured consequence (`O1c`): facts sourced from `let x: Int = 1` reused on a program that now says
`let x: Str = "a"` and `return x + 1` —

| path | verdict |
|---|---|
| seed (whole program) | **`invalid`** |
| later chunk **without** facts | `invalid` |
| later chunk **with the stale `x: Int` fact** | **`valid`** ← fail-open |

So a stale (or foreign) binding fact silently **overrides the source's own declaration** and accepts a
program the seed rejects. `O1b` records the parity failure explicitly: binding facts are not refused like
type facts.

**Minimum contract change (A1's call):** carry `document`/`revision` on `BindingFact` (or on the pool
admission) and apply the same `PEP_STALE_REVISION` guard the type facts already get — otherwise
"source-revision authority" is unenforceable for the half of the staged seam that carries bindings.

## FINDING 2 (medium) — `BindingPool.add()` cannot distinguish a conflict from a duplicate

`A1b`: for one source identity `(name, ownerFunctionId, scopeId, visibleFrom)` the pool returned
`first=1, identical=0, conflict=0` — an **identical duplicate** and a **conflicting fact** are
indistinguishable to the caller, and the conflicting fact is silently dropped (`A1`: first type wins;
`A2`: first mutability wins). A consumer pooling reports from two chunks therefore cannot detect that the
chunks disagreed, and cannot tell whether the pool is complete.

This is the **same class** as the duplicate-declaration defect already open with A1: silent resolution of a
conflict where a refusal (or a reported conflict) would be safe. Suggested shape: `add()` returns
`(added, conflicts)` or raises on a conflicting identity, and the pool exposes the conflicting names.

## FINDING 3 (low, API hygiene) — `facts()` hands out the pool's own dicts

`A4`: mutating a fact returned by `facts()` changed the pool's stored fact (`typeName` became `Str`). The
getter copies the list but not the records, so any consumer can corrupt shared pool state by accident.
Deep-copy on the way out (or document immutability and enforce it).

## What HELD (the checker side is sound where it can be)

| case | result |
|---|---|
| `A3` renumbering | admitted ids are `BASE+0, BASE+1, …`, unique, originals discarded — the documented behaviour |
| `B0` prefix chunk alone | `valid`, produces 1 binding fact |
| `B1` honest pooled facts | the later statement checks `valid` — the feature works |
| `B2` **forged binding type** (`x: Str` in a fresh fact set) | **`invalid`** — forged types are not trusted |
| `B3` no facts | `invalid` — non-vacuity for B1/B2 |
| `B4` binding owned by **another function** | **`invalid`** — cross-function leakage refused |

So the checker is fail-closed on forged *types* and foreign *owners*; the holes are (i) provenance
identity for bindings and (ii) the pool's silent conflict handling.

## Honest scope

- `O1c`'s stale fact set comes from an equivalent program (same document shape, changed binding type); binding
  facts have no document field, so the guard could not distinguish it even if the document differed. That is
  the finding, not an artefact.
- One binding, one chained statement pair; shadowing was probed only through `ownerFunctionId`/scope identity
  (B4), not through nested-block shadowing of the same name — not measured here and not claimed.
- `A1/A2` describe pool behaviour rather than a wrong verdict on their own; they matter because of `A1b`.
- Not acceptance evidence; the Full verdict for this candidate is FAIL 14/15 (`ACCEPT-c69e15d-FAIL.md`).

## Reproduce

```powershell
python verification\probes\binding_pool_attacks.py D:\Projects\wt-a3-int-c69e15d   # exit 1: 3 findings
```
