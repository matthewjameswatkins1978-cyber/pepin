# A10: Lexer-driven compiler foundations

**PROVISIONAL DESIGN GATE / NOT YET AUTHORISED TO IMPLEMENT.** This replaces the earlier broad foundation-library wish list with a bounded, executable goal. A8 is accepted; A9 is not a prerequisite. The destination is [A11, a Pep-written lexer](A11-PEP-WRITTEN-LEXER.md).

## Objective and falsifier

Equip ordinary Pep code to read an explicitly authorised original source-byte snapshot and construct a small, accurate token stream with errors in **time and memory that scale reasonably with input size**. Prove the facilities on a real Pep-written lexer slice rather than speculative standard-library completeness. The host may transport bytes and enforce budgets, but must not lex, pre-tokenize, decode away source positions or decide syntax.

## First inspect, then choose

Before changing compiler code:
1. Inventory OCaml scanner API/diagnostics, Pep `List[T]` / `Str` / record / variant behavior, tool protocol v1/v2, interpreter steps and constraints, and tests.
2. Establish corpus and baseline: byte length, token count, cold process startup, warm parse/check latency, run steps/peak memory if measurable, host/message cost and error latency. Distinguish source size from token count and report environment.
3. **Demonstrate or rule out quadratic token construction**: A6 `append(list, item)` is O(n), so repeated append is O(n²) in item count. Compare small alternatives (reverse accumulation / one-pass builder / bounded compiler-known temporary collection / chunked representation) before selecting. Expose an immutable result at the public boundary and explicitly account for work, allocation and serialization. A temporary builder need not imply general mutable lists.
4. Define exact `Bytes` / `Str` contract: original input bytes are the source coordinate system; avoid conflating byte length, Unicode scalar count and display column. Decide how malformed UTF-8 becomes an explicit error, and how LF/CRLF, BOM if supported and embedded NUL are treated from current lexer evidence.
5. Choose minimal fallible operations and typed error representation. `Result[T,E]`, `Option[T]`, `Map[K,V]`, general generics and string builders remain **candidates**, not automatic scope; prefer existing tagged unions/records when adequate.
6. Identify host authority: a revision-selected immutable source-byte value is explicit and bounded, with exact document/revision, no ambient filesystem, network, subprocess or access by guessed ID. Preserve typed holes and incomplete/invalid distinctions.

## Allowed scope after design approval

Only the proven source-byte, scan, error and accumulation primitives needed for an ordinary Pep lexer vertical slice; checked signatures, consistent parser/checker/interpreter behavior, bounded runtime and versioned typed transport. Split into smaller coherent slices if beneficial. Changes must not silently alter A5 v1 scalar tools, A7 v2 semantic snapshots, A8 analyser, immutable document revisions or host-enforced grants.

## Acceptance gate (to be finalised before implementation)

- A **real Pep source** demonstration scans representative bytes into typed token-like records with accurate half-open original UTF-8 spans; no hidden OCaml tokenization.
- Explicit errors for invalid encoding/escapes and EOF boundaries as applicable; Unicode and LF/CRLF fixtures, denied/stale target, oversized input, wrong values/versions and exhausted budget fail deterministically.
- Validated token construction on at least three increasing input sizes (example: 1, 4, 16 KiB) with time and/or charged-work data; distinguish a proven asymptotic failure from noisy wall-clock effects. No unsupported promises of linearity or speed.
- Lexer slice is usable through real checked Pep execution, not a mock JSON array. Test list/record serialization and preserve historical revision identity.
- Full existing Windows suite, separate OCaml / historical MoonBit counts, CLI and JSONL negative paths, byte preservation, git diff --check, secret/path review, evidence capsule and documented new tool limits. Compare changed semantics to the current seed and settle disagreements explicitly.
- Report the chosen construction strategy, rejected alternatives, observed measurements, revisions and what future A11 work remains.

## Non-scope and stop

No big compiler framework, mandatory Salsa/Tree-sitter dependency, full Map/Option/Result ecosystem, arbitrary mutable collections, cross-revision incremental compiler, concurrency, grammar redesign, general IO, native backend or self-hosting. If a dependency/representation materially changes Pep semantics or the authority boundary, stop for a consequential design decision. No code starts solely because this packet exists.

Read [compiler research disposition](../COMPILER_RESEARCH_AND_DECISIONS_2026-10.md), [CURRENT](CURRENT.md), [AGENTS](../../AGENTS.md), [DESIGN](../DESIGN.md), [session protocol](../SESSION_PROTOCOL.md), Founding v0.3, TR001 and TR002 before implementation.
