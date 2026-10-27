# Pepin Compiler Campaign Checkpoint

**Date:** 2026-10-27
**Repository:** `matthewjameswatkins1978-cyber/pepin`
**Branch / verified code SHA:** `campaign/pep-v01-sustained-build-20261027` / `f72c5e2f8a21809396c58682f7a97020b3c621f8` (remote-equal)

## Baselines and authority

- Accepted A12 parser base: `69a47fe77187666bdd045b8dc8a9f633a7dd49d7`.
- A13 review baseline: `7647ec4b6dc875745d883d82db25390b20c1c616`; PR #12 remains a separate draft review line. Lucy's review holds any claim that A13 `valid` is a complete semantic certificate.
- The campaign branch is the single active implementation line. No merge, `master`, release, `CURRENT.md`, or manifest update is authorized.
- Production truth remains the OCaml 5.5.2 seed. The project switch is `pepin-5.5.2` through `PEPIN_OPAM_ROOT`; a plain default-root opam query can select another installation.

## Verified implementation and evidence

The isolated Pep-written A13 checker resolves lexical names and function calls, types scalar expressions, scalar-element lists and scalar-field records, checks scalar union constructors, and types the implemented scalar-payload constructor-pattern subset. It checks arm-local payload bindings, match result agreement and contextual match result types, typed match-result holes, wrong-union patterns, duplicate constructor arms, exhaustiveness and unreachable arms after wildcard/binding catch-alls. Empty lists require a supported contextual List[T] type or receive OCaml-matched PEP_EMPTY_LIST_NEEDS_TYPE. Built-in type names cannot be redeclared, and functions cannot reuse builtin or constructor names. Nested constructor patterns and broader pattern forms remain unsupported. It rejects unsupported composite payloads, equality on aggregate values, assignment, and `for-in`. Non-Unit return validity is reported only when the current bounded block/if analysis proves coverage. The checker does not replace the OCaml production checker.

At implementation SHA `f72c5e2f8a21809396c58682f7a97020b3c621f8`, `python -m unittest tests.test_a13 -q` passed **28/28** against the staged checker source. Real Pep tool invocations matched OCaml's `PEP_MATCH_ARM_TYPE_MISMATCH` and exact byte spans for returns, annotated bindings, a recursive function argument, conditional-expression branches, list elements and record fields, across first, later and multiple bad arms. The record-field case now carries the declared field type into its nested match, matching OCaml's diagnostic code and span. A record-field match with a typed hole reaches the unchanged 100,000-step ceiling at checker line 2394:26, so its incomplete/hole facts remain unverified. The larger two-function argument specimen also reaches the fixed ceiling. The existing `_build/ocaml/pep.exe` provided the OCaml CLI oracle; no clean rebuild or full repository suite was run.

## Remaining risks and next action

A13 remains partial and unaccepted. Record and union recursive/composite payloads, nested and broader pattern forms, broader bidirectional checking, complete control-flow analysis and the checked-program contract remain unfinished. Large match analyses can exhaust the fixed tool-step budget; the checker must preserve that limit and report the practical envelope honestly. The reviewed fail-closed gate must remain active until each rule is independently implemented and differentially tested.

Next slice: reduce the record-field match-with-hole case and investigate its fixed-step cost. Review, test and separately decide whether to integrate the remaining unstaged declaration-gate edits in `tests/pep_checker_a13.pep`; they were not part of the verified SHA. A transient untracked `tests/pep_checker_a13_nested_records.py` appeared during review and was absent on reread; I did not create or remove it, and no copy was found. Preserve the 100,000-step and transport limits; A13 remains experimental.