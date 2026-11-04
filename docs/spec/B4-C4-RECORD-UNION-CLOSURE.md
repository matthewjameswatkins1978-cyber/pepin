# B4 Cycle-4 — Source-Wide Record+Union Closure and Two-Type Namespace Tests

**Assignment:** LUCY-20261104-008, A4 task 1. **Branch:** `spec/agent4-spec-lab`
**Pins (verified this slice):** A1 `9ad7d95` (BindingFact repair; type-fact path
unchanged from `f4eb231` line); integration `81398fa` (CANDIDATE-5, A3 verdict
pending); A3 `0e94029` (X3/X6 kind-crossing hole + row-level negative);
seed oracle `57fe424`.
**Evidence read, not rerun:** `tests/pep_checker_a13.pep:2503–2560` in
`wt-a1-fix` — `chunk_type_declarations` builds `ResolvedTypeDecl` exclusively
from `resolve_all_records` with `typeKind: "record"` (line 2550); no union
declaration is emitted as an external type fact.
No implementation changed; specification only.

## 1. The hole (ESTABLISHED shape, A3-reported at `cdbd742`)

- **X3:** chunk A declares `type D {a: Int}`, chunk B declares
  `type D = Left() | Right()`, body uses `d.a` → staged **`valid`**,
  seed **`invalid`/`PEP_DUPLICATE_TYPE`**.
- **X6:** same namesake, union first then record → staged **`valid`**.
- **Controls (pass):** X1/X5 distinct names valid both sides; X2/X4 duplicate
  records refused cross-chunk and same-chunk; X7 union-parameter across chunks
  refused `PEP_UNKNOWN_TYPE` on a seed-valid program (capability gap, same cause).
- **Mechanism (source-read at `9ad7d95`):** only records become external facts,
  so a record/union namesake contributes at most **one** `ResolvedTypeDecl`
  across the chunk set. The producer `duplicateType` flag and the consumer
  repeat-name count both need two observations of the name — with one kind
  invisible, neither fires. Order-insensitive (X3+X6 both fail).

## 2. Normative rule (PROPOSED: B4-CLOSURE-02, extends B4-C1 B4-CLOSURE-01)

- **B4-CLOSURE-02:** the staged type namespace is a SINGLE namespace over
  `{record, union}` declarations. D-closure for a revision R holds only if no
  two top-level type declarations in R share a name **regardless of kind**.
  A program containing a record/union namesake pair MUST NOT be reported
  `valid` under any partition, fact order, or `expectReturns` setting.
- **B4-CLOSURE-03 (PROPOSED):** union declarations MUST be first-class
  external facts with the same identity treatment as records: same
  `ResolvedTypeDecl` shape, `typeKind: "union"`, `(document, revision)`
  attested, byte-span carried. The existing repeat-name count then covers
  record/record, union/union, AND record/union mixes with no new counting
  machinery.
- Seed parity note: the seed rejects the namesake at
  `pep_ocaml.ml:396,402` without regard to kind. B4-CLOSURE-02 is parity, not
  a new semantic invention.

## 3. Minimal requirements for Agent 1 (no implementation prescribed)

- R-REC-1: emit one `ResolvedTypeDecl(typeKind: "union", fields: <empty or
  variant list — A1's call>)` per non-primitive union declaration from the
  same source-wide authority that feeds `chunk_type_declarations`.
- R-REC-2: reuse the existing duplicate-name count and `PEP_DUPLICATE_TYPE`
  code/span behavior; no parallel kind-specific code family.
- R-REC-3: X7 flips as a free consequence — union-typed parameters across
  chunks become resolvable once unions are facts. Assert the flip; do not
  ship a separate union-parameter feature.
- R-REC-4: primitive-named declarations (`type Int ...`) stay excluded from
  facts (existing A3-documented behavior); their staged refusal path is
  unchanged and out of scope for this slice.
- Explicitly NOT required here: per-fact signatures, name-mangling identity,
  emitter-side re-verification (rejected as over-engineering in B4-R3 §3).

## 4. Falsifiable tests for Agent 3 (extend `dup_decl_cross_chunk.py`, 9→14 claims)

- T-REC-1 (X3 retest): record-then-union namesake across chunks →
  assert non-`valid`, code `PEP_DUPLICATE_TYPE`.
- T-REC-2 (X6 retest): union-then-record namesake → same assertion
  (order-insensitivity locked).
- T-REC-3 (same-chunk mix): record+union namesake in ONE chunk →
  assert `invalid` (producer-side coverage of R-REC-1).
- T-REC-4 (X7 flip): union-typed parameter across chunks on a seed-valid
  program → assert `valid` after the fix (was `PEP_UNKNOWN_TYPE`).
- T-REC-5 (union/union duplicate): two identical union names across chunks →
  assert `invalid` (proves the count generalizes, not just the mix).
- Controls to keep: X1/X5 distinct-name `valid`; X2/X4 record-dup `invalid`.

## 5. Status labels

- ESTABLISHED: seed kind-insensitive duplicate rejection; A1 `9ad7d95`
  record-only emission (source-read lines cited above).
- REPORTED (A3, not rerun here): X3/X6 fail-open at `cdbd742`; X7 false-reject.
- PROPOSED: B4-CLOSURE-02/03, R-REC-1..4, T-REC-1..5.
- UNKNOWN: A1 repair SHA for this hole (does not exist yet); CANDIDATE-5
  `81398fa` behavior under T-REC (A3 gate pending — run T-REC-1..5 there as
  the pre-fix baseline: expect T-REC-1/2 fail-open, T-REC-4 false-reject).
- Next A4 (queue tasks 2–3, do NOT merge into this slice): audit `9ad7d95`
  BindingFact/callee admission vs B4-R1/R3 + A3 forged claims; then the
  rules→SHAs→oracle evidence matrix.
