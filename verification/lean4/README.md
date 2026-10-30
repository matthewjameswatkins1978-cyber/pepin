# Pep value-copy model (Lean 4, core only)

**Status:** `MODEL_PROVED` — kernel-checked locally on 2026-10-30 with
pinned `leanprover/lean4:v4.35.0` after the issue #22 native clearance.
Receipt: `../receipts/lean4-kernel-check.md`. Build label
`BLOCKED_SECURITY` retired with the hold.

## Provenance

- Accepted semantics: `PEP-LANG-FINAL-DRAFT-2026-10-27` §4 (DEC-001/DEC-005):
  ordinary data and collections are independent logical values; a later
  edit of one copy must not mutate an earlier logical copy.
- Model scope: `Int` / `Bool` scalars and arbitrarily nested `List`
  values — the DEC-001 subset observable in the current seed
  (`Int`, `Bool`, `List[T]`, immutable `append`, `var` reassignment).
- Out of scope (explicit assumptions): no FFI/host effects, no
  concurrency, no raw pointers, statically valid index paths only,
  source-level values (not C23/OCaml representations).
- Lean toolchain (pinned, official, installed via `elan` on this host
  after the #22 clearance): `leanprover/lean4:v4.35.0` (stable
  2026-10-12).

## Layout

- `Verification.lean` — library root importing both model modules so
  default-glob `lake build` checks the whole library (added after
  delegated tactic review 2026-10-29; avoids `lakefile.toml` glob
  syntax uncertainty).
- `Verification/ValueCopy.lean` — functional value model, checked edit,
  copy-preservation theorem, executable non-vacuity examples.
- `Verification/AliasedCounterexample.lean` — shared-backing variant in
  which the copy property FAILS, with an explicit `example` witness.
- `BrokenVariant.lean` (package root, NOT in `Verification/`) —
  intentionally unprovable variant; `lake build` MUST reject it (proves
  the build checks proofs).
- `lakefile.toml` — Lake build, no dependencies (no Mathlib needed).

## Build on an approved host

```powershell
elan --version; lean --version; lake --version
lake build
lake env lean Verification/ValueCopy.lean
lake env lean Verification/AliasedCounterexample.lean
lake env lean BrokenVariant.lean   # MUST FAIL with a type error
```

Acceptance for `MODEL_PROVED`: `lake build` green, no `sorry`/`admit`/
`axiom`/opaque escapes, `#print axioms` shows only standard Lean
axioms (`propext`, `Quot.sound`, `funext` as used by core), the broken
variant is rejected, receipts recorded under `verification/receipts/`.
A model theorem is NOT an implementation proof: correspondence with
real Pep execution is `TESTED` separately (see
`../adversarial/cases/VALUE_COPY_DEC001.md`, OCaml probes P1–P3).
