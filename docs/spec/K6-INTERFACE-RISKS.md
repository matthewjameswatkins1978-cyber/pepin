# K6 — Interface risk audit: A2 prototypes (123d8b3) × A1 stamps (727f8af)

SOURCE-READ only. No builder edits. No execution claimed.

## What the prototypes part is

`emit_c23_checked_part(..., part: "prototypes")` emits C declarations
`pep_fn_<name>(params);` for THIS chunk's functions only — no preamble,
no bodies, no epilogue. Name-based (`pep_fn_` + node.text), arena flag
(`requiresArena`) computed per chunk. Authentication claim (A2-032):
the checked chunk itself; no new facts. Sync-pinned against the header
tail by the bounded suite (`prototypes == header's tail`).

## The gap: assembly is identity-free

A1 stamps (document/revision) stop at the chunk boundary. Past it,
everything is C text: prototypes carry no revision, units carry no
revision, and nothing in the assembly step checks that prototypes(P)
and units(Q) came from the same chunk, revision, or even the same
program. The matched set holds today by probe convention
(`prepare()`), not by check. Combined with K1: B2/B3 guard fact
ingress; NOTHING guards C-assembly mixing.

## Two predicted counterexamples (A3 selects one)

**CE1 — mixed-assembly, diverged signatures.** Prototypes from chunk P
+ units from chunk Q, same function names, deliberately diverged
parameter lists. Predicted: NO diagnostic at assembly or seam layer;
the mismatch surfaces only at the C compiler (conflicting-types error)
or, worse, as a silent miscompile if the divergence is
link-compatible. Falsifier of my model: any seam/probe-layer refusal
of the mixed assembly before the compiler runs.
**CE2 — stale prototype reuse.** Prototypes emitted at revision R,
units re-emitted at R+1 after a signature change, assembled together.
Predicted: assembles without refusal (prototypes are stamp-free text).
Same root cause as CE1; tests the revision dimension rather than the
cross-chunk dimension.

## Suggested minimal guard (not implemented, A1/A2 decision)

Assembly-time agreement check: every emitted unit's (name, arity,
arena-flag) must match a prototype from the same assembly set, and
optionally a revision tag threaded through the assembly (not the
fact schema). Fails closed at the seam, before the toolchain.
Price INFERRED: one string-compare pass over the assembly manifest;
no checker, protocol, or schema change. If A2 prefers to own it, the
check lives in probe/assembly code, never in A1 files.

## Ask

A3: run CE1 or CE2 (your pick) at 123d8b3 + 727f8af. Either a silent
miscompile/late error (model confirmed, guard worth building) or an
early refusal I missed (model corrected) is a useful verdict.
