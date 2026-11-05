# PRE-REGISTRATION — A3 independent acceptance of Candidate7

**Registered:** 2026-11-05, A3 `codex/bootstrap-agent3-verification@1e2f8fa` (+this commit) · `verification/**` only.
**Registered BEFORE any Candidate7 exists.** At registration: A1 `3ff3bf1`, A2 `123d8b3` (**no re-pin pushed**), integration `46b6712` = Candidate6 (immutable, independently **FAIL 14/15**). No candidate SHA, no candidate tree, no candidate test results were visible to me when this was written.

**Why this file exists.** The dispatch sets the order A2 seam SHA → A1 Candidate7 SHA → A3 verdict. Committing the acceptance conditions *before* the candidate exists is the cheapest available defence against criteria drift — mine or anyone else's — after a red row appears. If a condition here is wrong, it must be corrected in #16 with a stated reason **before** the gated run, not after.

## 1. Instrument integrity — measured at registration

`verification/probes/verify_frozen_manifest.py D:\Projects\wt-a3-gate` → **exit 0, drift 0**.

| item | value |
|---|---|
| frozen runner blob | `b464e00e61e710023f506b11d6071347823e0270` (`verification/tools/run_acceptance_gates.ps1`) |
| declared baseline | `v2`, superseding v1 runner `e5cad4df7884168055bafd9acea08045c0d64d90` |
| pinned instrument paths | **15**, all matching `HEAD` blobs and byte-identical on disk |
| representative pins | `verification/probes/index_cache_adversarial.py` = `688042d7d394…`, `verification/bats/agent3-index-gates.yaml` = `f6086280bca7…` |

**Observation, deliberately not fixed:** the runner's own gate label reads `frozen-manifest (13 entries)` while the manifest actually pins **15** paths. The pinned set is what the check compares; the label is stale. Recorded because a stale label in an acceptance instrument is exactly the kind of small lie that later gets quoted as evidence. The frozen instrument is **not** edited by A3 (dispatch forbids runner/cap edits). @A1: a one-word label fix whenever the instrument is next legitimately re-frozen.

## 2. Acceptance conditions, fixed now

- **C1 — instrument, re-checked at the candidate tree (not assumed from this file).** `verify_frozen_manifest.py` must report drift 0 against the candidate's tree. If the candidate contains any modification to a pinned path, the verdict is **NOT-APPLICABLE** until A1 explains it and Lucy re-freezes; a candidate may not carry its own grader.
- **C2 — ancestry and non-destruction.** The candidate branch must contain `46b6712` (Candidate6) and the published A2 re-pin SHA; Candidate6 itself must be unchanged (commit and pinned blobs). No force-push, no rewritten history.
- **C3 — frozen Full-v2, exactly once, unmodified.** The five conditions I applied to Candidate6 are the acceptance contract: `NOT OBSERVED = 3`, `PROVEN = 0`, gates `13/15`, process exit `1`, SHA-bound receipt. **A red 66-node row is FAIL, never "accepted with caveat".** The run is not repeated to obtain a friendlier result; if it must be repeated for an environment reason, the reason and both outputs are recorded.
- **C4 — A2 re-pin independently re-checked.** Real checker identity (`git ls-remote` + `git cat-file -t`, exit codes printed — a keyword search is not proof), clean checkout, `prepare()` fetching `pep_chunk_contract.py` itself in a **cold clone with an empty `_build` and no manual support file**, the seed marker equal to the pin, and the full negative suite (12 as A1 reports). A green run that needed a hand-supplied file is **NOT** a pass.
- **C5 — hostile fact/provenance on the candidate SHA.** Both probes must run against the candidate and report their **pre-registered** expectations:
  - `stamp_schema_k1.py`: honest same-target positive `valid`; honest same-target negative `invalid/PEP_TYPE_MISMATCH`; foreign document and foreign revision refused `PEP_STALE_REVISION`; omitted stamp fields refused at transport; duplicate and aliased-id facts refused `PEP_DUPLICATE_FUNCTION`; **same-target forged parameter still ADMITTED** — this residual must **not** be reported as repaired unless a content-binding mechanism actually lands and the probe changes accordingly.
  - `forged_to_native_k2.py`: forged chunk report still reaches the emitter, and strict Clang **and** GCC still refuse the assembled C. If the emitter ever starts typing C from facts, this flips to a silent-miscompile finding and the candidate must not be accepted on the strength of a green checker.
- **C6 — no scope drift by A3.** No runner, cap, manifest, budget, master or release-pointer edit is made by me during acceptance. `100k` steps / `1 MiB` message / `65,536`-byte open remain untouched. A candidate that needs any of these raised is **rejected**, not accommodated.

## 3. Verdict vocabulary

`PASS` — C1–C6 all hold and Full-v2 is green.
`FAIL` — any condition false; the failing condition is named, with its observed value.
`NOT-APPLICABLE` — a precondition cannot be met for a reason that is not the candidate's merit (stale base, missing ancestor, unverifiable instrument); this is **not** a soft pass.
`BLOCKED` — the candidate does not exist yet, or a peer SHA is outstanding. Current status: **BLOCKED** (no Candidate7; A2 re-pin not pushed).

Builder-run green is never independent evidence, and my written verdict is never a substitute for the red row being visible.

## 4. Current status at registration

- **A2 re-pin: absent.** A2 head `123d8b3` still declares `A1_SHA = 2ad750b` and its `prepare()` still omits `pep_chunk_contract.py` (my K3/K7 measurement, second independent confirmation). The three-line ask is unchanged and I already verified the fix in a disposable clone: `A1_SHA → 727f8af`, fetch `pep_chunk_contract.py`, stamp `duplicate_fact`.
- **Candidate7: absent.** Integration remains `46b6712`.
- **Work completed while blocked:** frozen-manifest verifier added (`verify_frozen_manifest.py`) and the instrument proven intact; this pre-registration committed before any candidate exists.

## 5. Reproduce

```powershell
python -X utf8 verification\probes\verify_frozen_manifest.py D:\Projects\wt-a3-gate
# ROOT, BASELINE v2, RUNNER blob b464e00e..., 15 pins, drift 0, exit 0
```
