# pepin-source-scan — A4 SPEC (dogfood application, grammar-truth lane)

Owner: A4. Exclusive path: `examples/dogfood/`. No checker, emitter,
protocol, budget, CURRENT, manifest, master, Studio, or Watchtower changes.

## Program

`pepin-source-scan.pep` counts **identifier-start runs** in the granted
`SourceBytes` document and returns the count as `Int`.

- Identifier-start := single byte where `ascii_letter(byte)` is true.
  Predicates are verbatim from `examples/pep_lexer.pep`:
  `ascii_letter` = `A-Z / a-z / _`; `ascii_digit` = `0-9`;
  `ascii_continue` = letter or digit.
- New run := start byte at offset 0, or previous byte is NOT
  `ascii_continue`. No tokenizer state beyond `(n, o)`; no heap, no FFI.
- Non-ASCII bytes (e.g. UTF-8 continuation/emoji) never start or continue
  a run. Empty input returns 0.

`check` on `spec/agent4-spec-lab@712e549` base: **valid, 4 functions,
zero diagnostics** (ascii_letter:0, ascii_digit:1, ascii_continue:2,
main:3). Plain `run` without a host grant produces no count (exit 0, no
output) — the granted `SourceBytes` entry needs the A1 host grant / A2
native build, which is outside the A4 lane. This byte-count/scan distinction
is Dimensional: this program reports run counts, not a token stream; do not
cite it as a full lexer.

## Fixtures (real files on disk, independent Python reference)

Reference: byte-identical predicates over `read_bytes()` (see receipt).
Provenance: size in bytes + sha256-8 below, at the committed revision.

| file | bytes | sha8 | expected runs |
|---|---|---|---|
| `examples/dogfood/input_ascii.pep` | 168 | 7269de34 | 23 |
| `examples/dogfood/input_nonascii.pep` | 218 | bb82fc6f | 30 |
| `examples/dogfood/input_empty.pep` | 0 | e3b0c442 | 0 |
| `examples/dogfood/pepin-source-scan.pep` (self) | 1159 | f6e8f942 | 139 |

`input_ascii.pep`: ordinary ASCII Pep (identity/negate/main → 42).
`input_nonascii.pep`: comment + string with `Grüße`, `héllo`, `🎉`
(2-byte, 4-byte sequences); letter bytes inside identifiers still count,
all bytes ≥ 128 do not. `input_empty.pep`: 0-byte edge case.

## Explicitly unsupported

- Token text/kinds/positions: not returned (Int-only output contract).
- Keywords vs names, strings/comments skipped, digit-start runs: NOT
  distinguished — every `ascii_letter` start counts, including inside
  comments and string literals.
- NUL bytes: no special rule; `byte_at` value 0 is simply not a letter.
- Multi-file/directory walk, output formatting, CLI flags: out of scope
  for this slice.

## Command a user can eventually run

Once A1 wires the grant and A2 lowers `main(source: SourceBytes)`:

```powershell
.\pep.ps1 run-c23 examples/dogfood/pepin-source-scan.pep --grant-file examples/dogfood/input_ascii.pep
# expected: 23
```

Current slice does NOT claim this command works; it defines the contract
A1/A2 implement against (pinned source SHA + this SPEC). A3 pre-registers
predictions from this file before seeing native outputs.

## A4 handoff question for A1/A2 (one line)

Is `fn main(source: SourceBytes) -> Int` plus `byte_at`/`byte_length`
the revision-pinned granted entry you will lower, or do you need a
narrower request shape first?
