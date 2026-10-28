# Pepin Documentation Pack

**Edition:** 28 October 2026  
**Basis:** Matthew-approved `PEP-LANG-FINAL-DRAFT-2026-10-27`, with explicit 28 October product-priority correction.  
**Status:** Draft-derived documentation published for review; **not** a frozen language standard or official compiler release.

## Start here

| Document | Who should read it | What it contains |
| --- | --- | --- |
| [The Pepin Manual](PEPIN-MANUAL.md) | People learning Pep; AI agents beginning to use the language | Practical walkthrough, design examples labelled against real seed capabilities, workflow and philosophy, tests, semantic tools |
| [Pep Language Reference](PEP-LANGUAGE-REFERENCE.md) | Language implementers, advanced users, reviewers, tool authors | Organised accepted semantics, type/access/effect/safety contracts, open normative grammar questions, proof and release boundaries |

**Terminology:** Pep is the `.pep` source language; Pepin is the project/environment; Lucy is the intended compiler name. The installed compiler may still be invoked through `pep.ps1`.

## Editorial decisions

1. **Source of truth:** the [27 October signed-off final language design draft](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/design/final-language-draft-20261027/docs/final-draft/PEP-LANG-FINAL-DRAFT-2026-10-27.md), not historical founding v0.3 where superseded.
2. **Newer product clarification:** the [28 October priority decision](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7C563c337a-eb00-4cb4-aa42-95a2ba584a73) prioritises compiler-derived semantics/checkpoints and bottom-up Pep-written standard library; annotation-centred Semantic Notes are no longer central or a required 1.0 blocker.
3. **Syntax accuracy:** accepted direction is not equivalent to frozen grammar. Proposed spellings and unimplemented APIs are identified rather than invented.
4. **Implementation accuracy:** current seed support, experimental branch features and future targets are separate. A working manifest-driven `pep test` does not imply the draft's in-language `test` syntax.
5. **Semantic safety:** distinguish source facts, proofs, observations, tests, host grants, and human acceptance. Avoid unfounded platform, memory or correctness assurances.
6. **Code-first documentation:** Markdown is designed to live in a Git repository beside versioned sources, with stable headings and explicit cross-links.

## Repository location

These documents are published together on a documentation-only feature branch at:

```
docs/manual/README.md
    ← this file
docs/manual/PEPIN-MANUAL.md
    ← teaching manual
docs/manual/PEP-LANGUAGE-REFERENCE.md
    ← draft-derived language reference
```

This documentation branch does not change accepted language semantics, compiler code, or release pointers. Its pull request targets the active development campaign for normal editorial and technical review.

## Primary sources

- [Design packet, PR #14](https://github.com/matthewjameswatkins1978-cyber/pepin/pull/14) and [consolidated draft](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/design/final-language-draft-20261027/docs/final-draft/PEP-LANG-FINAL-DRAFT-2026-10-27.md)
- [DEC-009 accepted surface syntax](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7Caf91b899-62b4-4c8f-8a1e-429bda9d4fa3)
- [Acceptance matrix](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/design/final-language-draft-20261027/docs/final-draft/ACCEPTANCE-MATRIX.md)
- [28 October product priorities](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7C563c337a-eb00-4cb4-aa42-95a2ba584a73)
- [Seed implementation status](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/DESIGN.md), [Road 2](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/ROAD-2-PEPIN-1.0.md), [full-language gap ledger](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/FULL-LANGUAGE-LEDGER.md)

## Suggested next editorial pass

At the next accepted grammar contract, split the reference's **open normative decisions** into an exact language grammar and runnable conformance corpus. At the next accepted compiler release, refresh the manual's seed-vs-design labels from **that precise release SHA**, rather than from development-branch narration.