# Session edges: invalid bytes, repairable revisions, metrics (V0 set 11)

All observations via `pep.ps1 session --jsonl` (schema v3, OCaml
in-process session) from base `805062b`.

## O1 — `open_bytes` with invalid UTF-8: retained as invalid

`open_bytes` with bytes `[102, 110, 32, 255, 254]` (`"fn \xff\xfe"`)
→ `TESTED`: outcome `ok`, status `invalid`, diagnostic
`PEP_INVALID_UTF8`. Malformed encoding is retained (content-addressed
revision as usual) and reported with a byte span — same fail-closed
shape as file-based U3, now confirmed on the session transport path.

## O2 — breaking edit: invalid revision retained and queryable

Sequence: open `fn main() -> Int { return 1 }\n` (valid) → `apply_edit`
splicing `@@@` at bytes 26–27 → `TESTED`: outcome `ok`, new revision,
status `invalid`. Querying the NEW revision in-session → `TESTED`:
outcome `ok`, status `invalid`, diagnostic `PEP_UNEXPECTED_CHARACTER`.
The invalid revision is a first-class retained revision: re-analysis
runs, diagnostics are queryable, and the caller can inspect and repair
it (per SESSION_PROTOCOL.md: raw range edits "may create an invalid
revision so callers can inspect and repair it"). Repairability is real,
not just documented.

## O3 — `metrics` op: observable instrumentation

`{"op": "metrics"}` → `TESTED`: outcome `ok` with a metrics payload
(`parse_count`/`typecheck_count`/`cache_hits` shape per prior receipts).
Diagnostic instrumentation is queryable; it is not language semantics.

## Status

No findings. These close the session-transport loop left open by the
R-set (which covered rejection) and the H-set (which covered holes):
retention, repairability, and observability all behave per spec.
