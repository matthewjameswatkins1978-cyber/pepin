# A1 host repairs verified at `ba4b057` — IDX3 `CHUNK_DUPLICATE_EDGE`, STALE1 `PEP_STALE_REVISION`, CD3 still open; no over-refusal on real parses

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slices 1–2 and the repair half of slice 5) · **Evidence label:** `TESTED`
**Candidate measured:** `codex/p1-checker-cost-fix` @ **`ba4b0573bbba82e12045653f0c4bdc1f366fdb2e`** (pushed; pinned worktree `D:\Projects\wt-a3-a1-ba4b057`, detached, clean)
**Contrast pin:** `codex/checker-emitter-integration` @ **`8396b63`** (the previously verified failing candidate)
**My branch:** `codex/bootstrap-agent3-verification` · frozen runner blob `e5cad4df` and every bat/expectation untouched; **no frozen Full run** — `ba4b057` is an A1 fix branch, not an integrated successor of `8396b63` (verified: `8396b63` is not an ancestor of `ba4b057`).

## Slice 1 — my own reproducer had the defect the repair would have tripped over

`verification/probes/index_cache_adversarial.py`'s `try_refusal` helper computed
`outcome = "REFUSED" if expect == "any refusal" else refusal.code` and then compared that outcome
against `expect`. With `expect = "any refusal"` the comparison could **never** hold: a *correct*
refusal would have been scored as `FALSIFIED`. That is a false-negative in the gate, and it would
have reported IDX3 as still-broken immediately after A1 fixed it.

Repaired by Threadmoth (`edit`, `expect_count 1`, `unrelated_bytes_changed=false`, `lf→lf`) to
`outcome = expect if expect == "any refusal" else refusal.code`, so the outcome is canonical
(`REFUSED`) and the actual code still lands in `detail`. Frozen runners, bats, claims and
acceptance expectations were not touched — this is a non-frozen probe.

Disclosure: the same helper-shaped mistake appeared twice in this session's **new** edge probe
(`E1`/`E2` compared `"refused CHUNK_DUPLICATE_EDGE"` against `"refused"`), and the first run of that
probe scored two correctly-refused cases as failures. Caught by inspecting the run before recording,
repaired to carry only `refused` as the outcome with the code in `detail`. Recorded here rather than
quietly fixed: two instances mean the pattern, not the instance, is the risk.

## Slice 1 result — repairs verified, with exact codes

| case | at `8396b63` (baseline) | at `ba4b057` (repair) | verdict |
|---|---|---|---|
| **IDX3** duplicate child edge | `ACCEPTED (index built over duplicate edge)` | **refused `CHUNK_DUPLICATE_EDGE`** at `DocumentIndex` construction — "document has two children with parent 0, role 'statement', childIndex 0" | **REPAIRED** |
| **STALE1** crossed provenance | `outcome=ok`, report labelled rev2, `syntaxNodeCount=0` | **refused `PEP_STALE_REVISION`** before the tool ran | **REPAIRED** |
| **CD3** message parity | `PEP_UNKNOWN_TYPE` 11–18, wording differs | **unchanged**: whole `"Unknown type 'Nope'"` vs chunked `"Record field type is outside the implemented checker subset"` | **OPEN — owner decision** |

Full unchanged probe at the repair pin: `index_cache_adversarial.py` → **`SUMMARY cases=9 claim_falsified=0`**
(IDX1/IDX2 refusals, IDX3 now refused, CACHE1 `parse 3/3 typecheck 3/3 cache_hits 0→1→2` with
byte-identical diagnostics, CACHE2 exact `+4` span shift, CACHE3 revert restores revision identity,
STALE1 refused, consistent pre-edit pair still invokable). So the two repairs did not disturb the
reuse/determinism/staleness controls that sit around them.

## Slice 2 — edge-identity boundary, including the over-refusal the repair could have caused

New probe `verification/probes/edge_identity_boundary.py` (Agent 3 owned). A repair that keys
children too coarsely would reject *legitimate* documents, and that failure mode is invisible to the
original IDX3 claim, so it is measured directly against real parses.

| case | `8396b63` | `ba4b057` | reading |
|---|---|---|---|
| **E0** every parseable example builds a `DocumentIndex` | HELD (`built=9 refused=[]`) | **HELD** (`built=9 refused=[]`) | no over-refusal introduced |
| **E1** exact duplicate edge refused | **FALSIFIED** — `ACCEPTED (fail-open)` | **HELD** — `CHUNK_DUPLICATE_EDGE` | old failing baseline vs repaired |
| **E2** duplicate edge differing only in `kind`/`text` still refused | **FALSIFIED** — accepted | **HELD** — refused | identity is the edge, not the payload |
| **O1** (observation) real-parse key structure | 0 duplicate edges · **274 duplicate `(parent, childIndex)` pairs** | same | `role` is **load-bearing**: a `(parent, childIndex)`-only key would have refused real documents 274 times |
| **O2** (observation) distinct edges | same parent+childIndex/different role → accepted; same parent+role/different childIndex → accepted | same | the repair does not conflate distinct edges |
| **O3** (observation) document-level negative `childIndex` | accepted at index level | accepted at index level | unchanged IDX4 carryover; chunk validation still refuses it downstream |

Boundary fact: `examples/pep_parser.pep` (96,149 bytes) is above the 65,536-byte source-open cap, so
it is reported as a bounded **skip** (`PEP_SOURCE_BYTE_LIMIT`), not as a refusal or a harness error.

## What this does not say

- A1's `e36e67d` "flip 66n regression" and the S2 structural slices on this branch are **not verified
  here**. The 66n row belongs to the frozen Full procedure, which runs only on a genuine integrated
  successor of `8396b63`; nothing in this receipt shortens or relaxes that gate.
- CD3 is still an open owner decision (align the chunked messages with the seed, or declare message
  text outside the A13 guarantee). I have not narrowed the guarantee myself.
- One pin, one pass. No bisection of when the fail-open first appeared (it predates `05add76`, where
  it was first recorded).

## Reproduce

```powershell
python verification\probes\index_cache_adversarial.py  D:\Projects\wt-a3-a1-ba4b057     # exit 0
python verification\probes\edge_identity_boundary.py   D:\Projects\wt-a3-a1-ba4b057     # exit 0
python verification\repros\repro_host_defects.py       D:\Projects\wt-a3-a1-ba4b057 IDX3 STALE1   # exit 0
python verification\repros\repro_host_defects.py       D:\Projects\wt-a3-a1-ba4b057 CD3           # exit 1 (open decision)
python verification\probes\edge_identity_boundary.py   D:\Projects\wt-a3-int-8396b63     # exit 1 (E1/E2 = old baseline)
```

## Next action

Hand the repair confirmation and the still-open CD3 decision to A1 on #16. Frozen Full stays armed for
the first pushed **combined** successor of `8396b63` (tested checker + bounded emitter `e0e49e5`),
where the same unchanged runner decides acceptance; A3's verdict will be SHA-bound and will not
equate 15/15 with completed A→B→C self-hosting.
