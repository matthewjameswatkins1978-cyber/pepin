# CORRECTION — Str record fields WORK; the blocked types are List-field cases; the emitter's refusal message misleads (2026-10-30)

Corrects my `CENSUS-verified-1of4-3of9.md` mechanism column and
verifies the report lane's corrected metric (their #20 note,
`a25f520`-era). Combined stack (A1 `46bf1c0` + A2 emitter).

## Split probes (the decisive measurement)

| program | result |
|---|---|
| `type A { s: Str }` (Str-only record) + trivial main | **EMITS (4,510 B)** |
| `type B { xs: List[Int] }` (List-only) | **REFUSED** — `record fields require Int, Bool, or a preceding record declaration` |
| `type P { x: Int }` + `type Q { p: P, s: Str }` (record chain + Str) | **EMITS (4,668 B)** |
| real `LexCursor` standalone | REFUSED — and the declaration **contains `stringPartsReversed: List[Str]`** |
| `LexToken` static | contains `stringParts: List[Str]` (and Str fields) |
| `LexProgress` | contains `tokens: List[LexToken]` |

## Verdicts

1. **The report's corrected metric is RIGHT on the field-type
   attribution:** `SourcePosition` emits (no List field); the other
   three each contain ≥1 List field and refuse — **list-valued record
   fields are the single blocker for the type layer**, so "the type
   layer unblocks in one step" holds.
2. **My round-31 receipt's mechanism parenthetical "(Str fields)" was
   WRONG** — I inferred the field type from the refusal *message text*
   instead of measuring. Str fields demonstrably emit. Disclosed here;
   the census *counts* (1/4, 3/9) are unaffected.
3. **The emitter's refusal message is itself a mislabel (third
   instance class):** it says fields require "Int, Bool, or a
   preceding record declaration" — omitting Str, which works. Anyone
   (including me, last turn) reading it as the field inventory is
   misled about what to implement.
4. **"No lexer function in emittable territory" — precise reading:**
   true for *assembling the whole lexer* (any blocked type in the
   program kills it, so the full-lexer bundle needs the List-field
   fix). Not literally true per-function: the three classifiers
   reference zero lexer types and emit (native slice green) — their
   own 3/9 census. Both statements coexist: whole-lexer territory vs
   individual-function territory.

Method note: message-text inference is now banned as an attribution
method in this lane — field/type-level claims require split probes.
