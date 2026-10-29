# Lean 4 build status — BLOCKED_SECURITY (receipt)

**Date:** 2026-10-29. **Branch:** `codex/bootstrap-agent3-verification`.
**Sources:** `verification/lean4/` (`lean-toolchain`,
`lakefile.toml`, `README.md`, `Verification/ValueCopy.lean`,
`Verification/AliasedCounterexample.lean`, `BrokenVariant.lean`).

## Provenance of the toolchain pin (no download performed)

- https://lean-lang.org/install/manual/ — official install procedure
  (elan version manager + lake build tool; PowerShell installer on
  Windows). Read, not executed.
- https://lean-lang.org/doc/reference/latest/releases/ — release notes:
  Lean 4.35.0 stable (2026-10-12); v4.36.0 at rc2 (2026-10-27).
- Pinned `leanprover/lean4:v4.35.0` (latest stable at mission time).
- https://github.com/leanprover/elan — elan README confirms
  `lean-toolchain` pinning semantics.

## Why no build here

1. `elan`/`lean`/`lake` are absent on this Windows host (probed:
   all three `not recognized`).
2. This is the Defender-held machine
   (`runtime/pep_text/SECURITY_2026-10-29_DEFENDER.md`, Severe/Trojan
   quarantine, hold in force). The Agent 3 mission and the three-agent
   overlay explicitly do NOT authorise installing or executing Lean
   binaries here until the hold is lifted; no exclusions, restores, or
   binary relocations were performed or attempted.
3. No separately approved safe host has been provided to this session.

## What was (and was not) done

- Wrote: model + theorems + executable `#eval` expectations +
  aliased-counterexample `example` witnesses + intentionally broken
  variant + build manifest + README with exact approved-host commands.
- Did NOT: download, install, build, or kernel-check anything; claim
  `MODEL_PROVED`; use `sorry`/`admit`/`axiom`/`native_decide` anywhere
  (verify: `Select-String` for those tokens is part of the commit check).
- Proof labels stay `DRAFT` (sources) / `BLOCKED_SECURITY` (build).

## Next executable step (approved host only)

```powershell
elan --version; lean --version; lake --version
lake build
lake env lean Verification/ValueCopy.lean
lake env lean Verification/AliasedCounterexample.lean
lake env lean BrokenVariant.lean   # MUST fail with a type error
```

Build coverage note (delegated tactic review 2026-10-29): `lake build`
with default globs builds the `Verification` root module, which now
imports both model modules via `Verification.lean`; the receipt must
record all three `lake env lean` outcomes (two passes + one mandated
failure) plus `#print axioms` results before any MODEL_PROVED claim.

Record `lean --version` output, file SHAs, `#print axioms` results, and
the broken-variant rejection transcript in a follow-up receipt; only
then may `ValueCopy.lean` advance from `DRAFT` to `MODEL_PROVED`.
