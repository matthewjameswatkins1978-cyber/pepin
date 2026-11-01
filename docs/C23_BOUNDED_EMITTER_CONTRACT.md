# Bounded emitter input: the emitter-side contract (proposal for A1)

Mission `LUCY-20261101-004`, gate **N4**. Owner of this document and of the emitter-side
surface: A2-NATIVE. Owner of the checker and the host adapter: A1. Nothing here changes
a limit, and nothing here is implemented yet — this is the contract A1 and A2 need to
agree before either side writes transport code.

## Why this exists, in measured numbers

The Pep-written emitter is itself a Pep program with a fixed 100,000-step
per-invocation budget. Its cost is approximately **(full node-list scans) x (nodes)**,
and each statement of a lowered function performs about five full scans:

| probe | measured boundary |
| --- | --- |
| `acc = 1` per statement | tips at 21 statements |
| `acc = 1 + 2` | tips at 10 |
| `acc = 1 + 2 + 3` | tips at 6 |
| `acc = 1 + 2 + 3 + 4` | tips at 5 |
| unrelated padding nodes (0 / 6 / 12 / 18 / 24) | 21 / 19 / 17 / 15 / 13 statements |
| `acc = acc + 1` after removing one scan per statement | 7 -> 8, cheapest ladder 17 -> 21 |

Two conclusions follow directly, and the second one is the important one:

1. The emitter currently stops at roughly **twenty expression nodes per program**, far
   below `lexer_step`, `utf8_check` or `make_token`. No feature work changes that.
2. **Unrelated nodes cost almost as much as relevant ones.** Padding a program with
   functions that are never lowered reduces headroom one-for-one. So an emitter-side
   "filter the node list per function" trick cannot buy anything: every invocation still
   receives and scans the whole list. The reduction has to happen **in what the host
   sends**, which is why this is a joint contract and not an emitter optimisation.

## What the host would send

A chunk, not a whole program:

```
type EmitterChunk {
  document: Str,        // exact source document identity
  revision: Str,        // exact source revision
  chunkIndex: Int,      // 0-based
  chunkCount: Int,      // total chunks for this document
  part: Str,            // "header" | "function" | "main"
  functionIds: List[Int],   // present nodes' top-level owner(s); empty for header/main
  nodes: List[FlatAstNode]  // the bounded subset for this chunk only
}
```

and a matching checked-fact subset, because `emit_c23_checked` today refuses unless
`checked.syntaxNodeCount == length(parsed.nodes)`. That invariant is the guard against
forged or stale input and must not simply be dropped; it has to be replaced by an
equally strong per-chunk invariant.

## Proposed emitter-side entry points (A2 owns these)

```
emit_c23_header(       chunk: EmitterChunk, checked: CheckerReport) -> PepC23Emission
emit_c23_function_unit(chunk: EmitterChunk, checked: CheckerReport, index: Int) -> PepC23Emission
emit_c23_main_unit(    chunk: EmitterChunk, checked: CheckerReport) -> PepC23Emission
```

`emit_c23_checked(parsed, checked)` stays exactly as it is. The chunked entries must be
**additive**: for any program that emits today, concatenating
header + every function unit in program order + main must equal the current one-shot
output **byte for byte**. That equality is the acceptance test, and it is what makes the
change safe to land before any host work exists.

### Invariants each chunked entry must enforce (fail closed, never guess)

- `chunk.document` and `chunk.revision` must equal the live `semantic_snapshot()`.
- `chunk.chunkIndex` in `[0, chunkCount)`, and `chunkCount` consistent across calls is
  the host's job; the emitter validates the values it is given and refuses the rest.
- Every node the emitter is about to visit must be present in `chunk.nodes`. A missing
  node is a refusal (`Pep C23 chunk is missing a node it must lower`), never a silent
  skip: an emitted program with silently dropped statements is worse than no output.
- Nodes must be the *declared* ones: ids unique, `parentId` resolvable within the chunk
  or explicitly marked as an out-of-chunk parent, `childIndex` dense from 0 per
  (parent, role).
- `part == "function"` must carry exactly the nodes of the functions in
  `functionIds`, and `index` must select one of them.
- Replay and staleness: the same chunk delivered twice, or a chunk from a different
  revision, must be refused. Ordering is the host's concern, but a `main` unit arriving
  before the header it depends on is a refusal, not an implicit retry.

### Contract test matrix (the part that must exist before host work)

| case | expected |
| --- | --- |
| whole program, one-shot | unchanged output, existing suites green |
| header + units + main concatenated | **byte-identical** to the one-shot output |
| chunk with a node removed that the emitter must lower | refusal, no partial C |
| chunk with a duplicated id | refusal |
| chunk with a mismatched revision or document | refusal |
| same chunk delivered twice | refusal |
| chunk count / index inconsistent | refusal |
| compiler-sized fixture (the ~2,030-node lexer) | per-unit cost within budget, with the boundaries measured, not assumed |

## What this costs, honestly

Even with perfect chunking, per-unit cost is five scans times the unit's nodes, so a
single function of a few hundred statements still will not fit. Chunking converts
"no compiler-sized source can be emitted at all" into "each function can be emitted if
it is small enough", and the structural scan reduction (worth a measured 2.6x-5x) is the
complementary half. Both are needed; neither alone reaches `lexer_step`.

## What I am not doing

- Not raising the 100k step or 1 MiB transport caps.
- Not inventing a second semantic authority: the emitter consumes checker facts, it does
  not re-derive types.
- Not building transport, host glue or a parallel pipeline. A1 owns those.
- Not changing `emit_c23_checked` semantics, which stay authoritative for whole programs.

## What A1 needs to decide

1. Agree or amend the chunk shape above, especially `functionIds` and whether the header
   is one unit or per-record-type units.
2. Say how the checked-fact subset is carried: reuse `CheckerReport` scoped to the
   chunk's nodes, or a new bounded report type. That choice is on A1's side of the
   boundary; the emitter will validate whatever is agreed.
3. Confirm the byte-identical concatenation test is the acceptance gate for the emitter
   half, so I can land it before host work exists.

Once (1)-(3) are agreed I implement the three entry points plus the contract test
matrix, which is entirely emitter-side and testable without any host change.
