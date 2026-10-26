# A12: Pep-written parser and source-spanned AST
**PROVISIONAL / NOT YET AUTHORISED.** Depends on accepted A11 lexer.

## Objective
Write a complete enough Pep parser in Pep to reproduce the OCaml seed's supported source grammar and retain holes and exact source locations.

## Contract
- Consume Pep-lexer tokens, not a pre-parsed host representation. Represent AST as Pep records/tagged unions/Lists, with exact original byte spans, names, source revision and typed holes as real nodes.
- Specify operator precedence, associativity, typed annotations, declarations and recursive types, call forms, records, variants, nested patterns, list/control-flow forms and the distinction between if expression and if statement.
- Preserve comments and untouched original source bytes for structural editing through separate source storage; do not claim round-trip source fidelity from a pretty-printed AST.
- Parse valid, incomplete and invalid input with structured errors; choose bounded recovery vs explicit fail-fast based on existing implementation and tests, not novelty.
- Expose a deterministic typed AST serialization for differential checks.

## Acceptance
Real A11→A12 Pep pipeline on valid/incomplete/invalid golden corpus, including nested matches, typed holes, forward declarations, ambiguous syntax boundaries, malformed delimiters, Unicode/CRLF, string escapes and empty lists. Compare AST meaning and spans with OCaml parser; do not overfit JSON incidental ordering. The old OCaml parser remains production oracle until equivalence is demonstrated.

## Non-scope
Pep-written checker, expression evaluator, native emitter, formatter, new general AST database, compile-time macros or parser-generator ecosystem.

## Standing acceptance and authority
Before implementation inspect latest repository, AGENTS.md, docs/DESIGN.md, the real tests, Founding Design v0.3 and TR001/TR002. One Pep semantic authority; deterministic source-byte spans, typed holes, immutable revisions and versioned tool contracts. The host is trusted local, **not** a hostile-code sandbox. Preserve explicit host capabilities and resource limits. TR002 overrides earlier future C11 references with a **Pep-written C23 generator**, Clang primary and GCC independent verification.

Use focused evidence during work, then full clean Windows suite (report OCaml/MoonBit separately), real examples, negative and adversarial tests, documentation, git diff --check, secret/path review. Publish verified work as a distinct commit to public master; preserve unrelated work, never force-push, report actual SHA/commands/results/limitations. Do not change CURRENT for an unaccepted phase. **This packet remains a provisional design draft until expressly authorised after A8 review.**
