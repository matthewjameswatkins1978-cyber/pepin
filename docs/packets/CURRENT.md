# PEPIN: CURRENT IMPLEMENTATION PACKET

This is the **one stable entry URL** for agents. Verify live GitHub HEAD, not conversation history. Distinguish accepted code, reviewed direction and permission to implement.

## Accepted baseline: A8; roadmap reviewed, implementation paused

- **Last accepted implementation:** A8 at [da244417](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/da244417c45a961728181a17ad31581e4d5a21de).
- **Acceptance / original pause commit:** [4132d3f](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/4132d3f953a370b0837d9a20fc73067f7f0c666f). It is later than, and distinct from, the implementation commit.
- A8 is a **Pep-written example tool**, not an OCaml dead-code shortcut, built-in CLI analyser or self-hosted compiler. It consumes checker-resolved call facts and reports functions unreachable **under declared roots**.
- Published A8 record reports a clean OCaml 5.5.2 build, smoke tests, **55/55 primary tests** and **11/11 historical MoonBit tests**. These are builder-reported, SHA-bound evidence; this roadmap-only edit does not rerun the Windows suite.
- **No implementation phase currently authorised:** manifest `current: null`. Documentation changes do not mark A10 implemented or give worker permission to start coding.

## Reviewed direction, not a new acceptance claim

**Next proposed design/implementation gate: [A10 compiler foundations](A10-COMPILER-FOUNDATION-LIBRARY.md), driven directly by the needs of [A11, the first Pep-written lexer](A11-PEP-WRITTEN-LEXER.md).**

1. Inspect the actual OCaml lexer, checked Pep feature set, A8/A7 protocol, runtime and tests; measure the current costs before adding features.
2. Specify the minimum source-byte access, error reporting and efficient token accumulation a real Pep lexer needs. A6 `append` copies an immutable list in O(n): repeated token append may produce O(n²) work. Test alternatives rather than assuming a specific builder/collection design.
3. Demonstrate a Pep-written byte-to-token vertical slice with accurate original UTF-8 spans, LF/CRLF behavior, explicit invalid-byte handling and bounded host-authorised input. Do not expose a hidden host tokenizer.
4. Only then authorise the full A11 lexer and use the OCaml lexer as a differential oracle, while retaining the OCaml compiler as production semantic authority.

**A9** (more Pep-written linters) is deferred rather than deleted; A8 already proved self-extension. **A12–A15** remain provisional, with later gates reviewed against actual evidence. Planned self-hosting remains Pep-written C23, Clang primary, GCC cross-check. See [research and design disposition](../COMPILER_RESEARCH_AND_DECISIONS_2026-10.md).

## Authority and next legitimate action

The A6–A8 campaign is complete. **The next legitimate action is A10's bounded implementation-design gate and explicit authorisation of its scope, not automatic implementation or progression to A11.** Matthew retains consequential acceptance; agents can decide ordinary reversible details after implementation authority is delegated.

Read [packet index](README.md), [manifest](manifest.json), [AGENTS.md](../../AGENTS.md), [DESIGN](../DESIGN.md), [session protocol](../SESSION_PROTOCOL.md), [Founding v0.3](../FOUNDING_DESIGN_v0.3.md), [TR001](../TECHNICAL_RESOLUTION_001.md), [TR002](../TECHNICAL_RESOLUTION_002.md) and current code/tests. Do not advance this pointer or manifest `lastAccepted` until an implementation phase passes its own acceptance and is published.

A design proposal is not a shipped capability. A branch push is a review/checkpoint mechanism, not merge or acceptance authority.
