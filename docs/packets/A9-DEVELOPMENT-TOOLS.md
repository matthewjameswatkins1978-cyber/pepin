# A9: More Pep-written development tools
**PROVISIONAL / NOT YET AUTHORISED.** Depends on accepted A8 and a review of actual semantic API gaps.

## Objective
Prove the first Pep-written linter was not a one-off demo: implement at least two other useful development tools as ordinary Pep functions reusing the compiler semantic interface.

## Candidate scope
- **Unused local binding analyser** using checker-resolved bindings, definition/read identity, shadowing, lexical scopes and byte spans, rather than string search.
- **Dependency/change-impact analyser** tracing resolved function edges outward from a chosen edited function, with explicit direction and root semantics.
- Add only the minimal typed immutable facts absent from A7, such as BindingInfo and ReadEdge, keeping source document and revision scoped, transport versioned and bounded. Prefer compact query results to giant AST dumps.
- Reuse ordinary registration, actual test-vector validation, activation, structured result transport, discovery, revision permissions and failed-hot-replacement fallback. No per-tool OCaml algorithm.

## Acceptance examples
Shadowed same-named variables, unused local, read-only used binding, mutually recursive functions, disconnected cycles, calls via nested expressions; inaccurate or incomplete source must be flagged as nonauthoritative. Both tools run and hot-reload in a real session; checker identity and source spans match the seed. A hostile target or unsupported protocol fails closed. Prove one semantic API supports both algorithms.

## Revisit and non-scope
If A8 exposed a cheaper, higher-value second tool, choose it and record why. No general refactor framework, background monitoring, arbitrary IO, module-wide static reachability claim or LLM. Request an explicit A9 gate after the A8 review.

## Standing acceptance and authority
Before implementation inspect latest repository, AGENTS.md, docs/DESIGN.md, the real tests, Founding Design v0.3 and TR001/TR002. One Pep semantic authority; deterministic source-byte spans, typed holes, immutable revisions and versioned tool contracts. The host is trusted local, **not** a hostile-code sandbox. Preserve explicit host capabilities and resource limits. TR002 overrides earlier future C11 references with a **Pep-written C23 generator**, Clang primary and GCC independent verification.

Use focused evidence during work, then full clean Windows suite (report OCaml/MoonBit separately), real examples, negative and adversarial tests, documentation, git diff --check, secret/path review. Publish verified work as a distinct commit to public master; preserve unrelated work, never force-push, report actual SHA/commands/results/limitations. Do not change CURRENT for an unaccepted phase. **This packet remains a provisional design draft until expressly authorised after A8 review.**
