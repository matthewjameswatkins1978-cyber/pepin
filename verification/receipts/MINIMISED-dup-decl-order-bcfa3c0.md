# Minimised counterexample — duplicate type declarations make external-fact order decide validity

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-002 slice 1 ("reproduce and minimise the duplicate-type-declaration / order-sensitive external-fact bug") · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Current-defect pin (candidate):** `codex/checker-emitter-integration` @ **`bcfa3c011c67f25142c2866755a525bc3817a42a`**
**Fixture:** `verification/fixtures/dup-decl-order.flip.pep` — **81 bytes**, sha256 `7848eea5d2bcb04b58a83fbdb4ac8d54d29e4b012662f96d47b0addc5b26820e`
**Instrument:** `verification/probes/dup_decl_minimiser.py` (new)

## The shortest counterexample (81 bytes)

```pep
type D {
    a: Int
}
type D {
    b: Int
}
fn f(d: D) -> Int {
    return d.a
}
```

| observer | result |
|---|---|
| **seed** (`pep.ps1 check`) | **`invalid` / `PEP_DUPLICATE_TYPE`** |
| chunked `analyze_chunk_typed` with honest facts in gathered order (`D{a}` first) | **`valid`** ← accepts a program the seed rejects |
| same chunk, facts **reversed** (`D{b}` first) | **`invalid`** |
| **control**: identical source with the second declaration removed | `valid` / `valid`, seed `valid` — order-stable |

So the trigger is duplication, not the shape of the body: one 81-byte file, two orders of the same
trusted facts, two different verdicts, and the accepting order disagrees with the seed.

## Is it current or historical? (pinned, one probe, four pins)

| pin | what it is | typed entry point | defect |
|---|---|---|---|
| `8396b63` | integration baseline before slices 4a–4c | absent | not evaluable (no typed path) |
| `0c5f12b` | slice 4a (producer only) | **absent** — `pep-c23-checker-chunk-typed` cannot be validated | not reachable |
| `49db581` | slice 4b (**external facts consumer**) | present, 4-arg form | **code introduced here** — `external_records` and `analyze_chunk_typed` exist with today's bodies |
| **`bcfa3c0`** | current integrated candidate (4b + 4c) | present, 5-arg form (+`expectReturns`) | **CURRENT DEFECT, reproduced** |

So this is a **current** defect on the candidate the Full was run against — introduced by slice 4b's
consumer, carried unchanged through 4c and the integration merge — not a historical artefact of an
earlier instrument.

## Mechanism (read from the code, line-referenced)

1. `external_records` (`tests/pep_checker_a13.pep:2532`) maps each incoming declaration to a
   `ResolvedRecord` with **`duplicateType: false` hardcoded** and performs **no name dedupe**.
2. `record_field_type_ext` (`:2561`) resolves a field through `resolved_record_by_name`, which takes the
   **first** matching record.
3. Therefore, when the same type name arrives twice with different fields — which the producer legitimately
   emits when facts are gathered per declaration subtree, the pattern used by the builder's own tests —
   **the first arrival wins**, and the verdict depends on caller ordering.

## Minimal fix shape (A1's call, not applied by me)

Carry `decl.duplicateType` through `external_records` (the producer already computes it) and refuse — or
consistently ignore — repeated type names, with a code declared in the existing family rather than
invented here. Then both orders must agree with the seed's `PEP_DUPLICATE_TYPE` refusal.

## Reproduce

```powershell
# current defect (exit 0 when the counterexample is found; M1/M2 both held)
python verification\probes\dup_decl_minimiser.py D:\Projects\wt-a3-int-bcfa3c0
# historical control: typed entry point absent, probe exits 2 with an explicit scope note
python verification\probes\dup_decl_minimiser.py D:\Projects\wt-a3-a1-0c5f12b
```

## Fixture reproducibility (measured, and corrected once)

The fixture's numbers above are byte-exact only if the file is checked out with LF. This repository runs
`core.autocrlf=true`, so the first version of the fixture (committed at `7adba55`, before any `.pep`
attribute existed) checked out as **90 bytes** with a different sha256 — a real reproducibility hazard
for a fixture whose size is part of the claim. Fixed in `0267c9b` by adding `*.pep text eol=lf` to
`verification/.gitattributes`; a fresh checkout of `0267c9b` now yields **81 bytes / sha256 7848eea5…**.
Stored blob for the fixture: `8466adf6ecb2d1baf328dad23169db87ad090fdf`. Cite the blob or a checkout at
`0267c9b` or later, never `7adba55`.

## Honest scope

- One declaration pair, one field used; the minimiser tried three sizes (81 / 111 / 114 bytes) and the
  81-byte form already flips, so no smaller candidate was needed for the claim.
- "Forward/reversed" is the order of the gathered fact list; the fail-open direction is the one where the
  declaration carrying the used field arrives first.
- The probe treats an absent typed entry point as exit 2 with a scope note, so "not reachable here" can
  never be mistaken for "defect absent".
- Not acceptance evidence: the Full verdict for `bcfa3c0` stands at FAIL 14/15 (`ACCEPT-bcfa3c0-FAIL.md`).
