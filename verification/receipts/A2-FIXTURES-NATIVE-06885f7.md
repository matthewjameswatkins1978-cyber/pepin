# A2 `06885f7` — adversarial fixtures + native parity independently verified (emittability gap confirmed structurally)

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Assignment:** three-agent routing A3 item 2 — "challenge the four fixtures and the three native cases".
**Target:** `codex/a2-bounded-emission` @ `06885f71065b483e1f3630fa9c423eae4a0320d6`
(clean pinned worktree `D:\Projects\wt-a3-a2b-06885f7`; chain …`cbdce20 → 06885f7`).

## 1. A2's suite, rerun unchanged — **14/14 OK, ZERO skips, 11.9s** (second run 6.6s)

All four adversarial fixtures pass under independent execution:
`test_self_referential_union_closure_terminates`, `test_mutually_recursive_union_closure_reports_both_and_stops`,
`test_forward_declared_type_resolves_in_prerequisites`,
`test_index_arguments_and_node_id_arguments_are_not_interchangeable`.

**All three native cases EXECUTED, not skipped** (the `OK` line carries no `skipped=`):
`test_reassembled_unit_output_compiles_and_runs_under_clang_and_gcc` (scalar → 42),
`test_record_dependent_assembly_compiles_and_runs_natively` (typedef → 42),
`test_arena_dependent_assembly_compiles_and_runs_natively` (arena → 4) — each assembled
byte-identical, compiled `-std=c23 … -Werror` under **both** discovered compilers, run,
output compared to the interpreter. A2's "silent skip fails the test" property holds
in my run (zero skips observed).

## 2. Their timing claim, re-measured (3 runs, their protocol)

`probe_c23_sections --sizes 2,4,8` ×3: **byte identity 9/9 match**.
unit/all ratios per run: N=2 `0.79/0.60/0.59` (median **0.60**), N=4 `0.75/0.74/0.67`
(median **0.74**), N=8 `0.51/0.84/0.49` (median **0.51**); unit_last@N=8 `0.54/0.87/0.47`.
A2 published medians **0.64 / 0.65 / 0.56** — same band (mine 0.51–0.74 vs theirs
0.56–0.65); wall-clock at 1–6 ms stays noisy, bands remain the honest form. Their
"not O(1) end-to-end" statement agrees with my standing baseline (ratio floor ~0.6 from
transport of the whole parsed AST).

## 3. My probes, unchanged, at this SHA — all green

| probe | result |
|---|---|
| `per_unit_cost_baseline` | exit 0, ratio **0.71** (band series 0.98 → 0.63–0.74 → 0.67/0.71), `byte_identity=True` |
| `bounded_emitter_attacks` | **exit 0, `claim_falsified=0`** — CT0/CT1/CT3 held; CT2 + O1 observations (forward-decl accepted by seed+checker, attribution consistent) |
| `prereq_closure_attacks` | **exit 0, `SUMMARY cases=8 claim_falsified=0`** — CL1 exact `[Expr]`; CL2 exact `[Ping,Pong]` + whole refuses `tagged union has an unsupported layout`; CL3 both decls; CL4 refused at checker |

My fixtures and A2's four fixtures are **independent constructions of the same properties**
(different sources, different harnesses) — both suites green at the same SHA = double-sourced.

## 4. The named gap: prerequisite emittability — confirmed, with a concrete instance

- **Structural:** the bounded-unit report carries exactly
  `status, diagnostic, sourceParts, prerequisiteKinds, prerequisiteIds, requiresArena` —
  **no emittability field** (`emittability_field_present: false`). A2's honest "named gap"
  statement is accurate: a caller cannot learn emittability from the report.
- **Concrete instance at this head (from my CL2 stage map):** unit `take(p: Ping)` =
  `emitted` with prereqs `[Ping, Pong]`, while whole-program emission = `unsupported —
  "Pep C23 tagged union has an unsupported layout"` — the caller holding the unit+facts
  has no in-report signal that assembly of those declarations will fail; only whole
  emission reveals it. Exactly the gap A2 says needs a per-declaration entry point.
- **New observation:** my list-field fixture (`Outer { i: Inner xs: List[Int] }`) now
  passes **whole-program emission** at this head (`whole_status: emitted`) — the
  list-valued record field is no longer an emitter refusal here; the genuinely
  unemittable case has moved to tagged-union layout. (Campaign-era "List refused"
  receipts are stale for this head; recorded, not claimed.)

## Honest scope

One head; wall-clock = bands (3 runs, warm); native evidence = independent rerun of
A2's executed tests (compilers ran in my process — zero skips recorded), not a
second hand-written native harness; no builder files touched (`verification/**` only).
Job items 1 and 3 still gated: A1 head `05add76` (pack replay armed), no pinned
integrated candidate.

## Reproduction

```powershell
git worktree add --detach <wt> 06885f7
python -m unittest tests.test_c23_bounded_emission -v        # 14/14, 0 skips
python tests\probe_c23_sections.py --sizes 2,4,8             # x3: identity match
python verification\probes\prereq_closure_attacks.py <wt>    # exit 0, 8/0
python verification\probes\bounded_emitter_attacks.py <wt>   # exit 0, 5/0
python verification\probes\per_unit_cost_baseline.py <wt>    # ratio band
```
