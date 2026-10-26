# A15: Reproducible staged Pep self-hosting
**PROVISIONAL / NOT YET AUTHORISED.** Depends on accepted Pep-written A11–A14 compiler phases and verified C23 semantics.

## Objective
Prove the language can build a native compiler for itself, with the OCaml interpreter needed for initial bootstrap only. Distinguish an isolated success from a reproducible self-hosting chain.

## Proposed staged proof
1. **Seed:** OCaml interpreter checks/runs canonical Pep compiler source (lexer, parser, checker, C23 emitter), producing C23 for that Pep compiler. The generated code is compiled with Clang into native compiler A.
2. **A→B:** Native compiler A checks/translates the same canonical Pep compiler source, generating C23 built to compiler B.
3. **B→C:** Native compiler B translates the same source to compiler C. Preserve clear stage labels and exact source/runtime/toolchain hashes.
4. Compare generated C23 and/or binary behaviour under a documented reproducibility model, accounting for nondeterministic build metadata. Run a broad golden/differential corpus through A/B/C for execution and compiler semantic diagnostics.
5. Independently build the same generated C23 with GCC, test observable Pep equivalence, and document host C toolchain/runtime as an explicit dependency, not something magically eliminated.

## Acceptance
A/B/C each compile a declared source subset that includes their **own source** without invoking OCaml lexer/parser/type checker for B/C stages. Confirm exact checked semantics, typed holes/invalid/incomplete results, name resolution, recursive variants/lists/match, checked Int64 and JSON queries to the extent these are included in the claimed compiler interface. Failures reproducible, stage boundaries independently inspectable. Only then describe Pep as self-hosting, with precise limitations and reproducible build instructions.

## Stop/non-scope
No need to build a new kernel, package ecosystem, secure untrusted plugin sandbox, language VM or AI model backend. If Pep lacks a primitive, identify the smallest blocked operation and return to the relevant prerequisite gate instead of adding speculative systems.

## Standing acceptance and authority
Before implementation inspect latest repository, AGENTS.md, docs/DESIGN.md, the real tests, Founding Design v0.3 and TR001/TR002. One Pep semantic authority; deterministic source-byte spans, typed holes, immutable revisions and versioned tool contracts. The host is trusted local, **not** a hostile-code sandbox. Preserve explicit host capabilities and resource limits. TR002 overrides earlier future C11 references with a **Pep-written C23 generator**, Clang primary and GCC independent verification.

Use focused evidence during work, then full clean Windows suite (report OCaml/MoonBit separately), real examples, negative and adversarial tests, documentation, git diff --check, secret/path review. Publish verified work as a distinct commit to public master; preserve unrelated work, never force-push, report actual SHA/commands/results/limitations. Do not change CURRENT for an unaccepted phase. **This packet remains a provisional design draft until expressly authorised after A8 review.**
