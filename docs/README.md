# Pepin documentation guide

**Pepin** is the project and development environment. **Pep** is the language (`.pep` source). **Lucy** is the intended compiler/toolchain name; the current primary command is `pep.ps1`.

Documentation has three jobs: **help you try what exists**, **explain why the language is being built**, and **show what must be proved before 1.0**. They are not interchangeable.

## Start here

| If you want to… | Read |
| --- | --- |
| Understand the project in two minutes | [Project README](../README.md) |
| See the milestones and 1.0 finish line | [Road to 1.0](ROADMAP_TO_1_0.md) |
| Try the accepted OCaml seed | [Bootstrap and commands](BOOTSTRAP.md) |
| Know what is genuinely implemented | [Implementation status](DESIGN.md), then [seed-language specifics](SEED_LANGUAGE.md) |
| Understand machine-readable sessions | [Session protocol](SESSION_PROTOCOL.md), [tool protocol v2](TOOL_PROTOCOL_V2.md) |
| Give work to an implementation agent | [Current authorised packet](packets/CURRENT.md), then [packet index](packets/README.md) |
| Explore founding motivation | [Founding design v0.3](FOUNDING_DESIGN_v0.3.md) |
| Understand binding historical technical changes | [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md) and [Technical Resolution 002](TECHNICAL_RESOLUTION_002.md) |
| Investigate the first prototype | [Historical MoonBit A0](HISTORICAL_DESIGN_A0.md) |

## Reading the design without being misled

**Implemented** means accepted code and supported test evidence at a stated revision. **Designed** means an agreed desired semantic direction. **Proposed** means a candidate interface or syntax still under review. **Experimental** means development-branch work, not `master` release support.

Some founding examples and design documents predate later decisions. The accepted 27 October language draft expands the original founding design; subsequent 28 October priorities place **Pep-written library foundations and compiler-derived semantic facts/checkpoints** ahead of annotation-centred Semantic Notes. The future native backend is **C23**, not the original MoonBit/C11 proof.

Useful *review and development branch* documents, not part of accepted `master`:

- [27 October consolidated language draft (PR #14)](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/14): intended full language and unresolved grammar/implementation obligations.
- [28 October priorities (PR #17)](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/17): practical Pep-first stdlib and one compiler-derived semantic model.
- [Practical Pepin manual and reference (PR #18)](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/18): 18-chapter learner's manual and technical language reference; **design examples are not automatically runnable on master**.
- [Detailed Road 1 / Road 2 / full-language gap ledger](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/ROADMAP-INDEX.md): campaign planning/evidence; consult exact current branch SHA before citing test results.

A review PR may itself change or remain unmerged. The acceptance status and actual code on `master` do not change merely because a document or branch exists.

## Primary sources of truth

1. **Actual language behaviour:** compiled code, conformance tests and concrete revisions. Start with [DESIGN.md](DESIGN.md).
2. **Accepted integration state:** [CURRENT.md](packets/CURRENT.md) and [manifest](packets/manifest.json). They are deliberately not advanced by exploratory branches.
3. **Language direction:** the accepted design decisions and their revisions, with later explicit decisions overriding older conflicting prose.
4. **Implementation plans:** packet and campaign roadmaps. They do not authorise a worker to merge, publish or claim new release functionality.

If the docs and the compiler disagree about what runs, fix the docs or the compiler, but **do not claim the feature exists until the discrepancy is resolved and verified**.

## For contributors and agents

Read [AGENTS.md](../AGENTS.md) and the [current packet](packets/CURRENT.md) before implementation. Keep runtime/compiled/tested status distinct; describe new features with supported syntax, exact limits and their revision. Do not quietly redefine Pep's grammar from aspirational examples, claim sandbox security for a trusted-local host, or report draft compiler components as accepted.

The original MoonBit proof remains documented for history. Pepin's principal active seed is OCaml 5.5.2, with the intention to replace more of the compiler and tools with Pep itself.
