/-
  INTENTIONALLY BROKEN VARIANT — must be REJECTED by Lean.

  This file is NOT part of the `Verification` library and MUST NOT be
  imported by any built module. On an approved host, the receipt step is:

    lake build                                  # must succeed (real model)
    lake env lean BrokenVariant.lean            # must FAIL with a type error

  The failure proves the toolchain actually checks proofs instead of
  skipping files. Do NOT "fix" this file; do NOT add `sorry`/`admit`
  (those warn instead of failing). If `lake env lean` ever accepts it,
  the MODEL_PROVED claim is void and the toolchain is suspect.

  Status: DRAFT, same BLOCKED_SECURITY build label as the library.
-/
import Verification.ValueCopy
import Verification.AliasedCounterexample

/-- FALSE universal claim over the aliased model: no in-place
    shared-store write ever observably affects a handle-copy.
    Refuted by `cxStore/cxStore'/cxCopy` in AliasedCounterexample.lean,
    so the kernel must reject the `rfl` below. -/
example : aread cxStore' cxCopy = aread cxStore cxCopy := rfl
