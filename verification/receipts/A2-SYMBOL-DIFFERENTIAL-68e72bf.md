# A2 symbol scanner independently differential-tested at `68e72bf` — byte set, munch, Unicode refusal, EOF/CRLF all match the seed; the escaped-NUL gap persists

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slice 3: ambiguous operators, comments, named holes, EOF, CRLF, Unicode boundaries) · **Evidence label:** `TESTED`
**Target:** `codex/a2-bounded-emission` @ **`68e72bf`** ("feat(stdlib): seed-exact punctuation and operator scanning"), pinned worktree `D:\Projects\wt-a3-a2-68e72bf` (detached, clean, untouched)
**Instruments:** `verification/probes/a2_symbol_differential.py` (new), `verification/probes/a2_scanner_differential.py` (unchanged, re-run for currency)

## Method — the seed's lexer as a context-free oracle

The seed lexes before it parses, so a single unexpected byte is reported as
`PEP_UNEXPECTED_CHARACTER` whatever the grammar context, while a genuine token produces a
parse/checker/type diagnostic instead. Feeding one byte per document therefore yields a per-byte
verdict with no reconstruction of the reference lexer: `UNEXPECTED` (not a token), `TOKEN`, or one
of the classes another scanner owns — `HOLE` (bare `?`/`_`, status `incomplete`), `STRING`
(`PEP_UNTERMINATED_STRING` for `"`), `CLEAN` (`#` comments to end of line). The scanner side runs
`scan_sym_at`/`scan_sym_count` as registered v2 tools with the payload as the semantic target.
Nothing on either side is assumed; the expectations are derived from the measured seed classes.

## Result at `68e72bf` — 5 claims hold, 0 falsified

| case | claim | measured | verdict |
|---|---|---|---|
| **P1** | per-byte acceptance parity over all 32 printable non-alphanumeric bytes | scanner accepts exactly the seed's TOKEN bytes with the right one-byte text, refuses every `UNEXPECTED` byte (`$ % ' < > @ \ ^ \` ~`), and leaves `?`/`_`/`"`/`#` to the hole/string/comment scanners | **HELD** |
| **P2** | the seven two-byte forms are single tokens on both sides | `<= == != && || -> =>` each accepted in a real program position with no `PEP_UNEXPECTED_CHARACTER` (all seven programs check **valid**), and the scanner reports exactly those two bytes | **HELD** |
| **P3** | no over-munch across a separator | `- >` → scanner `-`, width 1; the seed refuses the lone `>` — munch is pair-exact, not greedy across whitespace | **HELD** |
| **P4** | refused multi-byte characters are named whole | `é` (2 B), `€` (3 B), `😀` (4 B) each refused with `text` equal to the whole character and `byteLength 0`; a truncated `€` (2 of 3 bytes) refuses with empty text instead of raising `PEP_RUNTIME_BYTE_BOUNDARY` | **HELD** |
| **P5** | EOF and CRLF | an offset at end-of-source refuses (`Pep scan found no symbol at the end of the source`) with `byteLength 0` and no consumed byte; `scan_sym_count("(\r\n)\t{\n}")` = **4** symbols, offset 8 — CR/LF are separators | **HELD** |

Interpretation for the boundary claims: A2 refusing `?`, `#` and `"` in a *symbol* scanner is correct
behaviour, not an omission — the seed itself routes those bytes to hole, comment and string scanners.
The claim asserts that routing explicitly so a future "fix" that starts claiming them would fail.

## Currency re-run of the earlier scanner differential (unchanged probe)

`a2_scanner_differential.py` at `68e72bf` → **`claim_falsified=1`, 4 held**:
Int64 max accepted / max+1 refused (seed agreement), negative offsets refuse without raising, escape
set parity (`\n \t \\ \" \0 \r` accepted, `\a \x41` refused, decoded content and literal width equal
to the seed). The one falsification is the previously recorded **escaped-NUL position gap**: `"\0ab"`
and `"ab\0"` still return identical `parts`/`nulCount`/`byteLength`/`nextOffset` while the seed's
decoded bytes are `00 61 62` vs `61 62 00`. So the new punctuation work did not regress the scanner,
and the disclosed NUL gap is unchanged rather than worsened — still A2's to close (position-carrying
fragment, or a documented token-compatible-not-equivalent claim).

## Own-instrument corrections (disclosed before recording)

The first version of this probe classified the seed's `"valid"` status as `COMMENT`, which also
labelled seven *valid* programs as comments and would have made P2's seed check vacuous in a
misleading way; and it initially lumped `"` with symbols, which would have scored A2's correct
refusal as a defect. Both were fixed before any result was recorded — by measuring the seed's actual
per-byte classes first and then shaping the claim around them, not by adjusting the expectation to
the outcome. Every edit was Threadmoth `edit` with `expect_count 1`.

## Honest scope

- Byte-level and single-token claims only. No driver-level token stream exists yet on this pin
  (`scan_sym_count` is the consumer-shaped entry), so comment/name/string/hole *sequencing* over a
  whole source is out of scope here.
- Comments are covered as "the scanner must not claim `#`"; the canonical comment scanner's own
  contents are not re-verified in this slice.
- One pin, one pass; no bisection of when the NUL gap appeared beyond the earlier `9d4ab42` reading.

## Reproduce

```powershell
python verification\probes\a2_symbol_differential.py   D:\Projects\wt-a3-a2-68e72bf     # exit 0
python verification\probes\a2_scanner_differential.py  D:\Projects\wt-a3-a2-68e72bf     # exit 1 (S5 disclosed gap only)
```

## Next action

Sent to A2 on #16: P1–P5 are the regression set to keep green through the driver work, and the NUL
position close is the one open item. If a driver lands, my next step is a token-stream differential
(names, numbers, strings, comments, holes, operators) against the reference lexer on real sources.
