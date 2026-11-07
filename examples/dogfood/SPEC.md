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

## Command a user runs (exe-direct native contract, per A1 grant answer)

There is no `run-c23 --grant-file` CLI and none is requested: A1 ruled that a
new CLI would be a new ABI, out of scope for this mission. The contract is the
compiled exe run directly with the granted file as argv[1], once A2 lowers
`main(source: SourceBytes)`:

```powershell
./pepin-source-scan.exe examples/dogfood/input_ascii.pep
# expected: 23 (in A2's native reporting convention, as exercised by A2's probe)
```

The runs-app binary does NOT exist yet (Blocker B stands); line-scan reached
native PASS under exactly this contract (A2 receipt 47, A3-034 gate). Pinned
source SHA + this SPEC remain the implementation target. A3 pre-registers
predictions from this file before seeing native outputs.

## Line-scan (second program, LUCY-20261107-008 Q3)

`pepin-line-scan.pep` counts LF bytes (value 10) over the same granted
`SourceBytes` input and returns the count as `Int`. Same predicates, grant
path and output contract as the runs program; `pepin-source-scan.pep` is
untouched (still frozen at `874cc02`). Deliberate shape: filled `then`,
empty `else` — the branch direction A3 proved builds (`empty_else.pep`
exit 0); no empty-`then` idiom. Native proof now exists: A2 receipt 47
FULL NATIVE VERTICAL PASS, A1 integrator repro on 86ff953, A3-034 gate
39/39 PROVEN (five real files, strict Clang+GCC, both assembly orders).

Confirmed native results on the identical fixtures: input_ascii 3,
input_nonascii 5, input_empty 0, self 39 (line_scan_gate_034.py, A3-034).
A3-040 extended the gate to 49/49: line-scan self (998 B -> 32) and a
NUL-sensitive edge (9 B, 2 NULs -> 3 LFs), plus fact gates M4/M5/M6
(M1-M3 N/A: line-scan carries zero cross-chunk call facts). Six files,
both compilers, both assembly orders, independent oracle.
Consumer: pair identifier-runs + line count per file as one documented
user task. Single-unit `check`: valid, 4 fns, 0 diagnostics (this branch).

## Checkout guard

`examples/dogfood/.gitattributes` pins `*.pep text eol=lf` so Windows
checkouts measure the committed bytes (A3 BOOT-A3-025 point 6: 1198 vs
1159 bytes). Scoped to this lane; no repo-wide attribute change.

## A4 grant question — ANSWERED by A1 (no action open)

A1's explicit grant answer: host entry is `open_bytes(name, bytes)` with
`entryFunctions: ["main"]`; native entry is the `pep_source_data` grant
wrapper with the exe run direct on the granted file path.
`fn main(source: SourceBytes) -> Int` plus `byte_at`/`byte_length` stands
as the lowered entry; no narrower request shape needed, no new CLI/ABI.
