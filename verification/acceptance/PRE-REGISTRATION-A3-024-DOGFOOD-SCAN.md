# PRE-REGISTRATION A3-024: independent corpus and predictions for the source-scan vertical

**Seat:** A3 (independent verification / hostile dogfood). Continuation after BOOT-A3-023,
under `LUCY-20261107-004` (dogfood restart), A3 lane only.

**Written and committed BEFORE any measurement of this vertical was run in this session.**
No build, no native execution, no session call had been made against these fixtures at the
time of writing. The predictions below are my own hand tallies from the fixture hex dumps,
not values taken from any builder output.

## What exists, and what does not

Checked before writing this:

- A4's dogfood application is **not published**. `spec/agent4-spec-lab@712e549` contains
  `examples/` but **no `examples/dogfood/` path**, so the mission's app cannot yet be run
  by anyone. Stated plainly rather than assumed.
- The only executable source-scan vertical that exists is the four-function chunked
  vertical: A1 checker `codex/a1-typed-bound-pipeline@a7d3ee1` + A2 emitter
  `codex/a2-bounded-emission@f0bbc12`.
- A2's branch is **not** a descendant of A1's for this purpose: `f0bbc12` *deletes* A1's
  chunk tooling (`pep_chunk_contract.py`, `tests/chunk_helper.py`, `pep_chunk_units.py`
  are all `D` in `git diff --name-status a7d3ee1 f0bbc12`). The measured "four functions at
  A1 a7d3ee1" is therefore a **merged seam**, not a single branch, and A3 must reconstruct
  it cold rather than trust a tree that happens to be green.

This pre-registration therefore targets semantics that already exist and are pinned, so it
is falsifiable **now** instead of blocked on A4. When A4 publishes `examples/dogfood/`,
these predictions are re-pointed at it without renegotiating the numbers.

## Fixed semantics under test

Authority: `examples/pep_lexer.pep` at `a7d3ee1`, blob `12bd93a1dfc5dba3b1cab49abefffed5e406b17d`.

```
fn ascii_letter(byte: Int) -> Bool {
  return (65 <= byte && byte <= 90) || (97 <= byte && byte <= 122) || byte == 95
}
fn ascii_digit(byte: Int) -> Bool { return 48 <= byte && byte <= 57 }
fn ascii_continue(byte: Int) -> Bool { return ascii_letter(byte) || ascii_digit(byte) }
```

`main(source: SourceBytes) -> Int` counts **every byte** `b` with `ascii_continue(b)` over
the whole file, with no exclusion for comments, strings or whitespace.

So the value under test is exactly

```
count = |{ b in file : b in [0x30..0x39] u [0x41..0x5A] u [0x61..0x7A] u {0x5F} }|
```

**Vocabulary discipline.** This is a *byte-class count*, not a lexer, not a token count and
not a "lexical category" breakdown. The gate vocabulary must not inflate it, and A3 will not
accept a receipt that calls it tokenisation.

## Inputs (exact bytes, created by A3, under `verification/fixtures/dogfood-scan/`)

| # | File | Bytes | SHA-256 | Distinct kind |
|---|---|---|---|---|
| F1 | `scan_ascii.pep` | 49 | `1cac438e0867f773f6fa6070565bb4004b1184a861652525faa8a7231714d399` | ordinary ASCII Pep source |
| F2 | `scan_nonascii.pep` | 58 | `325aa1b93655aae260caa81f1e76d2e1c05d794a0ff91473f4d6a34ea035f2f1` | non-ASCII UTF-8 (`é` = `c3 a9`, `→` = `e2 86 92`) inside a string |
| F3 | `scan_empty.pep` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | empty-file edge |
| F4 | `scan_nul.pep` | 31 | `b2ab07189603d6f643330ac11a91d60e274118e33193b781241a8dd2e240a4fd` | embedded NUL (`00`) at offset 18 |
| F5 | `scan_hello.pep` | 19 | `89667a79729f0f170d05de1e9a8b3c4389154c5d0cccc95d10ce9ec7605ca578` | byte-identical copy of real repo file `examples/hello.pep` @ a7d3ee1 (blob `f9b8a285c9afa4a00b87b47ad9421724df5c8b33`) |
| F6 | `scan_punct.pep` | 18 | `cff9abb88eb9488af027e63c233c71f2d55e727f0a8acf2eb31e8905d842ec90` | **non-empty, zero identifier bytes** |

F3 and F6 together are the discriminating pair: a scanner that returns `0` on *failure*
cannot be distinguished from a correct one unless a real, non-empty, legitimately-zero file
must also return `0`. F1/F2/F5 are the three genuinely different real files the first gate
asks for.

## Pre-registered predictions (hand tallies, shown in full)

| # | Tally | Predicted `Int` |
|---|---|---|
| F1 | `fn`2 + `add`3 + `a`1 + `Int`3 + `b`1 + `Int`3 + `Int`3 + `return`6 + `a`1 + `b`1 | **24** |
| F2 | `fn`2 + `main`4 + `Int`3 + `let`3 + `s`1 + `héllo`4 (`h`+`llo`; `é`=0) + `ok`2 + `return`6 + `0`1 | **26** |
| F3 | (no bytes) | **0** |
| F4 | `fn`2 + `main`4 + `Int`3 + `return`6 + `0`1 (NUL contributes 0) | **16** |
| F5 | `say`3 + `Hello`5 + `Pep`3 | **11** |
| F6 | (18 bytes, none in `[A-Za-z0-9_]`) | **0** |

## Pre-registered negative and hostile cases

| # | Case | Requirement | Prediction |
|---|---|---|---|
| N1 | argv path that does not exist | must not report a count | honest refusal (non-zero exit or explicit diagnostic). **Printing `0` is a FAIL** — silent wrong answer |
| N2 | argv path is a directory | must not report a count | refusal, same rule as N1 |
| N3 | no argv path at all | must not report a count | refusal, same rule as N1 |
| N4 | main chunk report with resolved call facts stripped | must refuse at emit | `Pep C23 cross-chunk call has no resolved call fact` |
| N5 | call fact `calleeId` severed to a foreign id | must refuse at emit | `Pep C23 cross-chunk call target is missing from the checked functions` |
| N6 | checked-callee arity forged to 2 for `ascii_continue` | must refuse at emit | `Pep C23 cross-chunk call argument count disagrees with the checked arity` |
| N7 | **anti-hardcode / metamorphic** | one binary, six files | outputs must be exactly `24, 26, 0, 16, 11, 0` — a build that prints a constant fails |
| N8 | revision binding | check a report under a different revision/stamp than the one it was produced on | must refuse (stale/cross-target). If not reachable on this seam, recorded **NOT TESTED**, never "pass" |

N1–N3 accept that the *path-refusal contract* may be previously unspecified: their expected
behaviour is therefore stated as the weakest honest requirement ("must not print a number"),
which holds under every plausible reading. If the binary prints `0` for a missing file, that
is recorded as a real silent-wrong-answer defect, not a missing feature.

## Two independent derivations required

A prediction is only evidence if two derivations that cannot share a mistake agree:

1. the **hand tally** above (fixed in this commit, before execution), and
2. an **independent Python reference** that reads the same bytes from disk and classifies
   them without using any Pep code, the checker, the emitter, or the seed interpreter.

The native binary (Clang strict and GCC strict) must equal both, and the seed interpreter
must equal both over the same byte values supplied as a literal `Int` list (the seed cannot
call `source_bytes()`; that is the authority boundary the earlier probe labelled). Any
disagreement between the two derivations is a **FAIL of the derivation**, not a result to be
averaged away.

## Byte provenance

Every reported value must name the SHA-256 of the exact bytes the binary was pointed at,
and that SHA-256 must equal the table above. A value without provenance is not evidence.

## Failure vocabulary

`PROVEN` = both derivations agree and both strict compilers agree on every row.
`FAIL` = any row differs, any negative control emits, or the binary answers a missing file
with a number. `NOT TESTED` = named explicitly with the reason. No aggregate score hides a
row.

## Scope guard

A3 owns only `verification/**`. This pre-registration does not touch A4's app, A1's
checker/host, A2's emitter, frozen gates, `CURRENT`, manifest, budgets or `master`, and it
does not reopen Candidate7.
