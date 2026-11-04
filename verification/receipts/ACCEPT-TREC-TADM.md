# A4 backlog rows 1–2 worked: T-REC-1..5 + T-ADM-4 executed at two pins

**Date:** 2026-11-04 · **Mission:** A4 B4-C6 §3 rows 1–2 (ordered A3 backlog) + B4-C4 T-REC + B4-C5 T-ADM-4 · **Evidence label:** `TESTED`
**Spec pins read (not edited):** `spec/agent4-spec-lab@489d722` — B4-C4-RECORD-UNION-CLOSURE.md (T-REC-1..5), B4-C5-ADMISSION-AUDIT.md (T-ADM-1..4), B4-C6-EVIDENCE-MATRIX.md (§3 order).
**Candidate pins (both detached, clean):** pre-fix `codex/checker-emitter-integration@81398fa` (`D:\Projects\wt-a3-int-81398fa`); post-fix `codex/p1-checker-cost-fix@f8ac7a8` (`D:\Projects\wt-a3-a1-f8ac7a8`).
**Instrument:** `verification/probes/dup_decl_cross_chunk.py` (9→14 claims, originals untouched) + `verification/probes/binding_pool_attacks.py` (+T-ADM-4, now 16 claims) @ this commit. JSON artifacts: `_build/trec-baseline-81398fa.json`, `_build/trec-f8ac7a8.json` (worktree-local, ignored).
REF: A4 AGENT4-20261104-012/013/014; GH #16 (this session, to be posted).

## 1. T-REC-1..5: pre-fix baseline at `81398fa` — A4's predictions confirmed exactly

14 claims, **6 falsified** (X3, X6, T-REC-1, T-REC-2, T-REC-3, T-REC-4):
- T-REC-1/2 fail-open (`valid`, no codes) ✅ as predicted in B4-C4 §5.
- T-REC-4 false-reject (`invalid` vs seed `valid`, facts=0) ✅ as predicted.
- T-REC-3 fail-open (`valid` vs seed `invalid/PEP_DUPLICATE_TYPE`) — same hole, producer side.
- **T-REC-5 HELD pre-fix — but codes=`['PEP_UNKNOWN_TYPE']`, zero facts emitted.** The refusal is the old union capability gap, NOT duplicate detection. Mechanism recorded in the JSON artifact so the post-fix comparison is exact (see §2).

## 2. T-REC-1..5: post-fix at `f8ac7a8` — 14/14, mechanisms exact

- T-REC-1/2: `refused+PEP_DUPLICATE_TYPE`, both orders (order-insensitivity locked).
- T-REC-3: refused, `duplicateFlags=[[True, True]]`, code `PEP_DUPLICATE_TYPE` — producer-side detection working, both facts flagged.
- T-REC-4: `valid`, seed `valid`, facts=1 — X7 flip as A4's R-REC-3 predicted (free consequence, no separate feature).
- T-REC-5: refused with code `PEP_DUPLICATE_TYPE` (vs `PEP_UNKNOWN_TYPE` pre-fix) — the count generalizes; the code flip proves the mechanism changed, not just the verdict.

## 3. T-ADM-1..4 — all TESTED now

- T-ADM-1 (O1b/O1c refuse `PEP_STALE_REVISION`; A1b raises): held 15/15 in prior slice.
- T-ADM-2 (identical re-admission dedupes silently): held (A1b distinguishes identical-0 from conflict-raise).
- T-ADM-3 (deepcopy egress lock): held (A4 isolates).
- **T-ADM-4 (new this slice): S4/O4-shape same-revision forgery (`ghost:Int`, stamps valid, producer never made it) is ADMITTED — expected-accept, held at both pins.** Binding probe now 16 claims, 0 falsified at `81398fa` and `f8ac7a8`. This documents the standing residual; verdict-level pinning stays with matrix row 3 (R-ID-1/callee-identity SHA, no such SHA exists yet).

## 4. Matrix-cell corrections for A4 (B4-C6 §1, for A4 to consume — own lane not touched)

- B4-CLOSURE-02/03 builder SHA is no longer NONE: `f8ac7a8` implements R-REC-1..3 (T-REC-1..5 all pass there).
- T-REC-1..5: UNKNOWN → TESTED at two pins (baseline 6-falsified-as-predicted; post-fix 14/14).
- T-ADM-1..4: "specified, unrun" → TESTED (T-ADM-4 expected-accept at both pins).
- B4-AUTH-05 (identity-keyed, consistent-by-construction): probed INDIRECTLY — A3 renumbering + conflict-raise + T-ADM-4 admission all consistent with identity-keyed pooling; still not a direct unit test of `_seen` keys (stating the limit honestly).
- Row 3 (R-ID-1/callee-identity) and row 4 (entry) untouched — no new SHAs, nothing to run.

## Reproduce

```powershell
python -X utf8 verification\probes\dup_decl_cross_chunk.py D:\Projects\wt-a3-int-81398fa  # 14 claims, 6 falsified (baseline)
python -X utf8 verification\probes\dup_decl_cross_chunk.py D:\Projects\wt-a3-a1-f8ac7a8   # 14/14
python -X utf8 verification\probes\binding_pool_attacks.py  D:\Projects\wt-a3-int-81398fa  # 16/16 incl. T-ADM-4 admitted
python -X utf8 verification\probes\binding_pool_attacks.py  D:\Projects\wt-a3-a1-f8ac7a8   # 16/16
```

## Limits

Full-v2 at `f8ac7a8` remains not-applicable (stale base, prior receipt); seam stands 7/0 from `81398fa`. No native execution (hold). T-REC-5 pre-fix "held" is mechanism-qualified (§1), not a pass of the duplicate machinery. No builder/spec files touched; no master/CURRENT/manifest/budget changes.
