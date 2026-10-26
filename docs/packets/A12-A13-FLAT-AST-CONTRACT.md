# A12–A13 Flat AST and continuation contract

This note describes the current A12 Pep-written parser result used as A13's syntax input. It is a consumer contract and an evidence boundary; it does not authorise or implement A13.

## `FlatAstNode`

Each node carries `id`, `parentId`, `childIndex`, `role`, `kind`, typed scalar payload fields (`text`, `integerValue`, `booleanValue`, `stringParts`), and source coordinates (`startByte`, `endByte`, `line`, `column`). `kind` identifies syntax. It does not identify a resolved binding, function, constructor, field, or type.

- IDs are zero-based, unique and contiguous for a complete parse of one exact source revision. Their intended order is deterministic AST preorder. Function nodes may be emitted in a later `ParserChunk` than their lower-ID header/body nodes; a consumer must collect chunks and order by `id`, not assume chunk arrival is preorder.
- A top-level root has `parentId = -1`, `role = "top_level"`, and a zero-based `childIndex` in source order across functions and declarations. Other nodes refer to an existing parent ID. `childIndex` is local to a role: repeated children in one role are numbered from zero; fixed slots may use their semantic slot (for example, a match arm's `result` is index 1).
- Roles distinguish grammar relationships: function `parameter`, `return_type`, and `statement`; binary `left`/`right`; conditional `condition`/`then`/`else`; match `value`/`arm`, then arm `pattern`/`result`; and declaration, record-field, loop, list, call, and pattern child roles. Parent plus role plus index defines the edge; preorder alone does not.
- Integer, Boolean, and string contents use their corresponding typed fields. Names, operators, declaration labels, and other compact syntax labels use `text`; unused payload fields remain defaults. Type syntax is represented as `type_scalar`, `type_named`, or recursive `type_list` nodes.
- Byte positions refer to the exact original source revision and are half-open. LF and CRLF remain distinct bytes. The node also carries the parser's line and column at its start. The current OCaml CLI AST JSON omits explicit type-node spans, so the A12 differential currently does not independently verify those particular spans; A13 must not treat that omitted comparison as span proof.

`ParserChunk.document` and `ParserChunk.revision` identify the host-selected semantic target used for that invocation. The revision is content-addressed from exact original bytes. These are separate from the immutable source revision that registered the Pep tool.

## Cooperative continuation consumption

`ParserCursor` is ordinary caller-supplied typed data, not an authenticated validation certificate. A caller can forge `done = true` and obtain a terminal-looking empty chunk, or provide inconsistent nested lexer state. The outer document/revision check and `source_bytes()` host grant remain tied to the invocation's `semanticTarget`; cursor fields do not grant access to another document or revision.

A complete, meaningful parser result is established only by a responsible consumer that:

1. Invokes `parser_start` with an authorised `semanticTarget`.
2. Passes each exact cursor returned by `parser_start` or the prior `parser_step` to the next `parser_step`.
3. Keeps the same authorised document and retained revision for every invocation.
4. Retains all emitted chunks, checks their document/revision and error status, and consumes the returned sequence through its legitimate terminal result.

Do not accept a caller-supplied cursor or its `done` flag as evidence that validation or parsing occurred. A13 should own and verify this chain locally before using the syntax as checker input. No cryptographic cursor token or host-side session manager is implied.

## Syntax versus checking

A12's nodes preserve syntax, source structure, and byte locations. They contain no resolved symbol IDs, binding identities, selected overload/constructor decisions, or inferred/expected types. A13 must keep parser syntax distinct from checker-owned resolved facts and checked expressions. Resolved identities should be revision-scoped, and diagnostics and typed holes should retain the original byte spans.

## Limits and error categories

`open_bytes` rejects source inputs above 65,536 bytes with `PEP_SOURCE_BYTE_LIMIT`; the A12 parser source itself exceeds that limit and has not been parsed through the source-byte route. This is a future module/composition dependency for A13 and later self-hosting work, not authority to raise the current cap.

Keep distinct: lexical/encoding diagnostics such as `PEP_INVALID_UTF8`; structural parser diagnostics such as `PEP_PARSE_EXPECTED`; A12's `incomplete` classification for expected EOF (the OCaml file CLI currently labels the same diagnostic `invalid`); interpreter/tool runtime-budget errors; and outer JSONL/typed-result transport errors such as `PEP_TOOL_MESSAGE_TOO_LARGE`. Compare diagnostic codes and original byte spans without silently collapsing these states.
