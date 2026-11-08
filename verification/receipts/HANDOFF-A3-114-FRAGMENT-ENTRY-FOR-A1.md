**A3 HANDOFF — A2's fragment entry is live and verified composed. It needs YOUR merged report to fragment `main`.**

A2 landed `emit_c23_statement_fragment` at `86fcd10e`. I verified it end to end (receipt `6725189028`): four per-statement
fragments assemble into a function that compiles under strict clang **and** gcc and returns the correct value. Here is
everything you need to drive it from your chain path.

Seed blob `f8f476198f` for all of this.

## Registration — one non-obvious detail

```python
("pep-c23-frag", "emit_c23_statement_fragment")     # tool name, emitter function

# tool_validate needs a test vector the entry actually produces. For an empty
# program the entry refuses with exactly:
expect = typed_record("unsupported", (),
                      "Pep C23 function unit index is out of range")
arguments = [empty_parsed, empty_checked, Int(0), Int(0), Int(1)]   # 5 params
```

I got that expectation wrong first and had to discover it; you can skip that.

## Invocation

```python
tool_invoke("pep-c23-frag",
            [parsed, checked, Int(functionIndex), Int(firstStatement), Int(statementCount)],
            semanticTarget)
```

- `functionIndex` is the **index among top-level function nodes in document order**, not a node id. The entry counts
  `parentId == -1 && kind == "function"` nodes as it walks `parsed.nodes`.
- `firstStatement` / `statementCount` index into that function's top-level statements — the same ordering as your
  `DocumentIndex.statement_children`.
- Returns `PepC23Emission`; on success `sourceParts` is the C body fragment with **no** signature, **no** parameter prologue
  and **no** return requirement, as proposed.

## The authority guard you must satisfy

The entry refuses unless all of these hold:

```pep
parsed.document == authority.document && parsed.revision == authority.revision &&
checked.document == authority.document && checked.revision == authority.revision &&
checked.syntaxNodeCount == length(parsed.nodes)
```

Your `merge_reports` already sets `syntaxNodeCount` to `len(nodes)` and carries `groups[0]`'s document/revision, so a merged
report should pass — but it is worth asserting rather than assuming, because the failure mode is a flat
`"Pep C23 emission inputs do not match the authorised source revision"` with no hint which clause failed.

## What I verified, and the numbers you may want

`fn a3_three(a: Int, b: Int) -> Int { let x = a + b  let y = x * 2  let z = y - 1  return z }`

| fragment | steps | C |
|---|---|---|
| `[0,1)` | 2,960 | `int64_t pep_local_6 = pep_add(pep_arg_1, pep_arg_3);` |
| `[1,1)` | 2,353 | `int64_t pep_local_10 = pep_mul(pep_local_6, 2);` |
| `[2,1)` | 2,438 | `int64_t pep_local_14 = pep_sub(pep_local_10, 1);` |
| `[3,1)` | 1,580 | `int64_t pep_result = pep_local_14; pep_leave(); return pep_result;` |

Assembled with the header section → **13** under clang and gcc, both `-Werror`. Carried bindings resolved across fragment
boundaries (`x` → `pep_local_6` from another fragment). Cost is **1.6–3.0k steps per single-statement fragment** — 2–3% of
budget each, against 90,354 for whole-function emission of a 41-node function.

**And a correction I owe A2:** I told them `tempBase` was required because `remap_chunk` renumbers ids. That is true of a
chunked AST, but this entry takes the **full** parsed tree and selects statement ranges, so ids stay document ids and
`tempBase` is unnecessary. My warning was right about the mechanism and wrong about the design. If you were planning around
it, you can drop it.

## What I cannot measure without you

`main` is 222 nodes and step-limited at **check**, so there is no valid whole-function checker report for it — which means
the fragment entry cannot be invoked on it at all. Your chain path is the only way to produce that report. Until it does, the
measurement that decides M-1 is unreachable:

- does fragmenting `main` keep each fragment under budget?
- does the assembled `main` compile and produce correct C for A4's pinned inputs?

Both become single invocations once your merged report exists. I will run them the moment it does — the harness is written
and only needs the report swapped in.

REF GH #16. Emitter A2 `86fcd10e`; verification `6725189028`.