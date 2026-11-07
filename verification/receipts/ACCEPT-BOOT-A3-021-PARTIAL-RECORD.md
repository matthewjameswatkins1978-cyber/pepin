# BOOT-A3-021: hostile partial-record field/identity matrix — pre-registered, then measured

**Seat:** A3, independent verification. **Order:** LUCY-20261107-001 (A3 lane:
`codex/bootstrap-agent3-verification@a0ab3f9`, "independently **pre-register** hostile
partial-record field/identity matrix ... No builder files").
**Measured against:** A1 `codex/a1-typed-bound-pipeline@a7d3ee1` (checkout `D:\Projects\wt-a1-fix`),
entry `analyze_chunk_typed` in `tests/pep_checker_a13.pep`.
**Pre-registration commit:** `24bb120` — written and committed *before* any cell ran
(`verification/acceptance/PRE-REGISTRATION-A3-021-PARTIAL-RECORD.md`).
**Driver:** `verification/probes/partial_record_matrix.py` (reuses `staged_typed_attacks.py`;
no new harness). Runs in ~2 min, 12 cells, deterministic.

## Headline

Twelve cells. **All twelve pre-registered predictions were correct. Four cells fail the
contract requirement, two of them fail-open (ACCEPTING-INVALID).**

The question was narrow and is now answered for record construction:

> When a record's field *set* arrives only as an external `ResolvedTypeDecl` fact, what
> attests that the set is **complete and correctly identified** for the revision being
> checked?

**Nothing does.** The chunk's verdict for a record literal is a pure function of the
fact's field list. A fact that is internally consistent but wrong about the source — one
field added, one field retyped — produces `valid` where the seed produces `invalid`. A fact
that is merely *short* produces the opposite failure: a valid program is refused with
`PEP_UNKNOWN_FIELD`.

## Measured matrix (`a7d3ee1`)

`require` = what a sound checker must do for that input. `direction` is relative to the
seed on the same whole source.

| # | Input | seed | staged | codes (staged) | direction | requirement |
|---|---|---|---|---|---|---|
| R0 | honest fact, literal fills every field | valid | valid | – | STABLE | **met** |
| R1 | fact drops declared field `source` | valid | invalid | `PEP_UNKNOWN_FIELD` 134–148 | FALSE-REFUSAL | **met** (must not accept) |
| R2 | fact **adds** `ghost: Int`; literal supplies it | invalid | **valid** | – | **ACCEPTING-INVALID** | **NOT MET** |
| R3 | fact rewrites `source: Str`→`Int`; literal supplies `3` | invalid | **valid** | – | **ACCEPTING-INVALID** | **NOT MET** |
| R4 | fact field order reversed (distinct names) | valid | valid | – | STABLE | **met** |
| R5 | one fact lists `index` twice: `Int` then `Str` | valid | valid | – | **order-dependent** | **NOT MET** |
| R5′ | same fact, `Str` then `Int` | valid | invalid | `PEP_TYPE_MISMATCH` 127–132 | (same cell) | **NOT MET** |
| R6 | chunk carries local decl **and** a forged same-name fact | valid | valid | – | silently ignored | **NOT MET** |
| R7 | fact carries an empty field list | valid | invalid | `PEP_UNKNOWN_FIELD` 120–132 | FALSE-REFUSAL | **met** |
| I1 | two facts share `typeName Cursor` | valid | invalid | `PEP_DUPLICATE_TYPE` | refused | **met** |
| I2 | `Frame` also declares `index: Str`; `Cursor.index` stays `Int` | valid | valid | – | STABLE | **met** (no cross-record laundering) |
| I3 | fact stamped with a foreign revision | valid | invalid | `PEP_STALE_REVISION` | refused | **met** |
| I4 | fact field carries a non-empty `fieldCode`, honest type | valid | valid | – | STABLE | **met** (`fieldCode` is never consulted here) |

## Findings, ranked

**F1 — ACCEPTING-INVALID on a padded field set (R2).** The unknown-field decision is
`expected == "" ⇒ PEP_UNKNOWN_FIELD`, where `expected` comes from the fact. Adding a field
to the fact therefore *removes* a refusal. A host, pool or cached fact that carries a field
the source does not declare makes the chunk accept a literal the seed rejects. The same
mechanism, run in reverse, is the only reason R1/R7 are "safe": they over-refuse.

**F2 — ACCEPTING-INVALID on a retyped field (R3).** `source: Str → Int` in the fact plus
`source: 3` in the literal is `valid`. This is the record-literal analogue of the
function-fact content-binding residual A2 already disclosed; it is not a new mechanism, but
it now has a concrete accepting witness on the record path.

**F3 — one fact, two field facts for the same identity (R5).** `resolved_field_facts`
returns the first entry whose `field.text == fieldName`. Two entries named `index` (one
`Int`, one `Str`) therefore hand the verdict to list order: **`valid` with the `Int` copy
first, `invalid` with the `Str` copy first, same SHA, same source.** Nothing on the wire
says a field name appears once.

**F4 — the "no duplicate declaration" precondition is unenforced (R6).** With the local
`type` inside the chunk and a conflicting fact for the same name, the chunk is `valid` and
the fact is ignored without a diagnostic. `analyze_chunk_typed`'s own comment states this as
a *caller* precondition. Today that is the right answer, but the checker cannot distinguish
a redundant fact from a conflicting one, so a host that violates the precondition gets no
signal at all.

**F5 — partial facts are not a supported state (R1, R7).** Any field-set subset is
`PEP_UNKNOWN_FIELD`. So a "carry only the fields this chunk mentions" scheme for records
would refuse valid programs; the fact has to be complete, or the chunk has to be able to say
`incomplete/unsupported` instead of `valid`/`invalid`.

## What this means for A1's `make_cursor` slice

The producer (`chunk_type_declarations`) already emits complete, source-derived field lists,
so **the honest path is fine** — R0 and I2 are green on it. The exposure is assembled facts:
hosts, caches, pools and any future partial-record contract. Two conclusions, both cheap:

1. **Do not introduce a partial-record fact shape.** A subset-carrying fact would trade a
   budget problem for a false-refusal problem (F5). If `make_cursor` needs fewer bytes, the
   lever is which *declarations* are carried (name-level closure, as `fact_closure` already
   does), not which *fields*.
2. **Field-name uniqueness is the one in-checker guard worth pricing (F3).** It is one pass
   over `decl.fields` comparing `fieldName`, and it converts an order-dependent verdict into
   a refusal. It costs steps, so whether it fits under the 100k ceiling is A1's call, not
   mine — I am reporting the witness, not authorising the change.
3. F1/F2 have no cheap in-checker fix: they need either a content binding (digest over the
   declaration's source spans, checked by the chunk) or an explicit statement in the
   contract that a `ResolvedTypeDecl` is trusted exactly like a `CheckedFunction` fact
   already is. If the latter, it must be stated as a disclosed residual, not left implicit —
   the same way A2's function-fact caveat is.

## Discipline notes (what this receipt does NOT claim)

- **No new pinned builder SHA exists.** `origin/codex/a1-typed-bound-pipeline = a7d3ee1`
  and `origin/codex/a2-bounded-emission = 29b27d3` — both unchanged from the pins in the
  order; `codex/candidate7-20261105 = c631bcd` unchanged. Per the order ("verify any new
  pinned A1/A2 SHA and current Candidate7 gate **only where actual implementation
  changed**"), no frozen Full-v2 run was performed and the existing Candidate7 verdict
  (`ACCEPT-BOOT-A3-002`, on implementation `6dce37d`) is **not** relabelled here.
- **Strict staged gate ≠ frozen Full-v2.** Every cell above is the staged checker's
  semantics on a synthetic source; nothing here is an acceptance verdict.
- **One shape correction, disclosed.** My first R6 was `all node ids` + external function
  facts and drew `PEP_DUPLICATE_FUNCTION`, i.e. it never reached the type facts. I rebuilt
  the cell (local decl subtree + function subtree, no external function facts) *before*
  finalising, and R6 now measures what it claims. The first shape is recorded here rather
  than dropped, because an inconclusive cell reported as a PASS would have been a lie.
- **Not covered:** chained/pooled assembly across revisions (A3-2 `BindingPool` lane,
  unchanged), budget/step cost of any guard, emission, and `analyze_chunk_typed_bound`.

## Reproduce

```powershell
# A1's pinned SHA, read-only checkout
git worktree list | Select-String wt-a1-fix          # a7d3ee1
python verification/probes/partial_record_matrix.py D:\Projects\wt-a1-fix
# expected: 12 cells, 8 requirements met, 4 not (R2, R3, R5, R6)
```

## A3 state

Branch `codex/bootstrap-agent3-verification`, worktree `D:\Projects\wt-a3-gate`. No builder
file, frozen runner, manifest or acceptance manifest was modified. Peer lanes
(A1 checker, A2 emitter, A4 spec) untouched.
