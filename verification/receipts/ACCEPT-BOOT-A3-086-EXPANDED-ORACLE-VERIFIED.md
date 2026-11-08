# ACCEPT BOOT-A3-086 — A4's expanded oracle verified: 13 pins, 26/26 checkable assertions, six new claims all exact

**Verdict: A4's expanded `EXPECTED.md` (@ `afd2d7e2`) is byte-exact on all 13 fixtures and every one of its seven
seed-classification claims is confirmed against the live seed — including the three cases where the oracle *deliberately
diverges* from the seed. `compiler_a.pep` is unchanged (`ca732536`), so BOOT-A3-083/084's 9-of-21 table still stands.**

## Delta since A3-079

A4 advanced `5f62e4b` → `afd2d7e2` with six commits: normative subset (`PEP0_SUBSET.md`), own-source census
(`OWN_SOURCE.md`), inventory (`INVENTORY.md`), and six new pinned negatives (`a_nul`, `a_big19`, `a_foo`, `a_dup`,
`a_gfn`, `a_grt`) plus an `examples/dogfood/.gitattributes`. `compiler_a.pep` blob is **unchanged**, so this is an
oracle/documentation expansion, not a source change — and my 21-function results remain valid against it.

Both harnesses extended to the new revision and re-run: `pep0_oracle_079.py` and `verify_m1_081.py`.

## Fixture bytes, verified individually

| fixture | len | hex head | matches oracle |
|---|---|---|---|
| `a_nul` | 27 | `00 66 6e 20 6d 61 69 6e …` | yes — leading NUL preserved through git |
| `a_big19` | 43 | `… 31 30 30 30 …` (19 digits) | yes |
| `a_foo` | 24 | `66 6e 20 66 6f 6f …` | yes |
| `a_dup` | 50 | `… 7d 0a 66 6e 20 6d 61 69 6e …` | yes, two forms |
| `a_gfn` | 25 | `66 6e 6d 61 69 6e …` (glued `fn`) | yes |
| `a_grt` | 25 | `… 72 65 74 75 72 6e 34 32 …` (glued `return42`) | yes |

The binary case matters most: `a_nul` starts with a literal `00`, and the new `.gitattributes` keeps it exact. A NUL
fixture that silently lost its NUL would make the whole negative vacuous, so it is checked byte-for-byte rather than by
`git show`.

## Seed classifications — all seven confirmed

```
a_ok      valid                        <- oracle: valid
a_badlit  invalid [PEP_PARSE_EXPRESSION]   <- oracle: invalid
a_badbrace invalid [PEP_PARSE_EXPRESSION]  <- oracle: invalid
a_str     valid                        <- oracle: valid (out of subset)
a_empty   valid                        <- oracle: valid
a_crlf    valid                        <- oracle: valid
a_u8      invalid [PEP_UNEXPECTED_CHARACTER] <- oracle: invalid
a_nul     invalid [PEP_UNEXPECTED_CHARACTER] <- oracle: invalid   NEW
a_big19   valid                        <- oracle: valid           NEW
a_foo     valid                        <- oracle: valid           NEW
a_dup     invalid [PEP_DUPLICATE_FUNCTION]  <- oracle: invalid    NEW
a_gfn     invalid [PEP_PARSE_EXPRESSION]    <- oracle: invalid    NEW
a_grt     invalid [PEP_UNKNOWN_VARIABLE]    <- oracle: invalid    NEW
```

26 checkable assertions, **0 failed**. `a_big19` being seed-valid while out of subset, and `a_dup` being seed-invalid with
a code the oracle does *not* use, are both exactly as A4 states.

## The three deliberate seed divergences — worth pinning so they are not "fixed" later

The oracle is not a transcript of the seed, and in three places it must not be:

| fixture | seed says | oracle says | why they differ |
|---|---|---|---|
| `a_dup` | invalid `PEP_DUPLICATE_FUNCTION` | exit **3** `ERR junk` | S0 has no duplicate detection; the second form is simply trailing bytes after the first `}` |
| `a_foo` | valid | exit **1** `ERR shape` | seed-valid, but S0 requires a `main`; `is_main4` fails on `foo` |
| `a_big19` | valid | exit **4** `ERR longlit` | valid Pep, but S0 caps literals at 18 digits |

Anyone comparing compiler A against the seed on these three would call correct behaviour a bug. Stating it here is the
cheapest way to prevent that, and it is checkable rather than remembered: the oracle replay asserts the seed's verdict and
the M-1 gate asserts A4's, in the same run.

## Status, unchanged in kind

Exit codes 0/1/2/3/4/5 and the exact stdout strings remain **PENDING** — compiler A does not run at 9/21 emission, so no
M-1 claim is made and A4's "native confirmation pending S2" is still accurate. I am confirming the oracle's *inputs* and
its *boundary classification*, which is the layer that can be verified without A existing.

The M-1 gate self-test was re-run after doubling the case count, since a larger suite could hide a blind spot:
`13/15` and `12/13` stub cases fail as they should, and `SELF-TEST: PASS` still holds.

## Reproduce

```
PEPIN_SEED_ROOT=<worktree with built seed> python verification/probes/pep0_oracle_079.py
python verification/probes/verify_m1_081.py --selftest
```

REF GH #16. Oracle `afd2d7e2:examples/dogfood/pep0/EXPECTED.md` (blob `af96f568`). Authored by A4; independent replay by A3.