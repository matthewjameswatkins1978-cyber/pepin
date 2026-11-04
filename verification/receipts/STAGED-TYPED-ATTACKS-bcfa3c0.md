# Staged-checker attacks on `analyze_chunk_typed` at `bcfa3c0` — one genuine fail-open: duplicate type declarations are order-dependent and can accept a program the seed rejects

**Date:** 2026-11-04 · **Mission:** PEP-A3-20261104-001 · **Lane:** Agent 3 independent adversarial verification · **Evidence label:** `TESTED`
**Candidate:** `codex/checker-emitter-integration` @ **`bcfa3c011c67f25142c2866755a525bc3817a42a`** (pinned `D:\Projects\wt-a3-int-bcfa3c0`, clean)
**Instrument:** `verification/probes/staged_typed_attacks.py` (new). Nine attacks plus one reachability variant, each compared against **the seed's verdict on an equivalent whole program**, so `valid` from the chunked path where the seed says `invalid` is a fail-open.

## GENUINE FINDING — duplicated type declarations: order-dependent, and one order accepts illegal source

| variant | facts order | typed-chunk verdict | seed |
|---|---|---|---|
| **S3** (hand-built conflicting facts) | `Point{x:Int}` then `Point{x:Str}` | **valid** | invalid (`p + 1` on a record) |
| | reversed | invalid | invalid |
| **S3b** (honest producer output, two real `type Dup` declarations, facts gathered per declaration root exactly as the builder's harness does) | `Dup{a:Int}` first | **valid** ← accepts `d.a` although the source has a duplicate type declaration | **invalid** |
| | reversed | invalid | invalid |

**Mechanism (read from the code, not inferred):** `external_records` (tests/pep_checker_a13.pep:2532) hardcodes
`duplicateType: false` for every external declaration and does **not** dedupe by name, and
`record_field_type_ext` → `resolved_record_by_name` takes the **first** matching record. So the
verdict depends on list order, and the producer's own `duplicateType` flag is discarded on the way in.

**Why it is reachable, not theoretical:** per-declaration gathering and concatenation is the documented
harness pattern (`for root in decl_roots: facts.extend(type_facts(...))`, used by the builder's
`test_chunk_typed.py`). A caller that does this on a source containing a duplicate type name gets an
order-dependent verdict, and one order accepts a body-only chunk whose program the seed rejects.

**Suggested fail-closed fix (owner's call):** carry `decl.duplicateType` through `external_records`
and refuse (or ignore duplicates) when a name repeats, so the typed path cannot agree with an invalid
program. The refusal code should follow the existing family (e.g. an `A13_*`/`CHUNK_*` duplicate
declaration code), declared rather than invented in the checker.

## Claims that HELD

| attack | result |
|---|---|
| **S0** control: honest facts let `p.x` check valid | **valid** (non-vacuity) |
| **S1** forged field type (`Point.x` declared `Str`) cannot make `p.x` valid | **not valid** |
| **S2** forged field types cannot make `p + 1` (arithmetic on a record) valid | **not valid** |
| **S6** foreign-document facts refused with **`PEP_STALE_REVISION`** | **held** |
| **S7** omitted field (`Point{x}` absent) refuses, no silent unknown-field acceptance | **not valid** |
| **S8** `expectReturns` gates a missing return: `true` → refused, `false` → accepted | **gated both ways** |
| **S9** diagnostic parity: whole path and typed chunk report the same `(code, span)` | **parity** |
| **S10** primitive/malformed declaration names are inert: a bogus record fact named `Int` leaves Int arithmetic valid; a non-identifier name (`"a b"`) is harmless beside the honest fact and cannot on its own supply `Point` | **inert** |
| **S11** multi-diagnostic parity: the typed chunk reproduces the whole path's diagnostics in the same order | **parity** (one diagnostic — the seed reports only the first error, so this is single-diagnostic parity; ordering across several errors is untested by design of the front end) |

## Observation (not a claim)

**O5 — declaration spans are never validated.** Supplying a fact whose `declStartByte`/`declEndByte` are
reversed and far outside the source changes no verdict; the consumer reads field types and ignores decl
spans. Harmless for soundness today, but it means a receipt cannot use these spans as identity/provenance
evidence.

## Statement-group attacks (slice 4c)

| attack | result |
|---|---|
| **S12** a statement group whose statement reads a binding declared in an **uncarried** earlier statement | **refuses** (`v` not visible in the group) |
| **S13a** group verdict agrees with the whole path on a body with unannotated `let`s | **agrees** (both valid) |
| **S13b** facts bind where a type **is** declared: forged `P.x := Str` makes `let v: Int = p.x` invalid while honest facts keep it valid | **binds both ways** |
| **O13** (observation) unannotated `let v = p.x` carries **no inferred binding type**, so neither honest nor forged field facts affect `v + 1`. Measured against the baseline: the **seed also accepts** that body, so this is a checker inference-coverage limit, not a staging authority gap |

`SUMMARY cases=16 claim_falsified=2` — both falsifications are the duplicate-declaration defect above.

## My own corrections (disclosed before recording)

Three harness bugs and two mis-shaped claims, all fixed/reframed before anything was reported:
`list(str)` instead of `str.encode()` for `open_bytes`; using the raw typed signature list where
`fetch_all_sigs` conversion was needed; `seed_verdict` fed a `str`; an expectation that foreign facts
produce a *host* refusal rather than a `PEP_STALE_REVISION` **report** (it is the latter, and correct);
an expectation that `expectReturns=false` should reject a returning body (the gate adds a requirement,
it does not forbid returns — reframed to the missing-return direction, which is what it actually gates);
and a span-forgery claim that asserted refusals where the real behaviour is "spans unused" (downgraded
to observation O5 rather than reported as a defect).

## Honest scope

- One candidate, one pin; twelve cases. The chunked path's correctness for the seed-*valid* majority is
  covered by the builder's own tests and my S0/S1/S2/S7/S9, not exhaustively re-proven here.
- S3's hand-built facts are forged input; S3b is the honest-output variant and is the one that matters.
- `expectReturns` was attacked in the missing-return direction only.
- **S13 was originally written as "forged facts govern statement-group checking" and it failed** — but
  the failure was my conflation: the body uses an unannotated `let v = p.x`, and neither the seed nor the
  Pep-written whole checker infers a binding type there, so forged facts *cannot* change that verdict.
  I measured the baseline (seed `valid`, whole path `valid`) before reporting, then split the claim into
  S13a (group/whole agreement) and S13b (facts bind where a type is declared), and recorded the
  unannotated-let behaviour as observation O13 rather than as a defect.
- Not acceptance evidence: the Full verdict for this candidate is FAIL on gate 5 (`ACCEPT-bcfa3c0-FAIL.md`).

## Reproduce

```powershell
python verification\probes\staged_typed_attacks.py D:\Projects\wt-a3-int-bcfa3c0   # exit 1, S3 + S3b falsified
```
