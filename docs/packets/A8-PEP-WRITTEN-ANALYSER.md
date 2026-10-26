# A8: First compiler-aware development tool written in Pep
**Status: COMPLETED.** Published in [da24441](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/da244417c45a961728181a17ad31581e4d5a21de). A8 closes the already scoped A6–A8 campaign; the repository now pauses for design and priority review.

## Objective
Implement **unused-function reachability analysis in ordinary Pep source** and run it through the existing versioned tool registry. The host supplies immutable checked facts, but **does not compute the answer**.

## Contract
- Read authorised ProgramInfo at exact target revision. Start with resolved root function IDs and repeatedly traverse CallEdge values until reachable set stabilises; report all other functions. Disconnected chains and mutually recursive cycles are unreachable. Reachable recursion is not erroneously flagged.
- Build an ordered **List[Finding]** (monomorphic record): kind = unreachable_function; revision-local symbol ID; function name; original source start/end byte offsets; explanation. Sort by declaration position. The tool response also identifies tool implementation revision, target revision, root policy, and protocol.
- Report **unreachable under declared roots**, not universal dead code. For incomplete/invalid targets do not silently assume missing calls are absent.
- The algorithm must live in .pep source, traverse Lists using A6 and consume facts from A7. No duplicate Pep parser, textual occurrence counter, OCaml reachability shortcut, or hand-crafted mock result.

## End-to-end acceptance journey
1. Open target containing entry→helper, an isolated orphan, and orphan_a↔orphan_b disconnected cycle. With entry as root, exactly the three disconnected functions are findings; correct IDs and byte spans. A naive textual reference counter must fail this case while the Pep algorithm passes.
2. Open the analyzer .pep implementation in the same live session. Derive its signature with checker, register it, run **real** test vectors on independently specified fixtures, explicitly activate, discover with tool_list and invoke through v2 structured transport.
3. Create target revision making one orphan reachable. New query changes findings; old retained revision gives old findings. Tool revision remains independent.
4. Hot replace tool from a newly checked revision in the *same* session; validate, activate and observe new tool revision. Submit incompatible/invalid/incomplete/failing-vector replacement and prove previous active revision still works.
5. Parse every session response as JSON. Demonstrate resource exhaustion, direct/transitive say and unauthorised target are correctly rejected.

## Fixture matrix
All reachable; one disconnected function; disconnected chain; disconnected mutual recursion; self recursion with/without root; direct top-level invocation; explicit entry root; unknown/ambiguous root; no-root policy disclosed; invalid/incomplete source refused as authoritative; UTF-8/CRLF spans; historical revision; duplicate textual spellings and constructor-vs-function disambiguation.

## Non-scope
Auto-delete, project-wide module graph, generalized refactoring, arbitrary FS access, LLM analysis, C23 backend, self-hosting. This is a first **self-development** proof, not self-hosting.

## Shared engineering contract
Read [founding design](../FOUNDING_DESIGN_v0.3.md), [TR001](../TECHNICAL_RESOLUTION_001.md), [TR002](../TECHNICAL_RESOLUTION_002.md), [implementation status](../DESIGN.md), [session protocol](../SESSION_PROTOCOL.md) and AGENTS.md before changing code. The latest accepted rules override speculative examples. **TR002 replaces the planned C11 generator with a Pep-written C23 generator** (Clang primary, GCC independent verification). Historical MoonBit C11 stays historical.

One compiler-owned syntax/type/scope authority. Preserve bidirectional typing, valid/incomplete/invalid, typed holes, exact original UTF-8 byte spans, LF/CRLF, immutable revisioned snapshots, checked editing and deterministic versioned JSON. The A5 tool host is **trusted local, not a security sandbox**: no ambient IO or process access, runtime budgets, transitive say denial and activation rollback must remain enforced.

Use focused checks while coding; at phase gate run clean OCaml build and full Windows CLI suite, with OCaml/MoonBit counts separate, plus real JSONL tests, negative/adversarial cases, git diff --check, secret/local-path review. Publish one coherent verified phase to public master without force-pushing or disturbing unrelated work; record public SHA, evidence, limitations and decisions. Only advance CURRENT after verified acceptance. Escalate semantic conflict, destructive work, material new dependencies or security/acceptance blockers, not routine reversible details.

## Acceptance receipt and pause

- Published implementation: [da244417c45a961728181a17ad31581e4d5a21de](https://github.com/matthewjameswatkins1978-cyber/pepin/commit/da244417c45a961728181a17ad31581e4d5a21de). Pep analyzer source: [`examples/unused_functions.pep`](../../examples/unused_functions.pep); end-to-end tests: [`tests/test_a8.py`](../../tests/test_a8.py).
- In one JSONL session, the suite checked and registered the analyzer, validated independently specified vectors, activated/listed/invoked it over protocol v2, exercised retained target revisions and stable tool revision, and hot-replaced the analyzer with an independently revised implementation.
- The matrix covered all-reachable and no-root cases, disconnected functions/chains/cycles, reachable and unrooted recursion, direct and explicit roots, constructor-versus-function edges, call-like text, UTF-8/CRLF byte spans, invalid/incomplete targets, unknown and duplicate roots, unauthorised documents, direct/transitive `say`, invalid/incomplete/incompatible/failing-vector replacements, rollback, and bounded exhaustion. Session output was parsed as JSON.
- Verification: clean OCaml 5.5.2 build and hello check/run smoke passed; **55/55 primary OCaml/A7/A8 tests** passed; **11/11 historical MoonBit tests** passed; `git diff --check` passed; reviewed changed files for credentials and local machine paths.
- Limits: findings mean unreachable under `top_level_calls_plus_host_entry_functions`, not universal dead code. Invalid/incomplete targets return non-authoritative results. Large reports can return a structured runtime budget error rather than partial findings. The analyzer is an ordinary Pep example invoked through the trusted-local tool host; it is not a built-in CLI command, sandbox, general project analyzer, or self-hosted compiler.

**After A8, stop for design and priority review. A9–A15 remain provisional and are not authorised by their presence.**
