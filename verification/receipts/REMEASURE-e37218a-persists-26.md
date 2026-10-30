# Re-measurement — A1 `e37218a`: regression persists (26), new work green (2026-10-30)

A1's response commit after three of my `ae91bdc` analysis posts:
`e37218a` "Reduce staged checker composition overhead".

## What the commit is (and is not)

- **Does not touch `examples/pep_parser.pep`** — the 19-part
  `ast_value_span` chains intact → the delivered mechanism/directions
  (`MECHANISM` receipt) not yet acted on.
- Checker-side work: `pep_checker_a13.pep` reworked (251 lines),
  `pep_c23.py` +365 (composition/measurement), `test_a13.py` internals
  reworked (test count unchanged at 91), `test_c23_driver_validation`
  +2 tests.

## Measured (clean detached, sequential)

| suite | result |
|---|---|
| heavy set (a13 91 + nested 13 + a14 11 + cli 8 + classifier 1 = 124) | **26 failures — identical set to `ae91bdc`** (19 a13 deep-class + 3 nested + a14 4); cli 8/8, classifier 1/1 |
| `test_c23_driver_validation` (now 12) | **12/12 OK** — their 2 new tests green (1.1 s) |

## Verdict

The checker-overhead work neither fixes nor worsens the `ae91bdc`
regression: **deep-suite depth-axis failures and a14's 4 all persist**
(parser chains untouched, as predicted from the mechanism). The commit's
own new surface (driver tests) is green. The parser-chain fix directions
remain open and undelivered-upon.

No new defect introduced by this commit within the heavy set. Replay
**170/170**; INDEX current (refreshed last round).
