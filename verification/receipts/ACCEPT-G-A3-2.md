# G-A3-2: E2b repair at `2ad750b` — all flips land with the specified code

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-013 / Campaign G A3 G-A3-2 · **Evidence label:** `TESTED`
**Repair:** `codex/p1-checker-cost-fix@2ad750b` ("refuse repeated/aliased external callee facts in one batch"), detached `D:\Projects\wt-a3-a1-2ad750b` (clean). Gate source-read to build expectations (batch name-repeat + id-alias loops, R-ID-1 first, builtins/ctors excluded, empty span).
**Instrument:** `verification/probes/ext_callee_attacks.py` (+E2bR reversed-order claim, this commit). JSON artifact `_build/extcallee-2ad750b.json` (worktree-local, ignored).
REF: A1 G-A1-1 commit message; A3 E2b repro (ACCEPT-EXT-CALLEE.md); GH #16 (this session, to be posted).

## Result: 6 records, 0 falsified — pre/post differential against `46b6712`

| case | `46b6712` (pre) | `2ad750b` (post) |
|---|---|---|
| E4 honest distinct-name/unique-id batch | valid | **valid** (unaffected ✅) |
| E1 colliding synthetic ids, distinct names | VALID (falsified) | **refused + PEP_DUPLICATE_FUNCTION** (aliased-ids rule ✅) |
| E2a identical duplicate entries (observation) | valid | **invalid + PEP_DUPLICATE_FUNCTION** (policy = refuse, not dedupe) |
| E2b contradictory batch | VALID (falsified, the repro) | **refused + PEP_DUPLICATE_FUNCTION** ✅ |
| E2bR contradictory batch, forged-first order | (new) | **refused + PEP_DUPLICATE_FUNCTION** (order-insensitive ✅) |
| E3p wire-field inspection | identity-free | **identity-free** (no stamps in this commit; field lists re-printed) |

Diagnostic span: empty node per A1's message (no local span exists for purely external collisions) — recorded, not separately asserted.

## Coverage notes vs the G-A3-2 card (honest deltas)

- Both name/fact orders: covered (E2b + E2bR). Identical vs contradictory: covered (E2a observation + E2b claim). Honest two-callee: covered (E4).
- Primitive/builtin exclusions: NOT probed (fixtures use plain user fns; A1's own tests own the exclusion paths — stated limit).
- Stale fn facts: NOT APPLICABLE — the wire schema still carries no document/revision (E3p re-verified), so staleness is unstageable; G-A3-3 waits on the schema SHA.
- Seed code/span: seeds printed per case (single-dup sources seed-valid by construction; the requirement is principle + A2 ambiguous-target precedent, as in the repro receipt).

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-a1-2ad750b 2ad750b
python -X utf8 verification\probes\ext_callee_attacks.py D:\Projects\wt-a3-a1-2ad750b  # 6 records, 0 falsified
```

## Limits

Repair-branch pin (not an integrated candidate — G-A3-6 waits for Primary-7). No native execution. No builder/spec files touched; no master/CURRENT/manifest/budget changes.
