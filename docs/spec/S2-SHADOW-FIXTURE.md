# S2 — shadowing fixture specification (for A3; seed-tested)

A3-075: same-scope duplicate → `PEP_DUPLICATE_BINDING` (NOT REACHABLE
as ambiguity); out-of-scope shadow leak NOT TESTED after three
rejected shapes. Specified + seed-tested below at `57fe424`
(`_build/k4/s2*.pep`, ignored scratch, `pep.ps1`).

## Results

- S2a (top-level `let x` + function reading `x`): **invalid**,
  `PEP_UNKNOWN_VARIABLE`. Top-level lets are INVISIBLE inside
  function bodies.
- S2b (outer `let x = 1` + function with inner `let x = 2`):
  **valid**, prints `2` then `1`. But S2a proves the outer was never
  a competitor — disjoint scopes, not shadowing.
- S2c (param `x` + inner `let x`): **invalid**,
  `PEP_DUPLICATE_BINDING` ("in this scope" — params share the body
  scope).

## Specification

Genuine shadowing (an inner binding suppressing a VISIBLE outer
same-name binding) is INEXPRESSIBLE in current Pep: every
constructible same-name pair is either refused (same scope, S2c and
A3's shapes) or disjoint (invisible outer, S2a). There is no
candidate-ordering semantics to specify — only a refusal rule and an
invisibility rule. This retires E11's residual: T-SHD-1'/T-SHD-2 have
no constructible subject matter.

## Boundary (NOT TESTED, not chased)

`match`-arm bindings were not probed. If a future Pep shape binds
names visibly inside match arms within a function scope, THAT is the
only remaining candidate site for a shadowing fixture. Until such a
shape exists, S2 is CLOSED by language fact, not by review choice.

Falsifier: one accepted program where an inner binding changes the
resolution of a same-name binding that is ALSO resolvable without
the inner one.
