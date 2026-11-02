# Real-lexer chunk ledger → node-volume correlation at A1 `05add76`

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Scope:** LUCY-20261102-005 target “5/10 working real lexer chunks vs four step-limited functions”, analysed against A1's *corrected* thesis (“node volume, not construct”, issue #16 `81302767` slice) and A1's earlier pinned framing (“construct-driven”, ledger test docstring at `87c9fec`).

## Method

Probe `verification/probes/lexer_chunk_volume_correlation.py` at `05add76` (clean pinned worktree `D:\Projects\wt-a3-mimo-8130276`): reuses the builder's measuring harness **read-only** (`tests.test_lexer_chunk_ledger.measure` + `tests.chunk_helper` — no builder file touched, no duplicated chunker) and executes the full staged pipeline itself, then applies **my** claims and the correlation/cost-band analysis, which neither pinned document performs.

Direct run: exit 0, `SUMMARY cases=7 claim_falsified=0` (5 claim cases + 2 observations). Claims: C1/C1b pinned-valid chunks valid, C2 pinned hot chunks `PEP_RUNTIME_STEP_LIMIT`, C3 `lexer_step` host-transport limit, C4 function-chunk outcomes ordered by node count.

## Measured ledger (15 chunks, 2,030 document nodes — matches the pin)

| chunk | nodes | result |
|---|---|---|
| declaration:SourcePosition / Utf8Check | 5 / 5 | valid |
| ascii_continue / ascii_digit | 10 / 12 | valid |
| declaration:LexToken | 18 | valid |
| ascii_letter | 24 | valid |
| advance_position | 33 | valid |
| declaration:LexCursor | 34 | valid |
| make_token | 55 | valid |
| lexer_start | **59** | `PEP_RUNTIME_STEP_LIMIT` |
| declaration:LexProgress | **76** | **valid** |
| make_cursor / make_progress / utf8_check | 103 / 125 / 268 | `PEP_RUNTIME_STEP_LIMIT` |
| lexer_step | 1,513 | host-transport-limit |

All pinned statuses reproduce exactly (C1–C3 held; C4: **max valid 55 < min failed 59** → function-chunk outcomes are *ordered by node count*).

## Analysis (the new part)

Under an explicit **linear-through-origin cost model** (stated assumption; fixed overheads ignored):

- **Function-body chunks:** cost/node in **(1694, 1818]** steps — tightest bounds from pass@55 and fail@59.
- **Declaration chunks:** cost/node **≤ 1315** (upper bound only, from pass@76).

Synthesis:

1. **A1's corrected volume thesis is corroborated within kind:** the five function passes (10–55) and four function failures (59–268) are strictly ordered by size — no construct-based crossover inside the function regime.
2. **The constant is kind-dependent:** a declaration chunk of **76 nodes passes while a 59-node function chunk fails**. Therefore **no universal node ceiling** describes the checker: neither the old “~24 nodes” nor a flat “~100 nodes” transfers across chunk kinds (the real-lexer function regime binds at 55–59, i.e. ~1700–1800 steps/node, not ~1000).
3. **A1's `test_checker_node_cost` fixtures (90 valid / 101 fail ⇒ ~1100 steps/node) sit in the declaration-like regime** — consistent with their measurement, but their headline “~1,000 steps/node → ~100 nodes per invocation” *understates* real function-body cost; per-unit planning for `utf8_check`-class bodies should assume the ~55-node binding until the checker gets cheaper.
4. **Doc-currency observation (not a defect):** the ledger test docstring at `05add76` still carries the superseded “construct-driven, not node-count-driven” framing that A1's own #16 `81302767` comment corrects; suggest the owner refresh the prose when convenient. File owner: A1.

## Honest scope

- The linear-through-origin model is an explicit simplification: bands are inequalities that hold *if* average cost is roughly proportional to nodes; fixed overheads would widen the implied constant (disclosed, not hidden).
- One corpus (real lexer), one head (`05add76`); transport-limited `lexer_step` bounds nothing.
- The correlation does **not** re-open the `d158044` regression (separate receipt) and does not measure emit-stage cost (Wall A/B remain the A2/contract lanes).
- Pure checker layer; no native build/execution; nothing outside `verification/**` changed.

## Reproduction

```powershell
git -C <worktree> checkout --detach 05add76e21d4c979d243fa1fd7cbd0eb2a9d945c
python verification\probes\lexer_chunk_volume_correlation.py <worktree>   # expect exit 0, claim_falsified=0
```

## Next action

Carry this into the next consolidated 3-slice review on #16 (with the triad's remaining slices); flag the docstring-currency note to A1 there.
