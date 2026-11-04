# Cross-chunk call-fact attacks (priority 4) — the checker's external facts have no provenance; the emitter itself does guard its inputs

**Date:** 2026-11-04 · **Mission:** PEP-WB-A3-20261104-B priority 4 ("attack Agent 2's cross-chunk calls with invalid and forged inputs") · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Where it runs:** the seam between A1's checked-chunk contract and A2's bounded emitter. A2's own pin `ea0bc9a` has the emitter but **not** `analyze_chunk`, so the attacks run in a **scratch merge tree** — `git merge-tree --write-tree c69e15d ea0bc9a` → clean, local commit **`3535056`** (`D:\Projects\wt-a3-seam`), never pushed, **not** a candidate. A2's own seam probe has the same shape (parse → plan chunks → `analyze_chunk` with external facts → emit per chunk).
**Instrument:** `verification/probes/seam_cross_chunk_attacks.py` (new, 7 cases + 1 observation)

## Result — `SUMMARY cases=7 claim_falsified=0`

| case | attack | measured |
|---|---|---|
| **S0** | control: caller chunk with **honest** external function + signature | `valid` (seed `valid`) |
| **S1** | callee facts **missing** | **not valid** — refused |
| **S2** | forged **arity** (both halves: signature params ×2 *and* `CheckedFunction.arity = 2` for a one-argument call) | **not valid** — refused |
| **S3** | forged callee **name** (both halves renamed) | **not valid** — refused |
| **S4** | **self-consistent forged callee fact set** (real `g: (Int) -> Str`, forged to `(Int) -> Int`, caller uses the result as `Int`) | **indistinguishable** from an honest set — see below |
| **S5** | emitter given a `checked` report from **another document** (with the parsed node tree and target from this one) | **same document → `emitted`; foreign report → `REFUSED:PEP_STALE_REVISION`** |
| **O4** | consequence of S4 | chunk says **`valid`** while the seed says **`invalid` / `PEP_TYPE_MISMATCH`** |

## FINDING (structural, same class as the BindingPool one) — callee facts carry no identity

`CheckedFunction { semanticId, syntaxId, name, arity, returnType, returnShape, startByte, endByte }` and
`ResolvedSignature { functionId, functionName, params, returnType, returnShape }` have **no document or
revision field** — unlike `ResolvedTypeDecl`, which does and which `analyze_chunk_typed_bound` guards
(`:2589–2593`). So a chunk cannot tell an honest callee fact from a forged one, and with a self-consistent
forgery (S4/O4) it validates a caller body whose program the seed rejects.

This is consistent with the binding finding (`BINDING-POOL-ATTACKS-c69e15d.md`), so the seam has **one**
provenance hole, not two:

| staged fact kind | carries document/revision | guarded |
|---|---|---|
| `ResolvedTypeDecl` | **yes** | **yes** — `PEP_STALE_REVISION` |
| `BindingFact` | no | no — stale facts flip a verdict |
| `CheckedFunction` / `ResolvedSignature` | no | no — forged fact set is indistinguishable |

Suggested contract change (owner's call, one place): give the three fact kinds the same identity fields the
type declarations already have, and reuse the existing `PEP_STALE_REVISION` guard at ingress.

## What held, and why it matters

- **The checker does validate call facts against each other** (S2, S3): arity and name forgeries are
  refused when both halves are forged, so the resolver is not blindly trusting a single field.
- **The emitter guards its own inputs** (S5): a stale/foreign `CheckerReport` passed alongside a node tree
  from another document is refused with `PEP_STALE_REVISION`. A2's bounded-unit seam is fail-closed even
  when the caller lies about the report.

## Own-instrument corrections (all before recording)

1. First S2/S3 forgeries changed only the **signature** half, leaving `CheckedFunction` authoritative — the
   chunk's `valid` was correct behaviour and my "falsification" was a one-sided forgery. Both halves are
   forged now.
2. First S4 was written as a fail-closed claim; when it failed I checked the design intent and reframed it
   as the *indistinguishability* claim with the consequence recorded separately (O4). A forged callee fact
   set is not a logic bug in the resolver — it is the provenance gap.
3. S5 first reported `PEP_STALE_REVISION` for the *same-document* case too, because I set the semantic
   target to the tool document instead of the parsed one. Fixed; the same-document case now emits.

## Honest scope

- Scratch tree, not an integrated candidate: the attacks exercise A1's checker with A2's emitter present,
  which is the seam both lanes will meet at integration; A2's `ea0bc9a` is not in `c69e15d`.
- One callee, one caller, four forgery shapes; deeper chains (three-partial signature sets, transitive
  callee-of-callee) were not measured.
- No native compilation in this receipt (S5 stops at the emitted unit); native claims are priority 5.
- Not acceptance evidence. The integrated candidate verdict remains FAIL 14/15 (`ACCEPT-c69e15d-FAIL.md`).

## Reproduce

```powershell
git merge-tree --write-tree c69e15d ea0bc9a        # tree 81638b0f…, exit 0
python verification\probes\seam_cross_chunk_attacks.py D:\Projects\wt-a3-seam   # 7 cases, 0 falsified
```
