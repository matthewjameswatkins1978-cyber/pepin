# Peer review round 6 — A2 multi-field union payloads `13d7fc3` (Agent 3)

**Reviewed pin:** `codex/bootstrap-agent2-b0@13d7fc3`
("Support multi-field tagged union payloads"; parent `54f1e42` was
round 5). Read-only detached worktree (since removed). No Agent 2
files modified.

## Independent re-run: 11/11 PASS

`python -m unittest tests.test_c23_source_emission -v` — 11/11 in
~17s, including the new
`test_two_payload_union_matches_scalar_and_record_fields`
(two-field payload construction + scalar/record field matching with
interpreter reference `23`). In-memory `emit` + OCaml interpreter only;
no C compiler, no binaries. Native remains `BLOCKED_SECURITY`.

## Source read: narrow no-finding with one test-coverage note

Delta since round 5 is coherent: payloads become per-variant
`struct { T field_N; ... }` members (named by child index, still
`pep_`-prefixed); constructor and pattern arity are matched by count;
multi-binding patterns allow bindings and wildcards with per-arm
binding-name resolution scoped to the arm; general-expression results
still fall through to recursive lowering with fail-closed propagation.

Two points verified beyond the suite:

1. **C evaluation-order guard is sound and correctly scoped.**
   `pep_c23_expression_may_fail` is conservative in the safe direction
   (calls always fallible; pure literals/names never; field/unary/
   binary recurse), and the constructor path rejects *two or more*
   fallible arguments while accepting zero or one — exactly the
   boundary where C's unspecified argument order becomes observable.
   I verified the boundary directly at this pin (in-memory `emit`
   only): `I(f(1), f(2))` → rejected with the dedicated
   "C evaluation order is unspecified" message; `I(f(1), 2)` and
   `I(1, 2)` → emitted. No defect.
2. **Test-coverage observation (low priority, not a defect):** the
   suite's two-payload test uses infallible (literal/record) arguments,
   so the multi-fallible rejection path has no direct test — a future
   refactor could silently weaken the guard without a red test. One
   suggested negative test: a two-call-argument construction expecting
   the `ValueError` above. A2 owns the test file; no patch supplied.

Round-5 backstops reconfirmed unchanged: `pep_invalid_union_tag`
present in the prelude, global constructor uniqueness enforced by the
checker, union-typed record fields still fail-closed at
`pep_c23_record_layout_supported`.

## Verdict

No defects. One low-priority test-coverage suggestion (multi-fallible
rejection lacks a direct test). Native proof of the emitted C still
awaits hold clearance.
