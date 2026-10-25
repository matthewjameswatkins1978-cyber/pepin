# Next packet: Compiler-backed structural edits

This packet follows the in-process revision-aware session in [Session Protocol v3](SESSION_PROTOCOL.md), under [Founding Design v0.3](FOUNDING_DESIGN_v0.3.md) and [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md).

## Objective

Add one narrowly scoped, compiler-backed structural edit that targets a semantic or syntax node in a specific document revision. It must reuse the OCaml parser/checker and the existing revision store; raw `apply_edit` remains the lower-level primitive and correctness reference.

## Scope to settle before implementation

- Choose one small edit with unambiguous syntax identity and observable value, such as filling a named typed hole from a current query result.
- Require document ID, source revision, and the complete revision-bound target identity. Reject stale or ambiguous targets without changing the current snapshot.
- Derive replacement boundaries from the parsed source span, preserving all untouched bytes, comments, whitespace, and LF/CRLF bytes.
- Apply through the existing byte-splice operation, then fully parse and check the resulting revision.
- Keep complete, incomplete, and invalid results distinct. Do not execute an incomplete program or claim a refactoring succeeded before validation.
- Keep this milestone in-process. Do not add extension activation, disk persistence, network transport, cross-revision incremental reuse, or new language syntax.

## Acceptance

- A successful operation is bound to the exact current revision and returns old/new revision identities.
- Stale revision, missing target, duplicate/ambiguous target, invalid replacement, or resulting type error leaves the current revision unchanged.
- Untouched bytes and line endings are byte-identical.
- The prior revision remains queryable; the new revision is fully re-analysed by the existing semantic authority.
- Tests compare the structural edit result with the equivalent raw byte edit and a fresh file-oriented parse/check, including UTF-8 and CRLF offsets.
- JSON request/response fields and schema-version behavior are documented; same-revision query determinism and existing OCaml/MoonBit suites remain intact.

## Boundary

This is one compiler-backed edit operation, not a general refactoring framework. Do not add a syntax-node identity that promises stability across revisions. Any returned action remains revision-bound and must be re-queried after an edit.

## Next decision

After the acceptance evidence exists, decide whether another structural edit is justified. Incremental cross-revision analysis remains a separate optimization and requires differential equivalence evidence before it is advertised.
