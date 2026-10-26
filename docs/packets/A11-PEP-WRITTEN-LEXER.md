# A11: Pep-written lexer
**PROVISIONAL / NOT YET AUTHORISED.** Depends on A10 byte/text/Result facilities.

## Objective
Port the language's **lexer algorithm** into ordinary Pep. Execute it under the OCaml interpreter first, using the current OCaml scanner as a differential oracle; never pass pre-tokenised OCaml output to the Pep lexer.

## Contract
- Return typed token kinds, values, original UTF-8 half-open byte spans and structured lexical errors.
- Accept exact original source bytes, preserving LF/CRLF distinctions and documented Unicode column semantics; reject malformed UTF-8 and invalid escapes deterministically.
- Cover implemented syntax, not a fantasy grammar: identifiers, keywords, numbers and overflow, strings and escapes, comments, operators, typed holes, Lists/control flow, functions, records, variants and patterns.
- Separate decoding, token scanning and source-position calculation only where useful. Ordinary Pep data structures and explicit error values; no hidden host lexer, grammar generator or AI parser.

## Acceptance
Golden corpus for every token class, invalid number/escape, EOF boundaries, comments between declarations, multi-byte UTF-8, LF/CRLF, invalid bytes, typed holes and nested expressions. Differential comparisons against OCaml for token kind/value/start-end byte spans/diagnostic kind. Store any counterexample and settle semantic disagreements explicitly. Real Pep source plus interpreter invocation are required; document performance on representative files and budget behavior.

## Stop/non-scope
No parser, type checker, native backend, new syntax for convenience or host-only lexical shortcuts. If Pep lacks a required primitive, return an evidenced minimal A10 repair instead of writing the scanner in OCaml.

## Standing acceptance and authority
Before implementation inspect latest repository, AGENTS.md, docs/DESIGN.md, the real tests, Founding Design v0.3 and TR001/TR002. One Pep semantic authority; deterministic source-byte spans, typed holes, immutable revisions and versioned tool contracts. The host is trusted local, **not** a hostile-code sandbox. Preserve explicit host capabilities and resource limits. TR002 overrides earlier future C11 references with a **Pep-written C23 generator**, Clang primary and GCC independent verification.

Use focused evidence during work, then full clean Windows suite (report OCaml/MoonBit separately), real examples, negative and adversarial tests, documentation, git diff --check, secret/path review. Publish verified work as a distinct commit to public master; preserve unrelated work, never force-push, report actual SHA/commands/results/limitations. Do not change CURRENT for an unaccepted phase. **This packet remains a provisional design draft until expressly authorised after A8 review.**
