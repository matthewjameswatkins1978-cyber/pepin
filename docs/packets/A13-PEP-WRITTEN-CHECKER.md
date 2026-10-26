# A13: Pep-written name resolution and type checking
**PROVISIONAL / NOT YET AUTHORISED.** Depends on A12 parser and its actual checked grammar. May be split into resolver/type-checker gates after review.

## Objective
Demonstrate that Pep can state and enforce its **own semantic rules** in Pep rather than depending permanently on OCaml's checker.

## Contract

The existing A12 syntax node fields, topology, source-span limits, and cooperative cursor-consumption contract are documented in [A12–A13 Flat AST and continuation contract](A12-A13-FLAT-AST-CONTRACT.md).

- Reproduce lexical binding/function identity, scopes, shadowing, call resolution (including forward and recursive calls), constructor-vs-function distinctions, fields and pattern variables.
- Implement explicit **synth(env, expr)** and **check(env, expr, expected)** operations, without pretending a general Hindley–Milner engine is required. Propagate expected types into annotated let, call arguments, return positions, match arms and lists.
- Produce partial checked expressions with typed/named holes, visible compatible bindings and original source spans; preserve valid/incomplete/invalid distinction and refusal to execute incomplete programs.
- Support compiler-owned revision-scoped symbol IDs, deterministic diagnostics, immutable query results, and the semantic function call edges relied upon by A7/A8.
- Use ordinary Pep source, A11 lexer and A12 AST; not an OCaml typed-tree oracle handed to a Pep wrapper.

## Acceptance
Differential corpus against OCaml: working recursion, shadows and scopes, nested variants/matches, lists/loops, missing returns, wrong argument count/types, non-exhaustive match, unreachable arm, underconstrained hole, typed hole, constructor disambiguation, original UTF-8/LF/CRLF byte positions. Compare **semantic facts** and diagnostics, not only execution results. If OCaml behaviour conflicts with canonical specification, file a concrete resolution, do not copy a bug blindly.

## Non-scope and stop
No independent host checker disguised as a Pep tool; no self-hosting claim before compiler chain. If missing data abstractions prevent implementation, fix the narrow Pep-language gap with measured tests, rather than expanding framework speculatively.

## Standing acceptance and authority
Before implementation inspect latest repository, AGENTS.md, docs/DESIGN.md, the real tests, Founding Design v0.3 and TR001/TR002. One Pep semantic authority; deterministic source-byte spans, typed holes, immutable revisions and versioned tool contracts. The host is trusted local, **not** a hostile-code sandbox. Preserve explicit host capabilities and resource limits. TR002 overrides earlier future C11 references with a **Pep-written C23 generator**, Clang primary and GCC independent verification.

Use focused evidence during work, then full clean Windows suite (report OCaml/MoonBit separately), real examples, negative and adversarial tests, documentation, git diff --check, secret/path review. Publish verified work as a distinct commit to public master; preserve unrelated work, never force-push, report actual SHA/commands/results/limitations. Do not change CURRENT for an unaccepted phase. **This packet remains a provisional design draft until expressly authorised after A8 review.**
