# FINDING BOOT-A3-175 — the checker divergence is real but inert on the sectional path, and here is why

**A3-174 established that the candidate runs checker `8f034bc3` (3,178 lines) while A1's and A2's tips both run `2d714a0e`
(2,961 lines), and said I had no evidence it changed behaviour. I went and looked. On the path compiler A actually uses, it does
not — because the 247 extra lines are unreachable there.**

Seed blob `f8f476198f`. Both trees' own `pep_sectional.py`, five programs each.

## The comparison

| program | A1 tip `2d714a0e` | candidate `8f034bc3` | same |
|---|---|---|---|
| `dup_record` | rc 2, top-level declarations unsupported | rc 2, same | **yes** |
| `dup_field` | rc 2, top-level declarations unsupported | rc 2, same | **yes** |
| `dup_union` | rc 2, top-level declarations unsupported | rc 2, same | **yes** |
| `plain` | rc 0, executable written | rc 0, same | **yes** |
| `dup_fn` | rc 2, `PEP_DUPLICATE_FUNCTION` | rc 2, same | **yes** |

Byte-identical diagnostics, identical exit codes, on every case.

## Why the extra 247 lines never matter here

The extra content is `DiagnosticLookup`, `is_type_table_diagnostic`, and the `PEP_DUPLICATE_TYPE` / `PEP_DUPLICATE_CONSTRUCTOR` /
`PEP_DUPLICATE_FIELD` family — duplicate **type-table** diagnostics. All three record/union cases are refused **before** the type
table is consulted:

```
Pep C23 unsupported: Pep C23 sectional build does not yet cover top-level declarations;
```

So on the sectional path — the only path compiler A is built through — the new diagnostics are dead code. They would matter on a
path that supports top-level declarations, and that path does not exist yet.

## What this settles, and what it does not

**Settles:** the blob divergence is not a behavioural divergence for compiler A's build. A1 can integrate without resolving which
checker is canonical *for this purpose*.

**Does not settle:** whether `8f034bc3` is the right checker to carry forward. It arrived by merge order — the candidate took its
first parent's version — and it is a superset of a region the project has not wired up. That is a provenance question for A1 and A2,
not a verification finding.

## Honest note on method

A3-174 said "no evidence it changes any behaviour I measured". That was true but weak — it left a reader to wonder. Five programs
across the exact feature area the extra lines implement is a small, cheap answer, and I should have run it before writing the
correction rather than after.

The corpus is also self-limiting in a useful way: I chose record and union cases **because** the diff was about duplicate types, and
discovered the sectional path refuses that whole category. That is a better finding than the one I set out to test.

## Limits

- Five programs, one feature area, sectional path only.
- I did not test the full checker surface; `8f034bc3` could differ elsewhere — for instance on programs the one-shot path accepts and
  the sectional path refuses.
- Records and unions are untested end to end because the sectional path declines them outright.

REF GH #16. Completes `6728877496` (A3-174).