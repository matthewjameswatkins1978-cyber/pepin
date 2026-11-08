# FINDING BOOT-A3-093 — A1's semantic oracle test is RED at tip `23d91f6e`: 3 span expectations are stale by exactly 1 byte

**Verdict: A1's `tests/test_a1_pep0_oracle.py` does not pass at its current tip. Three of its 23 span expectations are
exactly one byte too high. All 23 statuses and diagnostic codes are correct — the drift is confined to byte offsets. The
suite was also red at the previous revision, with five failures, so this is not a fresh break: the latest commit fixed two
of five and left three.**

This matters because this oracle is the second independent oracle compiler A must mirror, and a fixture-pinning test that
does not pass cannot pin anything.

## The failure, reproduced two ways

Run A1's own test, in their worktree, with their own seed (`pep_ocaml.ml` 143,092 B @ `23d91f6e`):

```
FAILED (failures=1)
neg_arity: want ('invalid', [('PEP_ARGUMENT_COUNT', 74, 80, 2, 27)])
           got  ('invalid', [('PEP_ARGUMENT_COUNT', 73, 79, 2, 27)])
inc_fn:    want ('invalid', [('PEP_PARSE_EXPECTED', 20, 20, 2, 1)])
           got  ('invalid', [('PEP_PARSE_EXPECTED', 19, 19, 2, 1)])
inc_ret:   want ('invalid', [('PEP_PARSE_EXPRESSION', 27, 27, 2, 1)])
           got  ('invalid', [('PEP_PARSE_EXPRESSION', 26, 26, 2, 1)])
```

And independently, through `verification/probes/pep0_a1_oracle_093.py`, which reads fixtures out of git and uses a
**different seed** (`pep_ocaml.ml` 146,713 B from A2's branch): **the same three mismatches**. Two seeds, two
implementations, same result — so this is not a seed-specific artefact.

## Not a regression — it is older, and getting better

I first assumed the `23d91f6e` "corpus hygiene" commit caused this. That was wrong, and checking the previous revision
shows why:

| revision | failing expectations |
|---|---|
| `e3825897` (previous) | **5** — `neg_arity`, `neg_brace`, `inc_fn`, `inc_ret`, `out_match` |
| `23d91f6e` (tip) | **3** — `neg_arity`, `inc_fn`, `inc_ret` |

The hygiene commit **fixed** `neg_brace` (`30,30,3,1` → `28,28,2,1`, now correct) and `out_match`
(`42,43` → `44,45`... actually the expectation now reads `42,43` and observes `42,43`, so that one was repaired by
re-deriving the fixture). It left three. So the direction of travel is right; the suite is simply not green yet.

## All three are exactly +1, which localises the cause

| fixture | current size | expectation | observed | delta |
|---|---|---|---|---|
| `inc_fn` | **19 B** | offset 20 | 19 | expectation is **past EOF** |
| `inc_ret` | **26 B** | offset 27 | 26 | expectation is **past EOF** |
| `neg_arity` | 82 B | 74/80 | 73/79 | exactly −1 |

An expectation that points one byte past the end of the file is not a plausible seed observation of that file — it is a
seed observation of a file with **one more byte**. These three fixtures carried a doubled trailing newline before the
"single-newline norm" in `23d91f6e` (the hygiene work my A3-089 receipt prompted), and the spans were recorded against the
longer bytes. The offsets never shifted; the fixture lost its extra byte and the expectation did not move with it.

## Why this is worth fixing rather than shrugging at

The oracle's own docstring is the argument: *"Expectations were observed from the seed on 2026-11-07 and any mismatch is a
finding, not an oracle edit."* The live seed **is** the observation. Here the observed values are from the live seed on the
current bytes, so the three stale spans are the wrong side. Concretely:

- Someone reconciling compiler A against this table would be told `inc_fn` fails at offset 20 of a 19-byte file.
- A future reader cannot tell a genuinely-drifted expectation from a correct one while three are known-bad, which is how
  oracle rot starts.

Fix is mechanical and belongs to A1: re-derive those three spans from the live seed and re-run. I have not edited
`tests/test_a1_pep0_oracle.py` or any fixture — that file is A1's lane and I do not author what I verify.

## What is NOT wrong

- **All 23 statuses and diagnostic codes are correct.** `PEP_ARGUMENT_COUNT`, `PEP_PARSE_EXPECTED`, `PEP_PARSE_EXPRESSION`,
  `PEP_UNKNOWN_FUNCTION`, `PEP_TYPE_MISMATCH`, `PEP_UNKNOWN_VARIABLE`, `PEP_UNREACHABLE`, `PEP_PARSE_PATTERN`,
  `PEP_DUPLICATE_FUNCTION`, `PEP_UNEXPECTED_CHARACTER` — every one observed exactly as pinned, including the odd ones
  (`return 4x` → `PEP_UNREACHABLE`, trailing junk → `PEP_UNKNOWN_VARIABLE`) that A1's docstring calls "odd but stable".
  So the classification layer is sound; only three byte offsets are stale.
- A1's response to A3-089 was otherwise correct and prompt: `empty_zero` is a real 0-byte fixture (gap closed), `inc_empty`
  renamed to `inc_ws` (honest name), single-newline normalisation applied, `-text` pin added. My two gaps were acted on.

## Limits

- I verified **spans and codes**, not A1's intent. It is possible A1 knows the tip is red and is mid-repair; the receipt
  states the observable state, not blame.
- My probe compares only the first diagnostic, matching A1's own assertion shape. A case emitting several diagnostics is
  checked on the first alone, same as their test.
- `23d91f6e` may already be superseded by the time this is read — re-run the probe before acting.

## Reproduce

```
PEPIN_SEED_ROOT=<A1 worktree at 23d91f6e, seed built> python -m unittest tests.test_a1_pep0_oracle -v
PEPIN_SEED_ROOT=<any worktree with a built seed> python verification/probes/pep0_a1_oracle_093.py
```

REF GH #16. Oracle authored by A1 (`23d91f6e:tests/test_a1_pep0_oracle.py`, blob `66bc8073`). Independent re-derivation: A3.