# Native semantic context: entry-grant review boundary

Status: experimental review candidate, not a tool-protocol change or an
accepted implementation. The OCaml session remains the semantic authority.

## Implemented vertical

`NativeSourceGrant.bind` implements a small part of the A1 entry-grant draft
(`a802290d01dd7d58c3a613f6ece397b1636918dd`). A trusted caller supplies the
explicit `entry-parameter` grant, retained document identity and immutable
retained bytes. The adapter checks the document, exact SHA-256 revision and
65,536-byte cap before emission. It does not open a path or obtain a grant.
`C23Emitter.generate_c23(source_grant=...)` accepts only an explicit
`main(source: SourceBytes)` entry. No CLI option or ambient `source_bytes()`
lowering is added. The generated disposable proof artifact embeds the exact
bytes, so it must not be published with private target content or used as a
reusable session carrier. The existing v2 `semanticTarget` wire schema is
unchanged; `sourceGrant` belongs only to this experimental host adapter.

Strict C23 test vectors include NUL, CRLF, UTF-8, malformed UTF-8, empty and
maximum-sized bytes, stale revision, missing grant and foreign document. A
real seed differential is present but requires a working PowerShell/OCaml
environment. Hand-authored checked IR is used for the portable native gate;
it is not a claim of a captured seed report.

## Remaining seam for the complete lexer

The existing lexer uses both `semantic_snapshot()` and `source_bytes()`.
The seed owns reserved `ProgramInfo`/`FunctionInfo`/`CallEdge`/
`SemanticDiagnostic` definitions and their negative checker IDs, but
`typed_json` currently exports only source-declared record/union layouts.
Do not reconstruct the missing facts by parsing source or reading a second
file. Extend the checked report with seed-authored reserved layouts, and
obtain the immutable `ProgramInfo` and bytes from the *same* retained
`session_semantic_target` result. An explicit native entry should receive
the snapshot and byte view as arguments; no global grant, new ambient file
read or weakened target validation. The existing source-facing lexer
wrappers can delegate to these explicit core entry functions, continuing
to use the seed's v2 tool protocol.

An end-to-end native tool carrier additionally needs checked typed transport
for the cursor and result, session-selected revision validation, no `say`,
128 tool-call depth and the seed's 100,000-step accounting. The plain native
512-depth guard is not tool-budget parity. Compare the real chained lexer
on identical target revisions (including invalid/retained older targets)
before adopting a carrier. This prototype deliberately does not claim
those guarantees or complete native lexer execution.

The builder's preceding full discovery at `71e5aa8` reported 30 failure
entries reproduced on `fe91cd9`: 29 staged A13 and one staged A14 step-limit
failure. Preserve these as red evidence, do not waive, reclassify or raise
budgets. Reconcile with the exact Windows oracle after integration.
