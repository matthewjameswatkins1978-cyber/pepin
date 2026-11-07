# ACCEPT BOOT-A3-048 — shape falsified too; I am stopping the cost-surface guessing, as pre-committed

**Verdict: S3 falsified. Operand-tree shape does not drive the cost.** Three candidate drivers have now
been tested and none survives. Per the discipline written into this pre-registration — *"next step is for
A2 to instrument the emitter, not for A3 to keep guessing from cost surfaces"* — I am stopping here and
reporting the anomaly rather than inventing a fourth hypothesis and chasing it.

## Associativity check passed first (so the experiment was valid)

| program | binary nodes | traversal shape |
|---|---|---|
| `1 + 2 + 3 + 4` | 3 | left spine |
| `((1+2)+3)+4` | 3 | identical to unparenthesised → **Pep is left-associative** |
| `1 + (2 + (3 + 4))` | 3 | right spine — genuinely different tree, same node count |

## Measured — same envelope, **same node count (34)**, same statement count

| var | body | nodes | steps | status |
|---|---|---|---|---|
| L | left spine, six additions | 34 | **61,130** | emitted |
| R | right spine, six additions | 34 | **55,690** | emitted |

Ratio **0.911** — the right spine is **9% cheaper**, not ≥15% dearer. **S3 falsified.**

## The anomaly that matters more than the falsification

Cost does not track **total node count** either. Combining this receipt with BOOT-A3-047:

| case | nodes | steps |
|---|---|---|
| 047 A: one assignment, 8-term chain | 38 | **80,118** |
| 047 B: five sequential assignments | 40 | **72,317** |
| 048 L: left spine, 7 binaries | 34 | 61,130 |
| 048 R: right spine, 7 binaries | 34 | 55,690 |

**Fewer nodes, more cost** (38 → 80,118 versus 40 → 72,317). So `381n + 35.68n²` is not a model of
anything causal — it was a good *fit* over one family (BOOT-A3-033) that breaks on a different family.

## What I am NOT doing

A fourth candidate is visible in the data — the cases that cost most have the most **binary/expression
nodes** (047A ≈ 8 binaries at 38 nodes vs 047B = 5 at 40 nodes) — but I am **not** going to assert or chase
it. This campaign has now falsified two of my hypotheses (A3-045 flattening, A3-047 per-statement scanning)
and a third (A3-048 shape). Cost-surface archaeology is producing confident-sounding stories that keep
dying, and each one has cost the team a receipt to read. **My pre-registration said I would stop, so I am
stopping.**

## What should happen instead

**A2 should instrument the emitter** — the metrics op already exists (`last_execute_steps`), but what is
missing is a *per-phase* breakdown inside one emission: how many steps the declaration pass, the statement
walk, and the expression lowering each consume. That would identify the driver definitively in one run,
whereas I can only infer it from black-box totals. I will not ask for a new ABI: a debug counter in the
emitter's own Pep source, or bisecting the emitter's passes by feature-flagging them, is A2's call.

## What stands, unchanged

- **A compiler-shaped function cannot be emitted today** (A3-045 one-conditional ceiling; A3-046 no list
  indexing, so no branchless dispatch).
- **`utf8_slice` is not a lowered builtin** (A3-043), so generated C *text* is separately blocked.
- **The bootstrap auditor is validated** for A1/2/3/4/6, A5 unproven (A3-044).
- **Do not fix the cap.** If the eventual answer needs a cap change, that is Matthew's decision, not an
  emitter patch.

## Honest limits

- Cost probe only; one family, one seed build, one machine; 34-node comparison at exact equal size.
- The "binary nodes" observation is **not measured** — it is an untested pattern in four data points, and I
  am labelling it as such rather than promoting it.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953; cd <t>
pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/operand_shape_048.py    # L 61,130 vs R 55,690 at 34 nodes each
python verification/probes/scan_vs_node_047.py     # 38 nodes 80,118 vs 40 nodes 72,317
```

## Scope

A3 changed only `verification/**`. No edits to A2's emitter. Cap unchanged; no `CURRENT`, manifest,
frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-048).