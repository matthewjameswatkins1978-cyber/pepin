# B4 Cycle 2 Slice 4 — Parser Continuation Guarantees + Large-Union Proof Obligations

**Packet:** PEP-WB-A4-20261104-B, Cycle 2 Slice 4. **Branch:** `spec/agent4-spec-lab`
**Pins:** A1 `2f939a0` (`ParserCursor`/`ParserChunk` shapes in `pep_c23.py:106-148`,
`docs/CHECKED_CHUNK_CONTRACT.md` node-id/topology rules, `test_prefix_coverage.py`
prefix-boundedness finding); A3 `24cd5b6`; campaign preflight (25+-member union
parser cost; 65,536-byte ingress; 100k-step/1MiB caps).
No implementation changed; obligations only.

## 1. Continuation contract (PROPOSED B4-PARSE-01..06)

Cursor and chunk shapes are A1's (`ParserCursor{document, revision, stream,
nextNodeId, done, functionActive, …, topLevelChildIndex, frames}`,
`ParserChunk{…, status, nodes, cursor, done, errorCode, …}`). The guarantees
a consumer may rely on — and that A1's path must therefore uphold:

- **B4-PARSE-01 (binding):** every step's cursor cites the exact
  `(document, revision)` under parse; mismatch → refuse, never continue.
- **B4-PARSE-02 (progress):** each non-terminal step strictly advances
  `nextNodeId`, byte offset, or `topLevelChildIndex`; a step returning an
  identical unconsumed cursor is a no-progress event the host must bound
  (looping it forever is a hang, not a hang-in-progress).
- **B4-PARSE-03 (coverage):** the union of delivered node ids is exactly
  `0..n-1`, each once. Duplicates → refuse (`CHUNK_DUPLICATE_NODE` family);
  gaps → coverage-incomplete, never silent `valid`.
- **B4-PARSE-04 (span fidelity):** every delivered node carries its original
  byte span; spans are transported, never recomputed. A member with a lost
  (zero/empty) span where the grammar defines one is a defect, not an
  approximation.
- **B4-PARSE-05 (done integrity):** `done=true` IFF the source is exhausted.
  A truncated final chunk marked done is a falsification of the whole path.
- **B4-PARSE-06 (buffer drainage):** tokens/nodes buffered across a step
  boundary (`bufferedTokens`, partial frames) MUST all be delivered in a later
  chunk; drainage is part of coverage, not an optimization.

## 2. Large-union proof obligations (the >25-variant case)

Campaign preflight records parser cost pressure at ~25+ union members. Size is
not a correctness exemption: a 30-variant union chunked mid-declaration must
satisfy B4-PARSE-01..06 identically. Specific obligations for A1:

- O-U1: chunk splits may land inside a union declaration (after any complete
  variant); resumption must continue at the next variant, never restart or
  skip (progress + coverage).
- O-U2: per-step work stays bounded (existing budgets); a declaration larger
  than one step's budget completes via continuation (each step progresses) or
  yields explicit `unsupported` — never silent truncation, never an unbounded
  retry loop.
- O-U3: variant payload types cross chunk edges intact (types are facts too;
  cf. B4-C2 signature-first — payloads must not be dropped where a consumer
  cannot re-derive them).

## 3. Negative cases for Agent 3 (falsify the path, not just the verdicts)

- N-U1: 30-variant union, chunk mid-declaration → assert all 30 variants
  present with distinct, ordered, in-source spans.
- N-U2: payload types on variants split across the edge → assert preserved.
- N-U3: harness drops variant 17 → consumer MUST detect (count/coverage
  mismatch) and refuse; acceptance = falsification.
- N-U4: harness zeroes one variant span → refuse (span fidelity).
- N-U5: harness duplicates a variant across chunks → refuse
  (`CHUNK_DUPLICATE_NODE`).
- N-U6: harness marks a truncated final chunk done → refuse (done integrity).
- N-U7: single declaration exceeding one step budget → assert completion via
  progressing steps OR explicit `unsupported`; assert NOT silent truncation
  and NOT a non-progress loop (bound the retries, count them).

## 4. Status labels

PROPOSED: B4-PARSE-01..06, O-U1..U3, N-U1..U7.
IMPLEMENTED (partial, A1 pin): cursor mechanics, node-id/topology validation,
chunk ledger over real lexer (15 chunks, mixed valid/STEP_LIMIT outcomes);
prefix-boundedness finding documents the analogous function-body limit.
TESTED (partial): ledger + contract hostile cases at A1 pin; real-lexer
differential rows.
UNKNOWN: chunked >25-variant union behavior end-to-end (no evidence found at
A1 pin — neither passing nor failing); per-step progress proof for union
splits; buffered-token drainage across parser steps under adversarial split
points. These unknowns are the point of N-U1..U7, not a gap in this slice.
