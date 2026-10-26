# Pepin implementation packets

Begin every implementation/handoff at [CURRENT.md](CURRENT.md). GitHub code/tests and published receipts, not packet titles, establish implemented truth. Founding Design v0.3 + TR001/TR002 remain binding; future native target is **Pep-written C23**.

| Stage | Packet | Implementation status | Roadmap priority / dependency |
|---|---|---|---|
| A6 | [Collections and control flow](A6-COLLECTIONS-AND-CONTROL-FLOW.md) | Completed | A5 |
| A7 | [Typed semantic API](A7-TYPED-SEMANTIC-API.md) | Completed | A6 |
| A8 | [Pep-written analyser](A8-PEP-WRITTEN-ANALYSER.md) | Completed | A7 |
| A9 | [More Pep tools](A9-DEVELOPMENT-TOOLS.md) | Provisional | **Deferred**; return only for specific demonstrated utility |
| A10 | [Lexer-driven compiler foundations](A10-COMPILER-FOUNDATION-LIBRARY.md) | Provisional | **Next recommended design gate**; follows accepted A8 |
| A11 | [Pep-written lexer](A11-PEP-WRITTEN-LEXER.md) | Provisional | First compiler-written-in-Pep target; depends on measured A10 proof |
| A12 | [Pep-written parser](A12-PEP-WRITTEN-PARSER.md) | Provisional | Depends on A11 |
| A13 | [Pep-written checker](A13-PEP-WRITTEN-CHECKER.md) | Provisional | Depends on A12; may split resolution/checking |
| A14 | [Pep-written C23 emitter](A14-PEP-WRITTEN-C23-EMITTER.md) | Provisional | Depends on sufficient checked Pep implementation |
| A15 | [Staged self-hosting](A15-STAGED-SELF-HOSTING.md) | Provisional | Depends on accepted A14 and reproducible bootstrap |

**Status rules:** `completed` means published implementation and verified acceptance evidence. `provisional` means a revisable contract, not permission to implement. `manifest.current: null` means no implementation packet is currently authorised. This roadmap review changes **priority**, not implementation status. The accepted A6–A8 test records remain attached to their original SHAs, not to later documentation commits.

## Design logic after A8

A8 proved Pep can operate on compiler-supplied semantic facts. Another two example linters are not the highest-value next experiment. Instead, pursue a real Pep-written compiler component. A10 is deliberately narrow: the byte/text, error and linear token-accumulation facilities that enable A11, with an executable lexer slice as the falsifier. Avoid adding Map/Option/Result, general generics, mutable shared ASTs, syntax or broad IO merely because a roadmap once listed them. Every primitive must justify itself against actual compiler code and verified tests.

Performance should be designed *for* from the beginning, not claimed early. Record cold startup separately from warm sessions, lexer work and bytes/tokens, peak memory, allocation/step costs, error latency, and JSON transport overhead. Demonstrate how costs scale across at least multiple input sizes; check semantics against a fresh full analysis before any cross-revision reuse. Reserve incremental parsing and cached dependency queries for later measured gates, without importing Salsa, Tree-sitter or LLVM as automatic dependencies.

Reference study: [compiler research and decisions, October 2026](../COMPILER_RESEARCH_AND_DECISIONS_2026-10.md). Candidate approaches are research, not features.

## Worker and acceptance procedure

1. Read [CURRENT](CURRENT.md), inspect repository HEAD and current implementation, then read the individual packet, AGENTS, DESIGN, protocol and technical resolutions. Check local capability and mature prior art before designing machinery.
2. **Only start implementation when a phase is explicitly authorised.** Work in coherent, targeted-tested slices; commit and push a development branch after each slice. Nonblocking review follows Matthew Way's three-slice cadence; a push does not request approval or imply merge rights.
3. Use proportionate checks during development and a clean build, full primary/historical Windows suites, actual CLI/session examples, negative tests, byte-span/revision checks, resource limit checks and `git diff --check` at phase acceptance. Preserve unrelated changes and never force-push shared master.
4. Publish a verified accepted phase with exact SHA, actual test counts, limitations, compatibility and affected evidence. Only then update `CURRENT.md` and `manifest.json` together and move `lastAccepted` by one accepted milestone. If blocked, do not advance.
5. Matthew retains product and consequential acceptance. Lucy independently reviews implementation claims; tests reported by builders are not misrepresented as independently rerun. The local tool host remains **trusted, not a sandbox**.

Historical MoonBit C11 is reference work; C23/Clang/GCC is future, not currently shipped. No native Pep backend, sandbox, package ecosystem or self-hosting claim follows from these plans.
