# REGRESSION on the A1 integration line — `d158044` pushes a native-path fixture over the checker step budget

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED` · **Classification: confirmed regression (new; not in any known-failure list)**

## The defect

At A1 `codex/checker-emitter-integration` head `05add76e21d4c979d243fa1fd7cbd0eb2a9d945c`, the test

```
tests.test_c23_str_contains.PepC23StrContainsTests.test_lucy_named_hole_continuation_guard_runs_natively
```

errors at the **check stage** (before any emission/native run):

```
RuntimeError: check parsed source: expected outcome='ok', received {...,
  'error': {'code': 'PEP_RUNTIME_STEP_LIMIT',
            'message': 'Execution step budget exceeded at 2514:26'},
  'metrics': {'parse_count': 3, 'typecheck_count': 3, 'cache_hits': 0}}
```

The fixture is Lucy's guarded-identifier-byte condition built from the real `examples/pep_lexer.pep` (`has_next_identifier_byte` + `ascii_digit`/`ascii_continue` predicates). The unchanged 100,000-step budget is exhausted while *checking* it.

## Bisect (53 commits, `6aadc4f..05add76`), boundary re-verified on both sides

| commit | role | single-test result |
|---|---|---|
| `6aadc4f` (2026-10-30, test added) | birth | **OK** (2.6s) |
| `61f1d33` (`fix(checker): accept empty list with nominal list annotation`) | parent of first-bad | **OK** (2.9s) |
| **`d158044c5fc512f038a91d8a3dc3223e3fb7dba9`** `perf(checker): fuse record loops, consult resolved field facts (make_token valid)` | **first bad** | **FAILED** (2.3s) |
| `05add76` (current head) | head | **FAILED** (2.4s) |
| A2-own `codex/a2-list-record-fields@c70d5eb` (checker change **absent**, test present) | cross-lane control | **OK** (3.1s) |

Method: `git bisect start 05add76 6aadc4f` + `git bisect run pwsh -File <probe>` over 53 commits, then both sides re-run manually (`git checkout <sha>` + single unittest). `d158044` touches **only** `tests/pep_checker_a13.pep` (+34/−10), so the flip is checker-side, not test-side.

## Terror Bats receipt (content-addressed)

- Bat `verification/bats/regression-hole-guard-passes.yaml` — `bat:sha256:c8e6b5a43f2e94a77e1a6cc82ffe3efadd543e4dfedbf765890d850a1a24c04a`
- Claim: *"the test passes at the pinned commit"* — oracle `exit_code run:0 not_equals 0`
- **Receipt: `receipt:sha256:67661e8d0e7da557dad52126b3d3a14163a81cea286f15fef57469bfa9cf8488`** (execution `6eaedbde-7380-4dbd-bfd3-104995465e81`, target `05add76`)
- Three layers: execution `Completed` / oracle `Falsified` / verdict **`PROVEN`** — deterministic evidence that the claim "this test passes at this commit" is false under the recorded conditions.
- stderr evidence `evidence:sha256:6d8a28edbf99b506efa000e520686d07b377531aa80f289c5b72517e09d28ce9` (digest verified on read) carries the verbatim `PEP_RUNTIME_STEP_LIMIT` failure inside the disposable worktree.

## Exhaustion position (mapped exactly, with the standing caveat)

Bundle line 2514 col 26 (bundle = `pep_c23.SOURCES` joined exactly as the tests do) maps to **`tests/pep_checker_a13.pep` line 143, col 26** — inside `is_constructor`'s full-node scan (`for node in nodes { if node.kind == "variant_declaration" ...`). That is *where the budget ran dry*, not proof of sole causation.

**Candidate mechanism (builder's call, not proven):** `d158044` adds an unconditional pre-scan of all nodes building `taRecordFields`/`taFieldDecls` at `type_analysis` entry, plus lazy `resolve_all_records` and the new `resolved_field_facts` lookups — extra spend that can push a fixture already near the ceiling over 100k. The bisect proves commit-level causality; the internal attribution is a candidate only.

## Blast radius (measured)

- **Integration line** `codex/checker-emitter-integration` `d158044..05add76`: affected. Module state at head: `tests.test_c23_str_contains` 25 tests → **21 pass, 1 error (this), 3 documented skips**; `tests.test_c23_cli` **8/8 OK** (native path otherwise healthy).
- **A1 structural line** `codex/a1-structural-budget`: `d158044` **is an ancestor** (change present); behaviour there **NOT_RUN**.
- **A2 line** `codex/a2-list-record-fields@c70d5eb`: unaffected (change absent; test OK).
- Not in the known-failure inventory (known set = a14 stale pair + arena CRLF): this is **new**. A1's posted suites this session (42/42 contract+scalar, ledger 4/4, node-cost 2/2, budgets 17/17) do not include this module, which is why it escaped both lanes' recent runs.

## Reproduction

```powershell
git -C <worktree> checkout --detach 61f1d33   # parent: OK
git -C <worktree> checkout --detach d158044   # first bad: FAILED
git -C <worktree> checkout --detach 05add76    # head: FAILED
python -m unittest tests.test_c23_str_contains.PepC23StrContainsTests.test_lucy_named_hole_continuation_guard_runs_natively
terrorbats run verification\bats\regression-hole-guard-passes.yaml --repo <worktree> --json   # PROVEN at 05add76
terrorbats replay receipt:sha256:67661e8d0e7da557dad52126b3d3a14163a81cea286f15fef57469bfa9cf8488
```

## Owner / next action

**Owner: A1 (checker, `tests/pep_checker_a13.pep`).** Agent 3 does not edit builder files. Suggested directions (builder's call): cut the unconditional pre-scan cost, hoist/caching for the scan helpers, or — if this fixture genuinely sits above the ceiling now — an explicit contract decision, not a silent test edit. Do not raise the 100k budget as a workaround (standing rule). Re-run this bat after the fix: expected `NOT OBSERVED`.
