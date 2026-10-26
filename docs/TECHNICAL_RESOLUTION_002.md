# PEPIN: Technical Resolution 002 — Modern by Default, Evolution by Evidence

**Status:** Binding design policy, 2026-10-26. **Implementation:** Documentation/design only; no native backend has been implemented.

This resolution amends [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md). The historical MoonBit A0 C11 emitter remains an accurate record of the old prototype, but C11 is **not** Pep's active future native target.

## Founding technology rule

> Pep should begin with the most modern **stable, technically appropriate** standards, languages, tools and techniques available. Reassess those choices as technology advances and adopt improvements wherever their demonstrated benefits justify the migration, without sacrificing correctness, simplicity, portability, reproducibility or existing language contracts.

"Modern" is an engineering input, not a synonym for "newest experimental preview". Prefer the current published standard rather than an obsolete one merely because older tooling happened to be available. Do not upgrade blindly or let incidental implementation fashions define Pep semantics.

Review choices at each substantive compiler/runtime milestone **and** whenever an important relevant stable standard or toolchain generation is published. Record the candidate, actual support, benefit, migration cost, tests and disposition. Adopt compatible improvements as routine maintenance; require an explicit design and compatibility decision for breaking changes. A deferred upgrade must say why and when to reconsider it.

This applies to Pep's host tools, native backend, runtime, type-checking approaches, AI/editor protocols, libraries and development tooling. Pep's human-readable source, semantic contracts, determinism and self-hosting goal remain the foundation.

## Native target now: C23

- Target **ISO C23, ISO/IEC 9899:2024**, the latest **published** C language standard as of this resolution.
- Supersede all forward-looking C11 backend commitments in Technical Resolution 001 and Founding Design v0.3. Do not silently fall back to C11 as the normative generated dialect.
- The current primary **OCaml 5.5.2 interpreter-first seed** remains; C23 is the intended output of a **future Pep-written** native generator, compiled by a host C compiler.
- Use newer C23 language/library facilities where they materially simplify implementation, not for novelty.
- Require an actually compatible C23 toolchain and pin/report accepted compiler versions and flags (for example `-std=c23` with a GCC or Clang version supporting features emitted). Toolchain differences, especially on Windows, must be tested rather than assumed. No GNU-only extensions without a separate, explicit portability decision.
- Validate generated programs against the checked interpreter, including errors and relevant numeric/string/data semantics. The backend must not become a second authority for Pep's language semantics.
- **C2y remains a draft** as of this resolution; review it when published and sufficiently supported rather than adopting unstable semantics speculatively.
- C23 is a **backend target**, not a declaration that C is forever the ideal IR. A future better-supported backend may be adopted through another measured decision.
- The Pep-written generator, native backend, and self-hosting are **not yet implemented**. Public capability discovery must continue to report only shipped capabilities.

## Record of change

Historical A0 MoonBit code that generated C11 remains untouched. Technical Resolution 001 remains for provenance, with its old C11 target explicitly overridden here. Other decisions in Resolution 001 remain binding.
