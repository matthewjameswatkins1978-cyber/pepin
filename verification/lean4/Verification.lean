/-
  Verification library root.

  Lake's default lib glob builds the root module only, so this file
  exists to pull BOTH model modules into `lake build`:
  - `Verification.ValueCopy` — functional value model + theorems
  - `Verification.AliasedCounterexample` — shared-backing refutation

  `BrokenVariant.lean` (package root) is deliberately NOT imported here;
  it must fail standalone checking (`lake env lean BrokenVariant.lean`).

  Status: `MODEL_PROVED` — kernel-checked 2026-10-30 (see
  verification/receipts/lean4-kernel-check.md).
-/
import Verification.ValueCopy
import Verification.AliasedCounterexample
