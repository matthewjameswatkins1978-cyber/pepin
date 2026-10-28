# Pepin Compiler Campaign Checkpoint

**Date:** 2026-10-28
**Repository:** `matthewjameswatkins1978-cyber/pepin`
**Branch / verified code SHA:** `campaign/pep-v01-sustained-build-20261027` / `cf764d9888c4175b2126ae1bdaad16ab4ac098b5` (remote-equal; test-only commit after checker SHA below)
**Verification test head:** `cf764d9888c4175b2126ae1bdaad16ab4ac098b5` (remote-equal)

## Baselines and authority

- Accepted A12 parser base: `69a47fe77187666bdd045b8dc8a9f633a7dd49d7`.
- A13 review baseline: `7647ec4b6dc875745d883d82db25390b20c1c616`; PR #12 remains a separate draft review line. Lucy's review holds any claim that A13 `valid` is a complete semantic certificate.
- The campaign branch is the single active implementation line. No merge, `master`, release, `CURRENT.md`, or manifest update is authorized.
- Production truth remains the OCaml 5.5.2 seed. The project switch is `pepin-5.5.2` through `PEPIN_OPAM_ROOT`; a plain default-root opam query can select another installation.

## Verified implementation and evidence

The isolated Pep-written A13 checker resolves lexical names and function calls; checks scalar expressions, two-level primitive lists, nominal record fields and record-valued union payloads; and retains named-record payload types in constructor-pattern bindings. It checks the implemented scalar-payload pattern subset, contextual match and if-expression result types, typed holes, wrong-union patterns, duplicate constructor arms, exhaustiveness and unreachable arms after wildcard/binding catch-alls. Empty lists require a supported contextual `List[T]` type or receive OCaml-matched `PEP_EMPTY_LIST_NEEDS_TYPE`. Built-in type names cannot be redeclared, and functions cannot reuse builtin or constructor names. Deeper recursive nominal/union graphs, nested constructor patterns, broader patterns, aggregate equality, assignment and `for-in` remain unsupported or unverified. Non-Unit return validity is reported only when the current bounded block/if analysis proves coverage. The checker does not replace the OCaml production checker.

At checker code SHA `3dcd88b47fc016f9649eb5b310ed14f7bf6f38d6`, tested with the committed test source at `0346120f93aab874587612b7f935d78db3d7ce67`, `python -m unittest tests.test_a13 tests.test_a13_nested_records -q` passed **33/33** in 79.143 seconds. This is 29 A13 checker tests plus four nested-record/list tests. Ten if-expression fixtures compare status, exact diagnostic codes/spans and typed-hole expectations with OCaml across returns, annotations, function arguments, list elements, record fields and branch mismatches. Four minimal record-field match-with-hole variants still return `PEP_RUNTIME_STEP_LIMIT`; the 100,000-step budget is unchanged. The earlier 32/32 attribution to the older `7533f4c` candidate is superseded: replaying that stale checker against newer nested-list mismatch cases exposed three expected failures, while the current `3dcd88b` checker passes the exact branch suite. The existing `_build/ocaml/pep.exe` provided the OCaml CLI oracle. No clean OCaml rebuild or full repository suite was run.

### Latest fail-closed differential follow-up

At checker/test SHA `3d6484a419de2dd82aa6ca7c9047ff0c769988eb`, `python -m unittest tests.test_a13 tests.test_a13_nested_records -q` passed **33/33** in 85.415 seconds. The strengthened gate compares exact diagnostic codes and byte spans with OCaml for wrong record fields, constructor payloads, if/while conditions, builtin arity and builtin argument types. It exposed an extra `PEP_LIST_UNTYPED` after `length()` already failed arity; Pep now skips list-specific validation for wrong-arity calls, matching OCaml's single `PEP_ARGUMENT_COUNT`. Statement-if and while holes match OCaml's `Bool` expectation and byte spans; candidate and visible IDs resolve to the scoped `Bool` parameter. The four record-field match-with-hole variants still hit the unchanged 100,000-step ceiling. This run predates the current uncommitted structural type-shape edits in `tests/pep_checker_a13.pep` and `tests/test_a13_nested_records.py`; those edits are not part of SHA `3d6484a` or its evidence. `git diff --check` passed; no clean OCaml rebuild or full repository run was performed.

## Remaining risks and next action

A13 remains partial and unaccepted. Recursive nominal/union relationships, nested constructor patterns, broader patterns, complete control-flow analysis and the checked-program contract remain unfinished. Four minimized record-field match-with-hole variants still hit the unchanged 100,000-step ceiling, so their hole facts remain unverified; do not increase the budget. The reviewed fail-closed gate remains required until each rule is independently implemented and differentially tested. Verification commit `3d6484a` was remote-equal when tested. The current checkout contains uncommitted structural type-shape edits in `tests/pep_checker_a13.pep` and `tests/test_a13_nested_records.py`; preserve and review them before relying on or extending that slice.

## Latest continuation state — 2026-10-28

The latest branch head is `cf764d9888c4175b2126ae1bdaad16ab4ac098b5`, a C23 CLI test-only commit after checker SHA `ca1f5a0cfdcc30178f5cf979fe7eab765d8a6c33` (`perf(checker): reuse function result shapes`). The A13 diagnostic integration `facc4a34f1e3d60d13a0d3a66abb995d3f610f87` is an ancestor; its list-return `PEP_TYPE_MISMATCH` correction remains present.

On checker SHA `ca1f5a0cfdcc30178f5cf979fe7eab765d8a6c33`, `python -m unittest tests.test_a13 tests.test_a13_nested_records tests.test_a14_c23.A14C23EmissionTests.test_native_bool_helpers_compose_with_direct_returns -q` ran **43 tests**: the A13 and nested-record/list suites passed **42/42**, while the added A14 case failed with `PEP_RUNTIME_STEP_LIMIT` at emitter position `3804:5`. At branch head `cf764d9`, `python -m unittest tests.test_c23_cli -q` passed **4/4** in 12.444 seconds, including GCC native CLI execution. No clean OCaml rebuild or full suite is implied.

A reduced resource probe found that A13 accepts `negate(negate(false))`, a direct call to either helper, and an unused extra helper, but the valid program `identity(negate(false))` with separate `identity` and `negate` helpers returns `PEP_RUNTIME_STEP_LIMIT` at checker bundle position `2766:15` on `0d88524`. After the `ca1f5a0` function-result-shape optimization, the same A14 case still exceeds the existing limit at emitter position `3804:5`. The 100,000-step budget is unchanged. Root cause is not yet established; repeated `lookup_node` scans during type inference are a concrete candidate, not a measured attribution.

The main checkout has one uncommitted C23 regression test in `tests/test_a14_c23.py`; preserve it. `tests/test_c23_cli.py` was committed at `cf764d9` and passed 4/4. An earlier A14 suite run at pre-optimization base `fe1b24d` passed 11 tests and failed the nested-helper case with the same `PEP_RUNTIME_STEP_LIMIT`, so the failure predates the latest optimization and is not evidence of a new regression.

Next action: profile/reduce the A13 two-distinct-helper nested-call case on a stable snapshot, identify repeated work, and optimize a narrow checker path without changing semantics or budgets. Then rerun the exact reproducer and A13/nested-record regression suites. A13 remains experimental and unaccepted; no merge, master, `CURRENT.md` or manifest advancement.
