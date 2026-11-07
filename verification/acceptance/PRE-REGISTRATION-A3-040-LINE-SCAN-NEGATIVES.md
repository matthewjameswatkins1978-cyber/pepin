# PRE-REGISTRATION A3-040: line-scan's malformed-fact negatives and a NUL-sensitive input

**Seat:** A3. **Written and committed before measurement.**

## Why this closes a real gap rather than adding another measurement

Re-reading the packet's acceptance shape for the first gate:

> a documented Pep source file under `examples/dogfood/`, an executable native build consuming **at
> least three genuinely different real files (ordinary ASCII, a source with non-ASCII bytes, a source
> with an empty/NUL-sensitive edge)**, correct deterministic results against an independent
> seed/reference with byte provenance, strict Clang/GCC, and an independent A3 gate **including
> intentionally malformed/incomplete fact cases**.

`pepin-line-scan` is the one program that runs natively (BOOT-A3-034, PROVEN 39/39). Against that list
it is missing exactly two things:

1. **a NUL-sensitive input** — its five files were ASCII, non-ASCII, empty, and two real Pep sources;
   none carried an embedded NUL;
2. **intentionally malformed/incomplete fact cases** — BOOT-A3-025/027 tested those for the *frozen*
   app, which never reaches emission, so they are `NOT TESTED` there. Line-scan **does** emit, so the
   emit-entry negatives are finally testable on a program that actually runs.

Both are squarely in A3's lane and neither requires any peer's code to change.

## Plan

**New fixture (A3-authored, exact bytes):** `idruns`-style NUL case for a line counter —
`61 00 62 0A 63 00 0A 64 0A` → `a\0b\nc\0\nd\n`, **9 bytes, 3 LF bytes, two embedded NULs**.

Prediction **NUL1**: line-scan reports **3**. A NUL must neither be counted nor break the count; a
scanner that stops at NUL would report 1, and one that counted NUL as LF would report 5.

**Malformed-fact matrix** on line-scan's `main` chunk (same four cases used throughout):

| # | tampering | predicted |
|---|---|---|
| M1 | resolved call facts stripped | refused `…has no resolved call fact` |
| M2 | `calleeId` severed to a foreign id | refused `…target is missing from the checked functions` |
| M3 | checked-callee arity forged | refused `…argument count disagrees with the checked arity` |
| M4 | honest report re-invoked on a second valid target | refused `PEP_STALE_REVISION` |
| M5 | **false-positive control**: the honest report on its own target | **must emit** |

M5 is the control that stops M1–M4 from being vacuous — without it, four refusals are indistinguishable
from an emitter that refuses everything.

## What would falsify or weaken this

- A NUL result other than 3 → the line counter mishandles NUL, a real defect in the shipped program's
  behaviour on a required input class.
- Any of M1–M4 emitting → an accepting-invalid fact gate on a program that runs natively.
- M5 refusing → the control fails and the four refusals mean nothing; that would be reported as
  **NOT TESTED**, not as a pass.

## Honest framing

This does **not** make the frozen acceptance target pass. `pepin-source-scan.pep` still has no native
result and this pre-registration does not touch it. It completes the packet's *shape* of evidence for
the one program that does run, and it is the cheapest remaining check with real acceptance value.

## Scope guard

A3 owns only `verification/**`. No edits to A1's checker/contract, A2's emitter, or A4's app and
fixtures. Cap unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.
