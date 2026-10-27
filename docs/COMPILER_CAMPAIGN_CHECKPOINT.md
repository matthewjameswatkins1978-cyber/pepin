# Pepin Compiler Campaign Checkpoint

**Date:** 2026-10-27
**Repository:** `matthewjameswatkins1978-cyber/pepin`
**Branch / verified code SHA:** `campaign/pep-v01-sustained-build-20261027` / `7533f4c86cb3663ad86748ae83a4a7aaa58d68cf` (remote-equal)

## Baselines and authority

- Accepted A12 parser base: `69a47fe77187666bdd045b8dc8a9f633a7dd49d7`.
- A13 review baseline: `7647ec4b6dc875745d883d82db25390b20c1c616`; PR #12 remains a separate draft review line. Lucy's review holds any claim that A13 `valid` is a complete semantic certificate.
- The campaign branch is the single active implementation line. No merge, `master`, release, `CURRENT.md`, or manifest update is authorized.
- Production truth remains the OCaml 5.5.2 seed. The project switch is `pepin-5.5.2` through `PEPIN_OPAM_ROOT`; a plain default-root opam query can select another installation.

## Verified implementation and evidence

The isolated Pep-written A13 checker resolves lexical names and function calls; checks scalar expressions, scalar-element lists (including differential-tested two-level primitive lists), scalar-field records, record-valued union payloads, and the implemented scalar-payload constructor-pattern subset. It checks arm-local payload bindings, match result agreement, contextual match and if-expression branch types, typed holes, wrong-union patterns, duplicate constructor arms, exhaustiveness and unreachable arms after wildcard/binding catch-alls. Empty lists require a supported contextual `List[T]` type or receive OCaml-matched `PEP_EMPTY_LIST_NEEDS_TYPE`. Built-in type names cannot be redeclared, and functions cannot reuse builtin or constructor names. Nested constructor patterns and broader pattern forms remain unsupported. Deeper recursive nominal/union graphs, aggregate equality, assignment and `for-in` remain unsupported or unverified. Non-Unit return validity is reported only when the current bounded block/if analysis proves coverage. The checker does not replace the OCaml production checker.

At code SHA `7533f4c86cb3663ad86748ae83a4a7aaa58d68cf`, an isolated A13 run passed **32/32**: the 29 checker tests plus the three committed nested-record/list tests. The candidate checker was built from remote head `9aa04ef` plus only the conditional-checking changes committed as `7533f4c`; concurrent uncommitted list-context edits were excluded. Six if-expression fixtures compare status, exact diagnostics and byte spans, and expected hole types with the OCaml reference. They cover one or two branch holes, wrong first/last/both branches under context, and an uncontextualized mismatch. A record-field match with a typed hole still reaches the unchanged 100,000-step ceiling, so its incomplete/hole facts remain unverified; the larger two-function argument specimen also reaches the fixed ceiling. The existing `_build/ocaml/pep.exe` provided the OCaml CLI oracle. No clean OCaml rebuild or full repository suite was run.

## Remaining risks and next action

A13 remains partial and unaccepted. Recursive nominal/union relationships, nested constructor patterns, broader patterns, complete control-flow analysis and the checked-program contract remain unfinished. Large match and hole analyses can exhaust the unchanged 100,000-step tool budget; no budget increase is proposed. The reviewed fail-closed gate must remain active until each rule is independently implemented and differentially tested. The current worktree also contains uncommitted list-context changes in `tests/pep_checker_a13.pep` and `tests/test_a13_nested_records.py`; they are not part of SHA `7533f4c` or its 32/32 evidence.

Next slice: reduce and measure the minimal record-field match-with-hole case, focusing on repeated scans during hole-fact construction. Separately review the visible list-context changes before treating them as a verified baseline. Preserve the 100,000-step and transport limits; A13 remains experimental.