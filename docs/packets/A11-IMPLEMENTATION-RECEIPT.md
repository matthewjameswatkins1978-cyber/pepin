# A11 development receipt: Pep-written lexer

**Status: implementation candidate; not accepted.** This receipt records the A11 development branch and evidence. It does not advance `CURRENT.md` or the packet manifest, grant A12 authority, merge prerequisite pull requests, or claim that the OCaml compiler has been replaced.

## Implementation identity

- Repository: [matthewjameswatkins1978-cyber/pepin](https://github.com/matthewjameswatkins1978-cyber/pepin)
- Branch: `a11/complete-pep-lexer`
- A11 implementation commit: `5a863686b2aa017154357acf991c460a96dc030e`; A11-R1 hardening commit: `d63837cf9bf0db90f58051a6395822c7f48ca55b`; reviewed PR #3 SHA: `fcfd600dedebc2c89718fab69b5e0316754cadd4`.
- Base: reviewed A10 implementation `ef088c1869f4c97fe935817f8f17b7654b96dc25`
- Current master remains A8 at `4132d3f953a370b0837d9a20fc73067f7f0c666f`.
- Roadmap PR #1 (`docs/lexer-first-roadmap-2026-10-26`) and A10 PR #2 (`a10/pep-written-lexer`) were verified open and unmerged. This work changes neither PR nor master.

## What the Pep program does

[`examples/pep_lexer.pep`](../../examples/pep_lexer.pep) implements `lexer_start` and resumable `lexer_step` in Pep. The host supplies the selected original source bytes through the existing schema-v3 session and version-2 tool protocol. Each result carries the target document and revision; the tool implementation revision remains separately reported by the host. A cursor is ordinary typed data bound to that target revision, not an authority token. The existing host grant remains the authority boundary.

Starting from `lexer_start`, the cooperative path validates the complete source as UTF-8, then scans in 32-byte work chunks per invocation. A caller-made scan-stage cursor can skip validation; this is documented and tested below. It returns typed `LexProgress` and `LexToken` records, original half-open byte spans, one-based line/column, decoded integer and hole data, structured diagnostics, and EOF. String contents are represented as ordered decoded `List[Str]` parts so Pep does not need a new string-concatenation primitive. Token lists use O(1) `prepend` and one `reverse` per chunk; escaped string parts are accumulated the same way and reversed when the string closes.

Coverage is differential against the existing OCaml lexer, which remains the production authority. A test-only oracle is generated under ignored `_build/a11/` from the existing OCaml lexer source. No production OCaml tokenization is called by the Pep scanner.

## Verification actually run

- Clean OCaml 5.5.2 build in `_build/a11-clean/`, followed by `pep.exe --help`: passed.
- `python -m unittest tests.test_a11 -v`: **7/7 passed**.
- `python -m unittest discover -s tests -v`: **93/93 passed** in 104.484 seconds: **82 non-MoonBit tests plus 11 historical MoonBit tests**. The MoonBit tests are included in this total.
- `python -m unittest discover -s tests -p 'test_moonbit_cli.py' -v`: **11/11 passed** independently; it reruns the same historical tests and adds no unique tests to the 93/93 total.
- `.\pep.ps1 check examples\pep_lexer.pep --json`: returned `status: valid`.
- `git diff --check`: passed on the A11-R1 final candidate before publication.
- The complete A11 differential suite compared **162 inputs: 162 matches, 0 mismatches**: 29 fixed lexical/error vectors, 60 deterministic generated inputs, all 53 byte prefixes of a 52-byte boundary source, 14 controlled 32-byte edge fixtures, and 6 repository Pep examples. It compares token kinds/values, byte spans, line/column and diagnostics. Edge fixtures cover valid, malformed and truncated UTF-8; two-byte operators; identifiers and named holes; string escapes, unterminated strings and quote termination; i64 limit and overflow; LF/CRLF comments; and EOF transitions. Every nonterminal result must differ from its input cursor.

## Performance observations

Command: `python tests\benchmark_a11_lexer.py`. It runs three trials per case in a warm, persistent Windows schema-v3 JSONL session. The wall times below include Pep tool execution **and** JSONL serialization/pipe transport; they are not interpreter-only timings. The response-byte total is the sum of JSON responses for one run. The 268.01 ms session-start observation measures process-spawn call duration only, not time to a ready compiler. `openMs` separately includes opening the original-byte target. Peak memory and exact interpreter step counts are not exposed by the current runtime, so neither is claimed.

| Input | Bytes | Tokens | Validate / scan calls | Median warm lexer time | Response bytes |
|---|---:|---:|---:|---:|---:|
| `name ` × 16 | 80 | 17 | 3 / 3 | 2.71 ms | 21,039 |
| `name ` × 64 | 320 | 65 | 11 / 11 | 12.71 ms | 75,396 |
| `name ` × 256 | 1,280 | 257 | 41 / 41 | 37.00 ms | 285,520 |
| `name ` × 1,024 | 5,120 | 1,025 | 161 / 161 | 147.89 ms | 1,127,944 |
| Dense `+,` | 4,096 | 4,097 | 129 / 129 | 264.86 ms | 2,476,484 |
| Unescaped string | 16,386 | 2 | 513 / 513 | 351.80 ms | 2,006,609 |
| A8 analyser example | 2,077 | 292 | 65 / 65 | 57.43 ms | 394,936 |
| Pep lexer source | 18,696 | 3,605 | 585 / 584 | 611.62 ms | 4,026,754 |

The identifier series grows broadly in proportion to bytes and tokens in this harness (80 to 5,120 input bytes: 64×; 2.71 to 147.89 ms: about 55×). This is a small three-trial measurement, not a general complexity proof. The largest exercised real source was 18,696 bytes and completed in 1,169 lexer-step calls. Transport volume is substantial because each resumable result returns typed tokens and a cursor. There is no measured fixed maximum input size here; larger sources cost more host round trips and serialized output. The existing per-invocation 100,000-step budget was not raised. The 32-byte work chunk bounds each invocation; the harness also fails after 3,000 resumptions. R1 changed only lexer comments and test/documentation code, so scanner-execution benchmark results are inherited and were not rerun.

## Remaining boundaries and A12 handoff

**Cursor contract:** `LexCursor` is ordinary caller-supplied typed data. A complete validated token stream is meaningful only when one cooperative caller starts with `lexer_start`, then passes each exact cursor returned by `lexer_step` to the next call for the same host-selected document and revision. A matching revision binds the source; it does not prove cursor history. Tests demonstrate that a forged `stage = "scan"` cursor can skip invalid byte 0 and scan a valid suffix, while a forged `stage = "done"` cursor can return completion with no tokens. Those results do not prove whole-source validation or a complete token stream. This is not a host-authority bypass: `semanticTarget` still selects the source bytes. No cryptographic cursor or session manager was added.

**A12 token-consumer contract:** A12 should initialize its own parser/lexer chain, retain and forward only the exact prior continuation for the same document and revision, and never accept an externally supplied cursor or `done` result as proof. Parse the token batch in each progress result; do not add a host round trip for every token or AST node. The measured A11 source used 1,169 calls and about 4.03 MB of responses, so A12 must measure combined lexer/parser calls, response bytes and per-call budgets before selecting batching. This remains a cooperative local tool contract, not a sandbox or authenticated stream. The existing [A12 parser packet](A12-PEP-WRITTEN-PARSER.md) remains provisional; no parser implementation has begun.

## Acceptance state

This is a pushed development candidate, not formal A11 acceptance. The A11 branch is separately reviewable at the SHA above. No acceptance record has been added to `CURRENT.md` or `manifest.json`; the repository's canonical pointer remains A8 until Matthew's acceptance and the prerequisite integration state are resolved.
