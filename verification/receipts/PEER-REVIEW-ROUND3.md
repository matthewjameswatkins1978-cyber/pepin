# Peer review round 3 — A2 `62885b8` emitter source read (Agent 3)

**Reviewed pin:** `codex/bootstrap-agent2-b0@62885b861e3f440b2efc5bbd9ebf24e9b6611d6e`
(diff `52f1b38..62885b8`, read-only). No Agent 2 files modified.
Behavioral re-run of this pin's suite already recorded 3/3 PASS in
`PEER-REVIEW-ROUND2.md`; this file covers the source read.

## What changed (source)

Record values across function boundaries: `pep_c23_c_type` (scalar else
declared-record typedef by Pep type name), `pep_c23_record_type`
(type_named + declared + layout-supported), call/parameter cases in
`pep_c23_record_value_type`, field-access passthrough in
`pep_c23_parameter_expression`, zero-arg record calls restricted to
direct record construction, `pep_result` typed via `c_type`, typedefs
and constructions renamed from `pep_record_<id>` to declared names.

## Verdict: narrow no-finding (source-level)

1. Parameter-expression extension recurses only through `field_access`
   bases — projection of a parameter stays parameter-derived. Sound.
2. Call/parameter value-typing resolves through declared, layout-checked
   records; anything else yields `""` → existing `unsupported` paths.
   Fail-closed preserved.
3. Recursion stays rejected on the record path: a recursive callee's last
   value has kind `call`, never `record`. Mutual recursion likewise
   fails the direct-construction requirement.
4. `main` must still return `Int` (text-compared); result/param plumbing
   consistently uses `c_type`; typedef and construction names agree
   (both use the declared type name).
5. `List[Point]` and undeclared/named-non-record types map to `""` →
   unsupported. No silent lowering.

## O1 (observation, not a defect): emitted C type names vs C keywords

`pep_c23_c_type` / typedef emission use the declared Pep type name
verbatim. Probed on the OCaml seed (base `805062b`, TESTED):
`type Point` twice → `PEP_DUPLICATE_TYPE` (uniqueness enforced ✓), but
`type int { x: Int }` → `valid`. The staged emitter would therefore emit
`} int;`, which Clang/GCC reject — fail-closed, but with a C-level
diagnostic far from the Pep source, and native confirmation is blocked
under the hold. Suggested owner-side hardening (no patch supplied, A2
owns the file): reject Pep type names colliding with C23 keywords (and
the `pep_` prefix space) at emission time with a `PepC23Emission`
`unsupported` diagnostic. Low severity: single-file scope, C compiler
remains the backstop, unusual names in practice.

## Status

No defects filed. O1 sent to Agent 2 via outbox + #16. Native
compilation/execution of any emitted C stays `BLOCKED_SECURITY`.
