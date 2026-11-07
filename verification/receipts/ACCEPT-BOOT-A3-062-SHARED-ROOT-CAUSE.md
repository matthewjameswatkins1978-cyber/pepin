# ACCEPT BOOT-A3-062 — `int_text` and `utf8_slice` share ONE root cause: builtins with no by-name lowering

**Verdict: confirmed, with the mechanism located in source. A builtin is usable in emitted C only if it is
named in three specific places in the emitter. `str_concat`, `byte_at`, `contains` and `byte_length` are named;
`int_text`, `utf8_slice`, `byte_slice` and `source_bytes` are named nowhere, so they fall through to a path
designed for cross-chunk USER calls and refuse with "no resolved call fact".**

This answers the open question from BOOT-A3-061. The two gaps are not independent.

## The count, straight from source (`tests/pep_c23_emitter.pep` @ `86ff953`)

Occurrences of each builtin name as a **quoted string** — i.e. the emitter's by-name sites:

| builtin | sites | usable in emitted C |
|---|---|---|
| `str_concat` | **3** | yes |
| `byte_at` | **3** | yes |
| `contains` | **2** | yes |
| `byte_length` | 1 | yes |
| **`int_text`** | **0** | **no** |
| **`utf8_slice`** | **0** | **no** |
| **`byte_slice`** | **0** | **no** |
| **`source_bytes`** | **0** | **no** |

## Why zero sites means this specific refusal

`pep_c23_cross_chunk_call` (line 643) resolves a callee **only** from `checked.calls`:

```
647:   for callFact in checked.calls {
648:     if callFact.syntaxId == node.id {
654:   if callMatches == 0 {
655:     return pep_c23_unsupported("Pep C23 cross-chunk call has no resolved call fact")
```

A builtin produces **no** `ResolvedCall` fact — there is no `CheckedFunction` for it, so no `calleeId`. A
builtin absent from the by-name sites therefore cannot be resolved by name either, and lands in exactly this
refusal. That is why `str_concat` worked in every position I tested in BOOT-A3-054 while `int_text` fails in the
simplest possible program (`iso_int_text.pep`, 10 nodes).

## The three sites, and the fact that the emitter already documents this pattern

The existing precedent is `str_concat`, at **L1181, L1252 and L2752**:

- **L1181** — classification, so `let` inits and `say()` accept its result. The emitter's own comment is explicit:
  *"str_concat is a BUILTIN (A1 844c8b0; seed @2ad750b): no top-level function node exists for pep_c23_function
  to find, and it returns Str -- classify it directly so let-inits and say() accept its results (Campaign G
  G-A2-7...)"*.
- **L1252** — the call-expression classification (`value.kind == "call" && value.text == ...`).
- **L2752** — the actual lowering (`node.text == ...`).

So adding a builtin is a **mechanical three-site pattern that already exists three times over**, not new design.

## Consequence for the mission

1. The two gaps I have been tracking — `utf8_slice` (the floor blocker) and `int_text` (which blocks *printing*,
   and therefore blocks any probe proving its own output) — are **the same defect class and the same patch
   shape**. One pattern fixes both.
2. My proposed `utf8_slice` patch addressed only the lowering. It **must also add the two classification sites**,
   or `let s = utf8_slice(...)` will still refuse before reaching the lowering. The proposal should be read as
   incomplete on that point.
3. `byte_slice` and `source_bytes` are in the same state and will fail identically the first time anyone needs
   them.

## Honest limits

- I located the mechanism by source inspection and by the counts above; I did **not** apply or test any patch, so
  whether three sites are *sufficient* for `int_text` is inferred from `str_concat`'s precedent, not measured.
- The counts are of quoted occurrences, so they would miss a lowering keyed on something other than a string
  literal. I found no such path in the cross-chunk resolver, but I did not read all 5,650 lines.
- No native runs: `int_text` still blocks printing, so the S dispatch shape remains emission-proven only.

REF: GH #16.