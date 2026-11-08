# FINDING BOOT-A3-115 — the fragment entry cannot be invoked on compiler A: one argument exceeds the 1 MiB transport limit

**Verdict: `emit_c23_statement_fragment` takes the whole `ParserProgress`, and for `compiler_a.pep` that argument alone is
**1,120,160 bytes** — larger than the session's 1 MiB JSONL message limit before a single other field is added. The full
`tool_invoke` request is **1,224,105 bytes**, 175,529 over. So fragmenting `main` is blocked not by the step budget but by
message size. The fix is small and I have the measurement for it.**

Seed blob `f8f476198f`. Emitter `86fcd10e`. Measured through A1's chain driver running against A2's libraries (see method note).

## The numbers

```
compiler_a: 1452 FlatAstNodes
parsed argument      : 1,120,160 bytes      <- exceeds the 1,048,576 limit on its own
merged main report   :   103,614 bytes
full tool_invoke req : 1,224,105 bytes      limit 1,048,576
over the limit by    :   175,529 bytes

main subtree alone   : 222 of 1452 nodes
parsed trimmed to main:   172,568 bytes     (sum with report: 276,182)
```

So the entry is unreachable for compiler A at its current signature, while a trimmed equivalent fits with 772 KB to spare.

## Why the step budget was never going to be the whole story

A3-099/100 established that a whole-function chunk costs ~2,100 steps/node for checking and 1,047–2,204 for emission, which
is why `main`'s 222 nodes cannot be handled in one call. The natural conclusion was "split by statement and the budget
problem goes away". It does — but the *argument* still carries all 1,452 nodes, because the entry walks `parsed.nodes` to
locate `functionIndex`. Splitting the work did not split the input.

## The fix, measured

Pass `parsed` with `nodes` reduced to the target function's subtree (222 nodes, 172,568 bytes) **keeping the original
document ids**. Two properties make this work and one guard has to change:

1. **Ids stay document-stable.** I filtered the node list without renumbering, so `pep_local_<id>` names remain exactly what
   the fragments reference. This is why A2's design does not need `tempBase` in the first place (A3-113), and trimming
   preserves that property — unlike `remap_chunk`, which renumbers 0..n-1 and would break it.
2. **The subtree is self-sufficient for emission**, since all of `main`'s bindings live inside it.
3. **`functionIndex` semantics change.** With only `main`'s nodes present there is exactly one top-level function, so the
   index becomes 0 rather than 20. Either the host passes 0, or the entry takes the function's root node id directly — the
   latter is less surprising and removes a walk over the node list.

**And the authority guard needs a decision from A2.** The entry refuses unless
`checked.syntaxNodeCount == length(parsed.nodes)`. A trimmed `parsed` has 222 nodes against a report claiming 1,452, so that
clause fails by construction. Options: compare against a supplied total, drop the clause when a subtree is passed, or keep
the full `parsed` and accept that fragmenting compiler A is impossible. The first two preserve the guard's intent (the check
that the report belongs to this source); the third fails the mission.

## Why this matters now rather than later

A1's driver is being built around this entry. If the signature is fixed as "full document" then the integration cannot
fragment `main`, and M-1 stays blocked however good the step budget looks. Better to change one parameter now than to
discover it while assembling the candidate.

## Method note — this is a mixed-lane measurement

I ran A1's `pep_sectional.py` (from `9bf18699`) with A2's libraries and A2's emitter (`86fcd10e`), because A1's chain path is
the only way to obtain a valid merged checker report for a step-limited function. It worked cleanly:

```
sectional tools registered
chain CHECK: 21/21 valid, failures=[]
main: functionIndex=20 of 21; top-level statements=31
```

**That independently reproduces A1's 21/21 chain-CHECK claim** and confirms A2's checker exposes the bound path A1 needs. But
the combination is not a real integration: it is A1 host code driving A2 emitter code, and the numbers above should be
re-measured on the actual candidate tree.

## What I did not get to

- **No fragment of `main` was emitted.** The transport refused before the first invocation, so I cannot say whether any
  individual fragment of `main` would fit the step budget. That remains the open question, and it needs the signature change
  (or a trimmed `parsed`) before it can be answered.
- `main` has **31 top-level statements** — useful for A2/A1 sizing, and more than I would have guessed from the 222-node
  count.

## Reproduce

Load A1's `pep_sectional.py` with `sys.path` pointing at A2's worktree, `register_sectional_tools`, `check_program` on
`compiler_a.pep`, then size `json.dumps` of the intended `tool_invoke`. The 1 MiB limit is enforced client-side by
`pep_c23.Session.send`, which is why it raises rather than being truncated.

REF GH #16. Emitter A2 `86fcd10e`; seed `f8f476198f`; driver A1 `9bf18699`. Finding: A3.