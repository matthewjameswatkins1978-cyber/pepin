# A1's type facts match the seed's own record declarations at `0c5f12b` — content differential, six claim cases held

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slice 2: "incorrectly reused expression/type facts" — facts that are well-formed but *wrong*) · **Evidence label:** `TESTED`
**Target:** `codex/p1-checker-cost-fix` @ **`0c5f12b`**, `fn chunk_type_declarations` in `tests/pep_checker_a13.pep`; pinned worktree untouched.
**Instrument:** `verification/probes/a1_type_facts_vs_seed.py` (new). **Oracle:** the seed's `check --json` AST, which carries every `record_declaration` with field names, type strings and exact spans — an independent model, not the producer's own view.

## Why this probe exists

The guard probe (`a1_type_facts_attacks.py`) proves the producer fails *closed*. That leaves the
opposite risk untouched: facts that are structurally fine and semantically wrong — a wrong span, a
mangled type string, a field reordered — which would propagate silently into chunked checking. This
compares the facts against the seed's declarations field-by-field.

## Result — `SUMMARY cases=6 claim_falsified=0`

| case | claim | measured |
|---|---|---|
| **F1** | same record names with matching declaration spans | **parity** — `Point`, `Box`, `Wrap`, `Crlf` with identical `declStartByte`/`declEndByte` |
| **F2** | same fields in the same order with matching field spans | **parity** — including the record-typed field `p: Point` and `xs: List[Int]` |
| **F3** | `fieldTypeName` equals the seed's type string | **parity** — `Int`, `Bool`, `Str`, `Point`, `List[Int]`, `E` |
| **F4** | primitive-typed fields carry no error code | **clean** — no primitive field carries a code |
| **F5** | a union declaration yields no record facts | **held** — `type E = Num(Int)` contributes nothing; only `Wrap` is returned |
| **F0** | (observation) sources the seed rejects have no ground truth | 2 fixtures recorded, not compared — see below |

The `crlf_records` fixture is included deliberately: spans still match the seed across `\r\n`, so the
producer's byte accounting is not LF-only.

## The two seed-rejected fixtures, handled honestly

`type Bad { n: Nope }` and `type D { a: Int  a: Bool }` are **invalid programs** — the seed refuses them
before building declarations, so it offers no AST to compare against. The producer still describes the
*parse* it is given, which is legitimate for a fact producer. Recorded rather than scored:

```json
{"fixture": "unknown_field", "seed_status": "invalid",
 "facts": [{"type": "Bad", "fields": [{"name": "n", "declared": "Nope", "code": "PEP_UNKNOWN_TYPE"}]}]}
```

That is the useful detail: the producer's per-field code for an unknown type is `PEP_UNKNOWN_TYPE` —
the **same code the seed's checker reports** for that field, so a consumer inherits the seed's
vocabulary rather than inventing one.

## Own-instrument correction (disclosed)

The first version of this probe treated the two seed-rejected fixtures as **F1 failures** ("seed has no
records, facts do"), i.e. it conflated *no ground truth* with *mismatch*. That is the same
prose-versus-outcome class of error I hit twice earlier in this mission, now on a different axis: the
claim was ill-posed rather than the comparison being malformed. Fixed by separating the two: parity
claims run only where the seed is `valid`, and rejected sources are recorded as `F0` observations. The
correction was made before anything was recorded anywhere.

## Honest scope

- Five fixtures, one pin, one pass. Parity is shown for these shapes, not proven generally.
- `fieldShape` (the producer's own type-shape enum) has no seed counterpart, so it is only checked for
  consistency in `a1_type_facts_attacks.py`/the code rows here — its semantics are not independently
  verified.
- No consumer of these facts exists yet on this pin, so this is producer-side verification; the emitter
  side is monitored by the frozen `declaration_emittability_agreement` probe on a combined tree.
- Not acceptance evidence; the frozen Full still waits on a pushed combined successor of `8396b63`.

## Reproduce

```powershell
python verification\probes\a1_type_facts_vs_seed.py D:\Projects\wt-a3-a1-0c5f12b   # exit 0
```
