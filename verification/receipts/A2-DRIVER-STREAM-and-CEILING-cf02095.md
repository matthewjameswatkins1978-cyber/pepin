# A2 driver at `cf02095` — token-stream invariants hold on real programs, and the driver's fixed-budget ceiling is ≈120 tokens / ~330 bytes

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slices 3/4: lexer semantics and real composition) · **Evidence label:** `TESTED`
**Target:** `codex/a2-bounded-emission` @ **`cf020959bc3797e4810bfe854b4258cae9c52531`**, pinned worktree untouched
**Instruments:** `verification/probes/a2_driver_stream_invariants.py` and `a2_driver_budget_ceiling.py` (both new)

## Part 1 — token-stream invariants, oracle = the source bytes

The seed (and the canonical Pep lexer) are both *implementations*; for whole-program tokenisation the
independent oracle is the bytes themselves. Ten tokenisable fixtures (five real `examples/*.pep` plus five
synthetic ones covering CRLF, tabs, comments, escapes and holes):

| claim | result |
|---|---|
| **C1** token spans + independently computed trivia (whitespace, `#`/`//` comments) **partition the source exactly** | **HELD** — no byte unaccounted for, no code swallowed by a comment |
| **C2** identifier/symbol text equals the source slice; integer `integerValue` equals `int(slice)`; `hole` carries its name without `?` (bare `_` has none); `eof` at end | **HELD** |
| **C3** each token's line/column equals a position **recomputed from the bytes** (LF advances, every byte advances the column) | **HELD** — including the CRLF and tab fixtures |
| **C4** string `parts` reproduce an **independent escape decode** of the literal body (`\n \t \r \\ \" \0`) | **HELD** |
| **C5** spans strictly increase, never overlap, `eof` last | **HELD** |

`SUMMARY cases=6 claim_falsified=0`.

## Part 2 — the budget ceiling (a "valid feature blocked by budget", quantified)

Same driver, generated valid Pep (`let aN = N;` × n):

| statements | bytes | tokens | driver | seed |
|---|---|---|---|---|
| 16 | 204 | 81 | **ok** (4 ms) | valid |
| 20 | 260 | 101 | **ok** (5 ms) | valid |
| 24 | 316 | 121 | **`PEP_RUNTIME_STEP_LIMIT`** (3 ms) | **valid** |
| 32 / 40 / 48 / 64 | 428 / 540 / 652 / 876 | — | `PEP_RUNTIME_STEP_LIMIT` | valid |

**Ceiling: ≈ 100–120 tokens (260–316 bytes).** On real programs that means
`examples/hello.pep` (20 B), `point_sum.pep` (185 B), `recursive_expr.pep` (242 B), `match_holes.pep`
(186 B), `fill_double_hole.pep` (83 B) tokenise **correctly**, while
`examples/a6_collections_control.pep` (1,611 B) and `examples/unused_functions.pep` (2,143 B) are refused
with `PEP_RUNTIME_STEP_LIMIT` — and the seed accepts both as valid programs.

That is roughly **800–1,000 steps per token** inside the fixed 100,000-step tool budget. For the
self-hosting question this matters more than any single token defect: a lexer driver that cannot read a
1.6 KB example program cannot be the front end of a self-hosted compiler, and it is the *same* budget
class that blocks the 66-node checker row. It is a budget fact, not a wrong token — C1–C5 say the tokens
it does produce are right.

## Own-instrument corrections (disclosed, both caught before recording)

1. First run registered the probe wrapper against the compiler bundle instead of the scan module, so the
   tool refused with `PEP_TOOL_FUNCTION_NOT_FOUND`. Fixed by opening `scan.pep + PROBES` as the tool
   document — the same pattern the earlier driver probe uses.
2. C2 initially failed with six "unexpected token kind 'hole'" entries: my probe simply had no `hole`
   branch. Adding the branch (with the `?name` / bare `_` contract) turned it into a real check — and it
   now passes. Recorded because a probe that cannot express a token kind must not look like a driver
   defect.
3. A budget refusal initially aborted the whole stream probe through a `require`; it is now recorded as an
   observation row (`O-budget`) so a fixed-budget stop can never masquerade as a token-stream defect.

## Honest scope

- Ten tokenisable fixtures + two over-budget examples; real programs are small by construction (the
  ceiling guarantees it), so this is not full-corpus coverage.
- C3's position model is "one column per byte", which matches the seed on every fixture measured here;
  it is a re-derivation, not a specification claim.
- C4 covers the six escapes the seed accepts; unsupported escapes make the driver refuse (checked in the
  earlier differential, `E1`).
- The ceiling is measured on one statement shape; a different mix of token kinds may shift it by tens of
  percent. The order of magnitude is the finding, not the exact byte.
- Not acceptance evidence; the frozen Full still waits on a pushed combined successor of `8396b63`.

## Reproduce

```powershell
python verification\probes\a2_driver_stream_invariants.py  D:\Projects\wt-a3-a2-cf02095   # exit 0 (10 fixtures)
python verification\probes\a2_driver_budget_ceiling.py     D:\Projects\wt-a3-a2-cf02095   # exit 1 (ceiling found)
```
