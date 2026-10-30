# v2 typed transport + host grants (V0 set 12)

All observations via `pep.ps1 session --jsonl` (schema v3,
`toolProtocolVersion: 2`, OCaml in-process session) from base `805062b`,
plus one ordinary `run`. Library: `type Point { x: Int y: Int }`,
`fn total(xs: List[Int]) -> Int` (sums), `fn getx(p: Point) -> Int`.

## V1 — List transport end-to-end

Register `total` → signature derived; validate vector `[1,2,3] → 6`
(real interpreter run) → `Validated`; activate → `Active`; invoke
`[4,5]` → `TESTED`: outcome `ok`, `{"type":"Int","value":"9"}`. v2
typed lists cross the boundary and compute.

## V2 — record transport, exact field order

Validate `getx` with `Point{x:3, y:4}` (declared order) → `Validated`;
invoke with `{x:7, y:8}` → `TESTED`: `7`. Names, presence and order all
enforced at the boundary.

## V3 — swapped field order rejected

Same fields as `{y, x}` → `TESTED`: validation `rejected`,
`PEP_TOOL_ARGUMENT_FIELDS` ("Record fields must match the declared
names and order"). Order is part of the contract, not cosmetic.

## V4 — `semantic_snapshot` without host grant refused

Ordinary `run` of a function calling `semantic_snapshot()` →
`TESTED`: rc 1, `PEP_RUNTIME_SEMANTIC_CONTEXT` ("available only during
a host-authorised tool invocation") with byte span. No ambient
authority: the grant must come through a v2 `semanticTarget`.

## V6 — nesting depth cap pinned at 16/17

`fn deep(x: List^N[Int]) -> Int` with a matching N-deep value:
N=16 → `TESTED`: validation `ok`; N=17 → `TESTED`: validation
`rejected`, `PEP_TOOL_VALUE_DEPTH` ("Typed tool value exceeds the
nesting limit"). The documented depth-16 boundary is enforced exactly
(one accepted probe each side; an earlier malformed probe that
mismatched inner type labels was correctly rejected as
`PEP_TOOL_ARGUMENT_TYPE` and is not counted).

## v2 host-only surface left `NOT_RUN`

`source_bytes()` / byte builtins need a v2 `semanticTarget` grant
(ordinary `run` cannot mint one); the 10,000-node and 1 MiB caps were
not stressed (depth is the binding documented axis and is now pinned).
The staged `emit` path already exercises v2 `semanticTarget`
authentication in production (see F2).

## Grant identity is pinned too (forged revision, wrong document)

Same grant path, identity attacks instead of entry-name attacks:
forged target revision (`sha256:fff...`) → `TESTED`: `rejected`,
`PEP_REVISION_NOT_FOUND` ("Revision is not retained in this
session"); unknown document id → `TESTED`: `rejected`,
`PEP_DOCUMENT_NOT_FOUND`. Forged, missing, and mismatched grant
identities all fail closed with dedicated codes — completing the
grant-identity side alongside the entry-name case above.

## Breadth budget: `PEP_TOOL_VALUE_LIMIT` at 10,000 decoded nodes

| probe | observed |
|---|---|
| v2 validate, `List[Int]` argument with **9,999** elements (`fn wide(x: List[Int])`) | `TESTED` — outcome `ok` (Validated) |
| same with **10,000** elements | `TESTED` — `rejected`, `PEP_TOOL_VALUE_LIMIT` ("Typed tool value exceeds the element budget") |

One charge per decoded list node (`tool_v2_max_nodes = 10_000` in the
host); boundary exact at 9,999/10,000 — the breadth twin of the
`VALUE_DEPTH` (16/17) probe above. A1's typed-value-ceiling finding
(`PEP_TOOL_VALUE_LIMIT` at scale) now has a pinned protocol-level home.

## Status

No findings: v2 transport is fail-closed at every probed transition
(types, names, order, depth, breadth, host grants).
