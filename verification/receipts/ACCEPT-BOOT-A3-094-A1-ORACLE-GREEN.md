# ACCEPT BOOT-A3-094 — A1's semantic oracle is GREEN: 23/23 verified two ways, and the spans are seed-independent

**Verdict: A1's `fix(a1): re-pin 3 spans to canonical bytes after *-text (same codes, -1 offsets)` closes BOOT-A3-093
exactly. Their own test passes at `ee7d104d`, and my independent probe reproduces all 23 cases — status, diagnostic code
and span — using a different seed. The second oracle for compiler A is now trustworthy.**

## The fix landed precisely at the diagnosis

A3-093 reported three span expectations each exactly 1 byte too high, two of them past EOF. `ee7d104d` changes exactly
those three, in exactly that direction:

| fixture | was | now | delta |
|---|---|---|---|
| `neg_arity` | `PEP_ARGUMENT_COUNT 74–80` | `73–79` | −1 |
| `inc_fn` | `PEP_PARSE_EXPECTED 20` | `19` | −1 |
| `inc_ret` | `PEP_PARSE_EXPRESSION 27` | `26` | −1 |

Commit message: *"same codes, -1 offsets"* — which is the diagnosis I published, not a coincidence. No other expectation
moved.

## Verified two ways, with two different seeds

1. **A1's own test, in their worktree, with their seed** (`pep_ocaml.ml` 143,092 B):

```
Ran 1 test in 16.509s
OK
```

2. **My independent probe** `verification/probes/pep0_a1_oracle_093.py` — separate implementation, fixtures read from git,
   and a **different seed** (`pep_ocaml.ml` 146,713 B from A2's branch):

```
23 cases, 0 disagreeing
A1 SEMANTIC ORACLE: REPRODUCES
```

All 23 match on status **and** on the full `(code, startOffset, endOffset, line, column)` tuple: `pos_42`, `pos_ws`,
`pos_twofn`, `neg_unknown`, `neg_arity`, `neg_rettype`, `neg_brace`, `neg_trail`, `neg_badlit`, `crlf_ok`, `nbsp_fn`,
`inc_ws`, `empty_zero`, `inc_fn`, `inc_ret`, `out_match`, `out_str`, `a_nul`, `a_big19`, `a_foo`, `a_dup`, `a_gfn`,
`a_grt`.

That the two seeds (143,092 and 146,713 bytes, materially different seed compilers) produce identical spans on all 23
fixtures is the stronger result: these expectations are properties of the *language and these bytes*, not of one seed
build. Compiler A can be reconciled against them without wondering which seed they were recorded on.

## The loop, stated plainly

- **A3-089** reported A1's corpus gaps (no 0-byte fixture; 7 of 22 doubled trailing newlines).
- A1 responded with `empty_zero`, `inc_empty` → `inc_ws`, single-newline normalisation, `-text` pin — all correct.
- That normalisation moved the bytes, and **A3-093** found three spans left stale, with the suite red at tip (and red at the
  prior revision too, 5 failures → 3).
- A1 re-pinned the three in `ee7d104d`.
- **This receipt** confirms green.

Two rounds, each verified independently. The oracle went from red-at-tip to green-and-seed-independent.

## Limits

- I verify the oracle *as an assertion set*. Whether compiler A actually mirrors these 23 shapes is still untested — that
  needs A to run, which is blocked at 9/21 emission.
- Only the **first** diagnostic per case is compared, matching A1's own assertion shape. A case emitting several
  diagnostics is pinned on the first alone.
- `ee7d104d` is a moving lane; re-run the probe before relying on it.
- `empty_zero` being `valid` is now covered both by A1's table and by my probe, but a 0-byte input still has no *native*
  confirmation (exit 0 silent) until compiler A exists.

## Reproduce

```
# A1's own test (their seed)
PEPIN_SEED_ROOT=<A1 worktree at ee7d104d> python -m unittest tests.test_a1_pep0_oracle -v
# independent, different seed
PEPIN_SEED_ROOT=D:/Projects/wt-a3-dbea PEPIN_ORACLE_REV=ee7d104d \
  python verification/probes/pep0_a1_oracle_093.py
```

REF GH #16, parent finding `6724577411` (A3-093). Fixed by A1 (`ee7d104d`); independently re-verified by A3.