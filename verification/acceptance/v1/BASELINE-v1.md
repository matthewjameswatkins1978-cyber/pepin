# Baseline v1 (superseded) — audit record

**Status:** SUPERSEDED by v2 (`verification/acceptance/ACCEPTANCE-BASELINE.md`). Kept for audit only.
**Superseded on:** 2026-11-03, by Matthew's ruling (option (a), controlled re-freeze).
**Nothing here is scored any more**; the files exist so the previous instrument can be re-run and
compared byte-for-byte.

| artifact | blob |
|---|---|
| `v1/run_acceptance_gates.ps1` (frozen runner as executed for every receipt up to and including the `8396b63` FAIL verdict) | `e5cad4df7884168055bafd9acea08045c0d64d90` |
| `v1/probes/index_cache_adversarial.py` (frozen probe it pinned at manifest line 49) | `e819607c2f844fd6c213f9df52fd7218b95f9804` |

## The 13 manifest entries v1 pinned (verbatim)

| path | blob |
|---|---|
| `verification/bats/agent3-index-gates.yaml` | `f6086280bca7115df79d0f412b8f8975f71e3898` |
| `verification/bats/index-cache-claims.yaml` | `3fe77b42058b83d54697b4c4d2570feccf9993e2` |
| `verification/bats/chunk-diagnostic-claims.yaml` | `204a62bc5315714afaab840307080e76a4c382c4` |
| `verification/bats/regression-hole-guard-passes.yaml` | `3dc134df5ef922f6876e4a5ce212e90550f39aa6` |
| `verification/probes/index_cache_adversarial.py` | `e819607c2f844fd6c213f9df52fd7218b95f9804` ← the defective recognition |
| `verification/probes/chunk_diagnostic_preservation.py` | `b0ef73686971f230a3a0a4d309a910f44d88c8cf` |
| `verification/probes/declaration_emittability_agreement.py` | `c5a0dec8627926f2a1b8ff22ea777fbc0702b6c4` |
| `verification/probes/prereq_closure_attacks.py` | `d2fb7c8020b0f9759c2f5094f9ef80afae031bed` |
| `verification/probes/bounded_emitter_attacks.py` | `036068c6fb21f00e1d9fa3d849a5085a68b4b342` |
| `verification/probes/refusal_code_coverage.py` | `81aeda92365a459715b6b2013031dbc07623c0c2` |
| `verification/probes/per_unit_cost_baseline.py` | `c3db70a0c64af3bd7ba09e8b7719643366445563` |
| `verification/probes/hostile_chunk_scalar_types.py` | `134b8d48833493d7c08350c1437601a40c07b34c` |
| `verification/probes/lextoken_make_token_checker.py` | `211490561f936d4b5bd2c7c951a0e19205a94187` |

## Why it was superseded (the measured defect)

`try_refusal` in the v1 probe built its outcome as
`"REFUSED" if expect == "any refusal" else refusal.code`, then scored
`falsified = claim and outcome != expect`. With the IDX3 call site passing the prose expectation
`"any refusal"`, a correct refusal produced `outcome = "REFUSED"`, which can never equal
`"any refusal"` — the claim was reported falsified **whenever the compiler was right**.

Measured at `ba4b057` (duplicate edge correctly refused with the declared `CHUNK_DUPLICATE_EDGE`):

```
FALSIFIED: IDX3 index refuses duplicate child edge (same parent+role+childIndex) -> REFUSED (CHUNK_DUPLICATE_EDGE)
SUMMARY cases=9 claim_falsified=1
```

and the unchanged bat: `verdict=PROVEN`, `receipt:sha256:efaa538b969cdae067b251a780fbce5729339a98ddce05b64717b04a92247754`.
At `8396b63` the same probe was right "for the wrong reason" (the edge really was accepted).

## Re-run v1 for comparison (audit only)

```powershell
# runner (v1) against a pinned candidate, using the archived probe through the frozen manifest:
powershell -NoProfile -File verification\acceptance\v1\run_acceptance_gates.ps1 -Mode Preflight
git show 356a14e:verification/probes/index_cache_adversarial.py > $env:TEMP\idx_v1.py
python $env:TEMP\idx_v1.py D:\Projects\wt-a3-a1-ba4b057        # exit 1: REFUSED but FALSIFIED (the defect)
python verification\probes\index_cache_adversarial.py D:\Projects\wt-a3-a1-ba4b057   # v2: exit 0
```

The v1 copy is not wired into any pack or gate; it exists to make the supersession auditable.
