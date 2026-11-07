# BOOT-A3-022: nested/nominal record fields across the fact boundary

**Seat:** A3. **Order:** LUCY-20261107-001 (A3 lane, continuation of BOOT-A3-021).
**Measured against:** A1 `codex/a1-typed-bound-pipeline@a7d3ee1`, entry
`analyze_chunk_typed` (`tests/pep_checker_a13.pep`).
**Pre-registration:** `2f5f9f6`
(`verification/acceptance/PRE-REGISTRATION-A3-022-NESTED-RECORD.md`), committed before
measurement. **Driver:** `verification/probes/partial_record_nested.py` (reuses the A3-021
driver; measured runtime 6.5 s).

## Headline

**6 of 7 pre-registered predictions were right; the seventh was wrong in the worse
direction, and the post-hoc control for it found the session's strongest fail-open.**

> A nested record literal whose declaration is **not** available — neither locally nor as a
> fact — is accepted **on its type name alone, with no field checking and no diagnostic**.
> An outer literal in exactly that position is refused `PEP_UNKNOWN_TYPE`. The asymmetry is
> measured, and it is a closure hazard: name-based fact carrying that drops a nested
> record's declaration silently disables the check for it.

## Measured cells (`a7d3ee1`)

Source under test (both records declared outside the chunk, supplied only as facts):

```
type Inner { n: Int }
type Outer { inner: Inner, tag: Str }
fn make_outer(n: Int, tag: Str) -> Outer { return Outer { inner: Inner { n: n }, tag: tag } }
```

| # | Input | seed | staged | codes | direction | requirement |
|---|---|---|---|---|---|---|
| N0 | honest facts for `Inner` + `Outer` | valid | valid | – | STABLE | **met** |
| N1 | `Outer.inner` retyped nominal `Inner`→`Int`; literal supplies `inner: 3` | invalid | **valid** | – | **ACCEPTING-INVALID** | **NOT MET** |
| N2 | `Outer` field renamed `inner`→`other`; literal supplies `inner` | valid | invalid | `PEP_MISSING_FIELD` 0–0 | FALSE-REFUSAL | **met** (must not accept) |
| N3 | `Inner` fact withheld, source valid | valid | valid | – | STABLE | **NOT MET** (predicted refusal) |
| **N3′** | `Inner` withheld **and** nested literal supplies `n: "s"` | invalid | **valid** | – | **ACCEPTING-INVALID** | **NOT MET** — post-hoc control, not pre-registered |
| N3″ | **no** type facts at all, both values wrong | invalid | invalid | `PEP_UNKNOWN_TYPE` 73–154 | STABLE | **met** — post-hoc control |
| N4 | honest facts, nested literal supplies `n: "s"` | invalid | invalid | – | STABLE | **met** |
| N5 | `Inner` fact padded with `extra: Int` | valid | invalid | `PEP_MISSING_FIELD` 0–0 | FALSE-REFUSAL | **NOT MET** |
| N6 | `Outer` fact lists `tag` twice (`Str`, `Int`), both orders | valid | valid \| invalid | – | order-dependent | **NOT MET** |

## Findings

**G1 — a nested literal with no available declaration is unchecked (N3′, N3″).** The literal
branch is guarded by `if declaration.found || externalEntry.recordId != -1`. When both fail
the field pass is skipped entirely, and the expression's inferred type is still the literal's
name, so an enclosing field whose declared type is that same name matches it. Measured
consequence: `Outer { inner: Inner { n: "s" }, tag: "x" }` with only the `Outer` fact is
`valid`, no diagnostics, seed `invalid`. With *no* facts at all the same body is `invalid`
`PEP_UNKNOWN_TYPE` (73–154) — i.e. the outer path fails closed and the nested path does not.
This is the one finding I would act on: it converts "carry fewer declarations to save budget"
into "silently stop checking nested records".

**G2 — nominal field retype is fail-open (N1).** The A3-021 R3 result transfers to nominal
shapes: `inner: Inner → Int` in the fact plus `inner: 3` in the literal is `valid`. Same root
cause as R3 (no content binding between fact and source declaration), now with a shape/kind
change rather than a builtin swap.

**G3 — duplicated field name is order-dependent (N6).** Confirms A3-021 F3 with a nominal
neighbour: `tag` first as `Str` → `valid`; first as `Int` → `invalid`. Same SHA, same source.

**G4 — padding over-refuses, and the diagnostic points at the fact (N5).** A padded `Inner`
declaration turns a valid program `invalid` with `PEP_MISSING_FIELD` at span **0–0**, because
the missing-field pass iterates the fact's own field nodes and a synthetic fact carries
whatever positions it was built with. A wrong fact therefore does not merely flip the
verdict, it mis-points the source location. (In my cell the fact really had 0–0 positions;
a producer-derived fact carries real spans.)

Controls that stayed green: N0 (honest nested facts), N4 (honest nested type check catches a
wrong inner value), N3″ (absent outer declaration refused), N2 (renamed field refused).

## Scope of G1, measured (so the finding is not overstated)

The shipped name closure does **not** currently drop `Inner` for this shape. Measured on the
same source with the chunk = `make_outer` subtree:

```
chunk node texts    : ['', 'Inner', 'Int', 'Outer', 'Str', 'inner', 'make_outer', 'n', 'tag']
fact_closure(names) : ['Inner', 'Outer', 'make_outer']
```

`Inner` is kept because the nested literal's type name is itself a node text inside the chunk,
and `DocumentIndex.fact_closure` over-approximates by node text. So G1 is **not reachable
through today's host on this shape**. It is reachable by any of:

- a host that supplies only the types named in *type annotations* (here just `Outer`) instead
  of every node text;
- a producer that emits declarations per bounded unit rather than per document;
- a fact cache or pool keyed on carried bindings/signatures rather than on all node texts;
- any future tightening of the closure to save bytes — which is exactly the direction the
  100k ceiling pushes.

That is the reason to close it now rather than when a cheaper closure lands: the checker's
behaviour when a nested declaration is missing is currently "valid, no diagnostics", so the
cost of a later closure change would be silent, not loud.

## What A1 can do with this

- **Cheapest sound fix for G1:** make the literal branch fail closed the way the outer path
  already does — if a record literal's type has neither a local declaration nor a fact,
  report `PEP_UNKNOWN_TYPE` instead of skipping the field pass. That is the asymmetry, and it
  needs no new fact field, no extra pass, and no wire change. Whether it fits under 100k is
  A1's measurement, not mine. Note it *will* turn currently-`valid` programs `invalid`; that
  is the correct direction, and it makes "carry fewer declarations" a visible refusal instead
  of a silent skip.
- **For `make_cursor`:** a cursor containing a nested progress/cursor record needs the nested
  declaration carried too, or its contents are unchecked (G1). Carrying by *name closure* is
  only safe once G1 is closed; until then, carry every record type the body constructs.
- G2/G3/G4 are the A3-021 findings (R3/R5/R1) repeating on nominal fields — same remedies,
  still A1's budget call.

## Discipline notes

- Predictions: N0 ✓, N1 ✓, N2 ✓, **N3 ✗** (I predicted a fail-closed refusal; measured
  `valid`), N4 ✓, N5 ✓, N6 ✓. N3′ and N3″ were added **after** N3's measurement as controls
  and are labelled post-hoc everywhere, including in the driver output.
- No new pinned builder SHA (`a1=a7d3ee1`, `a2=29b27d3`, `candidate7=c631bcd` unchanged), so
  no frozen Full-v2 run and the Candidate7 verdict is not relabelled. Strict staged semantics
  ≠ acceptance.
- No builder, frozen runner, manifest or peer file touched. `analyze_chunk_typed_bound` and
  the pooled/`BindingPool` lane are untouched.

## Reproduce

```powershell
python verification/probes/partial_record_nested.py D:\Projects\wt-a1-fix
# expected: 9 cells (7 pre-registered + 2 post-hoc), requirements met on N0, N2, N3'', N4;
# not met on N1, N3, N3', N5, N6
```
