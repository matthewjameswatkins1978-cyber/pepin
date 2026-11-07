# ACCEPT BOOT-A3-036 — A1's `shared_spine` admission rule is sound, and it can balance the app

**Verdict: SOUND. 15/15 checks.** A1's new admission rule holds every pre-existing invariant, and the
deeper split the capacity fix actually needs is expressible — with a concrete size.

This is the first independent test of `231caf1`, code that sits in the critical path of the only
proposed remedy to the capacity blocker and had not been reviewed by anyone.

## What the rule does, and why it exists

`pep_chunk_contract.plan_ids(..., shared_spine=...)` lets a set of node ids appear in **more than one
chunk** without carrying a subtree. Before it, cross-chunk repetition was only legal inside a
**shared root**, which drags its whole subtree along.

The structural reason: `parent-in-chunk` requires every node's parent in the same chunk, so a
sub-function split forces the **function node into every window** containing its descendants. Those
forced ancestors *are* the spine. A1's rule names them explicitly instead of pretending the chunks are
a partition.

## Pinned inputs

| Item | Value |
|---|---|
| Contract under test | `pep_chunk_contract.py` @ A1 `86ff953` (carries `231caf1`) |
| Application parsed | frozen `pepin-source-scan.pep`, 1159 B, blob `4a44dd65…` |
| Index | 90 nodes; functions at ids `ascii_letter=0`, `ascii_digit=24`, `ascii_continue=36`, `main=46` |

## Results

| # | Check | Result |
|---|---|---|
| S0 | baseline whole-function chunks accepted | 4 chunks, 90 ids, covers **90/90** |
| S1 | honest two-window split of `main`, spine = `[46]` | **accepted**; chunk sizes `[24,12,10,6,39]` |
| S2 | completeness still enforced with a spine | covers **90/90**, nothing missing |
| S4 | only the declared spine node repeats | nodes in >1 chunk: **`[46]`** — no leakage |
| S6a | undeclared overlap | `CHUNK_PLAN_OVERLAP` |
| S6b | unknown spine id `999999` | `CHUNK_UNKNOWN_NODE` |
| S6c | repeated id inside one chunk | refused (`CHUNK_COVERAGE_MISMATCH`) — see ordering note |
| S6d | non-ascending ids | `CHUNK_COVERAGE_MISMATCH` |
| S7 | a node dropped from coverage, spine declared | `CHUNK_PLAN_INCOMPLETE` |
| S5 | spine does **not** excuse a missing parent | `CHUNK_PLAN_OPEN_PARENT` |
| S8 | deep split inside the loop, spine `[46,54]` | **accepted**; windows **16 vs 30**, covers 90/90, duplicates exactly `[46,54]` |

Everything the rule was supposed to preserve is preserved, and the one thing it relaxes is relaxed
**only** for declared ids.

## The number A1/A2 need: a top-level split cannot balance, a deeper split can

- A split of `main`'s **direct children** produces windows of **6 vs 39** ids. Almost useless: `while`
  is a single child (node 54) carrying **34** subtree nodes, so splitting by child count is nothing
  like splitting by cost.
- A split **inside the loop**, sharing spine `[46, 54]`, produces **16 vs 30** and still covers all 90
  nodes with exactly the declared duplication.

**Projection, labelled as a projection:** BOOT-A3-034 measured a **30-node nested** `main` (line-scan)
at **51,009** of the 100,000 steps. So a 16/30 window pair is the plausible shape for the frozen app,
where its 44-node whole `main` exceeds the budget. I have **not** measured a windowed emission, because
the consuming side does not exist yet.

## The open question this raises — for A1/A2, not a bug claim

The contract now legitimately produces plans in which the **function node** (and, in the deep split,
the `while` node) belongs to two chunks. What the emitter does with a repeated node is **not** the
contract's business, and nothing in `_plan` prevents the shared node from being emitted twice.

- If a repeated node causes two C **definitions** of the same function, C rejects it — fail-closed.
- But a repeated **statement** emitted inside two different partial bodies could compile while
  misplacing code. I have **not** constructed such a case and I am **not** claiming it is exploitable.
- The question is simply: **does the consuming side emit each spine node exactly once, and how is that
  enforced?** A3 flags it because the plan-level evidence (`duplicates=[46]`, `[46,54]`) proves the
  host can hand the emitter a plan containing the same node twice.

## Two of my own test bugs, caught by the contract refusing correctly

Both initially showed as FAILs caused by my expectations, not by A1's code:

1. **S6c** — I expected `CHUNK_PLAN_OVERLAP` for a repeated id inside one chunk. The contract refuses
   first with `CHUNK_COVERAGE_MISMATCH`, because the strictly-ascending rule makes a repeat
   unreachable by the overlap rule. **Rule ordering, not a gap** — the repeat is still rejected. My
   check now asserts a refusal and records which rule fired.
2. **S7** — my first incompleteness test forgot to declare the spine, so the overlap rule fired
   instead. Corrected to declare the spine and drop a node unique to one window; then
   `CHUNK_PLAN_INCOMPLETE` fires as intended.

A third: my first deep-split windows omitted `main`'s other children, and the contract correctly
refused with `CHUNK_PLAN_INCOMPLETE` (9 nodes uncovered). Each time the contract was right and my test
was wrong — which is the outcome that raises confidence in the contract.

## Not tested

- The **consuming** side: no windowed emission was attempted, because the emitter cannot yet lower a
  partial function.
- Deeper spines than two levels (e.g. `main` → `while` → `if`), which the frozen app may well need.
- Whether a windowed chunk still **checks** valid (`analyze_chunk_typed` was not exercised on windows
  here — this receipt is about the *plan admission* rule).
- Hostile plans (deliberately misplaced statement nodes) — out of scope under the established
  host-authorised threat model, and not constructed.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/shared_spine_036.py     # 15/15 SOUND
```

## Scope

A3 changed only `verification/**`. A1's contract was read, not modified; A2's emitter and A4's app
untouched. No `CURRENT`, manifest, frozen-gate, budget, master or release change.

REF: GH #16 (BOOT-A3-036).
