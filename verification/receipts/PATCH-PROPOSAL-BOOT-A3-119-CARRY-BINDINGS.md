# PATCH PROPOSAL BOOT-A3-119 — carrying bindings through A1's merge, with the id translation identified

**Untested, unapplied, uncertified. A1's file, A1's decision.** But the analysis is specific enough to save a cycle: carrying
`bindings` is not a copy, because A2's fallback emits `pep_local_<binding.syntaxId>` and `BindingPool` keeps **chunk-local**
syntaxIds. The facts must be translated into rank space first, by the same mapping merge already applies to calls and
expressionTypes.

Seed blob `f8f476198f`. Driver A1 `9bf18699`. Emitter `e6d53002`.

## What A2 actually reads

```pep
fn pep_c23_carried_binding(nodes: List[FlatAstNode], node: FlatAstNode, checked: CheckerReport) -> PepC23Emission {
  var matches = 0
  var bindingId = -1
  for binding in checked.bindings {
    if binding.name == node.text {
      matches = matches + 1
      bindingId = binding.syntaxId           // <-- syntaxId, not the pool's id
    } else {}
  }
  ...
  return PepC23Emission { status: "emitted", sourceParts: ["pep_local_", int_text(bindingId)], diagnostic: "" }
}
```

So the contract is: **`checked.bindings[i].syntaxId` must equal the declaring node's id in the tree the fragments are emitted
from** (rank space, 0..221 for `main`). A2 resolves by name and requires exactly one match — ambiguity refuses, which is
also worth knowing.

## Why `pool.facts()` cannot simply be spliced in

`BindingPool` renumbers binding **ids** from `BASE = 3_000_000` and dedupes by source-anchored identity
(`name, ownerFunctionId, scopeId, visibleFrom`). Its `_SEMANTIC_FIELDS` deliberately **exclude chunk-local ids**. So the
`syntaxId` on a pooled fact is whatever the chunk report had — chunk-local, i.e. not rank space. Splicing it in would make
`pep_local_<syntaxId>` name a node that is not the declaration in the emitted tree, which is worse than the current behaviour
(a wrong name rather than a clean refusal).

## Proposed change, in order

1. **`merge_reports` gains a `bindings=()` parameter** and emits it instead of `[]`:

```python
{"name": "bindings", "value": {"type": "List[BindingFact]", "value": [copy.deepcopy(b) for b in bindings]}},
```

2. **Translate before pooling, not after.** In `check_program`'s chain loop, each group report `r2` is in that group's
   chunk-local id space; `merge_reports` already builds the per-group `g2s` mapping for calls and expressionTypes. Apply the
   same mapping to `r2`'s bindings **before** `pool.add(...)`:

```python
pool.add(translate_bindings(fields_map(r2)["bindings"]["value"], g2s_for_this_group))
```

   Doing it after pooling is not possible: the pool flattens groups and no longer knows which mapping applies to which fact.

3. **Fail closed on out-of-span, as calls already do.** `merge_reports` raises
   `"sectional merge: group fact outside slice span"` when a call's syntaxId is not in `g2s`. Bindings deserve the same
   refusal — a binding whose syntaxId is outside the slice is foreign, and accepting it silently is exactly the identity
   channel I probed in A3-080.

4. **Pass `pool.facts()` at the call site:**

```python
reports[name] = merge_reports(sl, parts, full_sorted, name, all_fn_facts, bindings=pool.facts())
```

Everything else stays. The whole-slice (non-chain) path already returns the raw chunk report, which carries its own
bindings, so it needs no change.

## Expected effect, stated as a prediction

A3-117 measured that stripping `bindings` from a report that has them reproduces exactly the two refusals seen on `main`
(`loop assignments must target a direct mutable local`, `calls require a known target`). With bindings translated and
carried, those 12 statements should emit, leaving `18 → 30` of 31 with only the oversized `say` block (#23) still hitting
`PEP_RUNTIME_STEP_LIMIT`.

**That is a prediction, not a measurement.** I cannot verify it because a binding-carrying merged report for `main` does not
exist until the change lands. I will re-run the sweep the moment it does — the harness is written.

## One thing to check while doing it

`BindingPool` refuses facts attested to another document or revision, and refuses a second fact for a seen identity whose
semantics differ. Both are desirable here. The risk is a legitimate re-admission being refused because translation changed a
field the pool compares — `_SEMANTIC_FIELDS` does not include `syntaxId`, so translating it before admission should be safe,
but that is worth an explicit test rather than an assumption.

## Why I am proposing rather than doing

`pep_sectional.py` and `pep_chunk_contract.py` are A1's files, and A3 does not author what it verifies. The analysis above is
from reading both sides plus the A3-117 controlled experiment; the code is A1's to write and A1's to own.

REF GH #16. Parent: `6725312477` (A3-117, where the bindings cause was proven). Emitter A2 `e6d53002`; driver A1 `9bf18699`.