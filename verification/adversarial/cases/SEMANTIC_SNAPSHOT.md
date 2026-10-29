# Semantic snapshot content (V0 set 17 — v2 host grant, read path)

All observations via `pep.ps1 session --jsonl` (v2, OCaml in-process
session) from base `805062b`. Tool library exposes snapshot-derived
scalars; target program: `fn a() -> Int { return 1 }` +
`fn main() -> Int { return a() }` with
`semanticTarget = {document, revision, entryFunctions: ["main"]}`.

## Snapshot contents are accurate and queryable through tools

| probe | observed |
|---|---|
| `length(snapshot.functions)` via validated tool | `TESTED` — `Validated` with expect `2` (`[a, main]`) |
| `length(snapshot.roots)` | `TESTED` — `Validated` with expect `1` (host-supplied entry `main`; callee `a` is not a root) |
| `length(snapshot.calls)` | `TESTED` — `Validated` with expect `1` (the single `main → a` call edge) |

The call graph, roots and function inventory in the host-authorised
snapshot match the target source exactly as specified
(TOOL_PROTOCOL_V2.md: roots = top-level calls + supplied entries;
constructors/builtins are not edges).

## Grant-target validation is strict

`entryFunctions: ["nope"]` (unknown in target revision) →
`TESTED`: validation `rejected`,
`PEP_SEMANTIC_ROOT_NOT_FOUND` ("Host entry function does not resolve
in the target revision"). Forged or mistyped entry points cannot mint
a grant (complements G-set: ungranted use is a runtime error).

## Status

No findings. The snapshot read path is accurate and the grant boundary
rejects unknown entries. Full `ProgramInfo` record transport (returning
the whole snapshot as a typed value) was not exercised — scalar
projections cover the correspondence; the v2 record machinery itself
is already covered by the V-set.
