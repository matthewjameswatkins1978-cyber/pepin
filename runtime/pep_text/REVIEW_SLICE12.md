# Agent-4 review checkpoint: slices 10–12 (cumulative materials)

Date: 2026-10-29. Reviewer: none available in this worker session
(logged per campaign rule; no self-certification claimed). Integrator
and sibling agents are invited to append findings below. `REVIEW_SLICE3`
covered slices 1–3, `REVIEW_SLICE6` slices 4–6, `REVIEW_SLICE9`
slices 7–9; this note covers 10–12.

## Scope under review

Isolated `runtime/pep_text/` plus `tests/test_textbuf_native.py`. No
edits to checker, emitter, testing, packets, or master at any point.
Slices 11–12 were built under the 2026-10-29 Defender security hold:
source only, syntax-checked but not executed (see below).

- Slice 10 (`bea69f9`): native fragment join over real emitter output
  (`frag_probe`), byte-identical to the Python join, then compiled and
  run under both toolchains. Pre-integration evidence for Agent 2.
  19/19 green (last full run, pre-hold).
- Slice 11 (`dec317b`): audit contract fixes (stale comments, strict
  null contracts, OVERFLOW doc, reserved enum, component-local codes),
  length-tagged `join_n`, NUL-fragment analysis with three options
  for Agent 2, subsystem README, test flag-dedup. Syntax-checked
  only — implemented but untested, pending a post-hold suite re-run.
- Slice 12 (this commit): `fragn_probe`, the length-tagged companion
  that joins explicit `[OFF, LEN)` file slices in one `join_n` call
  (NUL-preserving; argv cannot carry NULs, so slices address the file
  directly). Out-of-range slices fail closed before anything is
  written. Syntax-checked only, same hold terms.

## Adversarial notes (builder's own — not independent review)

1. The probe deliberately does NOT validate in the C library what the
   host must guarantee: `join_n` trusts `lens` (documented). Bounds
   checking lives in the probe/CLI layer, mirroring the planned
   host-side precondition (option (a) of the NUL analysis). A native
   library that silently clamped would hide Agent-2-side bugs.
2. `malloc(0)` is avoided throughout the probe (`pairs > 0 ? ... :
   1`) so no implementation-defined zero allocation is ever relied
   upon; every allocation path has an explicit null check with
   ordered cleanup (lens, parts, bytes — reverse order of acquisition
   is not required here since all are independent, but every failure
   path frees exactly what it owns).
3. The `(argc - 2) % 2` gate rejects odd argument counts up front;
   with zero slices the probe emits zero bytes and exits 0, which
   the post-hold test will pin.

## Known gaps (not hidden)

- Slice 11–12 code has never executed: syntax checks prove it parses
  and type-checks under strict flags, nothing more. The 19-test
  suite plus new `fragn_probe` vectors must run green post-hold
  before any of it counts as verified.
- The NUL-fragment decision (a/b/c) still belongs to Agent 2; both
  native joins are implemented and probed on the C side only.
- The Defender incident (see SECURITY file) remains open; nothing
  here presumes its outcome.

## Open questions for others (no response blocks Agent 4)

- Agent 2: `join` vs `join_n` and the NUL precondition — the C side
  now supports either answer with byte-exact probes waiting.
- Reviewer: the four incident asks stand, plus the standing
  post-hold suite re-run before any behavior-dependent commit.
