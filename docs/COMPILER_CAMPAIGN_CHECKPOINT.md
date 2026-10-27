# Pepin Compiler Campaign Checkpoint

**Date:** 2026-10-27
**Repository:** `matthewjameswatkins1978-cyber/pepin`
**Branch / verified code SHA:** `campaign/pep-v01-sustained-build-20261027` / `f4093df19e44038b4102dfccb80d207eaaacffba` (remote-equal)

## Baselines and authority

- Accepted A12 parser base: `69a47fe77187666bdd045b8dc8a9f633a7dd49d7`.
- A13 review baseline: `7647ec4b6dc875745d883d82db25390b20c1c616`; PR #12 remains a separate draft review line. Lucy's review holds any claim that A13 `valid` is a complete semantic certificate.
- The campaign branch is the single active implementation line. No merge, `master`, release, `CURRENT.md`, or manifest update is authorized.
- Production truth remains the OCaml 5.5.2 seed. The project switch is `pepin-5.5.2` through `PEPIN_OPAM_ROOT`; a plain default-root opam query can select another installation.

## Verified implementation and evidence

The isolated Pep-written A13 checker resolves lexical names and function calls, types scalar expressions, scalar-element lists and scalar-field records, checks scalar union constructors, and types the implemented scalar-payload constructor-pattern subset. It checks arm-local payload bindings, match result agreement and contextual match result types, typed match-result holes, wrong-union patterns, duplicate constructor arms, exhaustiveness and unreachable arms after wildcard/binding catch-alls. Empty lists require a supported contextual List[T] type or receive OCaml-matched PEP_EMPTY_LIST_NEEDS_TYPE. Built-in type names cannot be redeclared, and functions cannot reuse builtin or constructor names. Nested constructor patterns and broader pattern forms remain unsupported. It rejects unsupported composite payloads, equality on aggregate values, assignment, and `for-in`. Non-Unit return validity is reported only when the current bounded block/if analysis proves coverage. The checker does not replace the OCaml production checker.

At code SHA `f4093df`, `python -m unittest tests.test_a13 -v` passed **27/27**. The suite invokes the checker through real Pep tools and compares selected valid, invalid and incomplete cases with the OCaml CLI. List mismatch spans and empty-list diagnostics match OCaml, including single-diagnostic PEP_EMPTY_LIST_NEEDS_TYPE cases across five contexts. Match binding identity, expected hole types, subject/pattern errors, result-type codes, duplicate arms, exhaustiveness and unreachable-arm spans also match. Reserved built-in type and constructor/function name cases match OCaml. A larger duplicate-arm case with multiple payload bindings exceeded the unchanged 100,000-step tool budget; compact duplicate and unreachable-arm cases pass, and no budget was raised. `git diff --check` passed before the code commit; no full repository suite was run.

## Remaining risks and next action

A13 remains partial and unaccepted. Record and union recursive/composite payloads, nested and broader pattern forms, broader bidirectional checking, complete control-flow analysis and the checked-program contract remain unfinished. Large match analyses can exhaust the fixed tool-step budget; the checker must preserve that limit and report the practical envelope honestly. The reviewed fail-closed gate must remain active until each rule is independently implemented and differentially tested.

Next slice: test contextual match checking against every arm result so an enclosing expected type cannot mask an arm mismatch. Preserve the 65,536-byte source, 100,000-step tool and transport limits; do not promote A13 results into production authority.