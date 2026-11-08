# ACCEPT BOOT-A3-146 — main reaches 31/31 by narrowing the node list per fragment; no index needed

**The remaining blocker was never an emitter optimisation. It is the size of the node list the host passes. Give the fragment
entry a list narrowed to the function node, its parameters, the `var`/`let` declarations and the target statement, and every one
of `main`'s 31 statements emits — including #23, which has refused at the budget since the campaign began. `find_brace` reaches
21/24, with three call-heavy statements still over.**

Seed blob `f8f476198f`. A2 `e07e278f`. A1 host `07af079d`. **No emitter change. No `parentId` index.**

## Result

```
main:        31/31 statements emit with per-statement narrowing
find_brace:  21/24
   stmt 14 (50 narrowed nodes): ERR
   stmt 15 (50 narrowed nodes): ERR
   stmt 16 (50 narrowed nodes): ERR
```

Statement 23, previously `PEP_RUNTIME_STEP_LIMIT` at 100,001 on the 222-node slice, now emits the real code at **61,572 steps on
an 85-node list**:

```c
if (!!((pep_local_4 == 0))) {
  pep_say((pep_str){ .data = (const unsigned char *)"int mai…
```

## Why narrowing, and why it matters more than the index

The cost law from A3-125/126 is *(child lookups) × (nodes scanned) × ~9 steps*. A3-131 concluded that term was unreachable by
constant-factor work and that a `parentId` index was the only route. **That conclusion was wrong, and Pep may not even be able to
express an index**: there is no list indexing (`t[0]` is a type error, A3-046) and `reverse` is O(n), so a position table cannot
be traversed sublinearly.

Narrowing attacks the other factor. The emitter needs only the nodes it actually reads; passing 85 instead of 222 cuts the scan
by 2.6× and, because the declaration set is now present, the name-lookup refusals that previously masked the cost also disappear.

| statement | full slice | narrowed | outcome |
|---|---|---|---|
| `main` #23 | 222 nodes → 100,001 LIMIT | **85 nodes → 61,572** | **emits** |
| `find_brace` #11–13 | 288 → 100,001 | 33 → 36,634 | emits |
| `find_brace` #19 | 288 → 100,001 | 30 → 25,126 | emits |
| `find_brace` #14–16 | 288 → 100,001 | 50 → 100,001 | still over |

## A near-miss I caught before publishing

My first version of this experiment passed `firstStatement = 0` on the narrowed list and reported **"all 7 find_brace statements
now emit"**. That was wrong: the narrowed list contains the declaration statements too, so index 0 was emitting a *declaration*,
not the target. Inspecting the emitted C caught it — `int64_t pep_local_8 = pep_sub(0, 1);` is not an `if` statement.

Correct positions (`pos=4`, `pos=12`) give the real picture above. Two numbers changed because of it: find_brace went from a
claimed 7/7 to a true 4/7, and the narrowed costs roughly tripled. Recording it because a wrong "the blocker is solved" claim
would have cost A1 and A2 more than the delay.

## What this gives A1

The host-side change is small and does not touch A2's file: for each fragment, pass a `ParserProgress` whose `nodes` are
`{function node} ∪ {parameter subtrees} ∪ {var/let declaration subtrees} ∪ {target statement subtree}`, preserving document ids,
and call the fragment entry with `firstStatement` set to the target's position in that narrowed list. The existing
`syntaxNodeCount` guard needs the matching count.

Two consequences worth stating: **fragmentation now genuinely works for every function that checks**, and the host must compute
the target's position in the narrowed list rather than assuming 0 — precisely the mistake I made.

## What remains

`find_brace` #14, #15, #16 — three 33-node `if` statements with three conjuncts each, two of them cross-chunk calls
(`is_str3`, `is_bool4`, `is_unit4`). At 50 narrowed nodes they still exceed 100,000, so node narrowing alone does not close
them. Options: narrow further by pruning unused declaration subtrees (their decl set may be larger than needed), or accept one of
the A3-126 mechanisms for call-heavy statements. Not yet investigated.

## Limits

- One source, one emitter pin, one driver pin, one seed; mixed lanes.
- The narrowed `ParserProgress` has non-contiguous node ids, which `pep_chunk_contract.DocumentIndex` rejects
  (`CHUNK_COVERAGE_MISMATCH`). The emitter walks `parsed.nodes` directly and is unaffected; a host implementation must not route
  this list through `DocumentIndex`.
- Emitted fragments were checked by inspecting the C, not compiled as a complete program — A3-138's build path should be re-run
  with narrowing to confirm the full 21-function assembly, which cannot complete until find_brace's three close.
- Still **no M-1 claim**.

REF GH #16. Supersedes the conclusion in `6725863459` (A3-131) and the recommendation in `6726161829` (A3-137).