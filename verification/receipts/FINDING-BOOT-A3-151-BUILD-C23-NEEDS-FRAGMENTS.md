# FINDING BOOT-A3-151 — A1's `build_c23` cannot produce the M-1 build: it has no fragment path

**A3-150 showed M-1 passing 15/15 on a build assembled by calling the emitter tools directly. Running A1's own `build_c23` on the
same source **refuses with `PEP_RUNTIME_STEP_LIMIT`**, because it emits every function as a whole unit and has no fragment
fallback. That is now the single remaining link between the tracked tree and a real M-1.**

Seed blob `f8f476198f`. Emitter `e07e278f`. A1 driver `07af079d`. Scratch deleted; no peer lane touched.

## What `build_c23` does

```python
for name in order:
    status, diag, parts, _ = emit_unit(session, sem, slices[name], reports[name], 0)
    if status != "emitted":
        raise ValueError(diag or f"Pep C23 function unit refused {name}")
    rebuilt.extend(parts)
```

One `emit_unit` per function, fail-closed on the first refusal. Measured on the A3-150 source (the one that passes the gate when
assembled by hand):

```
build_c23 REFUSED: PEP_RUNTIME_STEP_LIMIT
```

Eleven of twenty-one functions are step-limited as whole units and only emit when fragmented (A3-137). So `build_c23` stops at
the first of them.

## A small diagnostic weakness, worth fixing in the same edit

The fallback `f"Pep C23 function unit refused {name}"` **never fires**, because `diag` is always a non-empty code string. So the
error names the code but not the function — whereas the check path above it does name the function
(`f"Pep C23 sectional check failed in {name}: {codes}"`). When this refusal did fire it gave no clue which of the eleven failed.

## The recipe, all measured

**1. Fragment fallback.** After an `emit_unit` refusal, emit the function statement-by-statement. Nine functions need it today
plus `find_brace` and `main`.

**2. Narrow the node list per statement.** Pass a `ParserProgress` whose `nodes` are *function node + parameter subtrees + `var`/`let`
declaration subtrees + the target statement's subtree*, document ids preserved. Without this, `main`'s #23 and `find_brace`'s
statements exceed the budget (A3-146). With it, `main` reaches 31/31 at 61,572 steps for #23 instead of 100,001.

**3. Compute the target's position — do not assume 0.** The narrowed list still contains the declaration statements, so
`firstStatement` must be the target's index within it. **This is the trap that made my own first attempt report success while
emitting a declaration** (A3-146). I hit it; the next implementer will too.

**4. `syntaxNodeCount` must match the narrowed list.** The restored guard compares it to `len(parsed.nodes)` (A3-118), so the
count has to be adjusted per fragment.

**5. Do not route the narrowed list through `DocumentIndex`.** It refuses non-contiguous ids with
`CHUNK_COVERAGE_MISMATCH: document node ids are not contiguous`. The emitter walks `parsed.nodes` directly and is unaffected; a
host that builds an index from this list will fail.

**6. Two epilogue edits** (A3-149/150), independent of all the above: drop the `printf` that echoes `main`'s return, and
`return (int)pep_fn_main(...)` instead of `return 0`. Without those the gate cannot pass whatever the function coverage.

## What this does not change

`find_brace`'s three five-conjunct statements still need the source rewrite — modelled as a `let` Bool local in A3-148, which is
A4's lane.

## Limits

- I called `build_c23` with a hand-built session and the A3-150 source; I did not run A1's `pep.ps1 build-c23 --sectional` wrapper,
  which additionally passes `measurements` and may add checks.
- One source, one emitter pin, one driver pin, one seed; mixed lanes.
- Still **no M-1 claim** for the tracked tree — the three modelled fixes from A3-150 all have to land first.

REF GH #16. Parents: `6726592523` (A3-150, the 15/15 gate result), `6726440672` (A3-146, narrowing and the position trap).