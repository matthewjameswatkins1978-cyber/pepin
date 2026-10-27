# Pepin Compiler Campaign Checkpoint

**Date:** 2026-10-27
**Repository:** `matthewjameswatkins1978-cyber/pepin`
**Branch / verified code SHA:** `campaign/pep-v01-sustained-build-20261027` / `9ecde10a91298b9c4be3bedb1da4683280641fd3` (remote-equal)

## Baselines and authority

- Accepted A12 parser base: `69a47fe77187666bdd045b8dc8a9f633a7dd49d7`.
- A13 review baseline: `7647ec4b6dc875745d883d82db25390b20c1c616`; PR #12 remains a separate draft review line. Lucy's review holds any claim that A13 `valid` is a complete semantic certificate.
- The campaign branch is the single active implementation line. No merge, `master`, release, `CURRENT.md`, or manifest update is authorized.
- Production truth remains the OCaml 5.5.2 seed. The project switch is `pepin-5.5.2` through `PEPIN_OPAM_ROOT`; a plain default-root opam query can select another installation.

## Verified implementation and evidence

The isolated Pep-written A13 checker resolves lexical names and function calls, types scalar expressions, scalar-element lists and scalar-field records, checks scalar union constructors, and types the implemented scalar-payload constructor-pattern subset. It checks arm-local payload bindings, match result agreement and contextual match result types, typed match-result holes, wrong-union patterns, duplicate constructor arms, exhaustiveness and unreachable arms after wildcard/binding catch-alls. Empty lists require a supported contextual List[T] type or receive OCaml-matched PEP_EMPTY_LIST_NEEDS_TYPE. Built-in type names cannot be redeclared, and functions cannot reuse builtin or constructor names. Nested constructor patterns and broader pattern forms remain unsupported. It rejects unsupported composite payloads, equality on aggregate values, assignment, and `for-in`. Non-Unit return validity is reported only when the current bounded block/if analysis proves coverage. The checker does not replace the OCaml production checker.

At code SHA `9ecde10a91298b9c4be3bedb1da4683280641fd3`, `python -m unittest tests.test_a13 -q` passed **28/28**. The suite invokes the checker through real Pep tools and compares selected valid, invalid and incomplete cases with the OCaml CLI. New differential coverage checks contextual match result types in three arm arrangements: all arms wrong, only the first wrong, and only a later arm wrong. Pep now matches OCaml's `PEP_MATCH_ARM_TYPE_MISMATCH` and exact byte span, closing a reproduced false-valid case. Earlier list, match, hole, naming and control-flow evidence remains as recorded above. The unchanged 100,000-step budget still rejects a larger duplicate-arm specimen with multiple payload bindings; compact duplicate and unreachable-arm cases pass. `git diff --check` passed. This slice used the existing `_build/ocaml/pep.exe`; no clean OCaml rebuild or full repository suite was run.

## Remaining risks and next action

A13 remains partial and unaccepted. Record and union recursive/composite payloads, nested and broader pattern forms, broader bidirectional checking, complete control-flow analysis and the checked-program contract remain unfinished. Large match analyses can exhaust the fixed tool-step budget; the checker must preserve that limit and report the practical envelope honestly. The reviewed fail-closed gate must remain active until each rule is independently implemented and differentially tested.

Next slice: probe contextual match expected types at the other supported sites—annotated bindings, function arguments, conditional-expression branches and list elements—against the OCaml CLI. Keep fail-closed behavior for unsupported contexts, and preserve the 65,536-byte source, 100,000-step tool and transport limits. Do not promote A13 results into production authority.