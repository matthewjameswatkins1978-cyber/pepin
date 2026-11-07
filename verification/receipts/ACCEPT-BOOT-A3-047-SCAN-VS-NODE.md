# ACCEPT BOOT-A3-047 — my per-statement-scan hypothesis is FALSIFIED; I withdraw the fix I recommended

**Verdict: R2 falsified. Cost does NOT scale with statements × nodes. A single deep expression is
*more* expensive than five statements at the same size.** I am withdrawing the "an index/map fixes it"
recommendation I gave A2 in BOOT-A3-046, because the test that would have supported it contradicts it.

Pre-registered at `c8259ee`, with R2 as the discriminator.

## Measured — same `while` envelope, comparable node counts

| var | body | nodes | steps | steps/node |
|---|---|---|---|---|
| **A** | **one** assignment with a long `+` chain | 38 | **80,118** | 2,108 |
| **B** | **five** sequential assignments | 40 | **72,317** | 1,808 |

B has **5× the statements** and 2 more nodes, and is **9,801 steps cheaper**. Ratio B/A = **0.90** —
the predicted ≥1.8× is not merely missed, it is inverted.

My first attempt sized both variants too large (48 / 52 nodes) and both refused, so it discriminated
nothing; that run correctly reported **R2 NOT TESTED** and I re-sized rather than interpreting a
refusal.

## What this falsifies, stated plainly

- **Withdrawn:** "the quadratic term is dominated by a per-statement scan of the node list, so a
  parent→children index would make it linear". BOOT-A3-046 offered A2 a handoff built on that reading.
  The reading is not supported by this measurement, so **the handoff's rationale is withdrawn**. Its
  *goal* (a 48-node two-conditional loop emitting under 100,000) remains a legitimate acceptance
  criterion, but I no longer claim to know which change achieves it.
- **Not withdrawn:** the measured cost surface itself — `381n + 35.68n²` (A3-033), the one-conditional
  ceiling (A3-045), the missing `utf8_slice` lowering (A3-043), and the absence of list indexing (A3-046).
  Those are measurements, and this receipt does not touch them.

## What the data now suggests instead (inference, labelled)

Cost appears to track **expression depth** rather than statement count: one 8-term `+` chain is dearer
than five independent assignments. That is consistent with the emitter lowering binary operand trees
recursively — the emitter's own comment mentions cross-chunk calls nested *"in binary operand trees"* —
but I have **not instrumented that**, and after this falsification I am explicitly not going to assert a
mechanism without measuring the variable directly.

**The next experiment that would actually discriminate:** hold node count and statement count fixed and
vary **expression depth** only (e.g. `n = n + (1 + (1 + (1 + 1)))` vs `n = n + 1 + 1 + 1 + 1` — noting
that Pep's associativity may make these identical, which is itself worth checking before designing the
ladder).

## Honest limits

- Cost probe only; nothing compiled or run. One family, one seed build, one machine.
- Node counts are close but not equal (38 vs 40); R1 passed at 1.05×.
- **I got this wrong once already in this campaign** (A3-045 flattening). The lesson I am applying: state
  the falsifier, run it, and withdraw the recommendation when it fails rather than re-narrating the data.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953; cd <t>
pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/scan_vs_node_047.py     # A 80,118 vs B 72,317 at 38/40 nodes
```

## Scope

A3 changed only `verification/**`. No edits to A2's emitter. Cap unchanged; no `CURRENT`, manifest,
frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-047).