# A2 lexer driver at `cf02095` — independent seed-oracle differential: 5/5 claims hold, including CRLF, tab and 4-byte UTF-8 positions

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slice 3: "test Agent 2's existing scanner **and subsequent driver** against the accepted reference lexer") · **Evidence label:** `TESTED`
**Target:** `codex/a2-bounded-emission` @ **`cf020959bc3797e4810bfe854b4258cae9c52531`** ("source-backed lexer driver with canonical token shape and seed error codes"), pinned detached worktree `D:\Projects\wt-a3-a2-cf02095`, clean, untouched.
**Instrument:** `verification/probes/a2_driver_vs_seed.py` (new). **Oracle: the OCaml seed**, deliberately not the canonical Pep lexer — A2's own suite already compares against `examples/pep_lexer.pep`, so using the seed makes the two oracles independent of each other.

## Result — `SUMMARY cases=5 claim_falsified=0`

| case | claim | measured |
|---|---|---|
| **E1** | error-code **and** byte-offset parity where the seed reports a lexer diagnostic | `crlf_positions`: `PEP_UNEXPECTED_CHARACTER@19` both sides · `tab_positions`: `@9` both · `utf8_4byte_unexpected`: `@0` both · `utf8_ident_unexpected` (`café`): `@7` both · `unterminated_escape_eof` / `unterminated_string`: `PEP_UNTERMINATED_STRING@0` both · `newline_in_string`: `PEP_NEWLINE_IN_STRING@0` both · `int_range`: `PEP_INT_LITERAL_RANGE@0` both · `invalid_utf8`: `PEP_INVALID_UTF8@8` both. **HELD** |
| **E2** | sources the seed accepts lex cleanly in the driver | `nul_mid_string` (`say("a\0b")`): seed valid, driver `ok`, kinds `identifier/symbol/string/symbol/eof` · `comment_after_program`: seed valid, driver `ok`, comment emits no token. **HELD** |
| **E3** | driver `errorLine`/`errorColumn` equal the seed's at the same offset | **CRLF `2:9`** (not 1:20), **tab `1:10`**, `1:8` for `café`, `1:9` for the invalid UTF-8 byte. Column semantics match the seed exactly, including a `\r`-bearing line. **HELD** |
| **E4** | refusals that belong to a *later* stage must not surface as driver errors | `x # trailing` → seed `PEP_UNKNOWN_VARIABLE` (checker) but driver `ok`; `x _ = "s\0" ?n # gone\n99` → seed `PEP_PARSE_EXPRESSION` but driver `ok` with `identifier, hole, symbol, string, hole, integer, eof`. The driver stays a lexer. **HELD** |
| **O1** | observation | bare `?`: seed `incomplete` (typed hole), driver `ok` with a `hole` token — recorded, not claimed, because `incomplete` is a front-end state rather than a lexer verdict |

The three position cases are the ones I most expected to break: `crlf_positions` advances a line boundary
with `\r\n`, and a naive implementation reports column 20 on line 1 instead of `2:9`. A2's driver agrees
with the seed to the byte.

## What this does and does not say

- It says the driver's **error contract and position accounting** agree with the seed on every
  adversarial input I could construct: CRLF, tabs, 4-byte UTF-8, non-ASCII identifier bytes, invalid
  UTF-8 mid-file, unterminated string, unterminated escape at EOF, newline in string, integer range,
  comment at EOF, NUL inside a string, and mixed comment/hole sources.
- It does **not** re-verify A2's token-shape claim against the canonical lexer (their own test does
  that) and it is not a proof of general equivalence: 14 fixtures, one pass, one pin.
- It is not acceptance: no frozen gate was executed for this receipt.

## Honest scope and controls

- Non-vacuity: every E1 fixture produced a real seed diagnostic of the expected family; every E2/E4
  fixture produced tokens, so "driver ok" is not an empty run. A harness error exits 2 and cannot read
  as a pass.
- Two of my own reporting defects were fixed before recording: the first version counted
  `seed=invalid (parser/checker) + driver ok` rows as silently-passing E2 cases with no explicit claim,
  and it lacked a valid-source comment fixture. Both were corrected (E4 added, `comment_after_program`
  added) rather than left as quiet gaps.
- The seed's first-diagnostic only is read, matching the front end's first-error semantics.

## Reproduce

```powershell
python verification\probes\a2_driver_vs_seed.py D:\Projects\wt-a3-a2-cf02095    # exit 0
```

## Next action

Reported to A2 on #16 as the driver verification, with the regression set (P1–P5, S1–S4, E1–E4) to keep
green through the next slice. A1's combined successor of `8396b63` is still the gate for the frozen Full.
