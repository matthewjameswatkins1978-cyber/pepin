# PRE-REGISTRATION A3-022: nested and nominal record fields across the fact boundary

**Seat:** A3 (independent verification). Continuation of BOOT-A3-021 under
LUCY-20261107-001 (A3 lane, `codex/bootstrap-agent3-verification`).
**Written and committed BEFORE measurement.**

## Why this follows A3-021

A3-021 measured record construction where every field's declared type is a builtin.
`make_cursor` does not look like that: a lexer cursor holds a nested cursor/progress
record, so the record-construction path has to resolve a field whose declared type is
itself a record that arrived as a fact. Two things are untested there:

1. **Nominal field types** — `fieldTypeName = "Inner"`, `fieldShape.kind = "nominal"`.
   Builtin fields exercise `same_type_shape` on `kind="builtin"`; nominal fields go through
   a different branch (`nominal` + record lookup), so the A3-021 result does not transfer.
2. **The declaration set, not just the field set** — a nested literal needs *two* external
   declarations. A3-021 forged field lists; this tests a truncated *declaration* set, which
   is the shape a name-based closure (`fact_closure`) can plausibly get wrong.

## Implementation under test

Identical pins to A3-021: A1 `codex/a1-typed-bound-pipeline@a7d3ee1`,
`tests/pep_checker_a13.pep`, entry `analyze_chunk_typed`; nested literals resolved through
`infer_expression_type_and_shape(..., externalRecords)` and the field-type check reached via
`resolved_field_facts` on the outer record.

## Cells and pre-registered predictions

Source shape (both records declared outside the chunk, supplied only as facts):

```
type Inner { n: Int }
type Outer { inner: Inner, tag: Str }
fn make_outer(n: Int, tag: Str) -> Outer { return Outer { inner: Inner { n: n }, tag: tag } }
```

| # | Hostile case | Requirement | Prediction |
|---|---|---|---|
| N0 | honest facts for `Inner` and `Outer` | `valid` | `valid` |
| N1 | `Outer` fact retypes `inner` from nominal `Inner` to builtin `Int`; literal supplies `inner: 3` | `invalid` | **ACCEPTING-INVALID** (`valid`) |
| N2 | `Outer` fact renames the field to `other: Inner`; literal supplies `inner` | `invalid` | **FALSE-REFUSAL** (`PEP_UNKNOWN_FIELD`) |
| N3 | only `Outer` supplied, `Inner` fact withheld (truncated declaration set) | not `valid` | `invalid`/`unsupported` — predicted `PEP_UNKNOWN_TYPE`-class refusal, i.e. fail-closed |
| N4 | honest facts, but the nested literal supplies `n: "s"` (a Str for an Int) | `invalid` | `invalid` (control: nominal nesting does not lose the inner type check) |
| N5 | `Inner` fact padded with a field `extra: Int` | `valid` | **FALSE-REFUSAL** (`PEP_MISSING_FIELD` — the missing-field pass iterates fact fields) |
| N6 | `Outer` fact lists `inner` **before** `tag` and again after (duplicate `tag`) | same verdict both orders, not silently `valid` | order-dependent, same mechanism as A3-021 R5 |

N1, N2 and N5 are the cells that could change a decision. N3 is the closure question:
whether a host that carries only the declarations the chunk *directly* names (here `Outer`)
fails closed rather than silently checking an incomplete world.

## Rules

Same as A3-021: seed class measured per cell and printed beside the chunk class;
`requires` is the contract requirement, the prediction is recorded separately in the receipt;
a prediction that fails is reported as failed; no builder file is touched.
