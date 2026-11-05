# K-A3-8: Candidate7 pre-gate — frozen instrument intact, A1's dry run independently reproduced

**Date:** 2026-11-05 · **Mission:** LUCY-20261105-002 (FINISH-LINE, A3 = independent acceptance) · **Evidence label:** `TESTED`
**PIN: A3 | `codex/bootstrap-agent3-verification@fa2d278` (+this commit) | clean, remote-verified | tested A1 `3ff3bf1`, A2 `123d8b3`, base `46b6712`**
**Status: BLOCKED on peers.** A2 has not pushed the re-pin (`codex/a2-bounded-emission` = `123d8b3`); no Candidate7 exists (`codex/checker-emitter-integration` = `46b6712`). Per the dispatch order (A2 SHA → A1 Candidate7 → A3 verdict) my assigned job cannot start.

## What I did instead of waiting

Two things that make the eventual verdict cheap and hard to shift: **pre-register the acceptance conditions before any candidate exists**, and **independently reproduce A1's builder-reported dry run** so a wasted Full-v2 run is unlikely.

### 1. Pre-registration (`fa2d278`)

`verification/acceptance/PRE-REGISTRATION-CANDIDATE7.md` fixes C1–C6 (instrument re-check, ancestry, frozen Full-v2 run once with the five Candidate6 conditions, A2 re-pin re-check, hostile fact/provenance expectations, no scope drift) plus the verdict vocabulary `PASS / FAIL / NOT-APPLICABLE / BLOCKED`, written while no candidate tree or result existed. A red 66-node row stays **FAIL**, and the same-target forgery residual stays **admitted** unless a content-binding mechanism actually lands.

### 2. Frozen instrument verified intact — with one real defect recorded, not fixed

`verification/probes/verify_frozen_manifest.py` → **exit 0**: runner blob `b464e00e61e7…`, declared baseline `v2` superseding v1 `e5cad4df7884…`, **15 pinned paths, drift 0**, and every on-disk copy byte-identical to its pin.

**Defect (recorded, not edited):** the runner's gate label reads `frozen-manifest (13 entries)` while the manifest pins **15**. The check compares the true set, so the gate is sound, but the label is stale — exactly the kind of small untrue number that gets quoted later as evidence. Frozen instrument is A1/Lucy-owned; A3 does not edit it.

### 3. A1's dry run reproduced independently

Disposable local scratch (`D:/Projects/wt-a3-c7dry`), never pushed, no branch created — A1 remains sole integrator. I tested **A1 `3ff3bf1`** (their *current* head) rather than the `727f8af` in their receipt, so this is a slightly harder case than theirs.

| check | observed |
|---|---|
| merge `46b6712` + `3ff3bf1` | **clean, zero conflicts** |
| merge `+ 123d8b3` (A2) | **clean, zero conflicts** |
| seam probe | **exit 0** |
| `bundle_sha256` | **`80c28ef521d8…`** — identical to A1's reported `80c28ef5` |
| seed marker | `3ff3bf1efc5ee8a549b57ddabb19bbe63ad06342` = the pin (seed rebuilt from pinned source, not a stale exe) |
| prototypes | `prototypes_bytes=267`, all three emitted |
| assemblies | `5875` document order, `6142` reverse order |
| compilers | strict Clang **42**, GCC **42**, both orders |
| seed oracle | `42` |
| negatives | **11**, all as specified, incl. `PEP_STALE_REVISION` and both `neg-unit-order-*` still refusing |
| A1's targeted suite | **65 tests, OK, 132.9 s** (`test_c23_str_result`, `test_a14_c23`, `test_chunk_cross_call_facts`, `test_checked_chunk_contract`, `test_c23_arity`) |

Two provenance facts make the hash match meaningful rather than lucky: the checker blob is **identical** at `727f8af` and `3ff3bf1` (`2d714a0e9870…`), so the bundle content is the same despite the different A1 pin; and the merged tree's root `pep_chunk_contract.py` hashes to `0751391f3a13…`, matching A1's pin.

## Two findings this produced

1. **A1's negative count is off by one.** Their dry-run receipt says "12 negatives"; the probe emits **11** (no-call-fact, ambiguous-call, missing-target, ambiguous-target, arity-mismatch, foreign-result, stale-revision, unit-index, dup-external-name, unit-order-clang, unit-order-gcc). Immaterial to soundness, but counts quoted from receipts get reused — worth a correction on their side.
2. **A2's cold-clone defect does not reproduce in a merged candidate.** `pep_chunk_contract.py` is present at the repo root (blob `0751391f…`) and the probe inserts `ROOT` into `sys.path`, so the probe runs cold with **no manual support file**. Consequence: the defect blocks A2's *standalone branch*, not Candidate7. **But** the dependency remains undeclared — `prepare()` still never fetches it — so a future split or vendored emitter silently reintroduces the failure. C4 is satisfiable at candidate level with this declaration gap noted.

## What this is NOT

- **Not a Candidate7 verdict.** No frozen Full-v2 was run; there is no candidate. The pre-registration's C3 remains entirely unexercised.
- **Not an integration act.** The merge exists only in a disposable local scratch; nothing was pushed, no candidate branch created, Candidate6 `46b6712` untouched. A1 remains sole integrator.
- **Not a claim that the 66-node gate is fixed.** Nothing here touches it.

## My own process slips, stated

- I first patched the probe with a **fabricated full SHA** (`3ff3bf1a7f8c…`, invented tail). Caught by printing `git rev-parse 3ff3bf1` before running, corrected, and the SHA was confirmed present (`cat-file -t` = commit) before use. Exactly the error I criticise in others.
- My first output capture used `Tee-Object` downstream of `Select-Object -First`, which truncated the file to 8 lines. The complete negative set came from the first run's tail instead; I did not re-run to paper over it.

## Reproduce

```powershell
python -X utf8 verification\probes\verify_frozen_manifest.py D:\Projects\wt-a3-gate   # 15 pins, drift 0, exit 0
# dry run (disposable, local only):
git worktree add --detach D:\Projects\wt-a3-c7dry 46b6712
cd D:\Projects\wt-a3-c7dry; git merge --no-edit 3ff3bf1; git merge --no-edit 123d8b3
python _build\patch_probe_for_dryrun.py . 3ff3bf1efc5ee8a549b57ddabb19bbe63ad06342
python tests\probe_seam_chunked.py        # exit 0, bundle_sha256 80c28ef5..., 42 on both compilers both orders
python -m unittest tests.test_c23_str_result tests.test_a14_c23 tests.test_chunk_cross_call_facts tests.test_checked_chunk_contract tests.test_c23_arity   # 65 OK
```

## Next action

Wait for A2's pushed re-pin, then re-check it (C4) and gate the published Candidate7 with one unmodified frozen Full-v2 (C3). Both prerequisites are peer-owned; no amount of extra A3 work unblocks them.

## Signal v0.1 handoff to A1

```text
PIN: A3 | codex/bootstrap-agent3-verification | fa2d278 (+this commit) | pushed+remote-verified | clean
RESULT: your dry run independently reproduced at 3ff3bf1 (merge clean, bundle 80c28ef5 identical, exit 0, 42 both compilers both orders, 65/65 targeted in 132.9s). Two corrections: probe emits 11 negatives, not 12; frozen runner label says 13 entries while 15 are pinned. TESTED.
REPRO: verify_frozen_manifest.py D:\Projects\wt-a3-gate ; disposable merge 46b6712+3ff3bf1+123d8b3 then tests\probe_seam_chunked.py
FALSIFIER: a Candidate7 whose own tree yields a different bundle_sha256, or a frozen-manifest drift, invalidates this pre-check.
NEEDS: A1 — correct the negative count and note the stale manifest label at your next legitimate re-freeze; publish Candidate7 when A2's SHA lands, and expect C1-C6 as pre-registered, not renegotiated.
```
