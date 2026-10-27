# Pepin Compiler Campaign Checkpoint

**Date:** 2026-10-27
**Repository:** `matthewjameswatkins1978-cyber/pepin`
**Branch / verified code SHA:** `campaign/pep-v01-sustained-build-20261027` / `ab9146220492ec25951c3b91bd1db75c21ac5590` (remote-equal)

## Baselines and authority

- Accepted A12 parser base: `69a47fe77187666bdd045b8dc8a9f633a7dd49d7`.
- A13 review baseline: `7647ec4b6dc875745d883d82db25390b20c1c616`; PR #12 remains a separate draft review line. Lucy's review holds any claim that A13 `valid` is a complete semantic certificate.
- The campaign branch is the single active implementation line. No merge, `master`, release, `CURRENT.md`, or manifest update is authorized.
- Production truth remains the OCaml 5.5.2 seed. The project switch is `pepin-5.5.2` through `PEPIN_OPAM_ROOT`; a plain default-root opam query can select another installation.

## Verified implementation and evidence

The isolated Pep-written A13 checker resolves lexical names and function calls, types scalar expressions, scalar-element lists and scalar-field records, checks scalar union constructors, and types the implemented scalar-payload constructor-pattern subset. It checks arm-local payload bindings, match result agreement and contextual match result types, typed match-result holes, wrong-union patterns, duplicate constructor arms, exhaustiveness and unreachable arms after wildcard/binding catch-alls. Empty lists require a supported contextual List[T] type or receive OCaml-matched PEP_EMPTY_LIST_NEEDS_TYPE. Built-in type names cannot be redeclared, and functions cannot reuse builtin or constructor names. Nested constructor patterns and broader pattern forms remain unsupported. It rejects unsupported composite payloads, equality on aggregate values, assignment, and `for-in`. Non-Unit return validity is reported only when the current bounded block/if analysis proves coverage. The checker does not replace the OCaml production checker.

At implementation SHA `9ecde10a91298b9c4be3bedb1da4683280641fd3` and test revision `ab9146220492ec25951c3b91bd1db75c21ac5590`, `python -m unittest tests.test_a13 -q` passed **28/28**. Real Pep tool invocations matched OCaml's `PEP_MATCH_ARM_TYPE_MISMATCH` and exact byte spans for three arm arrangements and contextual result sites in returns, annotated bindings, a recursive function argument, conditional-expression branches and list elements. The fix closes a reproduced false-valid where the expected result type masked every arm's actual type. A larger two-function argument specimen reaches the unchanged 100,000-step ceiling at checker line 2447:26 before producing a semantic result, so that broader case remains unverified; no budget was raised. The existing `_build/ocaml/pep.exe` provided the OCaml CLI oracle. `git diff --check` passed; no clean OCaml rebuild or full repository suite was run.

## Remaining risks and next action

A13 remains partial and unaccepted. Record and union recursive/composite payloads, nested and broader pattern forms, broader bidirectional checking, complete control-flow analysis and the checked-program contract remain unfinished. Large match analyses can exhaust the fixed tool-step budget; the checker must preserve that limit and report the practical envelope honestly. The reviewed fail-closed gate must remain active until each rule is independently implemented and differentially tested.

Next slice: reduce the two-function function-argument mismatch specimen and determine whether the fixed-step cost comes from repeated checker scans or typed-result construction. Optimize only measured avoidable work; do not raise the 100,000-step or transport limits. Keep fail-closed behavior for unsupported contexts and do not promote A13 results into production authority.