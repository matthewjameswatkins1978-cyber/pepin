# ACCEPT BOOT-A3-032 — A2's fix gated: capability gate gone, capacity blocker confirmed, two new findings

**Verdict: A2's claim is accurate on both halves, independently reproduced. 18/18 and 21/21
regression checks unchanged. Still no native result — the blocker has moved entirely to capacity, and
this receipt confirms it at A2's own SHA.**

## What was gated

| Item | Value |
|---|---|
| A1 integrated candidate | `scratch/a1-dogfood-scan@4e325e00ffeff1bb57c42047daf5045d396c5381` |
| Emitter inside it | blob `3f5b958271b33f5c19111a09ae6bc0e60e4839ca` — **identical to A2's own `ac3e2ea`** |
| A2 fix commit | `288662f` "feat(emit): empty-then conditionals emit; dogfood probe for A4 source-scan" |
| Frozen app | blob `4a44dd653e949258a196d247097197d7c24c1da7`, sha256 `f6e8f942…`, **unchanged** |
| Tree | fresh detached worktree at `4e325e0`, seed built there |

## 1. A2's fix works, and it is narrower than my experiment — correctly so

A2 changed the guard to:

```
if !foundThen && !foundElse { return pep_c23_unsupported("… requires a non-empty then branch") } else {}
```

at both walkers (lines 3384, 4479), keeping the registered diagnostic text. My BOOT-A3-027
experiment deleted the guard outright; A2 kept a rejection for the both-empty case. Verified
precisely, with **runtime values**:

| program | `check` | `build-c23` | runs as |
|---|---|---|---|
| `if 1 == 1 { } else { n = 1 }` | valid | **exit 0** | **0** ✓ (empty then; condition true) |
| `if 1 == 1 { n = 1 } else { }` | valid | **exit 0** | **1** ✓ |
| `if 1 == 1 { } else { }` | **valid** | **exit 2**, registered text | — |
| `if 1 == 1 { }` (no else) | **invalid** `PEP_PARSE_ELSE` | n/a | — |

The first two show the fix is not just "no longer refuses" but **semantically correct** — the C
emitted for an empty `then` really does nothing.

## 2. Blocker B confirmed as the first refusal, at A2's own SHA

On the unaltered pinned application at `4e325e0`:

```
chunk ascii_letter/ascii_digit/ascii_continue/main   all valid (24/12/10/44), zero diagnostics
FIRST REFUSAL unit main: PEP_RUNTIME_STEP_LIMIT  Execution step budget exceeded at 5342:10
```

This is exactly the layer and the offset my BOOT-A3-028 cost attribution predicted from the
semantics alone (`5342:59` in my disposable experiment; `5342:10` here — same source position, the
emitter source differs by the two comment lines). **A2's receipt says "first refusal fixed, 44-node
capacity blocker measured, chunk-window ask" — both halves are accurate.**

**Three independently written harnesses now agree on the same first refusal:** mine, A2's own new
`tests/probe_dogfood_source_scan.py`, and A1's `probe_dogfood_scan_a1.py`. That is the strongest form
of agreement available here — not one agent's harness repeated.

## 3. Regression checks at the new emitter

| Probe | Result |
|---|---|
| `illtyped_chunk_matrix_031.py` | **18/18 SOUND** — unchanged |
| `grant_byte_bounds_026.py` | **21/21 SOUND** — unchanged |

A2's change introduced no regression in either area.

## 4. Two findings, both small and precise

### (a) For A2 — the one construct your guard still refuses is *valid* Pep

`if c { } else { }` passes `check` with **status valid** and only the emitter refuses it. So the
guard now rejects a construct the language accepts — a no-op semantically, so low priority, but it is
an emitter/language inconsistency and worth a decision: lower it as an empty block, or keep it and
say why in the registered text.

Related correction to A2's comment: *"empty then AND empty/no else still refuses"* — the
"no else" half is **unreachable legitimately**, because a bare `if` is rejected by the **parser**
(`PEP_PARSE_ELSE`, "Expected else after if block"), not by the emitter. Only the both-branches-empty
case is actually the emitter's call.

### (b) For A1 (host/CLI lane) — an opaque diagnostic on invalid input

`pep.ps1 build-c23` on the parse-invalid program `if 1 == 1 { }` reports:

```
Pep C23 error: Pep C23 parser AST node ids are not contiguous
```

instead of the parse diagnostic the user needs (`PEP_PARSE_ELSE`). **Reproduced identically on
`537967e` and `4e325e0`, so this is pre-existing and not a regression from A2's change.** It is a
diagnostic-quality defect in the C23 host path: an invalid program surfaces an internal invariant
message. Low severity, but it would mislead exactly the user the dogfood lane is meant to serve.

## Mission status

**Still no native result for A4's application at any SHA.** The refusal is now purely capacity
(`PEP_RUNTIME_STEP_LIMIT`), i.e. the emitter's own execution budget on a 44-node `main` — A2's lane,
with A2 now explicitly asking A1 for a chunk window. A3 has nothing to add there except the
measurement already delivered (BOOT-A3-028: one `while` costs 59–60% of the budget; one nesting level
costs >41k steps).

## Not tested / stated

- I did not run A2's full test suite, nor A1's; only the two regression probes above and A2's own
  dogfood probe.
- Semantics of the both-empty construct remain unexercised natively (it does not build).
- One seed build, one machine.
- The `5342:10` figure is reported verbatim; I have not established what document that offset indexes.

## Reproduce

```powershell
git worktree add --detach <t> 4e325e0
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/idruns_scan_025.py            # FAIL: PEP_RUNTIME_STEP_LIMIT at unit main
python verification/probes/illtyped_chunk_matrix_031.py  # 18/18 SOUND
python verification/probes/grant_byte_bounds_026.py      # 21/21 SOUND
python tests/probe_dogfood_source_scan.py                # A2's own probe, same first refusal
```

## Scope

A3 changed only `verification/**`. Peer trees were read-only detached worktrees; nothing pushed to
any peer branch. No change to A4's app, A1's checker/host, A2's emitter, frozen Full-v2, `CURRENT`,
manifest, budgets, master or release labels. Cap unchanged.

REF: GH #16 (BOOT-A3-032).
