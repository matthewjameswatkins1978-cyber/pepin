# A1 Integration Ledger — 7 November 2026 (LUCY-20261107-014 Slice 1)

Non-destructive record. No merges performed, no files merged, no pins moved.
Branch: `codex/a1-integration-ledger-20261107` @ this commit. Worktree: `D:/Projects/wt-a1-ledger` (clean).

## Live pins (verified `git ls-remote` + local `cat-file -t` this session)

| Lane | Branch | SHA | Worktree | Dirty |
|---|---|---|---|---|
| Base (campaign) | `campaign/pep-v01-sustained-build-20261027` | `57fe424af47e6c097b49eb26a711b3a9f0d7b980` | `D:/Projects/pepin` | `M tests/test_a14_c23.py` (pre-existing, preserved) |
| A1 | `codex/a1-typed-bound-pipeline` | `d8a4b6b12a0f6ed30b3dd8ed15267855cb588918` | `D:/Projects/wt-a1-fix` | clean tracked + 2 untracked `tests/fixtures/mc_seam_*.pep` (preserved) |
| A1 scratch | `scratch/a1-full-integration` | `57c5291` | `D:/Projects/wt-a1-scan` | clean — **STALE** (predates A2 `1885566`, not reused) |
| A2 | `codex/a2-divergence-spike` | `188556696ac225e2accfc53c281d59652b7aef51` | `D:/Projects/wt-a2-divergence` | clean |
| A3 | `codex/bootstrap-agent3-verification` | `c7786f1d3873e907027e640fe6d2231170627819` | `D:/Projects/wt-a3-gate` | (not inspected — A3-owned) |
| A4 | `spec/agent4-spec-lab` | `eb141c75fc7070a30cb69ca8c8e3e01793f7196b` | `D:/Projects/wt-spec-a4` | clean |

Accepted baseline (unchanged): A8 implementation `da244417`, acceptance `4132d3f`; `docs/packets/CURRENT.md` + manifest still point at A8. No phase advance, no master/release change.

## True merge-bases

- `merge-base(57fe424, d8a4b6b)` = `ed4d6cb19b6aac9620373e16d220354c7e496fb5`
- `merge-base(57fe424, 1885566)` = `ed4d6cb19b6aac9620373e16d220354c7e496fb5` (same)
- `merge-base(57fe424, eb141c7)` = `57fe424` (A4 forked at the campaign base; zero divergence)
- `d8a4b6b` is **not** an ancestor of `1885566` (checked `merge-base --is-ancestor`, exit 1):
  A2 tip does **not** contain A1's parser resumptions (`1724fd5`, `2a5dca1`) or error-path
  fixes (`98b4147`, `d8a4b6b`). `1885566` is likewise not an ancestor of `d8a4b6b`.
  Neither direction fast-forwards; a future candidate integration is a real merge, not a re-pin.

## File overlap vs base (`git diff --name-only 57fe424 <tip>`, sorted)

- A1 lane touches 167 paths; A2 tip touches 163 paths; **every A2 path is also an A1 path**.
- Exactly 4 A1-only paths: `examples/pep_parser.pep`,
  `tests/test_parser_error_contract.py`, `tests/fixtures/list_probe_native.pep`,
  `tests/probe_list_native.py`.
- Content direction is opposite per file: `examples/pep_parser.pep` at A2 tip lacks all A1
  resumption/error work (371-line net delta A1-tip→A2-tip on parser+contract+emitter trio);
  `tests/pep_c23_emitter.pep` at A1 tip lacks all A2 lowering work (mutable Str,
  loop-local `utf8_slice` lets, `List[Str]` prepend, loop emission).
- Shared files with **divergent content on both sides** (merge-conflict zone, must be
  reviewed hunk-by-hunk, never auto-resolved): `pep_c23.py`, `pep_chunk_contract.py`,
  `tests/pep_c23_emitter.pep`, `tests/pep_checker_a13.pep`, `tests/test_c23_cli.py`,
  `tests/test_a13.py`, plus probe/test files both lanes extended.
- `tests/test_parser_error_contract.py` exists at A1 tip only (15 shapes, tracked
  red/green); absent at A2 tip. A2's in-repo proofs for `1885566` (mutable-Str,
  utf8let, List[Str] pieces, Clang/GCC) exist at A2 tip only.
- A4 tip is docs/spec-only (`docs/spec/*`, `docs/outbox/AGENT4_OUTBOX.md`);
  `examples/dogfood/` there holds flat fixtures only — **no `pep0/` canonical compiler
  source yet**. Zero code overlap with A1/A2 lines: no conflicts possible, nothing to merge.

## Dependency order for a future candidate integration (not performed)

1. Real merge of A1 `d8a4b6b` + A2 `1885566` on a disposable branch; resolve the shared
   files above by hand; re-run: contract test, `test_c23_cli`, chained/chunk suites,
   list-native vertical, A2's `1885566` in-repo proofs. (Scratch `57c5291` cannot be
   reused: it carries A1 `d8a4b6b`-era content but pre-A2-tip emitter.)
2. A3 independent verdict on `1885566` (pending) and on the merged parser error path.
3. A4 first `examples/dogfood/pep0/` source + 1 positive / 2 negative inputs.
4. Test the candidate on the disposable branch only; report SHA, targeted tests, failures,
   and the missing true-self-host step (A→B→C). No master/accepted merge.

## Blockers / missing inputs (7 Nov, owned by peers)

- A3 verdict on A2 `1885566` (Slice 1) — pending.
- A4 canonical Pep-0 source + inputs (Slices 1–2) — pending; A4 lane is unblocked and writing.
- A2 waits only on a specific consumer refusal — none outstanding from A1's side.

## Receipts this session

- A1 CLAIM: issue #16 comment `6711724928`.
- Ledger branch: `codex/a1-integration-ledger-20261107` (this commit).

## Addendum — shared campaign base moved (no action)

- The shared checkout `D:/Projects/pepin` (`campaign/pep-v01-sustained-build-20261027`)
  advanced `57fe424` → `bddd354` ("Bootstrap Agent 3: Final verification
  summary", Matthew, 19:06 UTC): adds `FINAL_SUMMARY_BOOTSTRAP_AGENT3.md` and
  commits the previously dirty `tests/test_a14_c23.py` (+8). Nothing of A1's
  touched; the preserved dirty file is now in history, not lost.
- Merge-bases recorded here are unaffected (the advance is one commit on top
  of `57fe424`; both A1/A2 lines still diverge at `ed4d6cb`). This branch
  stays pinned where created — non-destructive record, no rebase.

## Addendum — transport slice end-to-end arc (all receipts on #16)

- **Sectional emit mapped** (`5ba0668` lane): per-slice `function-unit` calls
  with per-slice reports. 2/21 emitted; 11 refused on the two-fallible rule
  (root-caused to `may_fail` marking pure arithmetic fallible), 6 refused
  `known target` in var/condition positions (documented checked-path
  boundary), 1 (`main`, 222 nodes) hit the emitter STEP_LIMIT.
- **Merge machinery proven + committed** (`tests/test_a1_sectional_emit.py`,
  green): chain-merged host reports with group→slice id translation and the
  whole-file-functions carried-facts recipe (A2's form, adopted verbatim in
  `aa2f3c1`). Host-side merge rules recorded: string Ints, re-ranked
  syntaxIds, empty bindings/references, hard fail on holes.
- **Driver productized** (`pep_sectional.py` + `--sectional` flag, `92422d3`
  then `4caaed8`): fn-granular check + chain fallback, section assembly
  `header + prototypes + units + main`. Committed invariant is
  alpha-equivalence vs one-shot (per-slice locals renumber; exact-byte oracles
  bind native stdout only). Neighbor suites 20/20 on the touched driver.
- **A2 fix #1 re-run** (`b758c91`, disposable detached checkout, removed):
  3/11 newly emit, 1 changed refusal class, 6 hit the emitter STEP_LIMIT
  (gate masked a cost wall — profile before threading more code through it),
  6 still known-target, main still STEP_LIMIT. Fix #1 necessary but not
  sufficient for the `&&`-heavy matchers.
- **Awaiting:** A2 fixes #2 (checked path in var/condition positions) and #3
  (big-fn emitter budget, possibly profile-first); A3 pass for the Slice-3
  merge (plan pinned at `2a1075f`). `compiler_a` bytes unchanged rev-3
  through A4 `@cc91913` — no re-measurement owed.
- A1 lane: `d8a4b6b` pushed; scratch `57c5291` pushed (stale, recorded as such).

## Addendum — A2 proofs head `83995e4` (same session)

- A2 pushed `83995e4` ("in-repo compiler-A backend proofs for 1885566, Slice 1")
  on `codex/a2-divergence-spike`: one commit on top of `1885566`, implementation
  pin unchanged per A2's RESULT. Characterization above still holds (shared
  merge-base `ed4d6cb`, real merge needed, same divergent-content zone); the A2
  head reference advances `1885566` -> `83995e4` (content + proofs).
- A1 reserve taken this session (Slice 3 still gated on A3 verdict + A4 source):
  committed `tests/test_a1_record_construct_seam.py` + `mc_seam_*` fixtures on
  `codex/a1-typed-bound-pipeline @ 544a0c0` (pushed) — checker-layer twin, no
  duplication with the tracked parser contract (still OK 3/3).
- A1 RESULT: issue #16 comment `6711765350` (Slices 1+2).

## Addendum — sectional CHECK proven for compiler_a rev-3 (A1 transport slice)

Probe `sectional_check_a4.py` (A1 lane `_build`, method: whole-file chunk
parse → per-function header-signature batch via `chunk_signatures` →
`bound-chunk` per fn slice with fact_closure-filtered externals + host
builtins → statement-group chain with carried BindingPool on step-limit
fallback). Target `d78735e` (9639 B, 21 fns, 1452 nodes):

- 15/21 fns **valid at function-granular**: 32k–97k steps, 19–44 KB per call.
- 6/21 big fns (`find_fn`/`find_parens`/`find_brace`/`find_ds`/`check_tail`/
  `main`) hit `PEP_RUNTIME_STEP_LIMIT` whole-fn and **CHAINED** via statement
  groups: 14/14, 11/11, 24/24, 16/16, 9/9, 31/31, all groups valid.
- **ALL-VALID.** Every call ≤44 KB / ≤4.2k scalars — the transport walls are
  never approached; the step wall is handled by statement sub-sectioning
  (existing `bound-chunk` chain pattern, no new tool needed).
- Two probe bugs found and fixed on the record: externals must exclude the
  slice's own function (else `PEP_DUPLICATE_FUNCTION`); `fact_closure` takes
  int ids (strings silently match nothing → `ext=0` false negatives).
- Check side of the transport slice is DONE. Remaining: same pattern for
  EMIT (`function-unit`/`header`/`prototypes`/`main` parts with per-slice
  reports), then host driver productization in `pep_c23.py`.

## Addendum — Slice-3 merge plan (prepared, NOT executed; still gated on A3 pass)

Tip-vs-tip `b449179` (A1) .. `bea071a` (A2) is 22 files, +1172/-1771,
re-verified this session (was 13 files at `544a0c0`..`739befe`; both lanes
moved since). Everything else is byte-identical between the lanes. Per-file
resolution strategy for the future candidate integration:

- `examples/pep_parser.pep` (371): **take A1 wholesale.** A2 never touched the
  parser; A1's resumptions + error contracts parse A4's real `compiler_a.pep`
  complete (1452 nodes rev-3, 428+ steps, measured).
- `tests/pep_c23_emitter.pep` (272): **take A2 wholesale.** Delta now covers
  the may_fail OR-rule (fix #1, verified by A1 re-run), append→prepend cost
  work, plus the earlier lowering set. Still lowering-only — no
  parser/chunk-contract interface drift.
- `pep_c23.py` (23, 4 hunks): **hunk-level union.** A2's arena-relay hunk +
  A1's `--sectional` flag / `emit(sectional=)` kwarg / driver branch live in
  distinct regions (verified: no overlapping hunks). Take both, verify
  SourceBytes grants + strict flags intact at merge.
- `tests/test_c23_say.py` (30): **take A2's** (documented supersedes stand).
- `tests/test_c23_cli.py` (87): **hand-merge only**, unchanged rule.
- `tests/test_a14_c23.py` (18): **take A2's** (one-sided A2 change: arith-guard
  supersession pins).
- **Union, no conflict:** A1 side takes `tests/test_parser_error_contract.py`,
  `tests/test_a1_record_construct_seam.py` + `mc_seam_*`, list-native
  probe/fixture, `pep_sectional.py`, `tests/test_a1_sectional_driver.py`,
  `tests/test_a1_sectional_emit.py`; A2 side takes `test_c23_arith_guard.py`,
  `test_c23_bump_pool_boundary.py`, `test_c23_bump_pool_overflow_asan.py`,
  `test_c23_checker_budget_walls.py`, `test_c23_chunked_emission.py`,
  `test_c23_compiler_a_backend.py`, `test_c23_cross_chunk_call.py`.
- Post-merge gate before reporting: contract 3/3, seam 1/1, list-native PASS,
  sectional driver + emit 8/8, `test_c23_cli` full, bounded-emission 19/19,
  A2's in-repo proofs, and the `compiler_a.pep` sectional check re-run
  against the merged tree (expect emit to advance past fix #1/#2).
- MECHANICAL CHECK (no branch, no commit, worktree removed after): test-merge
  of A1 `b449179` + A2 `bea071a` in a detached scratch worktree applies
  CLEANLY with zero conflicts — both sides' content verified present in the
  merged tree (sectional wiring + arena hunk + may_fail OR-rule + both test
  families). The hand-merge items above remain judgment calls for content
  correctness, but git mechanics are not a risk. Aborted immediately after
  inspection; still gated on A3.
  sectional driver + emit 8/8, `test_c23_cli` full, bounded-emission 19/19,
  A2's in-repo proofs, and the `compiler_a.pep` sectional check re-run
  against the merged tree (expect emit to advance past fix #1/#2).
- A3 pass remains the entry condition per the dispatch. Re-diff at merge
  time regardless: both lanes are still moving.
