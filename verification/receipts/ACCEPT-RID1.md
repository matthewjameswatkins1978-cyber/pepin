# A1 Primary-2 R-ID-1 gate — verified differentially (row 3, first SHA)

**Date:** 2026-11-04 · **Mission:** A4 B4-C6 §3 row 3 (first R-ID-1/callee-identity SHA) + Queue C A3 forged-call class · **Evidence label:** `TESTED`
**Repair:** `codex/p1-checker-cost-fix@52cb397` ("supply-time collision gate refuses chunk-local/external duplicate function names"); parent `f8ac7a8` verified by ancestry. Pre-gate pin `f8ac7a8`, post-gate pin `52cb397`, both detached/clean (`D:\Projects\wt-a3-a1-f8ac7a8`, `D:\Projects\wt-a3-a1-52cb397`).
**Instrument (new, this commit):** `verification/probes/fn_collision_gate.py` (R1/R2/R3, fixed expectations both pins — pre-gate falsifies to document the hole). Checker-side only, so it runs on repair-branch pins where the seam probe cannot (stale base: emitter-unit line absent). JSON artifact: `_build/fncoll-52cb397.json` (worktree-local, ignored).
REF: A1 #16 Primary-2 (`52cb397`, BOOT-A1-20261104-024); A4 B4-C6 row 3; GH #16 (this session, to be posted).

## 1. R-ID-1 differential — hole pre-gate, closed post-gate

| case | `f8ac7a8` (pre) | `52cb397` (post) | seed |
|---|---|---|---|
| R1 two-dup revision, chunk+externals collide | FALSIFIED (`valid`, no codes) — hole documented | HELD `refused+PEP_DUPLICATE_FUNCTION` | `invalid/PEP_DUPLICATE_FUNCTION` (A1's seed-parity claim confirmed on the oracle side) |
| R2 one-dup + self-consistent forged external naming the local fn | FALSIFIED (`valid`) — forgery admitted | HELD `refused+PEP_DUPLICATE_FUNCTION` | `valid` by construction — the refusal is rule behavior (collision refuses regardless), stated in the case detail, NOT seed parity |
| R3 honest control (externals name only other fns) | HELD `valid` | HELD `valid` — no over-refusal |

Gate source-read to build the fixtures (no guessing): `analyze_chunk_inner_bound` collects chunk-local top-level fn names (builtin/constructor exclusions mirrored), refuses on any external fn/sig name hit, skipped when no externals supplied. Fixtures use plain user fns, so exclusions are untested here (stated limit).

## 2. Row-3 legs triaged honestly

- **S4/O4-shape subset (externals naming the LOCAL fn): FLIPPED to refuse** — R2 above is exactly this shape for fn facts. ✅
- **True S4/O4 (non-colliding forgeries, externals name only other fns): NOT flipped, correctly so** — R-ID-1 fires on name collision only; a forged returnType for another fn passes the gate by construction. These need A2's document/revision schema on CheckedFunction/ResolvedSignature (still a proposal A2 must ACK; no wire change yet). Seam re-run impossible on this branch (stale base); verdicts stand from `81398fa` (S4 indistinguishable, O4 observed).
- **T-ADM-4 (binding forgery): still ADMITTED at `52cb397`** — binding probe 16/16, 0 falsified. No collateral change, as predicted (R-ID-1 gates fn/sig names, not bindings). The residual stands, locked as expected-accept.
- **T-CALL-6 (binding-id collision → refuse, never merge): NOT runnable** — no oracle exists (R-CALL-3 identity format still A1-to-declare; "A3's T-CALL-6 then has an oracle to test against"). R-ID-1 is a fn-name gate on a different axis. Deferred to the row that ships the identity format, with reason — not silently dropped.

## 3. Note for A2 (schema proposal, no action taken)

A1's proposal (document/revision on CheckedFunction+ResolvedSignature, stamp at production, reuse PEP_STALE_REVISION) mirrors the binding repair A3 already verified closed (15/15 + T-ADM-4 lock). If adopted, the S4/O4 flip becomes testable with the same O1b/O1c pattern; A3 can extend `fn_collision_gate.py` with stale/foreign callee facts the day a SHA carries the fields. ACK/counter-proposal is A2's to make.

## Reproduce

```powershell
git worktree add --detach D:\Projects\wt-a3-a1-52cb397 52cb397
python -X utf8 verification\probes\fn_collision_gate.py D:\Projects\wt-a3-a1-f8ac7a8   # R1/R2 falsified (hole), R3 held
python -X utf8 verification\probes\fn_collision_gate.py D:\Projects\wt-a3-a1-52cb397   # 3/3 held
python -X utf8 verification\probes\binding_pool_attacks.py D:\Projects\wt-a3-a1-52cb397 # 16/16, T-ADM-4 admitted
```

## Limits

Full-v2/seam at repair pins remain not-applicable (stale base, prior receipt); full battery waits for Primary-3 (merged successor of `81398fa`), as A1 scheduled. No native execution (hold). Builtin/constructor exclusions not probed. No builder/spec files touched; no master/CURRENT/manifest/budget changes.
