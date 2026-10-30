# Verified — A1 `46bf1c0` lands the blocker-2 recipe; blocker map now: Wall A + Wall B only (2026-10-30)

## Recipe landed — independently verified on both lines

A1 `46bf1c0` "Improve staged checker composition and adapter contract"
implements the tested recipe from
`FIX-RECIPE-blocker2-verified-wallA-measured.md` — visible in the diff:
`checker_cursor_value` now builds `CheckerNode` (8 fields) and
`nodes: List[CheckerNode]`; checker-start vector gains the Int arg;
checker-step arg is `typed_list("CheckerNode")` (plus a step-formula
adjustment — their own additional work).

| check | A1 `46bf1c0` own | combined `46bf1c0` + A2 `26be4be` |
|---|---|---|
| bundle | valid | valid |
| **`pep_c23.emit(trivial42)` smoke** | **OK — 3,205 B** | **OK — 4,379 B** |
| `test_a14_c23` | **2 known only** | 4 (Wall B set: countdown collapse, depth, + 2 known) |
| classifier | **1/1 PASS** (old emitter — no Wall A here) | **5 × `PEP_RUNTIME_STEP_LIMIT`** (Wall A) |
| `test_c23_cli` | **8/8 PASS** | **8/8 PASS** |
| `test_c23_str_contains` (A2 files) | — | **18 PASS** |
| nested (A2 files) | — | 65 tests total w/ str: **5 errors = ascii_continue only** (Wall A's twin); all other record/union/loop tests pass |

**A1's own line is green except the two long-known a14 items.** Their
#16 note ("adapter validation failure fixed; source-backed lexer test
passed the full wrapper-to-emitter path") reproduces exactly.

## Blocker map (current)

1. ~~Bundle typecheck~~ — **fixed** (both lines).
2. ~~Blocker 2 validation recipe~~ — **landed and verified** (emit OK
   own + combined).
3. **Wall A — classifier/`ascii_continue` staged emit cost: OPEN —
   the sole remaining `pep_c23.py`-path emit blocker.** Needs A2
   emitter cost work; A2 has been test-only since `26be4be` (no
   emitter commit since). str/cli green behind it prove it is
   closure-specific.
4. **Wall B — a14 all-in-one countdown collapse: OPEN in combined**
   (a14 4); A1-own with the old emitter shows a14 = 2 known, i.e. the
   collapse lives entirely in A2's emitter-cost series (the oscillation
   table stands).

## Honest notes

- Emitter blob on A1's line is still `9573c227` (old) — A1's green
  classifier result reflects the old emitter; only the combined state
  measures Wall A.
- Report lane's new section (`048bd6a`, collections suite half
  budget-blocked on A2's own branch) is consistent with the known 5
  checker-budget skips in A2's nested module — no contradiction.

Replay: corpus/`replay.py`/base untouched — **161/161** current.
