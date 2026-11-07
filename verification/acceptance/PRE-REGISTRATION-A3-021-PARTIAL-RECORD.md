# PRE-REGISTRATION A3-021: hostile partial-record field/identity matrix

**Seat:** A3 (independent verification). **Order:** LUCY-20261107-001 item "A3 —
`codex/bootstrap-agent3-verification@a0ab3f9`. Independently **pre-register** hostile
partial-record field/identity matrix, then verify any new pinned A1/A2 SHA ... No builder
files."
**Written and committed BEFORE any cell was executed.** Predictions below are binding:
a cell whose measured class differs from its pre-registered `expect` is reported as a
prediction failure, not quietly re-interpreted.

## Why this matrix, and why now

A1's next measured slice is the `make_cursor` record-construction unit, and A1's own
integration note asks for coordination on **any new partial-record fact contract**. The
existing A3 suites attack *whole* declarations (`staged_typed_attacks.py` S1–S6) and
*field selection* (`staged_partial_provenance.py` G1–G3). Nothing yet attacks **record
construction whose declaration arrives only as an external fact**, which is exactly the
shape the bounded/chained path must support. So the honest question is not "does the
checker refuse a forged type name" — it does — but:

> When a record's field *set* is carried as a fact, what attests that the field set is
> **complete and correctly identified** for the source revision being checked?

## The implementation under test (read, then pre-registered against)

A1 `codex/a1-typed-bound-pipeline@a7d3ee1`, `tests/pep_checker_a13.pep`:

- `external_records` (line ~2608) maps each `ResolvedTypeDecl` to a `ResolvedRecord` with
  `recordId = -2 - index` (**positional identity**), `duplicateType = false`,
  `firstType = false`, and whatever `fields` the fact carried.
- `analyze_chunk_typed` (line ~2656) guards, before checking: fact `document`/`revision`
  must equal the chunk's (`PEP_STALE_REVISION`), `decl.duplicateType` must be false
  (`PEP_DUPLICATE_TYPE`), and no `typeName` may repeat across the fact list
  (`PEP_DUPLICATE_TYPE`).
- The record-literal path (line ~1901 onward) resolves fields via
  `resolved_field_facts(records, recordId, fieldName)`, which returns the **first** entry
  whose `field.text == fieldName` inside the record whose `recordId` matches. A field with
  no such entry yields `expected == ""`, which is reported as `PEP_UNKNOWN_FIELD`; the
  missing-field pass iterates `externalEntry.fields`, so it can only see fields the fact
  itself listed.

Three consequences are visible from that reading alone, and the matrix is designed to
discriminate them rather than assert them:

1. Nothing on the wire attests that `fields` is the *whole* declared field set — only that
   each listed field's name and type are self-consistent.
2. Nothing attests that a field name appears **once** in the list; a repeated name is
   resolved by first-wins, silently.
3. `recordId` is positional, so identity is derived from list position, never from the
   source's own declaration identity.

## Cells, with pre-registered predictions

Each cell checks one function body as the chunk (the `type` declaration is deliberately
*outside* the chunk, supplied only as fact). Oracle: the seed (`pep.ps1 check`) on the same
whole source, whose verdict class is recorded per cell; the seed is authoritative for
"valid"/"invalid" here because the source really does declare, or not declare, those fields.

Direction vocabulary, deliberately asymmetric:
- **ACCEPTING-INVALID** — chunk says `valid`, seed says `invalid`. Fail-open. Worst class.
- **FALSE-REFUSAL** — chunk says `invalid`, seed says `valid`. Fail-closed but wrong; it is
  the `make_cursor` blocker in advance.
- **STABLE / REFUSED** — matches the seed or refuses transport: acceptable.

| # | Hostile case | Pre-registered `expect` | Predicted class (my claim) | If prediction holds |
|---|---|---|---|---|
| R0 | Honest fact, literal supplies every declared field | `valid` | `valid` | control: the shape works at all |
| R1 | Fact **truncated**: drops declared field `source`; literal supplies both | `invalid` | **FALSE-REFUSAL** (`PEP_UNKNOWN_FIELD` on `source`) | partial facts are unsafe in the refuse direction; a completeness attestation is required before `make_cursor` |
| R2 | Fact **padded**: adds `ghost: Int` the source never declares; literal supplies `index, source, ghost` | `invalid` | **ACCEPTING-INVALID** | fail-open: a forged field set buys a bogus accepting verdict |
| R3 | Fact **field-type forgery**: `source: Str` rewritten to `Int`; literal supplies `source: 3` | `invalid` | **ACCEPTING-INVALID** | field type is trusted from the fact with no content binding |
| R4 | Fact field list **reversed** (same two fields) | identical to R0 | `valid` | control: resolution is order-stable for distinct names |
| R5 | **Repeated field name** inside one fact: `index: Int` then `index: Str`, both orders | same verdict both orders, and not silently `valid` | **order-dependent** (first-wins) | field identity is not attested; the same tuple maps to two facts |
| R6 | Chunk carries the local `type` **and** a forged external fact for the same name | `invalid` or refusal | `valid` (fact silently ignored) | the `analyze_chunk_typed` precondition "chunk carries no type declaration also supplied externally" is documented, unenforced, and unobservable at the call site |
| R7 | Fact with an **empty field list** for a record the literal fully supplies | `invalid` | **FALSE-REFUSAL** | total truncation behaves like R1; no "incomplete fact" state exists |
| I1 | Two external facts, **same `typeName`**, neither flagged `duplicateType` | refused (`PEP_DUPLICATE_TYPE`) | refused | guard covers a host that concatenates two producers' outputs |
| I2 | Two external facts with **identical field facts**, different `typeName`; chunk constructs the second with the second's field type | `valid` | `valid` | control: `recordId` keying prevents cross-record field laundering — if this is `invalid`, field lookup is name-only and every pooled fact set is unsafe |
| I3 | Fact `revision` differs, `document` matches | transport/`invalid` | `PEP_STALE_REVISION` | control on the identity stamp |
| I4 | Fact field carries non-empty `fieldCode` (producer's unsupported-type channel) while shape/type match | not `valid` if the seed refuses the same source | **predicted `valid`** (`fieldCode` never consulted on the literal path) | the fact's supportedness channel is dropped when the declaration is external |

## Rules this matrix binds itself to

- The seed verdict class is measured per cell and printed next to the chunk verdict; no
  cell is graded against another chunk run alone.
- `R2`, `R3`, `R5`, `I4` are the cells that could change a correctness decision. A single
  reproducible ACCEPTING-INVALID is a finding regardless of every other row being green.
- A `FALSE-REFUSAL` is reported as a blocker for the `make_cursor` unit (A1's next slice),
  not as a soundness defect.
- Pre-registered predictions that turn out wrong are reported as wrong, with the measured
  class, in the receipt. The matrix is evidence about my model of the code, not a scoreboard.
- No builder file is touched. Nothing here edits A1's checker, the frozen runner, or any
  acceptance manifest.

## Artifacts

- Driver: `verification/probes/partial_record_matrix.py` (reuses `staged_typed_attacks.py`
  helpers; adds no new harness).
- Receipt: `verification/receipts/ACCEPT-BOOT-A3-021-PARTIAL-RECORD.md` (measured).
