# Pepin Compiler Campaign Checkpoint

**Date:** 2026-10-27
**Repository:** `matthewjameswatkins1978-cyber/pepin`
**Branch / verified code SHA:** `campaign/pep-v01-sustained-build-20261027` / `3dcd88b47fc016f9649eb5b310ed14f7bf6f38d6` (remote-equal)
**Verification test head:** `0346120f93aab874587612b7f935d78db3d7ce67` (remote-equal)

## Baselines and authority

- Accepted A12 parser base: `69a47fe77187666bdd045b8dc8a9f633a7dd49d7`.
- A13 review baseline: `7647ec4b6dc875745d883d82db25390b20c1c616`; PR #12 remains a separate draft review line. Lucy's review holds any claim that A13 `valid` is a complete semantic certificate.
- The campaign branch is the single active implementation line. No merge, `master`, release, `CURRENT.md`, or manifest update is authorized.
- Production truth remains the OCaml 5.5.2 seed. The project switch is `pepin-5.5.2` through `PEPIN_OPAM_ROOT`; a plain default-root opam query can select another installation.

## Verified implementation and evidence

The isolated Pep-written A13 checker resolves lexical names and function calls; checks scalar expressions, two-level primitive lists, nominal record fields and record-valued union payloads; and retains named-record payload types in constructor-pattern bindings. It checks the implemented scalar-payload pattern subset, contextual match and if-expression result types, typed holes, wrong-union patterns, duplicate constructor arms, exhaustiveness and unreachable arms after wildcard/binding catch-alls. Empty lists require a supported contextual `List[T]` type or receive OCaml-matched `PEP_EMPTY_LIST_NEEDS_TYPE`. Built-in type names cannot be redeclared, and functions cannot reuse builtin or constructor names. Deeper recursive nominal/union graphs, nested constructor patterns, broader patterns, aggregate equality, assignment and `for-in` remain unsupported or unverified. Non-Unit return validity is reported only when the current bounded block/if analysis proves coverage. The checker does not replace the OCaml production checker.

At checker code SHA `3dcd88b47fc016f9649eb5b310ed14f7bf6f38d6`, tested with the committed test source at `0346120f93aab874587612b7f935d78db3d7ce67`, `python -m unittest tests.test_a13 tests.test_a13_nested_records -q` passed **33/33** in 79.143 seconds. This is 29 A13 checker tests plus four nested-record/list tests. Ten if-expression fixtures compare status, exact diagnostic codes/spans and typed-hole expectations with OCaml across returns, annotations, function arguments, list elements, record fields and branch mismatches. Four minimal record-field match-with-hole variants still return `PEP_RUNTIME_STEP_LIMIT`; the 100,000-step budget is unchanged. The earlier 32/32 attribution to the older `7533f4c` candidate is superseded: replaying that stale checker against newer nested-list mismatch cases exposed three expected failures, while the current `3dcd88b` checker passes the exact branch suite. The existing `_build/ocaml/pep.exe` provided the OCaml CLI oracle. No clean OCaml rebuild or full repository suite was run.

## Remaining risks and next action

A13 remains partial and unaccepted. Recursive nominal/union relationships, nested constructor patterns, broader patterns, complete control-flow analysis and the checked-program contract remain unfinished. Four minimized record-field match-with-hole variants still hit the unchanged 100,000-step ceiling, so their hole facts remain unverified; do not increase the budget. The reviewed fail-closed gate remains required until each rule is independently implemented and differentially tested. The worktree was clean at verification head `0346120`.

Next slice: inspect repeated checker traversals in the minimal hole case and make only a measured bounded optimization. A13 remains experimental; no acceptance, merge, `CURRENT.md` or manifest advancement.