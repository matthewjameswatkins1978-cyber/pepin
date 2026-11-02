# Checked-chunk facts contract — `pep-checked-chunk-v1`

Host/protocol half of the bounded emitter handoff (A1 owns this file;
A2 owns the emitter side). The module is `pep_chunk_contract.py`, and
`pep_chunk_contract.CONTRACT` is the machine-readable form of this page.

Status: **v1, implemented and adversarially tested.** This is the G0
deliverable of the A1 mission (versioned checked-facts contract with
provenance, coverage and negative tests). It is not a claim of bounded
emission of compiler-sized source: no chunk of the real compiler bundle has
been emitted or executed through it yet.

## Why the split exists

Compiler-sized Pep source does not fit one JSONL invocation, so the emitter
can only be driven with bounded pieces. A2's emitter fails closed, and a
fail-closed consumer is only as safe as the provenance of what it receives.
The host therefore cannot simply "cut the AST up": every piece it hands on
must be provably a piece of the one authorised parse of the one authorised
revision, and it must carry only facts the Pep checker itself produced.

**A1 does not compute types, infer signatures, or validate scope.** The
host transports the checker's own `CheckerReport` and the checker's own
`ResolvedSignature` list. Everything below is identity, coverage and order.

## Envelope

One chunk is a plain mapping:

| field | meaning |
|---|---|
| `version` | `pep-checked-chunk-v1`; any other value is refused |
| `document` | the open target document the chunk was cut from |
| `revision` | the open target revision |
| `index` | 0-based position in the plan |
| `coveredNodeIds` | ascending unique **original** node ids in this chunk |
| `nodes` | `FlatAstNode` values, exactly the covered ids, original ids kept |
| `report` | the Pep `analyze_chunk` `CheckerReport` for this chunk |
| `suppliedSignatures` | the function ids the host supplied as external signatures |

`report.syntaxNodeCount` is the chunk's own node count, not the document's.
This is deliberate and is the exact point where an earlier pipeline mixed up
"checked this chunk" with "checked the whole source": a consumer must not
read a chunk report as whole-program coverage. Whole-program coverage is
`ChunkLedger.complete()`'s job.

## Plan invariants

- Every document node is in at least one planned chunk.
- A node repeats across chunks **only** inside a declared shared root, and
  each declared shared root must be whole inside at least one planned chunk.
  Measured reason: the current chunker (`tests/chunk_helper.py`) sends each
  function's subtree plus the declaration subtrees it textually references, so
  declaration nodes repeat. A contract forbidding that would not describe the
  pipeline that exists; a contract allowing arbitrary repetition could not
  detect a forged overlap. The earlier "shared root must be its own whole
  chunk" rule was relaxed after measurement: a declaration chunk needs its
  **transitive** type closure, so one declaration chunk legitimately contains
  another declaration's subtree.
- Each chunk is parent-closed: a node's parent is `-1` or in the same chunk.
- `parentId < id` and `childIndex >= 0` for every node.
- A chunk's `nodes` are exactly its covered ids — no extras, no gaps.
- The report's document, revision and node count match the chunk.
- External signatures must come from this document's `chunk_signatures`
  provenance.
- Chunks are accepted in plan order, once each, and all must arrive.

## Refusal codes

Plan-time: `CHUNK_PLAN_EMPTY`, `CHUNK_PLAN_INCOMPLETE`, `CHUNK_PLAN_OVERLAP`,
`CHUNK_PLAN_OPEN_PARENT`, `CHUNK_PLAN_SHARED_NOT_PLANNED`.

Chunk-time: `CHUNK_VERSION_UNKNOWN`, `CHUNK_STALE_REVISION`,
`CHUNK_INDEX_OUT_OF_RANGE`, `CHUNK_OUT_OF_ORDER`, `CHUNK_REPEATED`,
`CHUNK_COVERAGE_MISMATCH`, `CHUNK_UNKNOWN_NODE`, `CHUNK_DUPLICATE_NODE`,
`CHUNK_MISSING_NODE`, `CHUNK_OPEN_PARENT`, `CHUNK_INVALID_PARENT_ORDER`,
`CHUNK_NEGATIVE_CHILD_INDEX`, `CHUNK_REPORT_MISMATCH`,
`CHUNK_REPORT_COUNT_MISMATCH`, `CHUNK_REPORT_STATUS_UNKNOWN`,
`CHUNK_UNSUPPLIED_SIGNATURE`, `CHUNK_INCOMPLETE`.

A refusal is a correctness signal, not a retry hint. Python never "repairs"
a refused chunk.

## Who holds what

- **Pep checker** (`analyze_chunk`, `chunk_signatures`): local, sound facts
  for the nodes it is given, plus whole-function obligations inside those
  nodes. It stays stateless.
- **Host** (`pep_chunk_contract`): the authoritative parse, the plan,
  ordering/replay state, and coverage over the whole document. It cannot
  manufacture a semantic fact.
- **Emitter** (A2): consumes a validated chunk and fails closed on absent
  required node or fact, stale revision, duplicate ids, malformed
  parent/child relation, or inconsistent metadata.

## Stage-0 boundary

`pep_chunk_contract` is bootstrap orchestration, not semantics
(LUCY-20261101-006 decision 5). Its partition arithmetic and ledger state are
meant to move into Pep-written Lucy. Until then, **no type, scope or
signature logic may be added here**; that would recreate the hidden
second semantic authority the mission forbids.

`tests/chunk_helper.py` remains a prototype: its `decl_closure` is a
deliberate textual over-approximation (over-inclusion is bounded waste,
under-inclusion fails closed). It is not part of the contract and must not be
mistaken for checker-certified dependency analysis.

## Signature provenance (measured)

Two id spaces exist and must stay separate:

- **checker side** (`id`/`synid` in `tests/chunk_helper.py`): a synthetic,
  chunk-local key the Pep checker uses to look up external signatures for a
  call site. It must never be a document id.
- **contract side** (`node`): the original document node id of the function
  whose header chunk produced the signature. This is the only identity the
  contract can tie to a revision, and the only thing that belongs in
  `suppliedSignatures` or plan provenance.

Both mistakes were measured. Feeding the checker's synthetic key to the
contract produced duplicate provenance and `CHUNK_COVERAGE_MISMATCH`. Feeding
a document id to the checker collided with a body chunk's remapped ids and
**silently stopped cross-chunk type checking from reporting `invalid`** — the
existing chunked-mismatch regression caught it. Keep the two fields apart, and
keep that regression running.

## Measured on the real lexer

`tests/test_lexer_chunk_ledger.py` drives the whole contract over
`examples/pep_lexer.pep` at `87c9fec`: parse complete in 567 steps / 2,030
nodes, plan of 15 chunks (5 transitively closed declaration chunks + 10
functions, 2,340 node assignments), one `analyze_chunk` call per chunk.

| chunk | nodes | result |
|---|---|---|
| 5 declaration chunks | 5, 5, 18, 34, 76 | valid |
| `ascii_continue` | 10 | valid |
| `ascii_digit` | 12 | valid |
| `ascii_letter` | 24 | valid |
| `advance_position` | 33 | valid |
| `make_token` | 55 | valid |
| `lexer_start` | 59 | `PEP_RUNTIME_STEP_LIMIT` |
| `make_cursor` | 103 | `PEP_RUNTIME_STEP_LIMIT` |
| `make_progress` | 125 | `PEP_RUNTIME_STEP_LIMIT` |
| `utf8_check` | 268 | `PEP_RUNTIME_STEP_LIMIT` |
| `lexer_step` | 1,513 | host transport limit (> 1 MiB request) |

Two things that matter for the A2 seam:

1. The checker limit is **construct-driven, not node-count-driven**:
   `lexer_start` stops at 59 nodes while `make_token` passes at 55, and
   `utf8_check` is still ~234 KB of request. A universal "~24 nodes is safe"
   ceiling does not describe this stage.
2. A declaration-only chunk is not checkable alone. The first run of the real
   lexer produced `PEP_UNKNOWN_TYPE` on a 24-node declaration chunk whose
   record field named a type declared elsewhere; transitive closure fixed it.

## Evidence

`tests/test_checked_chunk_contract.py`: 24 synthetic hostile cases covering
every refusal code, plus 2 integration cases that drive the real staged
parser, the real `chunk_signatures` and the real `analyze_chunk` over the
shared-declaration chunk shape and assert a `valid` completed sequence.
`tests/test_lexer_chunk_ledger.py`: 4 pinned real-lexer ledger cases.
Every existing-file edit in this work was applied through Threadmoth with
`unrelated_bytes_changed=false`.

## Still open (A2 seam)

1. Byte-identical concatenation of staged units against one-shot output for
   already-supported bounded programs — A2's gate, not yet exercised through
   this contract.
2. Header/section versus per-function unit granularity, and whether a
   declaration chunk may be omitted when a body chunk carries it as a shared
   root. Today the shared root must also be its own chunk; that is a
   conservative choice and is cheap to revisit if measurement shows the
   duplicated declaration chunk is the expensive one.
3. Sub-function partition sizes: the plan accepts explicit id lists
   (`plan_ids`) precisely so dynamic subdivision needs no contract change,
   but no measured sub-function partition exists yet.
4. Where the shared-root set comes from. Today the host decides it from
   top-level declaration nodes; the checker does not yet certify the closure
   manifest.
