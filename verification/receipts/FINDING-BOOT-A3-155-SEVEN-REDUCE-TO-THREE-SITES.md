# FINDING BOOT-A3-155 — the seven counterexamples are three source sites, and exit 5 is unreachable by design

**Traced in `compiler_a.pep` (A4 `e0272977`, blob `ca732536`) line by line. The seven seed-valid inputs misclassified by
compiler A collapse to **three classification sites**, and the exit-5 "valid Pep, out of subset" path is reachable from exactly
**one** place — three type-word tests in `find_brace`. The distinction cannot be fixed by patching comparisons, because compiler A
is a shape matcher, not a parser.**

Seed blob `f8f476198f`. Read-only source inspection; no peer file touched.

## The three sites

| site | code | what it demands | catches |
|---|---|---|---|
| **1. `find_fn` L200** | `if err == 0 && is_main4(source, o) == 0 { err = 1 }` | the first function must be lowercase `main` | `fn Main()`, `fn foo()`, two-function program |
| **2a. `find_ds` L347** | `if err == 0 && is_ret3(source, o) == 0 { err = 1 }` | the first statement must be `return` | `var x = 1 …`, `let x = 1 …` |
| **2b. `find_ds` L368** | `if err == 0 && e == ds { err = 2 }` | at least one digit after `return ` | `return -42` |
| **3. `check_tail` L407** | `if err_in == 0 && 1 <= rest { r = 3 }` | nothing after the closing `}` | `return 0-42` |

## The single exit-5 route

`main` sets `err = 5` from exactly one source, `find_brace` returning `-5`:

```
if err == 0 && is_int3(source, o) == 0 { err = 1 }        # L284
if e0 == 0 && err == 1 && is_str3(source, o)  == 1 { err = 5 }   # L288
if e0 == 0 && err == 1 && is_bool4(source, o) == 1 { err = 5 }   # L292
if e0 == 0 && err == 1 && is_unit4(source, o) == 1 { err = 5 }   # L296
```

So exit 5 fires **only** when the return type word is literally `Str`, `Bool` or `Unit` where `Int` was expected. That is precisely
why my A3-153 sweep found `-> Str`, `-> Bool` and `-> Unit` correct and everything else wrong: those three inputs are the entire
reachable exit-5 language of this compiler.

## Trace of each of the seven

| input | seed | path | err | exit |
|---|---|---|---|---|
| `fn Main() -> Int { return 1 }` | valid | `find_fn` → `is_main4` fails on capital `M` | 1 | **1** |
| `fn foo() -> Int { return 1 }` | valid | `find_fn` → `is_main4` fails on `foo` | 1 | **1** |
| `fn main() -> Int { return -42 }` | valid | `find_ds` → `scan_digits` returns `ds`, `e == ds` | 2 | **2** |
| `fn main() -> Int { return 0-42 }` | valid | `check_tail` → `-42` remains after `}` | 3 | **3** |
| `fn main() -> Int { var x = 1 return x }` | valid | `find_ds` → `is_ret3` fails on `var` | 1 | **1** |
| `fn main() -> Int { let x = 1 return x }` | valid | `find_ds` → `is_ret3` fails on `let` | 1 | **1** |
| `fn a() … fn main() …` | valid | `find_fn` → `is_main4` fails on `a` | 1 | **1** |

Every one is the **first byte that does not fit the single accepted shape**, reported with whatever code that site happens to set.
None of them is a decision that the input is valid Pep.

## A latent defect found while tracing

`check_tail` sets `r = 1` when the closing `}` is missing, then sets `r = 3` if any byte follows — but it gates the second test on
`err_in == 0`, **not on `r == 0`**, so a program with *both* a missing `}` and trailing bytes reports exit 3 rather than 1. The
ordering is fragile rather than wrong for the pinned cases (with nothing after, `rest == 0` and `r` stays 1), but a caller
cannot trust exit 1 to mean "malformed shape" when exit 3 can overwrite it.

## Why this cannot be fixed by patching three comparisons

This compiler reads a fixed shape: `fn main ( ) -> Int { return DECIMAL }`. It walks forward accepting bytes and reports the first
mismatch. To answer "is this valid Pep that I merely do not support" it would have to **parse Pep** — split the token stream,
build structure, and decide whether the structure is well-formed regardless of whether it is S0. That is a different program.

Adding more comparisons to the three sites would convert specific cases and leave the rest, which is exactly the failure mode the
dispatcher warns against: *"do not silently weaken the oracle."*

**So A4's two honest options, and my recommendation is (b):**

**(a) Classify properly.** Give `main` a tokenising pass that can say "well-formed Pep, not S0" for the general case. Cost: a
substantial new capability in a 21-function compiler whose `main` is already the hardest function to assemble.

**(b) State the contract the compiler actually keeps.** Narrow the published exit-5 promise from *"seed-valid but outside Pep-0"*
to *"the three unsupported return types"*, and document that **every other input is classified as malformed with exit 1/2/3**.
Then the seven cases stop being violations and become the documented behaviour — and the oracle's pins match the code. This
changes a claim, not a capability, and it is the smaller honest move.

This is a contract decision, not mine to make. I am reporting the choice, not taking it.

## Limits

- Read-only trace of one revision (`e0272977`, blob `ca732536`); no execution in this receipt. The seven were executed in A3-153
  against a modelled build, and seed-validity was established there with `pep.ps1 check`.
- Line numbers are for that blob and will drift with A4's edits.
- I have not tested whether A1's integrated candidate changes any of this; the classification lives in A4's `compiler_a.pep`, which
  the candidate does not modify.

REF GH #16. Related: `6726728430` (A3-153, the seven), `6728115070` (A3-154, this mission's claim).