# Acceptance baseline — version record

**Current baseline:** `v2` · **runner blob** `b464e00e61e710023f506b11d6071347823e0270` · **adopted from** v1 runner `e5cad4df7884168055bafd9acea08045c0d64d90`
**Authority:** Matthew's ruling — option (a), *controlled re-freeze*. Recorded 2026-11-03.
**Status of this document:** the single source of truth for which acceptance artifacts are current and what changed between them.

> **v2 is an explicitly versioned successor to v1. It is NOT the original unchanged suite, and must
> never be described as such.** The evidence standard is unchanged; one probe's *recognition* of a
> correct refusal was repaired. v1 remains retrievable, byte-for-byte, under `verification/acceptance/v1/`
> and is re-verified by the runner on every run.

## Why a re-freeze was authorised

The frozen v1 probe `verification/probes/index_cache_adversarial.py` (blob `e819607c`) computed

```python
outcome = "REFUSED" if expect == "any refusal" else refusal.code
...      falsified = claim and outcome != expect
```

and its single IDX3 call site passed the prose expectation `"any refusal"`. `"REFUSED" != "any refusal"`
is always true, so a **correct** refusal was scored as a falsified claim. Measured at the repaired
candidate `ba4b057` (which refuses the duplicate child edge with the declared `CHUNK_DUPLICATE_EDGE`):

```
FALSIFIED: IDX3 index refuses duplicate child edge … -> REFUSED (CHUNK_DUPLICATE_EDGE)
```

The unchanged frozen bat therefore reported `verdict=PROVEN`
(`receipt:sha256:efaa538b969cdae067b251a780fbce5729339a98ddce05b64717b04a92247754`), while the
acceptance standard requires `PROVEN=0`. Gate 15 was therefore unreachable at exactly the candidate
the programme is waiting for. Nothing about the compiler was wrong; the instrument could not see that
it was right. Evidence: `verification/receipts/FINDING-frozen-probe-false-negative-ba4b057.md`.

The ruling rejected an exemption: waiving the child would have weakened the evidence where the
programme is trying to strengthen it.

## What changed (complete list)

| artifact | v1 | v2 | change |
|---|---|---|---|
| `verification/probes/index_cache_adversarial.py` | `e819607c` | **`688042d7`** | exactly one line: `outcome = expect if expect == "any refusal" else refusal.code` (a correct refusal now compares equal to the expectation it was declared with; the actual code still lands in `detail`) |
| `verification/tools/run_acceptance_gates.ps1` | `e5cad4df` | **`b464e00e`** | manifest hash for that probe updated; `$BaselineVersion = 'v2'`; a new **`acceptance baseline v2 …`** gate verifies the archived v1 bytes on every run; `baseline` / `baseline_supersedes` / `baseline_note` added to the JSON result and the header line |
| `verification/acceptance/v1/**` (new) | — | archive | byte-identical copies of the superseded runner (`e5cad4df`) and probe (`e819607c`) for audit |

The staging copy `verification/probes/index_cache_adversarial_v2.py` used to review the fix was
**adopted into the upstream name and then deleted** (Threadmoth certified lifecycle delete,
`committed_checked_lifecycle`); the adopted file is byte-identical to its pre-adoption blob
`688042d7d394144aafb208ff641fb0a26dafd5e2`, which remains retrievable from git history.

## What did NOT change

- **The claims and their intention.** Duplicate child edges must still be rejected, crossed revisions
  must still be refused, diagnostics must still be preserved. No claim text was edited.
- **The bats.** All four bat specs (`agent3-index-gates`, `index-cache-claims`,
  `chunk-diagnostic-claims`, `regression-hole-guard-passes`) are byte-identical to v1; the bats still
  pin `bat:sha256:3964c1ab…` etc. The oracle (`probe exit 1 = claim falsified`) is unchanged.
- **The gate list and every expectation**, including the 66-node regression row, the three
  `NOT OBSERVED` results, `PROVEN=0`, `NOT OBSERVED=3`, 15/15 green, exit 0 and the SHA-bound receipt.
- **Budgets and limits**: 100,000 steps, 1 MiB JSONL, 65,536-byte source open. None were touched.
- **No exemption.** Gate 15 is scored exactly as before; one of its children is now measurable.

## Standing rule for receipts

Any run of the frozen procedure must state its baseline and both blobs, e.g.

```
baseline=v2  runner=b464e00e61e710023f506b11d6071347823e0270  supersedes v1=e5cad4df7884168055bafd9acea08045c0d64d90
```

A v2 receipt must never be presented as a v1 (original unchanged suite) receipt, and a v1 receipt must
not be compared to a v2 run as though the instruments were identical. Where the distinction matters,
cite `verification/acceptance/v1/BASELINE-v1.md` for the superseded bytes.

## How to verify this record

```powershell
git hash-object verification/tools/run_acceptance_gates.ps1                                   # b464e00e… (v2)
git hash-object verification/probes/index_cache_adversarial.py                                # 688042d7… (adopted)
git hash-object verification/acceptance/v1/run_acceptance_gates.ps1                            # e5cad4df… (v1)
git hash-object verification/acceptance/v1/probes/index_cache_adversarial.py                   # e819607c… (v1)
powershell -NoProfile -File verification\tools\run_acceptance_gates.ps1 -Mode Preflight        # baseline gate must pass
```

**Fresh-checkout verification (measured, not assumed):** a clean `git worktree add --detach` of the
re-freeze commit yields `manifest drift 0/13` and exactly the recorded blobs — v2 runner
`b464e00e61e710023f506b11d6071347823e0270`, v2 probe `688042d7d394144aafb208ff641fb0a26dafd5e2`,
archived v1 runner `e5cad4df7884168055bafd9acea08045c0d64d90`, archived v1 probe
`e819607c2f844fd6c213f9df52fd7218b95f9804` — so the manifest check is stable across checkouts on this
repository's line-ending configuration (`core.autocrlf=true`), with no `.gitattributes` change needed.

**Runtime note:** run the runner under PowerShell 7 (`pwsh -NoProfile -File …`). Windows PowerShell
5.1 turns a child process's stderr into a terminating error under `$ErrorActionPreference='Stop'`, which
aborts the run at the first assertion suite — that is a host-shell mismatch, not a gate failure.

## Next baseline change (if any)

A further re-freeze requires the same three properties Matthew set for this one: **(1)** the test's
intention stays unchanged, **(2)** only the faulty implementation changes, **(3)** the previous version
is preserved for audit — and a new version number with the same explicit wording that it is not the
original unchanged suite.
