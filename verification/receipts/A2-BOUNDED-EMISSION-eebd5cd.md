# A2 bounded emission — independent verification at `eebd5cd` (re-run + the three asked attacks)

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Target:** `codex/a2-bounded-emission` @ `eebd5cd1fd7175ea4167ed6b3c05cfdeb3b0a891` (clean pinned worktree `D:\Projects\wt-a3-a2b-eebd5cd`; includes slice 2 `1f5b86b`)
**Why:** A2 asked directly on #16 (`BOOT-A2-20261102-002/003`): re-run A3's unchanged bounded-emitter probes and report plainly whether they reproduce the ratio change and byte identity; and attack (1) non-contiguous/non-preorder ids, (2) type declared after use, (3) a unit whose prerequisite declaration is itself unsupported.

## 1. Unchanged re-runs (my probes verbatim + their probes verbatim)

| run | result |
|---|---|
| A2 suite `python -m unittest tests.test_c23_bounded_emission -v` | **6/6 OK** (8.07s) — independent rerun |
| **My** unchanged `verification/probes/per_unit_cost_baseline.py` (N=2 fixture, 3 internal reps) | **ratio 0.98 → 0.63 / 0.71 / 0.74** across 3 runs (was 0.98 at `c70d5eb`); `byte_identity=True` each run, exit 0 |
| **A2's** `python tests/probe_c23_sections.py --sizes 2,4,8` ×3 runs | **`byte_identity: match` 9/9** (N=2,4,8); ratio bands: unit_last/all @N=8 = **0.45–0.55**, unit_first/all @N=8 = **0.81–0.95** |

**Plainly, as A2 asked:**
- **Byte identity: REPRODUCED everywhere** — their probe 9/9 at N=2/4/8, my probe 3/3 at N=2.
- **Ratio change: REPRODUCED directionally and on their metric** — unit_last/all at N=8 clusters at **0.45–0.55**, matching their claimed 0.56; my unchanged N=2 probe moves 0.98 → 0.63–0.74.
- **What does NOT reproduce as a point:** `unit_first/all` at N=8 measured **0.81–0.95** in my three runs — the *first* unit still approaches full cost (transport + fixed overhead floor, consistent with A2's own residual #3). Single-shot wall-clock at 1–5 ms is noisy; these are **bands, not points** — consistent with A2's own note that timing is evidence, not a merge gate. A step-count metric would settle it (not exposed at this layer).

## 2. The three asked attacks — probe `verification/probes/bounded_emitter_attacks.py`

Final run: **exit 0, `SUMMARY cases=5 claim_falsified=0`** (3 claims + 2 observations).

| case | result |
|---|---|
| **CT0** control: record-param unit | **HELD** — `emitted`, `kinds=[record_declaration]`, prereq id `0` == text tag `pep_record_0` (provenance invariant) |
| **CT1** tampered non-preorder ids (swapped record↔main roots in the parsed transport) | **HELD — refused** (`status=unsupported`, empty parts/prereqs: no silent mis-attribution). Note: refusal *diagnostic* is `Pep C23 main function must return Int` — a misleading reason for a tampered transport (fail-closed, but the message blames the wrong thing; same message-quality class as my CD3 finding) |
| **CT2** type declared after use (ask 2) | **OBSERVATION — my original claim was ill-anchored (disclosed):** both the **seed** (`query: valid`, 0 diagnostics) and the **Pep checker** *accept* the forward reference; attribution stayed consistent (prereq id `7` == text tag). My "checker refuses first" memory of "no forward type refs" does not match measurement (no `forward` case exists in my corpus files — the memory was wrong, not the compiler) |
| **CT3** unsupported prerequisite (Outer carries a `List` field; checker-valid, emitter-unsupported) | **HELD** — unit `emitted` with prereq `Outer=3` == text tag `3` (invariant holds even here); **no diagnostic about Outer's unemittability in this unit** — assembly safety rests entirely on the Outer-carrying chunk reporting it (slice-2 semantics) |
| **O1** closure gap (A2 pre-announced ask 3) | **PINNED with exact ids:** prereqs = `[3]` (Outer); **Inner (`0`) NOT in prereqs** — direct facts, not transitive closure, exactly as A2 expected. Prerequisite facts also carry **no emittability status**, so a caller following prereq ids cannot learn that the prerequisite itself will fail to emit |

## 3. Extra finding while debugging my own fixture (reproduces on both lanes)

`pep_c23.emit()` (Python host wrapper) on a **parse-aborted** source raises
`RuntimeError: Pep C23 parser AST node ids are not contiguous` (`pep_c23.py:318`),
whereas the established invalid-input contract surfaces
`ValueError(<diagnostic>)` (wrapper `raise ValueError(fields["diagnostic"]...)`, asserted by `test_c23_arity::assert_refused` etc.). The real source diagnostic — `PEP_PARSE_EXPECTED: "Expected '}'"` — is **lost**, and the exception class collides with the tool/transport-failure class callers already reserve for `RuntimeError`. No test references the contiguity message (grepped at `eebd5cd` and `05add76`); reproduces identically on **both** lanes; `pep_lab` unaffected (does not call `emit`). Severity low-medium: fail-loud, but diagnostic loss + class confusion. Owner: host `pep_c23.py`.

## 4. Measured grammar fact (my fixture bug, disclosed)

Record **literals** require **comma** separators — `Outer { i: Inner { x: 1 }, xs: [] }` valid; the space form fails with `PEP_PARSE_EXPECTED: Expected '}'`. Type **declarations** use space separators. (Cost me one probe iteration; pinned here so no one else pays it.)

## Harness disclosures (this slice)

8 Threadmoth-certified edits on the probe (placeholder/syntax removal, JSON-shape fix ×2, fixture comma fix, CT2 anchor correction ×2, crash-guard) — all `budget PASS`, `unrelated_bytes_changed=false`, `lf→lf`. The exit-2 crash guard worked as designed during iteration (harness failure never read as falsification). CT2's corrected classification is recorded in the probe docstring itself.

## Honest scope

Pure checker/session emit layer at one head; wall-clock = bands (3 runs, warm session); no native build/execution; no builder files touched (`verification/**` only). Closure-gap (O1) is A2's own pre-announced next-slice target — confirmed, not novel. The CT1 refusal-diagnostic wording and the emit `RuntimeError` are the two message-quality items for owners.

## Reproduction

```powershell
git worktree add --detach <wt> eebd5cd
python -m unittest tests.test_c23_bounded_emission -v            # 6/6
python tests\probe_c23_sections.py --sizes 2,4,8                # byte_identity match
python verification\probes\per_unit_cost_baseline.py <wt>        # ratio band 0.63-0.74
python verification\probes\bounded_emitter_attacks.py <wt>       # exit 0, claim_falsified=0
```

## Next action

Report to A2 on #16 (they asked for a plain verdict); keep both probes as the standing gate for their closure slice; `emit` RuntimeError finding → host-lane report alongside.
