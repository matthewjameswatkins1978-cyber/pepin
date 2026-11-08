# ACCEPT BOOT-A3-092 — A4's own-source census is exact on all 189 table fields; one summary total is wrong, and M-2's oracle depends on two step-limited functions

**Verdict: A4's `OWN_SOURCE.md` per-function table is correct on every one of its 189 cells — I recomputed all 21 functions ×
9 construct columns from the seed AST and found zero differences. But its summary line "`if` 21/21 (20 with `&&`/`||`)" is
wrong: the table and the source both say **18**. And the M-2 first-failure oracle A4 derives depends on `is_main4` and
`main`, both of which are step-limited — so the first own-source failure cannot be observed until statement-granular
emission exists.**

## The table: 189/189 exact

Recomputed per function from `pep.ps1 inspect --json` on blob `ca732536`, body only (signature excluded), across the nine
columns A4 uses — params, `SourceBytes` param, `var`, `while`, `if`, boolop, arithmetic, calls, string literal:

```
field-level diffs: 0
```

Including the awkward rows: `parse_value` has `while` and arithmetic but **no `if`** and no boolop; `skip_ws` and
`scan_digits` have `if` and `while` but **no boolop**; `main` is the only string-literal function; `find_fn` has exactly one
parameter and it is `SourceBytes`. All as A4 states.

## Summary totals: six right, one wrong

| A4 prose | computed | verdict |
|---|---|---|
| params 21/21 | 21/21 | correct |
| `var` 21/21 | 21/21 | correct |
| non-literal `return` 21/21 | 21/21 — **no function returns a bare int literal** | correct |
| `if` 21/21 | 21/21 | correct |
| `SourceBytes`-typed 19/21 | 19 | correct |
| arithmetic 19/21 | 19 | correct |
| calls 19/21 | 19 | correct |
| `while` 3/21 | 3 | correct |
| string literal 1/21 | 1 (`main`) | correct |
| **`if` 21/21 (20 with `&&`/`||`)** | **18** | **WRONG** |

The eighteen are: `is_ws`, `is_digit`, `is_ws_at`, `is_fn2`, `is_main4`, `is_int3`, `is_ret3`, `is_urn3`, `is_str3`,
`is_bool4`, `is_unit4`, `expect_byte`, `find_fn`, `find_parens`, `find_brace`, `find_ds`, `check_tail`, `main`.
The three without are exactly **`skip_ws`, `scan_digits`, `parse_value`** — the three loop functions.

This is not cosmetic. "20 with `&&`/`||`" implies only one function lacks boolean operators; the truth is three, and they are
precisely the functions the `while` rung (R6) touches. Understating that by two makes the R5 `if`/`&&`/`||` rung look like it
covers almost everything when it does not. The table is right, so the fix is one number in one sentence.

## The first-failure trace is sound — but its premise is blocked

A4's claim: *"`find_fn` matches `fn`, skips ws, then `is_main4` fails on the first definition (`is_ws`) → err 1 → exit 1
`ERR shape`."*

I can confirm the premise independently: `is_ws` **is** the first top-level definition in source order, and `is_main4` would
reject `is_ws` since it requires `main`. The hand-trace is logically coherent.

The problem is that observing it needs `is_main4` to *emit*, and per BOOT-A3-083/084:

| function | nodes | status at `bea071a` |
|---|---|---|
| `is_main4` | 49 | `PEP_RUNTIME_STEP_LIMIT` at whole-chunk check |
| `main` | 222 | `PEP_RUNTIME_STEP_LIMIT` at whole-chunk check |

So the M-2 first-failure oracle **cannot be executed yet**, and not because of anything A4 did wrong — because two functions
the oracle depends on sit past the 100k step wall. Both need statement-granular handling (A2-S2 / A1-S2). Worth stating
explicitly so M-2 is not attempted before that lands and mistaken for a semantic failure.

`is_main4` is also A4's own listed emitter-refusal candidate #1 (the 5-conjunct `&&`), which is consistent: it fails on cost,
not on semantics.

## Limits

- Verified the census as *counts and presence flags*. A4's marker scan could in principle see a construct I classify
  differently (e.g. whether `-` inside `0 - 1` counts as arithmetic); my walker takes any binary operator, which is the
  reading A4's column implies and it produced zero diffs, so we agree.
- I did **not** run the first-failure trace — it needs compiler A. I verified its premise (ordering, `is_main4` behaviour) and
  its cost blocker, nothing more.
- `compiler_a.pep` is `ca732536` at `18e46122`, unchanged, so all earlier measurements still apply.

REF GH #16. Census authored by A4 (`18e46122:examples/dogfood/pep0/OWN_SOURCE.md`). Independent recomputation: A3.