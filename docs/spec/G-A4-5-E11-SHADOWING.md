# G-A4-5 (E11) — Shadowing × Mutability × Hole-Candidate Order

**Campaign G, Agent 4 card 5.** ONE unresolved interaction, traced to
accepted rules, with a minimal counterexample and A3-ready cases. Labels:
ACCEPTED / INFERRED / UNKNOWN. No normative redesign proposed.

## The interaction

Three accepted mechanisms meet in one scope nest and their JOINT outcome is
unstated anywhere:

1. **Shadowing** (ACCEPTED — nested shadow suppression TESTED, A3 set 9;
   duplicate-in-same-scope refused `PEP_DUPLICATE_BINDING`).
2. **Mutability** (ACCEPTED — `var` + rebinding; immutable `let` default).
3. **Hole-candidate enumeration** (ACCEPTED fields — `visibleBindingIds`,
   `candidateBindingIds`; ORDER semantics unstated — UNKNOWN).

## Minimal counterexample

```pep
fn main() -> Int {
  var x = 1
  if true {
    let x = 2
    return take(?)
  } else {
    return 0
  }
}
```

`take` expects `Box` (G-A4-6 fixture shape); both `x`s are `Int`, so neither
is a candidate — the hole has ZERO candidates. Now vary: `take2(x: Int)`.

WITHDRAWN 2026-11-04 (independent review — the Q1/Q3 expectations below are
INVALID for this fixture): the seed looks up the innermost binding first
(`lookup`, `pep_ocaml.ml:345`) and hole visibility SUPPRESSES same-name
outers (`visible`, `pep_ocaml.ml:347-349`, Hashtbl-seen filter). The candidate
set therefore CANNOT contain both `x`s: with `take2(x: Int)` the ONLY
candidate is the inner `let x`, and in the `Box` version the outer MUTABLE
`x` is hidden too — the hole has ZERO candidates, not a risky mutable
fill. Filling `x` resolves to the inner binding, full stop. The "fill
correctness ≠ fill intent" consequence does not occur here; the real (much
smaller) consequence is candidate-list EMPTINESS under shadowing, which the
loop already handles (no candidates → no auto-fill → human asked).

REMAINING unknown (still legitimate): **ordering** across same-name-free
multi-candidate sets, including the AUTH-05 cross-chunk permutation
question (Q2, restated) — no source read establishes it. `find_binding`'s
`semanticId` keying is a checker-internal lookup detail, not evidence about
the candidate-SET key; the set key question is answered (name-suppressed
visibility), the ORDER question is not.

## What is approved vs inferred

APPROVED: shadowing suppression exists AND suppresses same-name outers from
hole visibility (seed `lookup`+`visible`, read this slice); same-scope dupes
refused; cross-chunk bindings carry scope+visibleFrom (B4-R1); candidates
are scope-visible + type-compatible (E5). The remaining gap is precisely:
**candidate ORDERING, whole-source and cross-chunk** (INFERRED-not-ESTABLISHED).

## Smallest conformance cases for A3 (when supported)

- **T-SHD-1 (WITHDRAWN — would fail by design):** the old expectation
  ({inner-x, outer-x}) contradicts seed `visible`. REPLACED by T-SHD-1':
  fixture with `take2(x: Int)`; assert the candidate set is EXACTLY
  {inner-x} (name-suppression holds) — locks the corrected rule.
- **T-SHD-2 (KEPT, the surviving question):** distinct-names fixture
  (`inner_a: Int` inner, `outer_b: Int` outer, both compatible); assert
  inner-precedes-outer in `candidateBindingIds` on whole-source AND on a
  two-chunk split with the inner scope in chunk 2. If chunk order permutes
  it, the finding is an ordering hole, not a validity hole — report as
  observation with the E6 auto-fill cap as the mitigator.

## One future user benefit of a clarified rule

An IDE/agent filling holes in shadowed scopes can stop worrying about
mis-fills: only the innermost same-name binding is ever offered, by
construction. The remaining ranking question (T-SHD-2 order) is worth one
probe, not a rule change.

## Status labels

CORRECTED 2026-11-04 (independent review): Q1/Q3 expectations WITHDRAWN as
invalid for the fixture; T-SHD-1 replaced; T-SHD-2 kept on a distinct-names
fixture; keying question CLOSED (name-suppressed visibility, seed-read);
ordering question OPEN. If T-SHD-1'/T-SHD-2 hold on first run, close this
card as specified-by-test. Next: G-A4-7 or G-A4-8.
