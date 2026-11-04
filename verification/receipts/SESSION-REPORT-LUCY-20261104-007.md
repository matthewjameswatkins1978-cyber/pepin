# A3 session report — LUCY-20261104-007 (resumable)

**Date:** 2026-11-04 · **Role:** Pepin independent adversarial verification (Agent 3)
**Branch:** `codex/bootstrap-agent3-verification` @ **`cc7831d7adea63b0c0efd36e4ac5567247b715e5`** (pushed, remote-equal, clean)
**Previous mission preserved:** PEP-WB-A3-20261104-B closed PARTIAL at `a4f2833` — nothing here restarts or rewrites it.

## What this session delivered (3 bounded slices)

**Slice 1 — candidate `cdbd742` diagnosed (Lucy's "A3 FIRST").**
Report: `ACCEPT-cdbd742-FAIL.md`. Posted on #16: `6632568170`.
- Ancestry verified before the run: parents `c69e15d` + `f4eb231`; contains `8396b63`, `e0e49e5`, `0c5f12b`,
  `97e420b`, `f4eb231`. **A2 `ea0bc9a` is absent from the integrated line.**
- Instrument verified before the run: manifest 13/13, runner `b464e00e…`, probe `688042d7…`, v1 archive
  `e5cad4df`/`e819607c` intact.
- **Verdict: FAIL 14/15.** Sole red gate 5 — `lexer=valid regression=PEP_RUNTIME_STEP_LIMIT`,
  `check=valid unit0=emitted all=PEP_RUNTIME_STEP_LIMIT`. Green: pack parse, 53 emitter suites
  (`Ran 53 tests in 150.124s OK`), stage ×3 `1a223920…`, synthetic-12/8, 7 probes 0 falsified, pack run
  exit 0 `NOT_OBSERVED=3 PROVEN=0`.
- **Duplicate-type repair VERIFIED CLOSED**: minimiser no longer flips (control stable), metamorphic matrix
  **13/13** (was 12/1), partial/provenance 8/0/1, cross-chunk duplicate **records** refused, primitive
  shadowing refused.
- **Residual hole FOUND (A1)**: record/union **namesake split across chunks** is accepted `valid` where the
  seed refuses `PEP_DUPLICATE_TYPE`, both orders; distinct-name control valid. Cause: only records become
  external facts (`resolve_all_records`), so neither the producer `duplicateType` flag nor the consumer
  repeat-name count can fire. Same cause refuses union-typed parameters across chunks with `PEP_UNKNOWN_TYPE`
  on a seed-valid program (fail-closed capability gap).
- Stale `BindingFact` fail-open still open at this pin (3 falsified: `O1c`, `O1b`, `A1b`).

**Slice 2 — row-level negative + primitive-shadow control.** Posted on #16: `6632600159`.
- `exact_node_ladder.py`: **62 nodes ok / 64 refuse** — the identical pre-repair band. The repair costs and
  moves the 66-node row nothing; 4 nodes (≈6 % of the per-node budget) short.
- `checker_pass_attribution.py`: `analyze_parsed` is the only refusing pass; the **new whole-source duplicate
  scan stays `ok`** at every rung measured (484-node boolean chains included) — it is not a cost driver.
- Primitive shadowing (`type Int {…}`, `type Bool {…}`): seed refuses `PEP_DUPLICATE_TYPE`; staged also
  refuses but via `PEP_A13_TYPE_UNSUPPORTED` + `PEP_UNKNOWN_FIELD`. Fail-closed — diagnostic mismatch only.

**Slice 3 — composition with A2's lane.**
- Scratch both-lane tree `D:\Projects\wt-a3-seam2` = `merge-tree cdbd742 ea0bc9a` → `4915a76c…`, local commit
  `8356373a05252217ed40d3b0621b0369ae611408` (**never pushed; measurement fixture, not a candidate**).
- `seam_cross_chunk_attacks.py`: **7 cases, 0 falsified**. Forged arity/name still refused; emitter still
  emits for the matching document and refuses a foreign report with `REFUSED:PEP_STALE_REVISION`. A1's call
  contract weakened no guard.
- `dup_decl_cross_chunk.py` on the merged tree: duplicate records refused, distinct names valid, **X3/X6 still
  accepted** — the residual hole is present in the merge too, so any union-fact fix must be validated there.

## Committed capability (permanent on this branch)

| artifact | purpose |
|---|---|
| `verification/receipts/ACCEPT-cdbd742-FAIL.md` | candidate verdict, repair verification, residual hole, row numbers, composition check |
| `verification/probes/dup_decl_cross_chunk.py` | 9 claims: cross-chunk duplicate records (X1/X2/X4/X5 controls), record/union namesake (X3/X6), union-fact coverage (X7), primitive shadow (P1/P2) |
| `verification/probes/dup_primitive_shadow.py` | cheap seed-oracle check for the primitive-shadowing exception |

## Exact next action (resume here)

1. `git fetch origin` and read `origin/codex/checker-emitter-integration` and
   `origin/codex/p1-checker-cost-fix`. Today they are `cdbd742` / `f4eb231` — **already diagnosed; do not
   re-run unchanged pins**.
2. On a **newer** integrated successor, or on an A1 repair of the stale `BindingFact` fail-open:
   verify ancestry + baseline-v2 instrument identity first, then run, in this order:
   ```powershell
   pwsh -NoProfile -File verification\tools\run_acceptance_gates.ps1 -Mode Full `
     -CombinedWorktree <new-worktree> -OutJson _build\accept-<sha>.json
   python -X utf8 verification\probes\dup_decl_minimiser.py <new-worktree>
   python -X utf8 verification\probes\staged_metamorphic_matrix.py <new-worktree>
   python -X utf8 verification\probes\staged_partial_provenance.py <new-worktree>
   python -X utf8 verification\probes\dup_decl_cross_chunk.py <new-worktree>
   python -X utf8 verification\probes\binding_pool_attacks.py <new-worktree>
   python -X utf8 verification\probes\seam_cross_chunk_attacks.py <both-lane-merge-tree>
   ```
   and post the SHA-bound verdict on #16 with a receipt in `verification/receipts/`.
3. If A1 ships union facts: the expected flips are X3/X6 → refused and X7 → `valid`; if A1 ships binding-fact
   identity: `O1c`/`O1b`/`A1b` → held. Anything else is a partial repair and should be reported as such.

## Discipline notes carried forward

- Never describe the current instrument as the original unchanged suite (baseline v2 adopts `688042d7`).
- Scratch merge trees are measurements, never candidates; only A1 integrates.
- `verification/**` is A3's only write surface; A1 owns Current Status; A2's lane is untouched.
- Report the *measured* band, not a projection: 62/64 is measured at `cdbd742`, not inferred.
