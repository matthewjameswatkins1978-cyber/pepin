# Typed-hole lifecycle: query, preview, apply, reject (V0 set 9)

All observations via `pep.ps1 session --jsonl` (schema v3, OCaml
in-process session) from base `805062b`. Program under test:

```pep
fn double(n: Int) -> Int { return ?calc }
fn main() -> Int { return 0 }
```

## Query: hole identity, scope, expectation, bindings

`query` returns one hole: identity object `{document, revision, scope: "double", name: "calc"}` (structured, not a bare string),
`expectedType: Int`, visible bindings `[n: Int]` (parameter in scope).
Status `incomplete`. Matches the A4 arm-local typed-hole contract at
the session layer (S3 covered the match-arm case; this is the
function-parameter case).

## H1 — preview of a valid fill: checked, not applied

`fill_hole(scope=double, name=calc, replacement="n + n", mode=preview)`
→ `TESTED`: outcome `ok`, candidate status `valid`. Current revision
unchanged (`baseRevision == currentRevision`); a distinct candidate
revision is returned alongside a byte-exact `sourceDiff`
(`startByte 34, endByte 39, removed "?calc", inserted "n + n"`).
Preview is pure: analysis without mutation.

## H2 — preview of a mistyped fill: rejected with diff

`replacement="true"` for the `Int` hole → `TESTED`: outcome
`rejected` (not `ok`). The response still carries the would-be splice
diff, but no candidate is adopted and the document is unchanged.
Type-incorrect suggestions cannot sneak in through preview.

## H3 — apply of a valid fill: advances, empties holes

`mode=apply` with `"n + n"` → `TESTED`: outcome `ok`, status `valid`,
current revision changed, `holes: []`. The hole is gone and the program
is complete.

## H4 — stale-revision fill: rejected

`expected_revision` forged (`sha256:000…0`) → `TESTED`: outcome
`error`, `PEP_STALE_REVISION` ("Structural edit expected a revision
other than the document's current revision"). Same guard family as R1
(`apply_edit`), now covering the hole path — no forged-revision fills.

## H5 — unknown hole name: rejected

`scope=double, name=nope` → `TESTED`: outcome `error`,
`PEP_HOLE_NOT_FOUND` ("No named hole matches the supplied scope and
name"). Hole identity is document+revision+scope+name; names do not
resolve globally or across revisions.

## Status

No findings: the hole lifecycle is fail-closed at every transition
(preview checks, apply validates, stale/forged/unknown rejected with
dedicated codes). The A13 Pep-written checker + session hole paths
remain `NOT_RUN`/`BLOCKED_SECURITY`; only the OCaml seed path is
covered here.
