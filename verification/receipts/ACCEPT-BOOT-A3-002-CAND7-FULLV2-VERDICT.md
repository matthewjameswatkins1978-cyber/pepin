# BOOT-A3-002: independent Full-v2 verdict on Candidate7 implementation `6dce37d` (PEP-BOOT-20261106-01, Agent 3 slice 2-3/3)

**Seat:** Agent 3 (independent verify). `verification/**` only; no builder code, no caps/manifest/runner edits.
**PIN: A3 | `codex/bootstrap-agent3-verification` @ `b76aa19` (clean) → this receipt.**
**Candidate:** implementation merge `6dce37d` (branch tip `033de4f` is receipts-only; the IMPLEMENTATION was gated, per LUCY-20261106-004).
Detached read-only worktree `D:/Projects/wt-a3-cand7impl` (removed after evidence capture); nothing pushed there.
Runner: UNCHANGED `verification/tools/run_acceptance_gates.ps1` blob `b464e00e…`, baseline v2.

## Preconditions (C1/C2/C6)

- **C1 instrument:** own-tree `verify_frozen_manifest.py` → exit 0, 15 pins, drift 0. Candidate tree
  contains NO `verification/` directory (`git ls-tree 6dce37d verification/` empty) → it carries no
  grader; no pinned path modified. C1 HOLDS (by vacuity, stated — the script's literal invocation
  errors on a grader-less tree, which is the expected shape, not drift).
- **C2 ancestry:** `46b6712` (Candidate6) IS ancestor of `6dce37d`; published A2 re-pin `1658ea9`
  ("re-pin to A1 727f8af and fetch the checked-chunk contract") IS ancestor. No force-push
  (branch advanced `6dce37d`→`033de4f` by append). C2 HOLDS.
- **C6 scope:** only this new receipt file added on my branch. C6 HOLDS.

## Frozen Full-v2 (C3) — all rows, verbatim, `RESULT: FAIL (first_fail=discriminating rows)`

Runner JSON: `a3-runner-Full-161209.json` (verify head `b76aa195`, dirty=0). 15/16 gates pass:

| # | gate | result |
|---|---|---|
| 1 | frozen-manifest (13 entries) | ok — 13/13 match |
| 2 | acceptance baseline v2 | ok — v1 archive intact |
| 3 | pack parse-check | ok — exit 0 |
| 4 | combined emitter suites | ok — **Ran 54 tests, OK** (160.7s; expectation text says 53, matcher requires Ran+OK — actual 54 recorded) |
| 5 | stage probe x3 byte-identical bundle | ok — `7fc7bb4a…846` (3 identical; differs from seam-probe bundle `80c28ef5…` — different fixture, both deterministic) |
| 6 | discriminating rows lexer=valid/regression=valid | **FAIL** — actual `lexer=valid regression=PEP_RUNTIME_STEP_LIMIT` |
| 7 | synthetic-12 bounded-beats-whole | ok — check=valid unit0=emitted all=STEP_LIMIT |
| 8 | synthetic-8 fully green | ok |
| 9–12 | A2 probes (emittability, bounded-emitter, prereq-closure, per-unit-cost) | ok — falsified=0 (4,5,8 cases; cost byte_identity) |
| 13–15 | A1 probes (refusal-coverage, hostile-scalar, lextoken-checker) | ok — falsified=0 (2,12,2 cases) |
| 16 | pack run at integrated SHA | ok — exit 0, NOT_OBSERVED=3 PROVEN=0 |

**C3: FAIL** (contract-literal). Deliberate reading: exactly ONE red row, and it is the
scale row — the lexer row flipped to `valid` (staged checking now covers the real lexer chunk),
while the larger regression program still hits `PEP_RUNTIME_STEP_LIMIT`. Bounded-beats-whole
(s12/s8) intact. Capability gap, not a regression; red stays red, no relabel.

## C4 — published re-pin re-checked: HOLDS

- Candidate `tests/probe_seam_chunked.py` carries all three re-pin lines: `A1_SHA=727f8af…`,
  fetch tuple `("pep_chunk_contract.py","pep_chunk_contract.py")` (line 47),
  `"document": sem["document"], "revision": sem["revision"]` (line 745).
- `git diff 1658ea9..6dce37d -- tests/probe_seam_chunked.py` = ONLY A2's later additive
  str_concat hunk (G-A2-7); re-pin lines untouched.
- Dynamic proof transfers from BOOT-A3-001 (`b76aa19`): byte-equivalent recipe in clean
  scratch → EXIT 0, seed marker = pin, build-input blob = `rev-parse(727f8af:pep_ocaml.ml)`,
  11 negatives refusing. No hand-supplied file needed. (Pre-reg said "12 as A1 reports";
  independently enumerated **11** — correction published BEFORE this run in K-A3-8 and BOOT-A3-001.)

## C5 — hostile fact/provenance on candidate SHA: HOLDS as registered

- `stamp_schema_k1.py <candidate>` → exit 0, **claims=10 held=9 falsified=1**: the single
  falsified claim is the PRE-REGISTERED same-target forged-parameter admission
  (stamps are consistency-only, as A1 documents). All refusals held: duplicates/aliases
  `PEP_DUPLICATE_FUNCTION`, foreign doc/revision + cross-target `PEP_STALE_REVISION`,
  omitted fields transport-refused. No content-binding mechanism landed; residual NOT claimed repaired.
- `forged_to_native_k2.py <candidate> <candidate>/tests/pep_c23_emitter.pep` → exit 0,
  **claims=7 held=7 falsified=0**: forged-valid chunk emits AST-driven C; strict Clang AND GCC
  refuse it (`pep_str` vs `int64_t`). No silent-miscompile path.

## Supplemental strict Policy-B gate (separate; does not touch frozen rows): FAIL with measured progress

- Static closure at `6dce37d` (`^fn ` counts): lexer 10 + parser 80 + checker **125** + emitter 110 = **325 fns**
  (checker 103→125 since A4's census; growth recorded, not judged).
- Staged dynamic: `tests.test_lexer_chunk_ledger + tests.test_chunk_typed` on candidate → **43/43 OK** (245.1s).
- Known uncovered (staged): `utf8_check` one-shot `100001` (A1 trial `1019234`, NEGATIVE — closed, not repeated);
  whole-regression program `PEP_RUNTIME_STEP_LIMIT` (re-measured above, frozen row 6).
  Per-function exhaustive staged proof for all 325 NOT performed → remainder explicitly **UNKNOWN**, never claimed.
- Semantic-equivalence half: K1/K2 above + bundle determinism (x3 identical both probes) + 11 seam
  negatives + all green suites/probes. Equivalence holds where measured; the admitted same-target
  forgery residual bounds it honestly.

## Verdicts

- **Frozen Full-v2 on `6dce37d`: FAIL** — sole failing gate `discriminating rows` (`regression=PEP_RUNTIME_STEP_LIMIT`; lexer now `valid`).
- **Strict staged-zero-uncovered on `6dce37d`: FAIL** — uncovered functions remain (`utf8_check`, regression-scale); remainder UNKNOWN.
- Hand back to **A1**: cheapest next coverage lever per packet is integrating existing
  `analyze_chunk_typed_bound` statement-group evidence into the canonical ledger (utf8_check
  helper extraction stays closed). A2's computed-call-args slice and the 4KiB-vs-unbounded
  `str_concat` divergence decision are builder lanes; untouched here.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-cand7impl 6dce37da8930bdb4b0f5ba410c8042f23110545d
./verification/tools/run_acceptance_gates.ps1 -Mode Full -CombinedWorktree D:/Projects/wt-a3-cand7impl -VerifyRoot D:/Projects/wt-a3-gate
python verification/probes/stamp_schema_k1.py D:/Projects/wt-a3-cand7impl
python verification/probes/forged_to_native_k2.py D:/Projects/wt-a3-cand7impl D:/Projects/wt-a3-cand7impl/tests/pep_c23_emitter.pep
python -m unittest tests.test_lexer_chunk_ledger tests.test_chunk_typed   # in candidate tree: 43 OK
```
