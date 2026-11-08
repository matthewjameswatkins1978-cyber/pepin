# FINDING BOOT-A3-153 — compiler A's exit-5 path covers 2 of 9 documented shapes: seven seed-valid inputs return 1/2/3

**The modelled compiler A passes the gate 15/15, but `PEP0_SUBSET.md` class (ii) lists nine seed-valid-but-out-of-subset shapes
and the oracle pins only one of them (`-> Str`). Testing the rest against the seed's own checker, **seven are genuinely seed-valid
and compiler A returns the wrong exit code**, so a caller cannot distinguish "not Pep" from "Pep, unsupported".**

Seed blob `f8f476198f`. Model of `compiler_a.pep` blob `ca732536` + A3-150's three fixes, assembled by A3, 31,587 bytes. Scratch
deleted.

## Seven genuine misclassifications

Each input below returned `valid` from the **seed's** own checker (`pep.ps1 check`), so it is inside Pep and outside S0 — which
`PEP0_SUBSET.md` class (ii) defines as **exit 5, no C**.

| input | seed | compiler A | contract |
|---|---|---|---|
| `fn Main() -> Int { return 1 }` | valid | **1** `ERR shape` | 5 |
| `fn foo() -> Int { return 1 }` | valid | **1** `ERR shape` | 5 |
| `fn main() -> Int { return -42 }` | valid | **2** `ERR literal` | 5 |
| `fn main() -> Int { return 0-42 }` | valid | **3** `ERR junk` | 5 |
| `fn main() -> Int { var x = 1 return x }` | valid | **1** `ERR shape` | 5 |
| `fn main() -> Int { let x = 1 return x }` | valid | **1** `ERR shape` | 5 |
| `fn a() -> Int { return 1 } fn main() -> Int { return 2 }` | valid | **1** `ERR shape` | 5 |

The two that do work — `-> Bool` and `-> Unit` → 5 — are the ones the source models as suffix tests (`is_bool4`/`is_unit4`) next to
`is_str3`. Everything else falls through to the shape scanner, which reports the *first* thing it cannot match rather than
"valid Pep, not S0".

`unary_minus` and `binary_arith` are the clearest: a `-` or a `-42` is reported as a **literal** error (exit 2) and as **trailing
junk** (exit 3), when class (ii) says both are S0-valid Pep that must exit 5. Exit 3 is especially misleading — it tells the caller
the program is malformed after the value.

## Three of my fifteen tests were my own errors — withdrawn

I predicted exit 5 for these three; the **seed rejected them**, so compiler A's non-5 answer is correct and my expectation was
wrong:

| input | seed's actual verdict |
|---|---|
| `if true { return 1 } return 2` | invalid `PEP_PARSE_ELSE` — a statement `if` needs an `else` |
| `record P { x: Int }` then `main` | invalid `PEP_UNKNOWN_VARIABLE` — my record syntax is wrong |
| `return match 1 { _ => 2 }` | invalid `PEP_MATCH_NON_UNION` — `match` scrutinee must be a union |

So this is seven defects, not ten. Writing the test inputs was where I was weakest, not reading the compiler.

## What this says about the gate

**A 15/15 pass coexists with seven contract violations.** The oracle tests one example per class and `-> Bool`/`-> Unit` happen to
share the `-> Str` code path, so the gate passes while the classification is wrong for every other documented shape. This is not a
flaw in the gate's construction — it does exactly what its pins say — it is the gate being **narrower than the contract it is
supposed to embody**.

Suggested extension cases for A4's oracle, each verified seed-valid above: `main_upper`, `no_main`, `unary_minus`, `binary_arith`,
`var_decl`, `let_decl`, `two_fn`, all expected exit 5.

## Limits

- Modelled build: A3's assembly of A4's source plus A3-150's three fixes. Defects 2 and 3 from A3-149 (epilogue echo, exit code)
  are fixed in this model, so these exit codes are the *corrected* binary's; the tracked tree returns 0 for everything.
- One seed, one source revision; the subset checker is A4's `main`/`find_brace` and is separate from A1's host analysis, which
  also reports `valid` on all seven.
- I did not test whether `expect_byte`'s punctuation comparisons or the `pS`/`pB`/`pU` rewrites interact with any of these.
- Class (i) — seed-invalid — was not exercised here; the oracle's `a_badlit`/`a_badbrace`/`a_gfn`/etc. cover it.

REF GH #16. Related: `6726592523` (A3-150, the 15/15 pass this qualifies), `6726664273` (A3-152).