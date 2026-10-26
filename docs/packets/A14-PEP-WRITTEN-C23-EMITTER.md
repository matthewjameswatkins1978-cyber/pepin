# A14: Pep-written C23 emitter
**PROVISIONAL / NOT YET AUTHORISED.** Depends on accepted A11–A13 and interpreter/runtime conformance baseline.

## Objective
Write a compiler backend **as Pep source** that emits valid, portable C23 for an explicitly supported Pep subset, with observable behaviour conforming to the established Pep checker and interpreter.

## Contract
- Consume an approved checked Pep representation. Choose a minimal explicit lowering/ABI strategy for checked Int64, Bool, Str/UTF-8, Unit, immutable records, recursive variants, Lists, match, loops, calls and controlled errors. Avoid silently dropping unsupported constructs or hiding helper algorithms in a new OCaml emitter.
- Generate canonical deterministic C23 text with no mandatory compiler extensions or silent fallback to C11/gnu23.
- Verify actual installed toolchains. TR002 declares **Clang primary and GCC independent cross-check**; use strict -std=c23, documented feature probes, warnings and linker/runtime assumptions. Clang 23.1.4 and GCC 16 were planning baselines, not automatic claims of availability or support.
- Build and execute sample generated code, comparing output, value semantics, integer overflow/division errors, recursive/match behaviour, UTF-8 handling, collections and conditions to interpreter. Document remaining supported/unsupported surface honestly.
- Maintain exact reproducibility of emitted source for identical checked inputs; avoid user-machine paths/timestamps in generated canonical artifacts.

## Acceptance
A Pep-written emitter running under the OCaml interpreter generates C23 that compiles and executes with Clang and GCC for a substantial pinned test corpus. Compiler disagreements investigated with isolated reproducer and documented semantic verdict. Unsupported Pep programs give structured compiler diagnostics, not wrong C. No native-backend capability claim until tests pass.

## Stop/non-scope
No self-hosting claim yet, LLVM-only IR, custom VM, OCaml-based emitter masquerading as Pep, arbitrary C extensions or rollback to historic C11.

## Standing acceptance and authority
Before implementation inspect latest repository, AGENTS.md, docs/DESIGN.md, the real tests, Founding Design v0.3 and TR001/TR002. One Pep semantic authority; deterministic source-byte spans, typed holes, immutable revisions and versioned tool contracts. The host is trusted local, **not** a hostile-code sandbox. Preserve explicit host capabilities and resource limits. TR002 overrides earlier future C11 references with a **Pep-written C23 generator**, Clang primary and GCC independent verification.

Use focused evidence during work, then full clean Windows suite (report OCaml/MoonBit separately), real examples, negative and adversarial tests, documentation, git diff --check, secret/path review. Publish verified work as a distinct commit to public master; preserve unrelated work, never force-push, report actual SHA/commands/results/limitations. Do not change CURRENT for an unaccepted phase. **This packet remains a provisional design draft until expressly authorised after A8 review.**
