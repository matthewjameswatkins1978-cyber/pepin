# ACCEPT BOOT-A3-027 — A1's candidate gated cold, and the empty-`then` fix proved insufficient

**Two results, both new:**

1. **A1's published candidate `scratch/a1-dogfood-scan@9282662` gated independently** — my
   BOOT-A3-025 finding reproduces on the *integrator's* SHA, not just my hand-built seam.
2. **The empty-`then` capability fix is necessary but NOT sufficient.** With the refusal removed,
   the pinned application then fails on `PEP_RUNTIME_STEP_LIMIT`. That answers the open question I
   deliberately left open in BOOT-A3-025.

**Native verdict for A4's application remains FAIL.** No native result exists for it.

## 1. Independent gate of A1's candidate (cold, from the published SHA)

| Item | Value |
|---|---|
| A1 candidate | `scratch/a1-dogfood-scan@9282662013ea62ff100369527ba9647d121f0134` |
| Candidate contents | A1 `a7d3ee1` checker/host + A2 `537967e` emitter + A4 `examples/dogfood/` + A1 probe |
| App blob inside A1's tree | `4a44dd653e949258a196d247097197d7c24c1da7` — **identical** to the pinned A4 blob |
| A4 head | `913552b` — **app blob unchanged** from `12e143f`; A4 changed only `docs/outbox/AGENT4_OUTBOX.md` |

**A4 honoured the freeze.** The application source is bit-identical at `12e143f` and `913552b`, and
A4's outbox carries an ACK of my BOOT-A3-025 pre-registration citing the same blob. No dispute to
reconcile.

Cold worktree at `9282662`, seed built from that tree, my own probes (not A1's) run against it:

| Probe | Result |
|---|---|
| `idruns_scan_025.py --oracle-only` | **25/25 `PROVEN-ORACLE-ONLY`** — six unseen predictions 3/5/6/3/0/0 and A4's 23/30/0/139, in both the Python oracle and the Pep interpreter |
| `idruns_scan_025.py` (full) | **FAIL** — chunks `valid` with zero diagnostics (24/12/10/44 nodes, byte-identical to my seam), then `unit main: status=unsupported Pep C23 conditional lowering requires a non-empty then branch` |
| `grant_byte_bounds_026.py` | **21/21 SOUND** — `PEP_RUNTIME_BYTE_RANGE` on all four out-of-range cases, both compilers |

So the first refusal, the chunk node counts, the semantics and the safety guard are all identical on
A1's integrator SHA to what I measured on the seam I built by hand. That upgrades BOOT-A3-025 from
"reproduced in an A3 tree" to "reproduced on the candidate the team is actually integrating".

## 2. Where the refusal actually lives (source read, quoted)

`tests/pep_c23_emitter.pep` @ `9282662` (blob sha256 `0bf0e1d4d016461e…`), two sites — lines 3384
and 4479 — in the checked and unchecked statement walkers:

```
      if !foundThen { return pep_c23_unsupported("Pep C23 conditional lowering requires a non-empty then branch") } else {}
```

`foundThen` is only set while iterating child statement nodes with `role == "then"`. An empty
`then` block has no child statement, so `foundThen` stays false and the emitter refuses — even
though `thenParts` is already initialised to `[]` and the code below it would emit
`if (!!(cond)) {\n<indent>} else {…}` , which is **valid C**. The refusal is a guard on a condition
that does not need guarding.

## 3. The decisive experiment — the guard is necessary but not sufficient

**This is an A3 experiment in a disposable worktree. It was never pushed, it is not A2's checkout,
and it is not a claimed fix.** The exact change, `--expect-count 2`, atomic Threadmoth edit:

```diff
-      if !foundThen { return pep_c23_unsupported("Pep C23 conditional lowering requires a non-empty then branch") } else {}
+      if foundThen { } else { }
```

| | |
|---|---|
| Emitter pre-hash | `0bf0e1d4d016461e334fd2e336205e442884107258279d1a259a1ccbfec0b069` |
| Emitter post-hash | `25b61666ec616a807cce72f1c133efe374d13f8dfe6a057b3bf9770ed7140200` |
| Change | 2 lines, 234 bytes, 2 matches, `committed_atomic_replace`, unrelated bytes unchanged |

Result on the **unaltered pinned application** at that tree:

```
chunk:ascii_letter    valid []
chunk:ascii_digit     valid []
chunk:ascii_continue  valid []
chunk:main            valid []          <- 44 nodes, zero diagnostics
emit:all              FIRST REFUSAL unit main:
                      PEP_RUNTIME_STEP_LIMIT  Execution step budget exceeded at 5342:59
```

And the one-shot path is unaffected by the experiment, still refusing earlier:

```
check parsed source: PEP_RUNTIME_STEP_LIMIT at 2919:13
last_execute_steps=100001, execute_count=40
```

### What this settles

In BOOT-A3-025 I wrote that the pinned app's own step cost was **unmeasured** because the capability
gate fired first, and that "the cheapest no-op lowering may also avoid blocker 4" was a *preference,
not a result*. **It is now measured, and the preference was wrong.** Removing the capability gate
entirely — the cheapest possible "lowering", since nothing is synthesised at all — still exceeds the
100k budget on `main`. Blocker 2 is real for the frozen application.

So the emitter work is two jobs, not one:

| Blocker | Layer | Status |
|---|---|---|
| A: empty `then` refused | emitter capability | a 2-line relaxation removes it (tested here) |
| B: emitting `main` exceeds 100k steps | emitter step cost | **survives the fix** — the actual blocker |

For scale, from earlier A3 measurements on the same seam: a 29-node `main` emitted fine
(BOOT-A3-024), `ascii_*` chunks of 24/12/10 nodes emit fine, and A4's 44-node `main` does not fit.
Cost per node is therefore not flat across shapes; nesting depth (a `while` containing an `if`
containing an `if`) is the obvious suspect but **A3 has not measured that attribution** and does not
claim it.

**A3 does not propose raising the 100k cap.** It is a frozen limit and a cap change is not available
to this lane. The honest options are cheaper lowering or a finer unit of emission, and that
choice belongs to A2/A1.

## 4. Updated HANDOFF — A2 (supersedes the BOOT-A3-025 offer)

- **From:** A3, `codex/bootstrap-agent3-verification`
- **To:** A2, owner of `tests/pep_c23_emitter.pep`
- **Measured on:** A1's `scratch/a1-dogfood-scan@9282662`, unaltered A4 app
  blob `4a44dd65…`, sha256 `f6e8f94240e05c2a…`
- **What A3 has already done for you (do not redo):** located both guard sites, proved the guard is
  unnecessary by construction, and proved that removing it is **not enough**.
- **The task is now B, not A:** reduce the emitter's step cost for `main`'s 44-node
  `while`→`if`→`if` chunk so it emits within the unchanged 100k budget. Take blocker A as a
  two-line follow-up, not as the goal.
- **Reproducers:** `verification/fixtures/emitter-nested-control/` (four minimal LF files).
- **Target values, already pinned by three agreeing derivations:** 23 / 30 / 0 / 139 and 3 / 5 / 6 /
  3 / 0 / 0.
- **A3 will independently gate** your published SHA on committed bytes with both compilers, and will
  not certify anything A3 authored. `CLAIMED` / `DECLINED` in your own outbox.

## Not tested / stated

- No native run of A4's application exists at any SHA. Blocker B prevents it.
- The attribution of step cost to nesting depth is a **suspicion, not a measurement**.
- My patched emitter was exercised only through my two probes; I did not run A1's or A2's test
  suites against it, and I make no claim that the 2-line change passes them.
- Whether other programs depend on the `foundThen` refusal as a *deliberate* rejection of some
  shape is unknown to me — A2 owns that judgement.
- The interpreter path for the bounds cases remains **NOT TESTED** (unchanged from BOOT-A3-026).

## Reproduce

```powershell
git worktree add --detach <tmp> 9282662
cd <tmp>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<tmp>'
python verification/probes/idruns_scan_025.py --oracle-only   # 25/25 PROVEN-ORACLE-ONLY
python verification/probes/idruns_scan_025.py                 # FAIL: empty then
python verification/probes/grant_byte_bounds_026.py           # 21/21 SOUND
# then apply the 2-line experiment to tests/pep_c23_emitter.pep and re-run the second command
# -> FAIL moves from the capability guard to PEP_RUNTIME_STEP_LIMIT
```

## Scope

A3 changed only `verification/**` in its own branch. The emitter experiment lives solely in a
disposable worktree that was never committed to any shared branch. No change to A4's app, A1's
checker/host, A2's branch, frozen Full-v2, `CURRENT`, manifest, budgets, master or release labels.
Peer worktrees read-only.

REF: GH #16 (BOOT-A3-027).
