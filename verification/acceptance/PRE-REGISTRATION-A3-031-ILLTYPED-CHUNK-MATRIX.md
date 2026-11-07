# PRE-REGISTRATION A3-031: does chunked checking REJECT ill-typed variants of the real app?

**Seat:** A3. Campaign `LUCY-20261107-007`, lane item 3: "attack the next strict staged-checking
soundness/coverage gap independently". **Written and committed before any measurement.**

## Why this is the most important untested question left

Every green result in this campaign — A1's four `valid` chunks, my `PROVEN-ORACLE-ONLY` 25/25, A4's
`check` clean, the eventual native run — rests on one assumption nobody has tested on the **real
application shape**:

> chunked checking, given honest external signatures and a chunk that contradicts them, **refuses**.

The earlier campaigns tested forged *facts* (call facts, arity facts, stamps). That is a different
question. This tests the ordinary one: a genuinely ill-typed **program body**, checked in chunks the
way A1/A2/A3 actually check the app. If any ill-typed variant comes back `valid`, then every `valid`
in this campaign is suspect and the staged path is not a soundness boundary at all.

That is worth more than another emitter measurement.

## Method

Take the pinned frozen application (blob `4a44dd65…`, sha256 `f6e8f942…`) and apply **one** targeted
corruption per variant. For each variant run the same chunked check the mission uses: parse, chunk
each of the four functions, supply the other three as external `CheckedFunction`/`ResolvedSignature`
facts, `analyze_chunk_typed`.

| # | Variant | Corruption | Predicted |
|---|---|---|---|
| V0 | control | **none** — the pinned app itself | all four chunks **`valid`** |
| V1 | bad predicate body | `ascii_letter` returns `byte` (Int) where `-> Bool` | at least one chunk **not `valid`** |
| V2 | string argument | `main` calls `ascii_letter("x")` | not `valid` |
| V3 | wrong arity | `main` calls `ascii_letter()` | not `valid` |
| V4 | wrong return type | one `main` branch returns `"s"` for `-> Int` | not `valid` |
| V5 | string offset | `main` calls `byte_at(source, "x")` | not `valid` |
| V6 | undeclared callee | `main` calls `ascii_lettr(...)` (typo) | not `valid` |

**I deliberately do not predict the diagnostic codes.** I do not know them for this shape, and
guessing codes then reporting agreement would be theatre. The falsifiable claim is the **status**:
`valid` versus not.

## What each outcome means

- **V0 `valid`, V1–V6 all not `valid`** → the staged boundary does its job on the real shape.
  **SOUND**.
- **Any of V1–V6 `valid`** → **ACCEPTING-INVALID**. That is a soundness failure of the layer, it
  outranks the emitter work, and it must be reported as such with the minimal reproducer.
- **V0 not `valid`** → the control failed and nothing else in the run means anything; report that.
- A variant that cannot even be parsed or whose signatures cannot be fetched is recorded as
  **NOT TESTED** with the exact diagnostic, never as a pass.

## Second, smaller question: two new peer reference claims

A4's `b57d4bf` outbox publishes reference values that I have not checked:

1. **continue-byte counts** on the four dogfood fixtures (the *old* vertical's semantics, A4 calls
   them "bridge values"): ascii **105**, nonascii **137**, empty **0**, self **706**.
2. **LF counts** for the new `pepin-line-scan` semantics: ascii **3**, nonascii **5**, empty **0**,
   self **39**.

Both are computable one-liners in pure Python over the committed blobs. Predictions: A4's numbers
hold. If they do not, that is a finding about A4's reference, reported separately from any compiler
question — the same discipline I applied in BOOT-A3-025.

These are **reference checks, not gates**: `pepin-line-scan.pep` is *not* the frozen acceptance target
and this pre-registration does not move the target or promote the second program.

## Evidence discipline

- All bytes come from `git cat-file blob` at the pinned revisions, never from a Windows checkout
  (BOOT-A3-029 measured that runs are CRLF-invariant, but provenance still requires pinned bytes).
- Variants are A3-authored diagnostic specimens derived from A4's file. **A4's file is not edited**
  and the frozen app is not modified anywhere.
- One seed build; strict determinism of the checker is assumed from prior slices, not re-proven.

## Scope guard

A3 owns only `verification/**`. No edits to A4's app, A1's checker/host, A2's emitter/runtime, frozen
gates, budgets, `CURRENT`, manifest, master or release labels. Cap unchanged.
