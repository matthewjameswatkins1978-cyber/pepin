# ACCEPT BOOT-A3-035 — A1's chunk-window protocol: no regression, but the refusal has not moved

**Verdict: A1 `86ff953` gated. `pepin-line-scan` still PROVEN 39/39 (no regression from the contract
change). `pepin-source-scan` still refuses with the *identical* first refusal at the *identical* source
position.** So the window work, as published, has not yet unblocked anything.

This matters because "chunk windows landed" could otherwise be read as "the capacity blocker is
solved". It is not, yet.

## What changed in `86ff953`

```
86ff953 Merge A2 4b70c61 … into dogfood scan scratch
725754e Merge A1 231caf1 (shared-spine plan windows) into dogfood scan scratch
231caf1 feat(host): shared-spine sub-function windows in plan_ids (A1 window protocol)
```

| artefact | at `4e325e0` | at `86ff953` |
|---|---|---|
| `tests/pep_c23_emitter.pep` | `3f5b9582` | `3f5b9582` — **unchanged** |
| `pep_ocaml.ml` | `f8f47619` | `f8f47619` — **unchanged** |
| `pep_chunk_contract.py` | — | **+27 lines** (sub-function windows in `plan_ids`) |
| `examples/dogfood/pepin-source-scan.pep` | `4a44dd65` | `4a44dd65` — **frozen, unchanged** |
| `examples/dogfood/pepin-line-scan.pep` | — | **absent** from A1's tree |

## Gates at `86ff953` (fresh worktree, seed built there)

| Probe | Result |
|---|---|
| `line_scan_gate_034.py` | **39/39 PROVEN** — contract change caused no regression; five real files, both compilers, both orders, metamorphic, path negatives |
| `idruns_scan_025.py` | **FAIL** — chunks all valid, then `FIRST REFUSAL unit main: PEP_RUNTIME_STEP_LIMIT, Execution step budget exceeded at **5342:10**` |

**The refusal offset is byte-for-byte the same as at `4e325e0`.** That is the point: a host-side
`plan_ids` change cannot alter a refusal that happens inside the emitter's own execution, and the
emitter blob is unchanged. The window protocol is therefore **inert with respect to this blocker as
published** — it is groundwork, not a fix.

## What this does and does not say

- **Does say:** A1's change is safe (no regression), and the observable capacity blocker is unmoved.
- **Does not say** the window work is wrong or wasted. It says the *consuming* side is missing: for a
  sub-function window to help, the emitter has to lower a smaller unit, and the emitter is unchanged.
  That is A2's lane, and A3 does not design it.
- A3's own probes still work against the new contract (`DocumentIndex` unchanged in behaviour for our
  chunk slicing), which is the regression check that mattered for my tooling.

## Consequence for the frozen target

`pepin-source-scan.pep` (blob `4a44dd65…`) remains **unproven natively at every SHA**, now for the
fourth consecutive gate. Its target values stay pinned and unused: **23 / 30 / 0 / 139** and A3's
**3 / 5 / 6 / 3 / 0 / 0**.

The measured difference remains exactly as BOOT-A3-034 reported: line-scan `main` is **30 nodes /
51,009 steps** (fits, 48,991 spare); scan `main` is **44 nodes** and exceeds 100,000.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/line_scan_gate_034.py    # 39/39 PROVEN
python verification/probes/idruns_scan_025.py       # FAIL: PEP_RUNTIME_STEP_LIMIT at 5342:10
```

## Scope

A3 changed only `verification/**`. Peer tree read-only detached worktree; nothing pushed to any peer
branch. Cap unchanged; no `CURRENT`, manifest, frozen-gate, budget, master or release change.

REF: GH #16 (BOOT-A3-035).
