# ACCEPT BOOT-A3-055 — DIVERGENCE-2 restaged: exactly one item blocks it

**Verdict: with the decomposition recipe applied, the decisive input-dependent-C test now fails at exactly
one point — the missing by-name `utf8_slice` lowering. Nothing else blocks. The test will return a verdict
the moment that lowering exists.**

## 1. Peer state, checked rather than assumed

I checked the actual worktrees before concluding anything about peers, because git refs do not show local
work:

| worktree | HEAD | uncommitted source | most recent local activity |
|---|---|---|---|
| `wt-a2-bounded` (A2) | `4b70c61` (12:29) | **none** — clean | `_build/debug53.py`, `patch_twin_branch_hoist.py` at 12:47–12:52 (diagnostic scripts) |
| `wt-a1-fix` (A1) | `231caf1` (12:30) | two untracked `tests/fixtures/mc_seam_*.pep` | `_build/census2.py` 13:20, `census.py` 13:25 |

So A2 is **not mid-way through a lowering** — it has been running diagnostics, not editing the emitter.
That is peer coordination, not a human-owned dependency, so I did **not** block; per the mission's rules I
handled it directly.

## 2. One targeted nudge, not a broadcast

Sent a single Intercom message to the session most likely to be implementing (actively running tools),
addressed "whoever owns `tests/pep_c23_emitter.pep`; ignore if you are A1/A4", containing:

- the measured one-item ask (by-name `utf8_slice` lowering + small C slice helper);
- the evidence (`str_concat` 3 quoted lowering sites, `byte_at` 3, `byte_length` 1, **`utf8_slice` 0**);
- the correction that semantics are already settled in the seed interpreter;
- **that their window/traversal probing is off the critical path**, since a five-function lexer-shaped
  program already emits and runs natively under decomposition (BOOT-A3-051/053);
- the reusable instruments to verify with.

## 3. DIVERGENCE-2 restaged, and it now fails at exactly one point

BOOT-A3-042's generator used `say(utf8_slice(...))`, which the emitter refuses for a *second* reason
(`say` accepts only literals, Str parameters, Str locals, Str fields). Applying my own BOOT-A3-053/054
recipe — **bind the slice to a `Str` local, then `say(local)`** — removes that noise:

```
PASS  D1:host-valid           open_bytes status=valid []
PASS  diag:call-facts         chunk report carries 0 call fact(s) and 1 function fact(s)
FAIL  D2:emits                FIRST REFUSAL unit: Pep C23 cross-chunk call has no resolved call fact
```

**Every other obstacle is now gone.** The program is host-valid; `say` accepts the local; `str_concat`
and the loop/call shapes are all proven to emit. The single remaining refusal is the unknown callee — i.e.
`utf8_slice` has no lowering.

So DIVERGENCE-2 is a **loaded test**: the next time someone adds that lowering, one command produces a
verdict on the campaign's floor claim (two unseen inputs → different C text → both compile under strict
Clang and GCC → run to different outputs).

## Why I did not block for Matthew

The remaining work is **possible for a peer and merely not started**, and it is reversible and bounded. The
mission reserves human attention for irreversible, financial, security-sensitive or out-of-scope decisions,
and explicitly says not to wait for dispatch of routine reversible subjobs. Blocking here would have spent
his attention on "please restart A2", which the evidence does not support — A2's session is alive and
working, just on a different axis.

## Honest limits

- The nudge may not reach the right session: Intercom session names here are auto-generated, not the stable
  `a2-pepin` identity, so I addressed it by role description rather than identity. If it landed with A1 or
  A4 instead, it is a bounded, skippable message.
- DIVERGENCE-2 still has **no verdict**; the floor capability remains **unproven by anyone**.
- One seed build (`a7d3ee1`) on A1's tree (`86ff953`), one machine.

## Reproduce

```powershell
$env:PEPIN_GATE_ROOT='<t>'
python verification/probes/divergence_2_042.py    # exactly one refusal: the unknown callee
```

## Scope

A3 changed only `verification/**`. A1's and A2's worktrees were read, not modified. Cap unchanged; no
`CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-055).