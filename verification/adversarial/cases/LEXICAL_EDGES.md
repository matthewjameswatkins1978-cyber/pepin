# Lexical edges: escapes and non-decimal literals (V0 set 15)

All observations via `pep.ps1 check/run` from base `805062b` (OCaml
seed, interpreter only), plus a read-only source read of the lexer's
escape table in `pep_ocaml.ml` (no files modified).

## Escape set: exactly six, everything else fail-closed

Source-read escape table (lexer): `n → \n`, `r → \r`, `t` → TAB,
`0` → NUL, `\\` → backslash, `"` → quote; any other escaped char →
`PEP_INVALID_ESCAPE` ("Unsupported string escape") at the escape span.

TESTED behaviorally — accepted: `\n`, `\"`, `\0`, `\t`, `\r`, `\\`
(all produce the exact byte); rejected with `PEP_INVALID_ESCAPE`:
`\q`, `\x`, `\u`, `\'`, `\b`, `\f`. No `\uXXXX`, `\xNN`, octal (other
than `\0`) or single-quote escapes exist. The closed set is confirmed
from both directions.

Transport note (measured, not language): `say` appends one `\n` to its
output, and the Windows C runtime translates emitted `\n` bytes to
`\r\n` on the console pipe (raw-byte capture: `a\tb\rc\\d\n` +
say-newline observed as `...\r\n\r\n`). Byte-observant tests must
compare accordingly; the replay lab asserts through text mode and
avoids asserting on raw `\r`.

## Non-decimal integer literals do not exist

`0x10`, `0b101`, `1_000` are not lexed as numbers. The lexer splits
them (`0` + name `x10`/`b101`/`_000`), so the failure mode depends on
position rather than naming the real problem:

- `let v = 0x10` → `TESTED`: `invalid`, `PEP_UNKNOWN_VARIABLE`
  ('x10' at its span) — precise mechanism, confusing code.
- `return 0x10` (after `return`) → `TESTED`: `invalid`,
  `PEP_UNREACHABLE` ("Statement follows an unconditional return") —
  a knock-on diagnostic, same root cause.
- Identical behavior for `0b101` → `'b101'`, `1_000` → `'_000'`.

There is no "unsupported literal" diagnostic; both codes are
position-dependent knock-ons. Fail-closed in all positions (never
mis-parsed as a value), but a future diagnostic could name the actual
issue. Recorded as a diagnostic-quality observation, not a defect.

## Status

No findings. The escape surface is fully mapped (6 in / rest out);
non-decimal literals are absent with fail-closed-but-confusing codes.
A13 parity and native behavior stay `NOT_RUN`/`BLOCKED_SECURITY`.
