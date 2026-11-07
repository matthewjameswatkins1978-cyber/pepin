# ACCEPT BOOT-A3-054 — the Str blocker is ONE item, not a general builtin-fact gap

**Verdict: `str_concat` works fully. Only `utf8_slice` is missing. This corrects my own BOOT-A3-042/043
framing and reduces A2's remaining work to a single by-name lowering.**

## Measured ladder — five minimal Str programs

| # | program | result |
|---|---|---|
| s1 | `say("literal")` | **EMITS** |
| s2 | `let s = "abc"` then `say(s)` | **EMITS** |
| s3 | `let s = str_concat("ab", "cd")` then `say(s)` | **EMITS** |
| s4 | `say(str_concat("ab", "cd"))` inline | **EMITS** |
| s5 | `let s = utf8_slice(source, 0, 3)` then `say(s)` | **REFUSED** — *"cross-chunk call has no resolved call fact"* |

## The correction I owe

In BOOT-A3-042/043 I framed the blocker as *"builtin calls never get resolved-call facts, so a builtin call
cannot be bound in a declaration initialiser"*. **That is too broad, and s3/s4 falsify it.**
`str_concat` — a builtin with a **by-name lowering** in the emitter (3 quoted name sites, BOOT-A3-052) —
binds in an initialiser **and** works inline. No fact problem arises for it.

The accurate statement is narrower and more useful:

> A call to a name the emitter **knows how to lower by name** works anywhere, including initialisers.
> `utf8_slice` is **not** such a name (0 quoted name sites), so it fails — and the "no resolved call fact"
> message is simply what you get for an unknown callee, not evidence of a general fact-minting gap.

## What this means for the mission — the ask is now exactly one item

Text building needs two operations: **concatenation** and **getting input bytes into a Str**.

- **Concatenation: already available.** `str_concat` works in initialisers and inline, so a C generator can
  assemble output as a chain of concatenations of literals and slices.
- **Bytes → Str: missing, and it is the only missing piece.** Add a **by-name `utf8_slice` lowering**
  analogous to `str_concat`, plus a small C runtime helper that copies a grant-buffer range into a `Str`.

That is the entire remaining blocker for source-dependent C text. Not an emitter overhaul, not a cost fix —
one lowering case and its runtime helper.

## Evidence this is small, not hand-waving

- The emitter already has by-name lowering for `str_concat` (3 sites), `byte_at` (3) and `byte_length` (1).
  `utf8_slice` has **0** — it is the outlier (BOOT-A3-052).
- `utf8_slice` already exists and works in the **seed interpreter** (`pep_ocaml.ml`, 6 sites) and is used by
  `examples/pep_lexer.pep`, so its semantics are settled; only the C23 lowering is absent.
- Control flow is no longer a blocker: decomposition makes a lexer-shaped probe emit and run natively
  (BOOT-A3-051/053).

## What I have not established

- That the C runtime can express the slice cheaply — the grant buffer is `unsigned char*`, and a `Str` is a
  distinct type; copying vs viewing is A2's design call. I have **not** measured a slice implementation and
  am not claiming it is trivial, only that it is one lowering plus one helper.
- No source-dependent C text has been produced by anyone; the mission floor remains unproven.

## Honest limits

- Five tiny programs, one seed build (`a7d3ee1`) on A1's tree (`86ff953`), one machine. Emission feasibility
  only — nothing compiled or run for these five.
- s5's refusal text is quoted verbatim from the emitter; my reading of *why* (unknown callee) is an
  interpretation, though it is supported by the 0-by-name-lowering measurement.

## Reproduce

```powershell
$env:PEPIN_GATE_ROOT='<t>'
foreach ($k in 's1_say_literal','s2_str_local','s3_concat_local','s4_concat_inline','s5_slice_local') {
  $env:PEPIN_APP_REL="verification/fixtures/str/$k.pep"; $env:PEPIN_APP_REV='8bbc820'
  python verification/probes/emit_any_049.py
}
```

## Scope

A3 changed only `verification/**`. No edits to A1's checker, A2's emitter or A4's app. Cap unchanged; no
`CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-054).