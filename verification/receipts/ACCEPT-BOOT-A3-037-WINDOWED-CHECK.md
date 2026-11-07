# ACCEPT BOOT-A3-037 — windows are checkable, but only dependency-closed, and then barely shed anything

**Verdict: VIABLE with a heavy qualification. 12/12 checks.** A sub-function window **can** pass the
Pep-written checker — so the remedy is not dead. But making a window checkable forces almost the whole
function back into it: **39 of `main`'s 44 nodes.**

That is the finding A2 should see before building a windowed emitter.

## What was asked

BOOT-A3-036 proved the *host* accepts sub-function windows (`spine [46,54]`, windows 16 vs 30, 90/90
coverage). The emitter can only consume chunks the checker calls `valid`, so: does a structurally
partial function still check?

## The answer, layer by layer — each step moved one diagnostic

| construction | ids | status | diagnostic |
|---|---|---|---|
| whole predicate chunks (harness sanity) | 24 / 12 / 10 | **valid** | `[]` |
| **window A** (declarations + first half of the loop body) | **16** | **valid** | `[]` |
| **window B, raw subtree half** | 30 | **invalid** | `PEP_MISSING_RETURN` |
| + locals (`var n`, `var o`) *bare ids* | 33 | invalid | `PEP_UNKNOWN_VARIABLE` |
| + locals **with their value subtrees** | 36 | invalid | `PEP_UNKNOWN_VARIABLE` |
| + parameter declaration (`source`) | 38 | invalid | `PEP_A13_TYPE_UNSUPPORTED` |
| + the function's own type annotation | **39** | **valid** | `[]` |

So a window must be closed over **four** things, not just parent links:

1. **the function's return** — otherwise `PEP_MISSING_RETURN`;
2. **the locals it references, as full subtrees** — a bare `var` id is not a declaration;
3. **the parameter declaration** — `source` is referenced inside the loop;
4. **the function's own type annotation** — otherwise `PEP_A13_TYPE_UNSUPPORTED`.

## Why this weakens the remedy

`main`'s subtree is **44 nodes**. The checkable window B is **39**. **The window sheds five nodes.**

The declarations (`parameter`, `type_scalar`, both `var`s, `return`) are five nodes that every window
must carry, and they are exactly the five that get shed. Window A is small (16) only because it *is*
the declarations plus a small body; the expensive half cannot shrink.

**Consequence, stated plainly:** the honest split for this app is **16 / 39**, not 16 / 30. Whether a
39-node nested chunk fits inside the unchanged 100k budget is **not established** — BOOT-A3-034
measured a 30-node nested `main` at 51,009, and BOOT-A3-033's fit is a lower bound for nested shapes
(it under-predicted by 17.2%), so 39 nodes could plausibly land near or above the budget. **A3 has not
measured a windowed emission and is not predicting a pass.**

The stronger lever remains the one BOOT-A3-033 identified: the quadratic node term (80.5% of cost at
44 nodes). The window route fights the checker's own function-level obligations and wins back only
5 of 44 nodes.

## Two incidental results worth keeping

- **The checker refuses a chunk that duplicates a function it is also given as an external fact**
  (`PEP_DUPLICATE_FUNCTION`). That is direct evidence bearing on BOOT-A3-036's open question about
  spine nodes appearing in two chunks: any duplicate *function definition* will be caught, not
  silently emitted.
- **`remap_chunk` refuses a chunk with a dangling `parentId`** (raises `KeyError`), so parent closure
  is enforced client-side as well as at plan admission.

## My own errors in this slice — five of them, all caught by the system refusing

1. Supplied `main` both inside the window chunk **and** as an external fact → `PEP_DUPLICATE_FUNCTION`
   on every window (my first run). The checker was right; my call was wrong.
2. Added `var` ids **without** their value subtrees → `PEP_UNKNOWN_VARIABLE`.
3. Added the locals but **not** the parameter → `PEP_UNKNOWN_VARIABLE` still.
4. Added the parameter but **not** the function's type annotation → `PEP_A13_TYPE_UNSUPPORTED`.
5. Labelled the raw window-B failure as a **requirement** instead of a diagnostic, which made the
   verdict read "BLOCKED" when the correct reading is "un-closed windows fail, closed ones pass".

Each correction came from the compiler telling me something specific. The prediction in the
pre-registration — "both windows check valid" — was therefore **falsified for window B as I built it**,
and the chain of diagnostics is the useful part of this receipt.

## Not tested

- **No windowed emission was attempted**, so no cost figure exists for a 39-node window.
- Spines deeper than two levels (`main`→`while`→`if`); the frozen app may need them and each extra
  level costs another mandatory declaration set.
- Whether a *dependency-closed* window can keep proving useful on shapes with more locals; one app,
  one function.
- Hostile plans — out of scope under the host-authorised threat model.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/windowed_check_037.py     # 12/12, VIABLE
```

## Scope

A3 changed only `verification/**`. A1's contract/checker, A2's emitter and A4's app were read, not
modified. Cap unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-037).
