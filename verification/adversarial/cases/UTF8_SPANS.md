# UTF-8 / CRLF / span adversarial set (V0 set 2)

All observations via `./pep.ps1 check <file> --json` from base `805062b`
(OCaml seed, interpreter only). Byte arithmetic verified by hand.

## U1 — non-ASCII identifier byte rejected with byte span

Input (UTF-8): `fn café() -> Int { return Unknown(1) }\nfn main() -> Int { return 0 }\n`

| oracle | result |
|---|---|
| SPEC | identifier charset is unspecified (open detail register); lexer must fail closed, never split the multibyte sequence silently |
| OCAML | `TESTED` — `invalid`, `PEP_UNEXPECTED_CHARACTER` `\195` (first byte `0xC3` of `é`) at bytes 6–7, line 1. Fail-closed with byte span. No finding (spec does not require Unicode identifiers). |

## U2 — CRLF preserved: valid, LF-style lines, byte-exact offsets

Input bytes: `fn main() -> Int {\r\n  return 1\r\n}\r\n` (38 bytes)

| oracle | result |
|---|---|
| SPEC | LF/CRLF style preserved; exact original byte offsets |
| OCAML | `TESTED` PASS — `valid`; `1`-literal span bytes 29–30 (the `\r` at 30 excluded); function span 0–33 (covers `}` at 32); line 2 numbering treats `\r\n` as one break. `\r` bytes participate in offsets (not stripped). |

## U3 — invalid UTF-8 fails closed with byte span

Input bytes: `fn main() -> Int { return \xff\xfe }\n`

| oracle | result |
|---|---|
| SPEC | `Str` is valid UTF-8; invalid source bytes must be diagnosed, not decoded unsafely |
| OCAML | `TESTED` PASS — `invalid`, `PEP_INVALID_UTF8` at bytes 26–27 (exact position of `\xff`), line 1. |

## U4 — multibyte string content: byte-exact literal spans

Input (UTF-8): `say("hé")\n` — `é` is 2 bytes (`c3 a9`), literal is 5 bytes

| oracle | result |
|---|---|
| SPEC | exact original byte offsets |
| OCAML | `TESTED` PASS — `valid`; string span bytes 4–9 (quote,h,2-byte é,quote). Multibyte content does not shift spans. |

## U5 — multibyte comment line: line counting unaffected

Input (UTF-8): `# café comment\nfn main() -> Int { return Unknown }\n`

| oracle | result |
|---|---|
| SPEC | comments skipped; later diagnostics keep true line/byte positions |
| OCAML | `TESTED` PASS — `invalid`, `PEP_UNKNOWN_VARIABLE` at bytes 42–49, line 2 (2-byte `é` on line 1 correctly advances the line-2 base offset to 16). |

## E2 — columns are byte-derived (informational, not a finding)

Input (UTF-8): `say("hé"); Unknown\n` (`;` separates statements on one line)

| oracle | result |
|---|---|
| observed | `TESTED` — `Unknown` at byte offset 12, **column 13** (= line-byte-offset + 1). A scalar-based column would be 12. Columns are thus byte-derived, consistent with the byte-exact offsets the acceptance criteria require. Unicode scalar/grapheme column semantics are in the open detail register; no defect claimed. |
| A13 | `NOT_RUN` (Agent 1 owned; their span-differential suites cover ASCII spans) |
| C23 | `BLOCKED_SECURITY` |

## Coverage boundary

No case here executes native code or touches builder-owned files. All
`TESTED` rows are OCaml-seed observations; A13/C23 columns stay
`NOT_RUN`/`BLOCKED_SECURITY` per ownership and the hold.
