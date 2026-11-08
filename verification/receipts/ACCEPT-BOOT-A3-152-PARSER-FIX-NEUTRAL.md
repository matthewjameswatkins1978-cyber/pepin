# ACCEPT BOOT-A3-152 — A1's parser fix is output-neutral: also a false alarm I raised and withdrew in the same turn

**A1's `d26ba575` ("resumed match followed by operator/field refuses loudly, was silent truncation") changes
`examples/pep_parser.pep`, which is part of the emitter's own SOURCES bundle — so it could have shifted every measurement in this
lane. Swapped in isolation, it does not: `d_a`, `d_b` and `d_c` emit **byte-identically** and all seven gates stay green.**

Seed blob `f8f476198f`. Emitter `e07e278f` with A1's parser substituted. Scratch reverted after.

## The regression check

| fixture | A2 pin alone | + A1's parser fix | identical |
|---|---|---|---|
| `d_a_byte_builtins` | `7D4AE57B7373` | `7D4AE57B7373` | **yes** |
| `d_b_int_text` | `B234213E1076` | `B234213E1076` | **yes** |
| `d_c_arith` | `5215C9F63D60` | `5215C9F63D60` | **yes** |

```
7 gate(s) ran, 0 failed, 0 skipped — A3 GATES: ALL GREEN
```

The header section is 9,644 bytes both ways. So the parser change is invisible to emission on everything this lane tracks.

## The false alarm, recorded

My first attempt checked out A1's commit wholesale and saw `d_c` change hash (`46DDC2160938`) and `d_a`/`d_b` refuse with
`cross-chunk call has no resolved call fact`. I nearly reported a regression.

**It was my comparison that was wrong.** A1's branch carries A1's own emitter (`efedda39`, which predates A2's last four commits),
so checking out their commit swaps the emitter too — the difference was the emitter, not the parser. Swapping **only**
`examples/pep_parser.pep` into A2's tree gives byte-identical output.

This is the same class as the mismatched-id-space error in A3-116: a whole-tree swap presented as a single-variable change. The
discipline that catches it is the one I applied on retry — change exactly one thing, and check that the control still reproduces.

## What the fix actually does

From the diff, after a resumed `match` closes it peeks the next token and refuses with `PEP_PARSE_EXPRESSION` if it is any binary
operator or `.`:

```
if afterClose.ok && afterClose.token.kind == "symbol" &&
   (afterClose.token.text == "." || "||" || "&&" || "==" || ... ) {
  return parser_match_error(cursor, parse_error("PEP_PARSE_EXPRESSION",
    "Resumed match expression cannot be followed by a binary operator or field access", ...))
}
```

A1's own comment is candid about why: every node id is assigned parent-before-child, so no fresh parent can be created for a
match after its closing brace, and the old path silently dropped the rest. So this is a **fail-closed improvement in diagnostic
honesty**, not a feature — it converts silent truncation into a loud refusal.

I verified the non-regression and read the guard. I did **not** construct a resumed-match-plus-operator program to watch the old
parser truncate it and the new one refuse; that needs valid `match` syntax and is A1's lane to demonstrate.

## Effect on the campaign

**None on M-1.** The three fixes A3-150 identified are untouched by this commit and remain outstanding: A4's punctuation literals,
and the epilogue dropping its return echo and propagating `main`'s return as the exit code. A1's `build_c23` also still has no
fragment path (A3-151).

## Limits

- One test: parser swapped into A2's bundle, three fixtures compared, gate suite run. No exhaustive differential over the parser's
  behaviour.
- The old truncation behaviour was not reproduced.
- One seed, one emitter pin; mixed lanes.

REF GH #16. Related: `6726613746` (A3-151), `6726592523` (A3-150). Corrects my own false regression claim from earlier in this turn.