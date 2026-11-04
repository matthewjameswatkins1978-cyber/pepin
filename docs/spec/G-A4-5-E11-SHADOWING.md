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
Both `x`s are visible and type-compatible. Questions no rule answers:

- **Q1:** does `candidateBindingIds` contain one or both `x`s? (If the
  checker dedupes by NAME, the mutable outer `x` is invisible to the fill
  loop — a soundness-adjacent omission. If by ID, both appear — INFERRED
  from `find_binding` keyed on `semanticId`, B4-R1 reads — but ORDER?)
- **Q2:** in what ORDER? Scope-inner-first is the only order that makes
  auto-fill (E6, single-candidate cap) and human review sane — but if the
  order is pool-insertion order (AUTH-05 renumbering!), chunk order can
  permute it. Cross-chunk, the inner `x` may be admitted AFTER the outer
  one. UNKNOWN — no source read establishes candidate ordering.
- **Q3:** if the fill loop (E6) auto-fills the single-candidate case and the
  single candidate is the MUTABLE outer `x` (because the inner `let x`
  shadows with an incompatible type in the `Box` version), the fill binds a
  mutable variable into a position the author may have assumed immutable.
  Valid? Yes. Intended? Unknowable to the checker. This is the user-facing
  consequence: **fill correctness ≠ fill intent under shadowing.**

## What is approved vs inferred

APPROVED: shadowing suppression exists; same-scope dupes refused;
cross-chunk bindings carry scope+visibleFrom (B4-R1); candidates are
scope-visible + type-compatible (E5). INFERRED: ID-keyed (not name-keyed)
candidacy; deterministic order — NEITHER established. The gap is precisely:
**candidate identity key + ordering rule are unspecified.**

## Smallest conformance cases for A3 (when supported)

- **T-SHD-1:** fixture above with `take2(x: Int)`; assert the candidate SET
  equals {inner-x, outer-x} by semanticId (locks ID-keying; falsifies
  name-dedupe).
- **T-SHD-2:** same, assert inner-x precedes outer-x in `candidateBindingIds`
  on whole-source AND on a two-chunk split with inner scope in chunk 2
  (locks order across the exact boundary AUTH-05 renumbers). If chunk order
  permutes it, the finding is an ordering hole, not a validity hole — report
  as observation with the E6 auto-fill cap as the mitigator.

## One future user benefit of a clarified rule

An IDE/agent filling holes in shadowed scopes can rank inner-first with a
cited rule instead of a heuristic — and the E6 loop's single-candidate
auto-fill becomes provably the INNER binding, which is the one the author
sees. Small rule, real trust.

## Status labels

BOUNDARY (not a bug report): no fail-open demonstrated; the unspecified
piece is ordering + keying, both INFERRED-not-ESTABLISHED. If T-SHD-1/2 hold
on first run, close this card as specified-by-test. Next: G-A4-7 or G-A4-8.
