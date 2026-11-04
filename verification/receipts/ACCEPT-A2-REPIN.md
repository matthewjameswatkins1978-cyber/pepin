# F2-followup: A2 re-pin `e03553a` (A1 2e81f35) — exit 0 reproduced; R-ID-1 quiet as designed

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-012 / Campaign F fallback ("new A1/A2 SHA → review the changed interface") · **Evidence label:** `TESTED`
**A2 pin:** `codex/a2-bounded-emission@e03553a` ("re-pin probe to A1 2e81f35"), detached `D:\Projects\wt-a3-a2-e03553a` (clean before/after; ignored `_build/` only). Probe VERBATIM → **EXIT 0**. A1 checker SHA now `2e81f35` (contains R-ID-1 gate, union facts, binding stamps, CHECKED_CHUNK_CONTRACT; objects verified local; seed rebuilt by the probe via opam pepin-5.5.2).
**Toolchains:** Clang 23.1.4, GCC 16.2.0 (same as F2). Full log `_build/a2-repin-run.log` (worktree-local, ignored).
REF: A2 e03553a commit message (no BM/#16 handoff found — this receipt is the independent record); A3 F2 receipt ACCEPT-A2-PROOF.md; GH #16 (this session, to be posted).

## Result: re-pin is clean — no R-ID-1 collateral, no stamp/union breakage

- 4 chunks valid (18/55/8/5, unchanged node counts); header+3 units+epilogue (5,875 B, same size).
- Strict Clang AND GCC run → `42`; seed oracle → `42`.
- All 10 negatives OK with identical diags (stale still refused at host transport gate).
- **R-ID-1 gate (new in this A1 pin) does not fire anywhere in the probe**: the probe's per-chunk externals never name the chunk's own function, so the gate stays quiet exactly as designed — honest shapes unaffected, verified live rather than assumed.
- Raw-collision side NOT re-run: the renumber block is byte-unchanged and A1's helper is independently measured still broken at `4c4064e` (own builder pin `[9000,9000,9000]`, red by admission — A3 ran the pins), so raw behavior is unchanged by construction (INFERRED, labeled).

## Reproducibility: half the gap closed, half stands

- FIXED by A2 in this commit: `prepare()` now extracts `tests/chunk_helper.py` at the pin (the exact gap from my F2 receipt — consumed same-day, verified: probe passes line 94 unaided). ✅
- STILL OPEN: `pep_chunk_contract` import (line 265) has no extraction — fresh worktree fails `ModuleNotFoundError` again. I supplied `2e81f35:pep_chunk_contract.py` (pin-matching, 33,757 B) manually. **A2: one more line in `prepare()`** — same pattern as the helper fix.
- A2 pushed with no BM outbox/#16 handoff visible at run time; nothing in the commit needed one (7+/3- probe-only + docstring), but the R-ID-1-quiet result above is new evidence worth one line in their next receipt.

## Limits

No raw rerun (argued above, labeled inference). A1 pin `2e81f35` is test-only delta over `52cb397` (T-REC-3/5 pins); the R-ID-1/union/stamp substance was verified by A3 at earlier SHAs and re-confirmed live here through the probe. No builder files touched; no master/CURRENT/manifest/budget changes.
