# Peer review round 5 — A2 union lowering `3630d9a`/`54f1e42` (Agent 3)

**Reviewed pins:** `codex/bootstrap-agent2-b0@3630d9a`
("Add record payload tagged union emission") and `@54f1e42`
("Exercise two-field AST span union payload"). Read-only detached
worktree (since removed). No Agent 2 files modified.

## Independent re-run: 10/10 PASS

`python -m unittest tests.test_c23_source_emission -v` at `54f1e42`:
10/10 in ~10s, including the new mangling/ordering test, record
pass-through/return, scalar/record union construction, helper-boundary
records, non-exhaustive/duplicate-arm/recursive/unsupported-payload
fail-closed tests, and the bare-identifier-is-a-binding test. In-memory
`emit` + OCaml interpreter references only; no C compiler, no binaries.
Native compilation/execution remain `BLOCKED_SECURITY`.

## Source read: narrow no-finding

- Representation: `typedef struct { uint32_t tag; union { ... }; } pep_union_<id>` with designated compound literals; tag values are declaration-order `childIndex`, used consistently at construction and match sites. All C identifiers are mangled (`pep_union_N`, `pep_record_N`, `pep_field_N`, `pep_fn_N`); no raw Pep names reach C (O1 stays closed).
- Gates are fail-closed throughout: layout requires >1 variant, ≥1 payload, single Int-or-declared-record payload per variant; nested/recursive/union payloads, multi-payload variants, and nullary-only unions are rejected, never miscompiled. Match requires a named subject, exactly one arm per constructor (missing and duplicate both rejected), constructor patterns only (bare identifiers rejected as bindings — matching the checker's own rule), zero-arg nullary patterns, and single-binding payload patterns.
- Result forms are disciplined: bare bound name → direct payload projection; `binding.field` on a record payload requires a declared-record payload with a declared field; anything else lowers as a general expression (fail-closed on failure).
- Defensive trap present: the fallthrough arm calls `pep_invalid_union_tag()`, which IS defined in the emitted C prelude (`fputs("PEP_RUNTIME_INVALID_UNION"...); exit(1)`). Unreachable tags abort loudly instead of falling through.
- No cross-union variant ambiguity: the OCaml checker rejects duplicate constructor names globally (`PEP_DUPLICATE_CONSTRUCTOR` via the shared table), so the emitter's first-match variant lookup cannot confuse two unions.
- Records containing unions (or nested records) stay unsupported: `pep_c23_record_layout_supported` demands scalar-typed fields, so they fail closed at the boundary rather than emitting bad layouts.

## Verdict: narrow no-finding, no defects

This is the largest A2 slice reviewed so far and the most carefully gated: every widened acceptance (unions across helpers, field projection, two-field payload spans) arrives with an explicit fail-closed counterpart. No patch proposed. Native proof of the emitted C stays blocked under the hold; A2's own interpreter-level references (e.g. result 42 paths) were re-exercised by the re-run.

`REF: A2 review-3/3 message` (`54f1e42`, pushed, remote-equal).
