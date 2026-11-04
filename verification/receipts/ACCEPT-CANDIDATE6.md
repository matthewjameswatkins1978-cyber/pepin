# INTEGRATED-CANDIDATE-6 `46b6712` — Full-v2 **FAIL 14/15**; repairs verified in-tree; T-ADM-4 pinned against A1's expectation

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-012 / Campaign F A3-F1 · **Evidence label:** `TESTED`
**Candidate:** `codex/checker-emitter-integration` @ **`46b6712df20eba5ec5dea5a95771017f4245602a`** — "union type facts + supply-time collision gate (INTEGRATED-CANDIDATE-6)". Parents verified: `81398fa` + `52cb397` (exact); `e0e49e5` in ancestry; `152f76c` NOT in ancestry (merge-base fails). Later A1 test-only `2e81f35` deliberately absent per assignment.
**Tree:** `D:\Projects\wt-a3-c6-46b6712` (detached, clean) · **Instrument:** `verification/**` @ `751c274` (frozen manifest 13/13 verified at run time; no instrument change this slice)
REF: A1 BOOT-A1-20261104-025 + #16 Candidate-6 message; GH #16 (this session, to be posted).

## Verdict: FAIL 14/15 — sole red is the 66-node row, measured not assumed

Full gate (`run_acceptance_gates.ps1 -Mode Full`): manifest ok, baseline-v2 ok, pack parse ok, combined emitter suites **53 OK**, stage x3 byte-identical, synthetic-12 ok, synthetic-8 ok, 7 probes ok (0 falsified), pack run ok. Red: discriminating rows `lexer=valid regression=PEP_RUNTIME_STEP_LIMIT`. `first_fail = discriminating rows`. No gate skipped.
Row-level (`exact_node_ladder.py`): **62 nodes ok / 64 nodes PEP_RUNTIME_STEP_LIMIT** — identical band to `81398fa`/`cdbd742`. Both integrated repairs cost the row nothing and move it nothing. **Candidate-6 is NOT accepted** (fails the frozen 15/15 standard on the unchanged red row).

## Repairs verified IN the integrated tree (not just on repair branches)

| battery | at `46b6712` | prior pin |
|---|---|---|
| `dup_decl_cross_chunk` (T-REC 14) | **14/14** (T-REC-1/2 +code both orders; T-REC-3 flags [[True,True]]+code; T-REC-4 valid; T-REC-5 refused+code) | 14/14 at `f8ac7a8` |
| `binding_pool_attacks` (16) | **16/16** (O1b/O1c invalid+code; A-conflict/deepcopy locks hold) | 16/16 at `81398fa`/`f8ac7a8`/`52cb397` |
| `fn_collision_gate` (R1/R2/R3) | **3/3** (R1+R2 refused+PEP_DUPLICATE_FUNCTION, R3 valid) | 3/3 at `52cb397` |
| `dup_decl_minimiser` | no flip (M1 records no-counterexample; M2 stable) | same |
| `staged_metamorphic_matrix` | **13/13** | same |
| `staged_partial_provenance` | **8 pass 0 fail 1 observed** | same |
| `seam_cross_chunk_attacks` | **7 cases, 0 falsified** (emitter unit present in-tree; S4 indistinguishable + O4 observed stand) | 7/0 at `81398fa` |
| `source_ingress_negative` | **4/4** (G1/G3 host PEP_STALE_REVISION, G2 pep A13_PARSER_BUDGET) | 4/4 at `81398fa` |

## T-ADM-4 pinning — explicit verdict against A1's expectation (row 3)

A1 asked to pin "T-ADM-4 residual now refuses on fn-name collision (R-ID-1)". Measured at `46b6712`, the picture splits by fact kind:
- **Binding-level forgery (`ghost:Int`, T-ADM-4 as specified in B4-C5 §4): still ADMITTED** — expected-accept UNCHANGED. R-ID-1 gates `CheckedFunction`/`ResolvedSignature` names only; it does not touch `BindingFact` admission. A1's expectation does not apply to this case; reusing the expected-accept row here would mislabel the behavior.
- **Fn-fact subset (R2: self-consistent forged external naming the local fn): REFUSES with PEP_DUPLICATE_FUNCTION** — the flip A1 predicted, verified 3/3 in-tree.
- **True S4/O4 (non-colliding forgeries) and T-CALL-6 (binding-id collision): unchanged/open** — need A2's schema / R-CALL-3 format respectively; neither SHA exists.
Net for the matrix: row 3 is closed for the colliding subset, open by prior analysis everywhere else. No behavior in this candidate contradicts that split.

## Reproduce

```powershell
git worktree add --detach D:\Projects\wt-a3-c6-46b6712 46b6712
pwsh -NoProfile -File verification\tools\run_acceptance_gates.ps1 -Mode Full -VerifyRoot <a3-worktree> `
  -CombinedWorktree D:\Projects\wt-a3-c6-46b6712 -OutJson _build\accept-46b6712.json
python -X utf8 verification\probes\dup_decl_cross_chunk.py    D:\Projects\wt-a3-c6-46b6712   # 14/14
python -X utf8 verification\probes\binding_pool_attacks.py    D:\Projects\wt-a3-c6-46b6712   # 16/16
python -X utf8 verification\probes\fn_collision_gate.py        D:\Projects\wt-a3-c6-46b6712   # 3/3
python -X utf8 verification\probes\seam_cross_chunk_attacks.py D:\Projects\wt-a3-c6-46b6712  # 7/0
```

## Limits

No native C23 build/run in this slice (F2 covers A2's path separately). Same-revision forgery residuals stand as documented. Builder counts cited by SHA only. No master/CURRENT/manifest/budget changes. No builder/spec files touched.
