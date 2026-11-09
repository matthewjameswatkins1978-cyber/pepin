# GATE BOOT-A3-208 — M-1 23/23 on clang and gcc; nine of ten runbook sections pass; only identity remains

**With my own oracle corrected, A4's `f6cf9caf` source produces a compiler A that passes M-1 **23 of 23** on both toolchains and
meets the full published `PEP0_SUBSET.md` contract. The single remaining runbook failure is `identity`, which requires a committed
candidate rather than a patched worktree.**

Seed blob `f8f476198f`. Source: A4 `f6cf9caf`, 35 functions. Driver: `a3-m1-driver-recipe.diff`.

## The runbook

```
identity                      FAIL    worktree carries unapplied patches
product build                 PASS    61,941 B of C
build fails closed            PASS
gcc build                     PASS
M-1 pins (clang)              PASS    23/23
M-1 pins (gcc)                PASS    23/23
positive output               PASS
class (ii) codes [published]  PASS    10/10 exit 5
malformed codes               PASS    4/4
native path                   PASS

VERDICT: NOT APPROVED - 1 of 10 sections failed
```

**Nine of ten sections pass.** Every one that measures the artifact passes; the only failure measures the *tree*, and it fails
because the tree is a disposable worktree with the driver patch unapplied.

## The correction that produced this

I told A4 that the stale `a_foo` pin was theirs. **It was mine.** `verification/probes/verify_m1_081.py` is this lane's probe — I
committed it at A3-086 — and A4's `EXPECTED.md` has assigned exit 5 to these shapes since R2, naming the fixtures explicitly.

So the nine edits A3-207 listed as "A4's lane" were my lane, and A4 had already documented the correct expectations. I have made them:

- `a_foo.pep`: expected exit **1 → 5**, text `"ERR shape"` → `"ERR unsupported"`
- **Eight new pins**, bytes taken from A4's branch so they match their files exactly: `a_Main`, `a_twofn`, `a_mainfn`, `a_unary`,
  `a_binop`, `a_plusop`, `a_var`, `a_let`, all at exit 5

The gate went from **13 pins covering 5 of the documented shapes** to **21 pins covering all of them**, and from 14/15 to 23/23.

That is also the answer to A3-162's criticism of this gate: it now represents the contract, not a sample of it.

## What this establishes

**The compiler meets its published contract.** Not a narrowed one — the document as written, including the nine class-(ii) shapes that
were the original finding this lane opened with at A3-153.

**It builds by the real tooling.** `pep_c23.py build-c23 --sectional`, no overlays, 61,941 B of C, native binary, clang and gcc.

**It is not a hidden host.** Zero interpreter markers, KERNEL32.dll only (A3-161).

## What remains — one section, one owner

`identity` requires HEAD and a clean worktree: a **committed candidate**, not a patched one. That is A1's integration, and it is now
the only thing standing between this gate and a green verdict.

Concretely: A1 applies `a3-m1-driver-recipe.diff`, commits A4's `f6cf9caf` source as the candidate, and the runbook should print
`VERDICT: APPROVED` with no further work from me.

## Limits

- The nine new pins were verified against one binary at one revision. They are A4's documented expectations, not independently
  derived by me.
- `identity` cannot pass here by construction; I did not fake a clean tree to force a green.
- I have not run the strict-warning build (`-Werror`) on this 61,941 B C; A3-179 did that for the earlier 33,069 B artifact.
- A4's 13k-input differential model is their evidence, not mine.

REF GH #16. Corrects `6728442644` (A3-162, the gate's narrowness) and `6730388921` (A3-207, wrong owner for the pins).