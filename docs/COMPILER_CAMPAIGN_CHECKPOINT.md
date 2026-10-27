# Pepin Compiler Campaign Checkpoint

**Date:** 2026-10-27
**Repository:** `matthewjameswatkins1978-cyber/pepin`
**Branch / verified code SHA:** `campaign/pep-v01-sustained-build-20261027` / `7bce56e21de7b1706513830a831603e6787ab31d` (remote-equal)

## Baselines and authority

- Accepted A12 parser base: `69a47fe77187666bdd045b8dc8a9f633a7dd49d7`.
- A13 review baseline: `7647ec4b6dc875745d883d82db25390b20c1c616`; PR #12 remains a separate draft review line. Lucy's review holds any claim that A13 `valid` is a complete semantic certificate.
- The campaign branch is the single active implementation line. No merge, `master`, release, `CURRENT.md`, or manifest update is authorized.
- Production truth remains the OCaml 5.5.2 seed. The project switch is `pepin-5.5.2` through `PEPIN_OPAM_ROOT`; a plain default-root opam query can select another installation.

## Verified implementation and evidence

The isolated Pep-written A13 checker resolves lexical names and function calls, types scalar expressions, scalar-element lists and scalar-field records, and checks scalar union constructors. It rejects duplicate nominal/type members and unsupported composite payloads, equality on aggregate values, assignment, `for-in`, and unimplemented pattern semantics. Non-Unit return validity is reported only when the current bounded block/if analysis proves coverage. The checker does not replace the OCaml production checker.

At code SHA `7bce56e`, `python -m unittest tests.test_a13 -v` passed **22/22**. The suite invokes the checker through real Pep tools and compares selected valid, invalid and incomplete cases with the OCaml CLI. New list mismatch tests matched OCaml diagnostic codes and original byte spans for `append`, `contains` and an annotated list element. Union constructor, typed-hole, duplicate declaration, arity, payload and unsupported equality cases also pass. `git diff --check` passed before the commit; no full repository suite was run in this slice.

## Remaining risks and next action

A13 remains partial and unaccepted. List diagnostics for unconstrained empty lists still differ from OCaml and can cascade into a second list-type diagnostic. Record and union recursive/composite payloads, match typing and exhaustiveness, broader bidirectional inference, complete control-flow analysis and the checked-program contract remain unfinished. The reviewed fail-closed gate must remain active until each rule is independently implemented and differentially tested.

Next slice: align unconstrained empty-list handling and suppress derivative diagnostics without weakening rejection. Preserve the 65,536-byte source, 100,000-step tool and transport limits; do not promote A13 results into production authority.