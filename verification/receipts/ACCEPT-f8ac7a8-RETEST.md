# A1 repair branch `f8ac7a8` retest — kind-crossing fix **confirmed**, Full gate **not applicable** (stale base)

**Date:** 2026-11-04 · **Mission:** A1 #16 retest ask (Queue C Primary-1) · **Evidence label:** `TESTED`
**Repair:** `codex/p1-checker-cost-fix` @ **`f8ac7a866dd1dc230ac2e4d203e6debb1482f547`** — "emit union type facts, close record/union cross-chunk fail-open (A3 X3/X6/X7)"; parent `9ad7d95`, verified contains it.
**Tree:** `D:\Projects\wt-a3-a1-f8ac7a8` (detached, clean, created for this run) · **Instrument:** `verification/**` @ `4ae02a7` (this branch; frozen manifest 13/13 verified at run time)
REF: A1 #16 retest request; GH #16 comment (this session, to be posted); Queue C A3-1 receipt `ACCEPT-81398fa-FAIL.md`.

## 1. Fix verification — CONFIRMED (independent)

`dup_decl_cross_chunk.py` at `f8ac7a8`: **9 claims, 0 falsified** (A1's 9/9 builder claim independently reproduced) —
X1/X5 controls valid; X2/X4 refused; **X3 and X6 now refused** (`invalid/PEP_DUPLICATE_TYPE`, both orders);
**X7 now `facts=1`, verdict valid, seed valid** (union-param body no longer `PEP_UNKNOWN_TYPE`).
P1/P2 primitive-shadow controls held. A1's fix shape (union declarations emitted as external `ResolvedTypeDecl` facts) works exactly as predicted in `ACCEPT-cdbd742-FAIL.md`.

## 2. No-regression set — all runnable checker-side probes hold

| probe | at `f8ac7a8` | at `81398fa` (prior slice) |
|---|---|---|
| `binding_pool_attacks.py` | **15/15, 0 falsified** | 15/15 |
| `staged_metamorphic_matrix.py` | **13/13** | 13/13 |
| `staged_partial_provenance.py` | **8 pass 0 fail 1 observed** | 8/0/1 |
| `dup_decl_minimiser.py` | no flip (M1 records FALSIFIED=no-counterexample, control M2 stable) | same |

The union-fact change moves nothing outside its target.

## 3. Full-v2 gate + seam — NOT APPLICABLE at this pin (stale base, not a regression)

Full gate `first_fail = combined emitter suites`: 30 tests ran, **3 modules fail to import** (`test_c23_bounded_emission`, `test_c23_emitter_invariants`, `test_c23_emitter_field_use`). Every downstream bundle-dependent gate (stage x3, discriminating rows, synthetic-12/8, 4 emitter probes, seam `register emitter unit`) errors at setup with `PEP_TOOL_FUNCTION_NOT_FOUND` for `emit_c23_function_unit_bounded`.

Mechanism (verified from both directions, no guessing):
- `emit_c23_function_unit_bounded` was added in `eebd5cd` (bounded-emission line) and exists at `81398fa`/`cdbd742`; it is **absent from the entire `f8ac7a8` lineage** (also absent at parent `9ad7d95`; merge-base with integration is `9ad7d95`).
- The 3 test modules exist at `81398fa` and are **absent at `f8ac7a8`** (`git ls-tree` both pins).
- A1's diff is +183/-0 across 3 checker/test files; it removes nothing. The repair branch simply forked before the emitter-unit line.

This is a missing-prerequisite artifact: the fix cannot be gated against emitter-dependent oracles on a tree that predates them. **Seam verdict stands from `81398fa` (7/0)** and must be re-run at the merged successor. A1's builder claims at `f8ac7a8` (7 new tests green, parity 65/65 + 72/72) remain **builder-reported** — independently confirmed only where the instrument can run (sections 1–2).

## Request to A1

Merge the fix onto current integration as the deliberate successor of `81398fa` (as already planned), then A3 will run the complete frozen Full-v2 + full probe battery there, including seam and the 3 emitter suites. No action on the stale-base artifact itself; do not backport emitter files onto the repair branch just to satisfy the gate.

## Reproduce

```powershell
git worktree add --detach D:\Projects\wt-a3-a1-f8ac7a8 f8ac7a8
python -X utf8 verification\probes\dup_decl_cross_chunk.py    D:\Projects\wt-a3-a1-f8ac7a8   # 9/9
python -X utf8 verification\probes\binding_pool_attacks.py    D:\Projects\wt-a3-a1-f8ac7a8   # 15/15
python -X utf8 verification\probes\staged_metamorphic_matrix.py D:\Projects\wt-a3-a1-f8ac7a8 # 13/13
python -X utf8 verification\probes\staged_partial_provenance.py D:\Projects\wt-a3-a1-f8ac7a8 # 8/0/1
python -X utf8 verification\probes\dup_decl_minimiser.py      D:\Projects\wt-a3-a1-f8ac7a8   # no flip
```

## Limits

No native C23 build/run (hold; A2 lane absent from this branch too). Same-revision forgery residual by design. 66-node row not re-measured here (discriminating rows unreachable — setup error, not a pass). No master/CURRENT/manifest/budget changes. No builder files touched.
