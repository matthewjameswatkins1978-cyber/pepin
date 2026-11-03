# FINDING — the frozen acceptance instrument scores a **correct** repair as falsified, so gate 15 can never reach `PROVEN=0`

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013) · **Evidence label:** `TESTED`
**Severity:** acceptance-blocking. It does not prevent a candidate from being correct; it prevents the frozen gate from *observing* correctness.
**Affected artifact:** `verification/probes/index_cache_adversarial.py` — frozen manifest entry in the frozen runner `verification/tools/run_acceptance_gates.ps1` (blob `e5cad4df`), line 49: `e819607c2f844fd6c213f9df52fd7218b95f9804`.
**Owner of the decision:** Matthew (frozen artifacts / acceptance), routed through Lucy. **Not repaired by me.**

## The defect

`try_refusal` builds its outcome as
`outcome = "REFUSED" if expect == "any refusal" else refusal.code`
and then `record()` scores `falsified = claim and outcome != expect`. When the caller passes the prose
expectation `"any refusal"`, the comparison is `"REFUSED" != "any refusal"` — **always true**. Any
correct refusal is therefore reported as a falsified claim.

Exactly one frozen call site uses that expectation: IDX3 (the duplicate-child-edge claim).

## Measured consequence at the repaired candidate

Pinned probe blob `e819607c` (restored bit-for-bit from `356a14e`), run at **`ba4b057`** — where A1
correctly refuses the duplicate edge:

```
FALSIFIED: IDX3 index refuses duplicate child edge (same parent+role+childIndex)
           -> REFUSED (CHUNK_DUPLICATE_EDGE)
SUMMARY cases=9 claim_falsified=1
exit 1
```

The refusal happened, with the declared code; the instrument still says the claim is falsified. The
unchanged frozen bat then reports the claim as **`PROVEN`**:

```
terrorbats run verification\bats\index-cache-claims.yaml --repo D:\Projects\wt-a3-a1-ba4b057 --json
  id=index-cache-claims  verdict=PROVEN  receipt:sha256:efaa538b969cdae067b251a780fbce5729339a98ddce05b64717b04a92247754
  bat:sha256:3964c1ab56a56123f15ee0db12dd9373590b6f461c8e19c860ecabb063395525 (unchanged)
```

Because gate 15 requires `NOT OBSERVED=3, PROVEN=0`, **this child is unachievable at any candidate that
repairs IDX3** — which is precisely the candidate the mission is waiting for.

## Why this is a genuine contradiction inside the frozen procedure, not a builder problem

- Gate 1 (frozen manifest) hard-fails on any drift, so **the probe cannot be fixed in place** without a
  re-freeze.
- The manifest literal lives *inside* the frozen runner, so re-freezing the probe **also changes the
  runner blob** `e5cad4df` that the acceptance text names as immovable.
- The bat is also frozen (`3964c1ab…`), so the claim cannot be re-scoped at the bat level either.

Therefore the two acceptance conditions **`runner blob = e5cad4df`** and **`PROVEN = 0 / NOT
OBSERVED = 3`** are jointly unsatisfiable for a repaired candidate until the owner authorises a
re-freeze or an explicit exemption. Only Matthew can release that; I will not edit a frozen artifact,
and I have restored the probe to its pinned bytes (`e819607c`, manifest re-verified: **0 drift of 13**).

## The minimal fix, ready and not applied

`verification/probes/index_cache_adversarial_v2.py` (new, **non-frozen**, blob
`688042d7d394144aafb208ff641fb0a26dafd5e2`) is byte-identical to the pinned probe except one line:

```diff
-        outcome = "REFUSED" if expect == "any refusal" else refusal.code
+        outcome = expect if expect == "any refusal" else refusal.code
```

With that single line the probe exits 0 at `ba4b057` (`SUMMARY cases=9 claim_falsified=0`) and still
exits 1 at `8396b63` (`FALSIFIED: IDX3 … -> ACCEPTED`), i.e. it discriminates repaired from unrepaired
in both directions. No claim, expectation, gate or bat is altered.

**Required authorised change (either):**
1. **Re-freeze:** adopt `index_cache_adversarial_v2.py` content as `verification/probes/index_cache_adversarial.py`,
   update line 49 of the runner manifest to `688042d7d394144aafb208ff641fb0a26dafd5e2`, and publish the new
   runner blob (which then supersedes `e5cad4df` for subsequent runs); or
2. **Exempt:** rule that gate 15's `index-cache-claims` child is scored on the v2 probe (or excluded)
   for the acceptance run, and record that ruling with the receipt.

Either way the ruling should name the blob(s) so the next receipt is unambiguous.

## Scope check — is any other frozen instrument affected?

Searched all eight frozen probes for the same pattern (`outcome != expect`, `"any refusal"`): six share
the helper *form*, but only this one call site pairs a prose expectation with a different outcome
vocabulary. The other probes pass matching tokens (`parity`, `refused+4`, `shift+4`, …), so they do not
misfire. `per_unit_cost_baseline.py` does not use the pattern at all.

## Boundaries

- **RESOLVED 2026-11-03 — Matthew's ruling, option (a), controlled re-freeze.** The one-line fix was
  adopted as `verification/probes/index_cache_adversarial.py` (`e819607c` → `688042d7`) with the runner
  manifest updated, publishing baseline **v2** (runner `b464e00e`). v1 is preserved byte-for-byte in
  `verification/acceptance/v1/` and re-verified by the runner on every run; see
  `verification/acceptance/ACCEPTANCE-BASELINE.md` and `verification/acceptance/v1/BASELINE-v1.md`.
  v2 is **not** the original unchanged suite and must not be described as one. No exemption granted.
  Measured after adoption: bat `index-cache-claims` = `NOT OBSERVED` at `ba4b057`
  (`receipt:sha256:395ceef5…`) and `PROVEN` at `8396b63` (`receipt:sha256:8e71e23c…`).
- At the time of writing (before the ruling), no frozen artifact was modified: probe restored to
  pinned bytes, runner blob `e5cad4df`, manifest 13/13 verified by `git hash-object`.
- No bat, claim, expectation, budget, limit or gate definition changed.
- The pinned probe copy used for the measurement was materialised from `356a14e` into a temp path
  (hash verified `e819607c…`), never written back over the working tree.
- Repro:
  ```powershell
  git show 356a14e:verification/probes/index_cache_adversarial.py > $env:TEMP\idx_pinned.py
  python $env:TEMP\idx_pinned.py D:\Projects\wt-a3-a1-ba4b057     # exit 1, IDX3 REFUSED but FALSIFIED
  python verification\probes\index_cache_adversarial_v2.py D:\Projects\wt-a3-a1-ba4b057   # exit 0
  python verification\probes\index_cache_adversarial_v2.py D:\Projects\wt-a3-int-8396b63 # exit 1, IDX3 ACCEPTED
  ```
