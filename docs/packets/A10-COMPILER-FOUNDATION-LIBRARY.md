# A10: Compiler-capable Pep library and bounded input
**PROVISIONAL / NOT YET AUTHORISED.** Depends on evidence from accepted A6–A8; A9 may provide useful additional requirements but is not inherently prerequisite.

## Objective
Equip Pep with the small set of data, text and fallible operations genuinely necessary to write its lexer, parser, checker and C23 generator **in Pep**, rather than disguising them as large OCaml builtins.

## Candidate scope
- Add compiler-privileged **Map[K,V]**, **Option[T]**, **Result[T,E]** only with documented key/equality constraints, immutable semantics and fully defined typing. List[T] originates at A6. No arbitrary user generics or undocumented type-class system.
- Provide explicit **Str vs Bytes** semantics, byte slicing, UTF-8 decoding/errors, concatenation or bounded builders, integer conversion and raw original-byte offsets. Errors should be typed results, not silent sentinels.
- A minimal, explicit **host source-input** operation, ideally supplying immutable source snapshots from an authorised session. Avoid ambient filesystem, network, environment or process access. If real file read is necessary, make it host granted, bounded, auditable and non-ambient.
- Resource-budget limits for collection operations, source decoding, string construction and structured serialization. A compiler written in Pep needs scalable but predictable allocations, not an unaccounted built-in escape.

## Acceptance
Write an ordinary Pep function that accepts source bytes, decodes a representative input, constructs token-like records using collections and returns a structured result/error with correct original UTF-8 spans. Test invalid encodings, denied input, oversized data, duplicate Map keys where defined, missing Option, Result propagation, nested containers and LF/CRLF positions. Verify type errors and backwards compatibility with A5/A7 extension protocols. Demonstrate every blessed primitive's concrete compiler use case.

## Design gate
First list language gaps observed in A8/A9 (where available). Remove any primitive without a demonstrated need; choose syntax, host signature and complexity before implementation. This is a library foundation, not a standard library ecosystem.

## Standing acceptance and authority
Before implementation inspect latest repository, AGENTS.md, docs/DESIGN.md, the real tests, Founding Design v0.3 and TR001/TR002. One Pep semantic authority; deterministic source-byte spans, typed holes, immutable revisions and versioned tool contracts. The host is trusted local, **not** a hostile-code sandbox. Preserve explicit host capabilities and resource limits. TR002 overrides earlier future C11 references with a **Pep-written C23 generator**, Clang primary and GCC independent verification.

Use focused evidence during work, then full clean Windows suite (report OCaml/MoonBit separately), real examples, negative and adversarial tests, documentation, git diff --check, secret/path review. Publish verified work as a distinct commit to public master; preserve unrelated work, never force-push, report actual SHA/commands/results/limitations. Do not change CURRENT for an unaccepted phase. **This packet remains a provisional design draft until expressly authorised after A8 review.**
