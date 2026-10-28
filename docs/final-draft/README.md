# Pepin — Final Language Design Draft Packet

**Date:** 27 October 2026  
**Language:** Pep (.pep)  
**Status:** Matthew accepted the final language-design direction and Decision 9. This is a **design/handoff packet**, not an implemented or frozen language standard.

## Read in this order

1. **[PEP-LANG-FINAL-DRAFT-2026-10-27.md](PEP-LANG-FINAL-DRAFT-2026-10-27.md)** — consolidated accepted semantics and surface syntax, AI-first compiler requirements, source three-layer model, standard library, native testing, memory, concurrency, constraints and honest open questions.
2. **[IMPLEMENTATION-MISSION.md](IMPLEMENTATION-MISSION.md)** — compact, actionable agent mission contract, authority limits, dependencies, milestone waves, review cadence and receipt shape.
3. **[ACCEPTANCE-MATRIX.md](ACCEPTANCE-MATRIX.md)** — positive/negative test cases, adversarial safety gates, byte-preservation requirements, compiler/backend differential tests and evidence classification.

## Completion objective: the entire accepted language

Matthew has explicitly confirmed that **the product is the full Pep language described in this final draft, not just the subset sufficient to self-host**. Native C23 compilation and self-hosting should be achieved as early as dependencies permit, then development continues until the accepted complete grammar, type rules, memory and ownership safety, effects, structured concurrency, standard library, built-in testing, and AI-first semantic compiler interfaces are implemented and verified. A compact syntax is a design strength, not grounds to silently remove a difficult implementation obligation.

Active agents must maintain an evidence-linked full-language completion/gap ledger and coordinate ownership on [GitHub issue #16](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/16). See the active campaign's [full-language and two-agent contract](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/missions/FULL-LANGUAGE-ENDSTATE-AND-TWO-AGENT-PLAN.md). The design is the **target**, not proof that any implementation or release gate has passed.

## Authoritative boundaries

The accepted design **does not mean the current OCaml seed implements the described language**. Check the real implementation at [../DESIGN.md](../DESIGN.md), the current authoritative development phase at [../packets/CURRENT.md](../packets/CURRENT.md), and binding earlier technical resolutions [TR001](../TECHNICAL_RESOLUTION_001.md) and [TR002](../TECHNICAL_RESOLUTION_002.md).

Semantic Notes have a separate **[draft design PR #13](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/13)**. The target three-layer source concept is agreed, but the parser contract remains subject to testing. Terror Bats is a separate [adversarial testing framework](https://github.com/matthewjameswatkins1978-cyber/The-Terror-Bats); Pep should inherit its evidence rules and provide an adapter, not clone the whole runtime.

## Deliberate reconciliations

- **Independent value semantics** supersede founding v0.3's reference-like collection assumption.
- **Future C23 backend** per TR002 supersedes historical C11 plans.
- **Compiler facts ≠ source comments ≠ AI suggestions ≠ test observations ≠ human acceptance**.
- **Effect declarations ≠ host-authorised permissions**.
- **Manual allocation ≠ unchecked raw pointer access**; danger keeps checkable obligations and explicit trust boundaries.
- **One module per file**, with selected entry point permitted top-level execution but importable modules free of side-effecting implicit initialisation.
- **The packet is not a blanket build order.** Approval of bounded implementation phases remains separate. Do not automatically edit/merge master or advance A9–A15 based on this folder.

## Next legitimate action

Perform a live repository and branch preflight, then select and explicitly authorise one bounded compiler/grammar milestone with targeted acceptance tests. Use feature/workshop branches, regular pushed coherent slices, and an independent evidence-based review after three slices.
