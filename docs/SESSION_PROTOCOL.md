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
- `query` and `inspect`: required `document` and retained `revision`; optional nonnegative `offset` selects a hole beginning at that original byte offset. Both use the same existing semantic data and include the source-spanned AST, checked tree where available, diagnostics, and holes.
- `apply_edit`: required `document`, `expected_revision`, `start_byte`, `end_byte`, and `replacement`. The range is half-open `[start_byte, end_byte)` in original UTF-8 bytes. This low-level operation may create an invalid revision so callers can inspect and repair it.
- `fill_hole`: required `document`, `expected_revision`, `scope`, `name`, `replacement`, and `mode` (`preview` or `apply`). The scope and name must identify exactly one current named hole. No caller-supplied byte offset is accepted.
- `metrics`: returns session-local `parse_count`, `typecheck_count`, and `cache_hits`.

## Semantic hole filling

`fill_hole` resolves the named target from the current checked tree, parses the replacement as exactly one Pep expression, splices only the hole's original UTF-8 byte span, then reparses and checks the whole candidate with the existing compiler. The candidate must be valid or incomplete; an invalid candidate is rejected with `candidateStatus: "invalid"` and its structured diagnostic.

A `preview` response includes the candidate revision and status, the unchanged `currentRevision`, and `sourceDiff` with `startByte`, `endByte`, `removed`, and `inserted`. Preview does not advance the document or execute the candidate. An `apply` repeats the expected-revision check and validation, then advances the current revision and returns its semantic analysis. Incomplete candidates are allowed when unrelated holes remain. Stale, missing, or ambiguous targets and invalid candidates leave the current revision unchanged. Previous revisions remain queryable.

The returned hole identity is document, revision, scope, and name. A name does not identify a hole globally or across revisions. Re-query after every edit; never apply an action derived from an older revision.
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

## Implemented session behavior

This session is in-process and ephemeral. It retains immutable revisions, provides raw byte-range edits and revision-bound filling of a uniquely named typed hole, and fully re-analyses changed source. It does not provide persistence, a network service, parametric containers, a native backend, or self-hosting.

## Local tool protocol v1 (A5)

Tool operations use the existing session envelope with schemaVersion 3 and require toolProtocolVersion 1. Every request and response is one JSON object per line. Error responses for tool operations carry the same tool protocol version.

Registration names a tool, document, exact retained source revision, ordinary Pep function, and optional description. The checker derives the function signature. The first boundary accepts only Int, Bool, Str, and Unit parameters and results; records and variants remain internal. Registry states are Registered, Validated, Active, Rejected, and Superseded. Only Active entries are callable.

Validation requires complete checked source, host-policy approval, and at least one test vector executed by the real interpreter. A vector has an arguments array and an expected result, each encoded as a typed value object. Int uses a signed 64-bit decimal string, Bool a JSON boolean, Str a JSON string, and Unit null. Activation is a separate operation and only succeeds for a Validated entry.

A tool invocation resolves the active entry and its immutable document revision. It accepts typed scalar arguments, checks count and types, and returns a typed scalar result. A successful replacement becomes active atomically and marks the prior registration Superseded. An invalid, incomplete, incompatible, or failed replacement does not change the current active entry.

The host exposes no Pep operations for filesystem, network, environment, or process access. It blocks say both through reachable-call validation and an interpreter runtime check. Execution is limited to 100,000 interpreter steps and 128 function-call depth. This is a trusted-local prototype, not a sandbox. Registry state ends with the session process.

A registration and validation exchange has this shape; use the exact revision returned by open or apply_edit:

```jsonl
{"schemaVersion":3,"toolProtocolVersion":1,"op":"tool_register","tool":"fee","document":"doc-1","revision":"sha256:<revision>","function":"calculate_fee","description":"Calculate the fee"}
{"schemaVersion":3,"toolProtocolVersion":1,"op":"tool_validate","tool":"fee","document":"doc-1","revision":"sha256:<revision>","testVectors":[{"arguments":[{"type":"Int","value":"20"}],"expect":{"type":"Int","value":"22"}}]}
{"schemaVersion":3,"toolProtocolVersion":1,"op":"tool_activate","tool":"fee","document":"doc-1","revision":"sha256:<revision>"}
{"schemaVersion":3,"toolProtocolVersion":1,"op":"tool_invoke","tool":"fee","arguments":[{"type":"Int","value":"20"}]}
```

The invocation response contains the active revision and a typed result. tool_list reports each registration's status, callability, signature, description, and activeRevision for its tool name. The placeholder revision above is illustrative; clients must use the exact returned revision.