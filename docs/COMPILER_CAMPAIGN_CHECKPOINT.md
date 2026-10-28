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


## Continuation 03 — nested helper resource repair (2026-10-28)

This update supersedes the prior checkpoint's unprofiled root-cause hypothesis. The campaign branch advanced to `ec3782964629860ad0d6a24c7b007113aac2119e` while work was isolated. That commit changes `token_at` to return on the requested token rather than scanning the rest of the token list, and adds the exact nested Boolean A13 budget regression. The local implementation was rebased onto that commit before verification.

Implementation and test commit: `ab1f7f01d9511c9b49f1a55a37c775a73152fb0b`. The CLI test source `tests/test_c23_cli.py` has blob SHA-1 `a7d0b449f2771326bf5e40f7c485795b27ceb994`; the resource probe used the exact nested source SHA-256 `58c3734651c51667eb2d304ed9cdc4d08760bb11321fb2c547d0f8ae3ba3d175` (167 UTF-8 bytes). The measured compiler bundle SHA-256 was `c7d2270b726e9eb44eb76e660da632f03e54b1b70c75b74702adccfd97265ad8`.

### Resource evidence and decision

On the same nested-helper program after the parser lookup change, test-only OCaml step instrumentation recorded parser-only `59,964`, checker-only `32,803`, and the A13 combined parse/check path `98,613` steps. The prior parser-only measurement was `65,877`, a reduction of `5,913` steps. The combined A13 path now completes, but has only `1,387` steps of headroom. The monolithic A14 `emit_c23` path still reaches the unchanged `100,001` sentinel. These measurements identify accumulated parser, checker and emitter execution as the boundary; `lookup_node` scans are present but are not alone the cause.

The native CLI now passes the exact typed `ParserProgress` result into `analyze_parsed`, then passes that same parse value and the checker's exact `CheckerReport` into `emit_c23_checked`. The three isolated Pep invocations measured `59,962`, `32,800` and `19,015` steps, respectively, each under the unchanged `100,000` per-invocation ceiling. The Python driver only relays stage results; parsing, semantic checking and C23 emission remain Pep-authored. No token-by-token host round trips, hidden host lexer/checker, budget increase or protocol schema change was introduced. The older one-shot `emit_c23` entrypoint remains available and can still exceed the budget on this case; CLI compilation uses the bounded staged path.

### Verification at implementation SHA

- `python -m unittest discover -s tests -v`: **174/174 passed** in 315.410 seconds. This full-discovery count includes the 11 historical MoonBit tests; those are included once in 174.
- A13 nested-helper regression: passed in full discovery; the source is now parsed and checked under budget on the updated campaign branch.
- A14/C23 and actual `run-c23` coverage: passed in full discovery. The new native regression compares interpreter output with C23 execution under both installed Clang and GCC; both return `42`.
- Fresh OCaml 5.5.2 `ocamlopt` compile and `describe --json`: passed; the report still declares `maxSteps=100000`.
- `python -m py_compile pep_c23.py tests/test_c23_cli.py`: passed. `git diff --check`: passed before the checkpoint append.
- Test-only profile run emitted all 52/52 expected profile records. It is instrumentation evidence, not an isolated CPU or memory benchmark.

### Boundaries and next work

A13 remains experimental and unaccepted. The exact A13 combined nested case is close to the budget, larger variants such as a nested relay and two-argument helpers still reach the runtime step limit, and the monolithic A14 tool path can still fail where its individual stages pass. The practical improvement is limited to the staged native CLI route and the measured A13 case; no broad large-program guarantee is established. There are no new semantics, `CURRENT.md` or manifest changes, merges, or master updates. The main checkout's unrelated uncommitted A14 test remains untouched.

## Continuation 03 — mutable assignment typing (2026-10-28)

**Implementation and test SHA:** `cc6a6d8916b35d66f892017e95b6c65a3f4d106e` (pushed to the campaign branch). The A13 checker now resolves assignment targets through the existing lexical binding and semantic identity tables. It accepts type-correct writes to `var`, rejects writes to `let` bindings and parameters as `PEP_ASSIGN_IMMUTABLE`, reports unresolved targets as `PEP_UNKNOWN_VARIABLE`, and checks RHS type names and structural shapes. Nested-list mismatches point at the offending leaf. Assignment context supplies expected types to empty lists and holes. `for-in` remains fail-closed as unsupported.

Verification at the exact implementation/test SHA: `python -m unittest tests.test_a13 tests.test_a13_nested_records -v` passed **44/44** in 112.651 seconds; the assignment differential test compares 10 scenarios against OCaml, including byte spans and diagnostic precedence. `python -m py_compile tests/test_a13.py` and `git diff --check` passed. The full repository suite was not rerun for this checker slice. The 100,000-step budget and `CURRENT.md`/manifest are unchanged.

Limitations: assignment checking covers variable targets and the currently represented structural type subset; `for-in`, complete missing-return analysis and broad flow-sensitive semantics remain unsupported. A13 remains experimental and unaccepted. No master merge or release action occurred. The main checkout's unrelated A14 edit remains untouched.

Next slice: after rereading the coordination outboxes, implement the smallest OCaml-matched `for-in` type-checking rule, preserving lexical loop-binding scope and fail-closed behavior for any unimplemented body or flow semantics.
