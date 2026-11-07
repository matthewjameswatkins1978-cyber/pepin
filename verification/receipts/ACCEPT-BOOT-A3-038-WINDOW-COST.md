# ACCEPT BOOT-A3-038 — windows DO emit, but they cannot shrink this app's expensive chunk

**Verdict: NO REDUCTION AVAILABLE. 10 checks, 9 passed, 1 prediction falsified.**

The window route is not impossible — a window emits, cheaply. But for the frozen app the split that is
both **checkable** and **lowerable** leaves the expensive part at exactly **44 ids = the whole
function**, refusing at the *identical* offset as the unsplit `main`.

**This closes the window question and points A2's effort at cheaper lowering.**

## Measured (COST PROBE ONLY — windows are semantically incomplete and were never run for correctness)

Frozen app, A1 `86ff953` tree, fresh worktree, seed built there.

| chunk | ids | status | steps |
|---|---|---|---|
| **window A** — shared base ∪ the loop's `if` statement | **44** | **refused** | ≥100,001 `PEP_RUNTIME_STEP_LIMIT at 5342:10` |
| **window B** — shared base only | **20** | **emitted** | **21,972** (364 C bytes) |
| whole `main`, unsplit | 44 | refused | ≥100,001, same offset |

The refusal offset for window A is **byte-identical** to the unsplit function, which is what you would
expect: window A *is* the whole function by node count.

## Why — the structure, read from the AST

`while` (node 54) has exactly three children:

```
55  unary       role=condition     (the `!(byte_length(source) <= o)`)
60  if_statement role=body         (the scanning core, 24 ids of subtree)
84  assignment  role=body          (the `o = o + 1` increment)
```

The emitter's loop lowering **requires a condition and a non-empty assignment body**, so every window
must carry: the function node, the `while`, the condition's full subtree, the sole `assignment`
statement's subtree, the parameter, the function's type annotation, both locals and the return. That
mandatory base is **20 ids**. The only separable statement is the `if` (**24 ids**) — and
`base ∪ if = 44 = the whole function`.

**There is nothing left to divide.** The expensive part is not a separable sibling; it is the remainder
after you have already carried everything the loop lowering insists on.

## My pre-registered predictions were wrong, and why

| # | Prediction | Result |
|---|---|---|
| C1 | the 39-node dependency-closed window emits | **PASS, but for a different reason** — the emitting window is 20 ids, not 39. The 39-id window was an artefact of an earlier naive split that was not lowerable at all. |
| C2 | steps in 70,000–95,000 | **FALSIFIED** — 21,972. I calibrated the band on a chunk that turned out not to exist. |
| C3 | 16-node window under 40,000 | **NOT TESTED** — that window refused (it lacked the condition). |
| C4 | window cheaper than whole main | **PASS** — 21,972 vs ≥100,001. |

The prediction I got wrong was wrong about *which* chunk would be the small one. The measurement that
matters — that the expensive window equals the whole function — was not something I predicted at all.

## The chain of construction errors that produced the correct answer

Four successive refusals, each of which was **my** error and each of which taught a real constraint:

1. index-based split cutting between `condition` and `body` → `…requires a condition and a non-empty
   assignment body` (each window had half of it);
2. bare `unary` condition without its operand subtree → `Pep C23 unary expression has no operand`;
3. (from BOOT-A3-037) bare `var` ids without value subtrees → `PEP_UNKNOWN_VARIABLE`;
4. (from BOOT-A3-037) missing parameter / type annotation → `PEP_A13_TYPE_UNSUPPORTED`.

Only after all four were fixed did the real numbers appear. **A general lesson worth carrying into any
future window or slice work: in this AST a node is not usable without its subtree — "include the node"
always means "include everything under it".**

## What this means for A2, concretely

- **Do not build a windowed emitter for this app.** There is no window that both checks and lowers and
  is smaller than 44 nodes.
- The capacity wall is therefore **not** addressable by partition. It must be addressed by **cost per
  node** — BOOT-A3-033's quadratic term, which is 80.5% of the cost at 44 nodes. That remains the only
  measured lever.
- A windowed path may still be worth it for *other* applications with several separable statements in a
  loop body; the frozen app has exactly one separable statement and it is the cheap one.

## Not tested / stated

- No window was compiled or executed for correctness — deliberately, they are semantically incomplete.
- The 20-id window's 21,972 steps describe emitting a chunk that does nothing useful; it is not a
  saving, because the statement that does the work is in the 44-id window.
- Deeper splits (inside the `if`) were not attempted. Given the pattern, each nesting level adds its
  own mandatory base, and BOOT-A3-037 already showed closure forces nearly everything back in; but I
  have **not** measured a split inside the `if` and do not claim it is impossible.
- One app, one function, one seed build, one machine.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/window_cost_038.py     # 10 checks; verdict NO REDUCTION AVAILABLE
```

## Scope

A3 changed only `verification/**`. A1's contract/checker, A2's emitter and A4's app were read, not
modified. Cap unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-038).
