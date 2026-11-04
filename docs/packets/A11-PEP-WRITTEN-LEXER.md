# A11: First real Pep-written compiler component, the lexer

**PROVISIONAL / NOT AUTHORISED.** Depends on a *verified* A10 byte-input and efficient token-accumulation slice; a planned packet or abstract library is not sufficient.

## Outcome

In ordinary `.pep` source, scan the original input bytes into typed tokens and structured errors, with the OCaml lexer supplying only the differential oracle. No host-computed token stream. OCaml remains the operational compiler authority during the staged transition.

## Representation and performance rules

- Carry source document/revision and original half-open UTF-8 byte spans through every token/error. Preserve LF vs CRLF, invalid encoding behavior and the current language's line/column semantics separately from byte offsets.
- Use the efficient A10 accumulation path proved by measurement. Avoid repeated immutable `append` when it would copy the growing token list. Keep public results immutable and tool transport bounded.
- Represent token kinds/values with a small, inspectable typed model. Investigate compact token-kind IDs and integer offsets instead of repeating source substrings, but do not invent opaque process-global IDs or break revision-local identities.
- Scanner must exercise implemented Pep grammar (not prospective features): names, keywords, i64 literals and overflow, strings and escapes, comments, operators, holes, Lists, loops, records, variants and match patterns.
- Explicit error/no-progress guarantees at EOF and malformed input. Account for scanning, allocation, token materialization and transport work in budgets; do not hide large loops inside free host builtins.

## Differential acceptance

Run real Pep lexer over a corpus of complete, incomplete and invalid source with escaped strings, adjacent tokens, long strings, integer limits, comments, nested syntax, source positions under Unicode and LF/CRLF, malformed UTF-8 and EOF. Compare token kinds, decoded token values, spans and relevant lexical diagnostics against the existing OCaml lexer. If the seed lacks a suitable token-output hook, add **test-only read-only instrumentation**, not a second production lexer or a runtime bypass.

Measure at multiple file sizes and token densities; report wall-clock/steps/memory where available and growth ratios without inventing claims. Preserve counterexamples, make reference-behavior ambiguities explicit, and fix language inconsistencies by separately accepted resolution, not by copying a bug.

## Exit / stop

A fully checked Pep-written scanner runs in the interpreter and matches the defined corpus with evidence. This **does not** make Pep self-hosting or replace the OCaml production lexer. A12 parser remains a separate approval gate. If Pep lacks a primitive, return a narrow evidenced A10 change. No forced conversion to Tree-sitter or wholesale grammar replacement.

For standing authority and verification, read [CURRENT](CURRENT.md), [packet index](README.md), [research](../COMPILER_RESEARCH_AND_DECISIONS_2026-10.md), AGENTS, DESIGN, session protocol and TR001/TR002. Record tested commit SHAs, real suite counts and limitations; push development slices without treating checkpoints as merge approval.
