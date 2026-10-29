# v2 transport exclusions: unions and SourceBytes (V0 set 18)

All observations via `pep.ps1 session --jsonl` (v2, OCaml
in-process session) from base `805062b`. Tool library:
`type E = A(Int) | B()`, `fn first(x: E) -> Int` (match with
`A(v)`/`B()` arms), `fn grab() -> SourceBytes` (returns
`source_bytes()`); target `fn main() -> Int { return 0 }` with a
standard `semanticTarget` grant.

## Registration derives signatures without transport checks

`tool_register` for the union-taking `first` and the
SourceBytes-returning `grab` → both `TESTED`: outcome `ok`, status
`Registered`, signatures derived (`(E) -> Int`, `() -> SourceBytes`).
Registration is name+signature plumbing; it draws no transport
boundary. (Note: the library itself must be *valid* Pep — an earlier
probe draft with bare `B` failed at parse, unrelated to transport.)

## Validation enforces the boundary — nothing excluded can activate

| probe | observed |
|---|---|
| union-typed argument `{"type":"E","value":1}` | `TESTED` — validation `rejected`: "Version 2 supports only scalar, List, and monomorphic record values" |
| union disguised as record-shaped value (`fields:[{name:A,...}]`) | `TESTED` — same `rejected`, same code |
| `grab()` (SourceBytes result) under a valid grant | `TESTED` — validation `rejected` with the same transport error |

Since validation is a prerequisite for activation (T-set: only
`Validated` entries activate), union-typed and SourceBytes-typed tools
can never become callable. The exclusion lives at exactly one gate,
applied uniformly to arguments, disguised shapes, and results.

## Status

No findings. The v2 transport allowlist (scalar/List/monomorphic
records) is enforced as documented; everything else fails closed at
validation with an explicit code. Combined with set 12 (allowed types
work) this completes both sides of the v2 transport contract at the
seed layer.
