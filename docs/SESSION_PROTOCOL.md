# Pep session protocol v3

The OCaml seed exposes a small, in-process JSON Lines session for editors and AI clients. It wraps the existing parser and checker; it does not add another semantic implementation. This is a schema-v3 session contract. Existing file-oriented CLI JSON remains schema v2.

## Launch

```powershell
.\pep.ps1 session --jsonl
```

Send one UTF-8 JSON object per input line. The process emits exactly one JSON response line per request, flushes it, and continues until standard input closes. Requests in one process share one in-memory document store. The session does not write source files or persist snapshots after exit.

## Request envelope

Every request has `schemaVersion: 3` and a string `op`. Unknown versions, malformed JSON, missing fields, and unsupported operations produce a structured error response. A malformed line does not end the session or mutate snapshots.

Supported operations:

- `open`: required `source` string; optional `name` string or null. Returns a generated session-local document ID and the initial revision.
- `query` and `inspect`: required `document` and retained `revision`; optional nonnegative `offset` selects a hole beginning at that original byte offset. Both use the same existing semantic data and include the source-spanned AST, partial checked tree where available, diagnostics, and holes.
- `apply_edit`: required `document`, `expected_revision`, `start_byte`, `end_byte`, and `replacement`. The range is half-open `[start_byte, end_byte)` in original UTF-8 bytes. A successful edit returns the new current revision and its analysis.
- `metrics`: returns session-local `parse_count`, `typecheck_count`, and `cache_hits`.

## Revision and snapshot rules

A revision is `sha256:` followed by the lowercase SHA-256 digest of the exact UTF-8 source bytes. Line endings are not normalized. LF and CRLF therefore retain their distinct byte offsets. An edit that leaves the source bytes unchanged keeps the same content-addressed revision. Document IDs and snapshots live only for the session; older revisions remain queryable until it ends.

An edit must name the document's current revision. Stale revisions, out-of-range or reversed ranges, and byte positions inside a UTF-8 code point are rejected without changing the current revision. Replacement strings must be valid UTF-8. The edit splices the original bytes around the selected range, preserving every untouched byte, including whitespace and line endings. This raw range operation is not yet a compiler-backed structural refactoring.

Named-hole identity is returned as document, revision, scope, and name. A name does not identify a hole globally or across revisions. Query again after every edit; never apply an action derived from an older revision.

## Analysis and cache boundary

The first analysis parses and checks a newly opened source. Repeated requests for an already retained revision reuse its immutable analysis and increment `cache_hits`; semantic query JSON itself remains deterministic. A source edit is analysed with the existing full parser and checker. There is no cross-revision parse or type reuse, dependency graph, or incremental compilation claim. `metrics` is diagnostic instrumentation, not language semantics.

Complete, incomplete, and invalid remain distinct states. Incomplete trees can be queried; the existing interpreter still refuses to run a program with any unresolved hole. This session adds no syntax and does not alter file-oriented command behavior.

## Example

```json
{"schemaVersion":3,"op":"open","name":"example","source":"fn double(n: Int) -> Int { return ?calculation }\n"}
{"schemaVersion":3,"op":"query","document":"doc-1","revision":"sha256:<revision returned by open>"}
{"schemaVersion":3,"op":"metrics"}
```

Use the exact document and revision returned by the process. `doc-1` is illustrative; clients must not assume IDs are stable across sessions.

## Implemented limits and next step

This A2 protocol is in-process and ephemeral. It provides raw byte-range edits, not AST-targeted structural edits; all changed revisions are fully re-analysed. It does not provide persistence, a network service, extension activation, parametric containers, a native backend, or self-hosting. The next work packet is [compiler-backed structural edits](NEXT_PACKET.md).