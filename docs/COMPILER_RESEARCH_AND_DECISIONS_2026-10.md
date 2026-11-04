# Compiler architecture research and design disposition — 26 October 2026

**Status:** evidence-informed design input for the *next gate*, not implementation proof or an automatic new dependency. Baseline: A8 accepted at `da244417c45a961728181a17ad31581e4d5a21de`; acceptance/pause on `master` at `4132d3f953a370b0837d9a20fc73067f7f0c666f`. [CURRENT](packets/CURRENT.md) is the canonical live pointer.

## Project-specific observations (verified from repository docs/code)

- Pepin uses OCaml 5.5.2 interpreter/checker, immutable revisioned in-process session analysis, original UTF-8 byte offsets, typed holes and source-preserving edits. Each changed revision is currently **fully re-parsed/rechecked**; caching is for repeated *identical* revisions only.
- A6 compiler-known `List[T]` is immutable and `append` is **O(n)** by design. Building n lexer tokens by repeated append can incur O(n²) copying. It is a performance **risk**, not a benchmark result. The trusted tool interpreter has a 100,000-step/128-depth budget; the ordinary CLI differs.
- A7 exports versioned, immutable typed `ProgramInfo` / `FunctionInfo` / `CallEdge` snapshots from the checker under explicit host-authorised document and retained revision. V1 scalar messages stay supported; v2 permits bounded monomorphic records and lists.
- A8 is an actual Pep-written unused-function reachability tool using semantic facts; no host reachability shortcut. Its published Windows acceptance record reports **55 primary + 11 historical MoonBit tests**, not independently rerun by this documentation review. It establishes **self-extension**, not parser/compiler self-hosting.
- No Pep-written lexer/parser/checker, cross-revision incremental compiler, native C23 backend or enforceable untrusted-extension sandbox currently exists.

## External sources, useful ideas and explicit disposition

1. **rust-analyzer's compiler architecture** keeps a per-file syntax tree and a compact item summary (`ItemTree`) distinct from function `Body`; changing a function body need not invalidate unrelated declaration data. **Borrow later:** declaration/body dependency boundaries and stable revision-scoped IDs, not a new HIR framework for A10. Source: https://rust-analyzer.github.io/book/contributing/architecture.html
2. **Salsa** tracks dependencies of pure queries and checks whether inputs changed before reusing results. **Borrow later:** query-level dependency and invalidation tests only after measuring meaningful repeat-edit cost; do not adopt the Rust Salsa implementation inside the OCaml seed by default. Sources: https://github.com/salsa-rs/salsa/blob/master/book/src/reference/algorithm.md and https://docs.rs/salsa/latest/salsa/
3. **Tree-sitter** updates old syntax trees after byte/range edits and reuses unaffected structure during incremental reparsing. **Borrow later:** source-preserving revision models and structural sharing ideas, not a parallel Pep grammar or new production parser before a proven benefit. Source: https://github.com/tree-sitter/tree-sitter/blob/master/docs/src/using-parsers/3-advanced-parsing.md
4. **Zig 0.16.0** (released April 14, 2026) separates fast incremental error feedback from expensive LLVM object generation. Crucially Zig's release notes say its incremental mode still had miscompilation bugs and was disabled by default. **Lesson:** preserve fresh-analysis differential oracles and never advertise incremental correctness or speed until proven. Sources: https://ziglang.org/news/0.16.0-released/ and https://ziglang.org/download/0.16.0/release-notes.html
5. **QBE 1.3** (June 2026) added Windows ABI support and optimisations in a small native backend. The upstream author cautions that the assembler/Windows workflow was not fully tested locally. **Revisit at A14 only:** small-backend alternative benchmark if C23/Clang is shown inadequate; do not silently replace binding C23 target. Sources: https://c9x.me/compile/releases.html and https://c9x.me/compile/release/qbe-1.3.html

No external licence or third-party source has been vendored by this research. Proven algorithms and architectural ideas may be credited and adapted after targeted review.

## Decisions for the next packet review

**Now:** target a correctness-first, *measured* lexer-first foundation (A10 → A11). Specify explicit immutable source bytes + revision, typed fallible scan result, an efficient but bounded token accumulation mechanism, stable spans and host authority. Do not assume general Map/Option/Result or generic collections are necessary; establish missing uses in concrete Pep lexer code first.

**Measure before choosing:** cold launch vs warm session; parse/check/token scan separately when instrumented; steps, allocations/peak memory when measurable; original bytes, token density, input sizes and token count; JSON serialization; error diagnostics latency. Compare 3+ sizes and repeated runs. A6's append is analytically quadratic if repeated at every token, but the relative speed of any replacement is not known until measurement. If a temporary builder is justified, keep it scoped, budget-charged and hidden behind immutable output.

**Later:** only if real edit workloads justify it, explore function-level semantic query dependency boundaries (rust-analyzer/Salsa) and persistent syntax structural sharing (Tree-sitter) under full-recheck differential tests. Evaluate native backend alternatives (QBE/Cranelift) against the accepted C23 path at A14, not now.

**What we refuse to infer:** accuracy from a cache hit, universal dead-code findings from A8, memory safety from typed input, sandboxing from trusted-local host checks, native compilation from C23 planning, or benchmark speed-ups from other projects.

## Gate and ownership

Matthew retains substantive product choice and consequential acceptance. Lucy can refine a proposed packet and independently inspect SHA-bound evidence. Agents may only implement an expressly authorised phase, make reversible local decisions inside it, commit/push coherent feature-branch slices and submit actual verification. A9 remains deferred; A10 is the next *design/authorisation* gate with A11 as immediate proof target. [Packet index](packets/README.md) and [manifest](packets/manifest.json) carry the status.
