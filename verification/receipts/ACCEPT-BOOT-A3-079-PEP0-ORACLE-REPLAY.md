# ACCEPT BOOT-A3-079 — A3-S2: A4's Pep-0 oracle now has an executable replay; its fixtures and classifications hold

**Verdict: A4's `EXPECTED.md` oracle is internally consistent and its seed classifications are independently confirmed —
14/14 checkable assertions pass. The exit-code table is NOT yet verifiable and is reported as pending, never as passed.**

## The gap this closes

`examples/dogfood/pep0/EXPECTED.md` is precise — seven pinned inputs with exact bytes, exact exit codes and exact stdout —
but nothing in the repository executed it (`git ls-tree 5f62e4b tests/` contains no pep0 or compiler_a harness). A prose
oracle cannot catch itself drifting from its own fixtures, and cannot be replayed from a fresh checkout. That is A3 reserve
R1, done here.

`verification/probes/pep0_oracle_079.py` replays the layers that do not depend on compiler A existing, and reads fixtures
from git so it never mutates A4's lane.

- **L1 fixture integrity** — the committed bytes must equal the bytes the oracle's prose describes.
- **L2 seed classification** — the oracle's seed-valid / seed-invalid claims must match the **live seed compiler**, which is
  an independent oracle: the seed, not A4's prose, decides.
- **L3 exit codes** — the 0/1/2/3/4/5 table and exact stdout. **PENDING**: requires compiler A to run 21/21.

## Result

```
PASS L1 a_ok.pep        byte-exact per oracle
PASS L2 a_ok.pep        seed status=valid [] vs oracle claim 'valid'
PASS L1 a_badlit.pep    byte-exact per oracle
PASS L2 a_badlit.pep    seed status=invalid [PEP_PARSE_EXPRESSION] vs oracle claim 'invalid'
PASS L1 a_badbrace.pep  byte-exact per oracle
PASS L2 a_badbrace.pep  seed status=invalid [PEP_PARSE_EXPRESSION] vs oracle claim 'invalid'
PASS L1 a_str.pep       byte-exact per oracle
PASS L2 a_str.pep       seed status=valid [] vs oracle claim 'valid'
PASS L1 a_empty.pep     byte-exact per oracle
PASS L2 a_empty.pep     seed status=valid [] vs oracle claim 'valid'
PASS L1 a_crlf.pep      byte-exact per oracle
PASS L2 a_crlf.pep      seed status=valid [] vs oracle claim 'valid'
PASS L1 a_u8.pep        byte-exact per oracle
PASS L2 a_u8.pep        seed status=invalid [PEP_UNEXPECTED_CHARACTER] vs oracle claim 'invalid'

14 checkable assertions, 0 failed
ORACLE REPLAY: PASS
```

Byte-level facts worth stating because they are easy to get wrong and the oracle depends on them:

| fixture | bytes | note |
|---|---|---|
| `a_ok` | 34 B `fn  main() -> Int {\n  return 42\n}\n` | **double** space after `fn` is part of the spec |
| `a_crlf` | 36 B, three `0d 0a` pairs | CRLF genuinely preserved, not normalised |
| `a_u8` | 32 B, `66 6e c2 a0 6d …` | NBSP U+00A0 in place of the space after `fn` |
| `a_empty` | 0 B | |

The distinction that matters most: `a_str`, `a_empty` and `a_crlf` are **seed-valid**, while `a_u8`, `a_badlit` and
`a_badbrace` are **seed-invalid**. That split is exactly A4's `(ii) seed-valid but outside Pep-0` vs `(i) seed-invalid`
boundary, and it is now checked rather than asserted. A compiler A that rejected `a_str` with the seed's error, or accepted
`a_u8`, would be caught against the seed here.

## What this does NOT establish — stated plainly

- **No compiler-A behaviour is verified.** Exit codes 0/1/2/3/4/5 and the exact stdout strings are untested. At 9/21
  emission compiler A cannot be built, so no M-1 claim is made, and this receipt is not evidence that A refuses invalid
  input without emitting misleading C.
- **L2 uses the seed as the oracle for seed-validity only.** It says nothing about whether S0 accepts the *right* subset;
  A4's prose defines S0, and the seed merely classifies the boundary cases.
- The dispatch's "two unseen source forms" (A3-S2) is **not** covered here. Those need compiler A's runtime.

## Reproduce

```
PEPIN_SEED_ROOT=<worktree with a built seed> python verification/probes/pep0_oracle_079.py
# PEPIN_ORACLE_REV selects A4's revision, default 5f62e4b
```

Runs against seed `pep_ocaml.ml` @ 148791 B (the campaign seed shared by `1885566`, `3ad2bff`, `bea071a`).
Note `wt-a3-gate`'s own seed is older (145104 B) — a reminder that the seed is not one object across all branches.

REF GH #16. Oracle authored by A4 (blob `ca732536` compiler_a, `68c5920` EXPECTED). Independent replay: A3.