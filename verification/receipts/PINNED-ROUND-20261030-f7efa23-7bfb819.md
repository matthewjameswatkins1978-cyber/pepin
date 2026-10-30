# Pinned differential round — A1 `f7efa23` / A2 `7bfb819` (2026-10-30)

Detached read-only worktrees; no builder-owned file edited on any branch.

## What landed this round

- **A1 `f7efa23`** "Reduce staged checker composition costs": staged
  type-analysis chunks to four AST nodes, compacted continuation cursor,
  96-local regression added (`test_a13` 79→80). Builder receipt claimed
  93/93 A13+nested and 16/16 driver+cli, and stated **"Native run not
  performed in this slice"** — that arm is this lane's job.
- **A2 `7bfb819`** `5445bda`+`7bfb819`: **SourceBytes lowered to C23**
  (checked `byte_at` + `byte_length`); `test_c23_str_contains` 12→14
  tests. Emitter blob moved again: `8493e9d3…` → **`23ef2b19…`**.

## Verification results

| state | check | result |
|---|---|---|
| A1 `f7efa23` (clean) | `test_a13` + `test_a13_nested_records` + `test_c23_driver_validation` + `test_c23_cli` | **109/109 OK** — confirms their 93+16 claim exactly |
| A1 `f7efa23` (clean) | `test_a14_c23` + classifier (**the native arm they skipped**) | 12 tests, **2 FAIL — same two a14 failures by name** (recursion contract, length exemplar); classifier 1/1 OK |
| **combined** `f7efa23` + A2 `7bfb819` emitter (`23ef2b19`) + str_contains test | `test_c23_str_contains` (14 tests) | **14/14 OK, ZERO skips** — incl. the two new SourceBytes native tests |
| combined | `test_a14_c23` + `test_c23_cli` + classifier + `test_c23_driver_validation` (28 tests) | 26 OK, **2 FAIL — same two a14 failures by name**; new emitter introduces no regression |
| A2 `7bfb819` own branch | `test_c23_str_contains` | **14 OK (3 skipped per contract)** |

**No new failure anywhere.** Recursion-contract decision still not
landed: `test_a14_c23.py` empty diff across `fd5c5d5..f7efa23`.

## Significance for the self-hosting path (observed, not speculated)

SourceBytes was one of the two named blockers for the `utf8_check`
harness (report's earlier inventory: `byte_length(source_bytes())`
"calls require a known target"). With `7bfb819` those calls lower
natively and execute correctly in the combined state — verified by
execution, not by reading the emitter. The remaining named blockers
(loop-body `let`, function-shape diagnostics, checker budget at larger
sizes) are tracked in the report lane's counted inventory; none of them
regressed here.

## Cross-lane

Report `c05cc06` independently re-ran the `eb8f7c0` baseline: 262
tests, same three known failures — matches my baseline exactly. Its
sections on budget-masking (third occurrence) and the withdrawn
reorder-the-checks recommendation are its own findings; nothing there
contradicts this round's measurements.

## Replay

Corpus, `replay.py`, base `805062b` untouched — **161/161 PASS**
(`ede45d8`) remains current.
