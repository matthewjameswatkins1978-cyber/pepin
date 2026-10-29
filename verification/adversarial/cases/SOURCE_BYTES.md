# SourceBytes + byte builtins via host grant (V0 set 13 — A10 surface)

All observations via `pep.ps1 session --jsonl` (v2, OCaml
in-process session) from base `805062b`, except where noted.
Tool library: byte readers over `source_bytes()`; target program:
`fn main() -> Int { say("h\u00e9llo") return 0 }` (44 bytes, `é` =
bytes 25–26, `0xC3 0xA9`). The grant is a v2 `semanticTarget`
`{document, revision, entryFunctions: ["main"]}` naming the retained
target revision.

## G1 — `byte_length(source_bytes())` through the grant

`tool_register(blen)` → `Validated` with vector `[] → 30` →
`Active` → `invoke` → `TESTED`: `{"type":"Int","value":"30"}` = exact
target byte count. Host grants flow end-to-end; byte counts are exact.

## G2 — `byte_at`: unsigned bytes + range fail-closed

`byte_at(25)` → `TESTED`: `195` (`0xC3`); `byte_at(26)` → `TESTED`:
`169` (`0xA9`). Out-of-range (`9999`) validation vector →
`TESTED`: `rejected` with the true runtime code
`PEP_RUNTIME_BYTE_RANGE` ("Byte offset is outside the source").
Unsigned values, exact positions, no wraparound.

## G3 — `utf8_slice`: exact slices convert, splits trap precisely

`utf8_slice(25, 27)` → `TESTED`: `"é"`. Mid-codepoint `(25, 26)`:
validation with a well-formed expect vector → `TESTED`: `rejected`
with the true runtime code `PEP_RUNTIME_BYTE_BOUNDARY` ("UTF-8 slice
boundary splits a UTF-8 sequence"); the same call through an
already-validated tool at invoke time → `TESTED`: `error`
`PEP_RUNTIME_BYTE_BOUNDARY` with byte span. Both layers report the
real fault, not a generic failure.

## G4 — `byte_slice` splits freely; length observable without `Str`

`byte_length(byte_slice(25, 26))` → `TESTED`: `1`. Raw slicing
(including codepoint splits) is allowed; only `Str` conversion
polices boundaries.

## Validation-vector diagnostics, mapped (TESTED)

Same harness, three controlled mistakes:
- trapping vector + well-formed expect → `rejected` with the TRUE
  runtime code (`PEP_RUNTIME_BYTE_RANGE`, `PEP_RUNTIME_BYTE_BOUNDARY`).
- correct slice + wrong expect *type* (`Int` for a `Str` result) →
  `rejected`, `PEP_TOOL_ARGUMENT_TYPE`.
- correct slice + wrong expect *value* → `rejected`,
  `PEP_TOOL_TEST_FAILED` ("Interpreter result did not match").

Fail-closed in all three cases; the true fault survives where the
vector itself is well-formed.

## Grant boundaries (TESTED where stated)

- `semantic_snapshot()` in ordinary `run` (no grant) → `TESTED`:
  rc 1, `PEP_RUNTIME_SEMANTIC_CONTEXT` ("available only during a
  host-authorised tool invocation").
- A `semanticTarget` must name a retained revision whose entry
  functions resolve: pointing it at an *invalid* target program
  (bare `héllo` bytes) fails validation with
  `PEP_SEMANTIC_ROOT_UNAVAILABLE` ("Entry functions cannot be resolved
  for invalid target source") — TESTED. Grants do not launder broken
  targets. (Whether an invalid-bytes target is usable with empty
  `entryFunctions` was not probed; recorded as untested, not assumed.)
- `SourceBytes` never crosses a tool parameter/result boundary and has
  no ambient lookup (protocol statement, not re-probed).

## Status

No findings. The A10 byte-builtin surface is fail-closed at every
transition probed: exact counts, unsigned bytes, boundary traps with
byte spans, grant-gated host access, validated-then-active tools.
`NOT_RUN`: v2 10,000-node / 1 MiB caps (not stressed); invalid-bytes
targets with empty entry lists.
