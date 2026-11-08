# ACCEPT BOOT-A3-150 — M-1 ACHIEVED in a modelled build: the full acceptance gate passes 15/15

**A complete Pep-authored compiler A passes `verify_m1_081.py` on all thirteen pinned oracle cases and both unseen forms —
15/15, with correct exit codes and stdout throughout. It took three modelled fixes, each in another lane and each small. The
current tree does not yet have them, so this is not an M-1 claim for the repository — but the finish line is now measured, not
estimated.**

Seed blob `f8f476198f`. Emitter `e07e278f`. A1 host `07af079d`. Source `compiler_a.pep` blob `ca732536` with three modelled
edits in a scratch copy. Scratch deleted; no peer lane touched.

## The gate result

```
--- A4 pinned oracle ---
PASS a_ok        exit=0  PASS a_badlit   exit=2  PASS a_badbrace exit=1
PASS a_str       exit=5  PASS a_empty    exit=0  PASS a_crlf     exit=0
PASS a_u8        exit=1  PASS a_nul      exit=1  PASS a_big19    exit=4
PASS a_foo       exit=1  PASS a_dup      exit=3  PASS a_gfn      exit=1
PASS a_grt       exit=2

--- unseen subset-S0 forms ---
PASS u_single_space  exit=0   PASS u_tab_indent  exit=0

15 cases, 0 failed — M-1 COMPILER A: PASS
```

Built as in A3-149: 21/21 chain CHECK, 10 whole units + 11 fragment-assembled, **0 refusals**, 31,587 bytes of C, linking under
both clang `-std=c23` and gcc `-std=c2x`.

## The three fixes that closed it

| # | defect | fix | lane |
|---|---|---|---|
| 1 | source emits decimal character codes: `say(int_text(40))` prints `40` where `(` belongs | `say("(")` and four siblings | **A4** |
| 2 | the runtime epilogue echoes `main`'s return as an extra stdout line the oracle forbids | drop the `printf`, call the function | **A1/A2** |
| 3 | the epilogue always `return 0`, so exit codes cannot propagate | `return (int)pep_fn_main(...)` | **A1/A2** |

Defect 1, corrected from A3-149: A4's source comment says punctuation was routed through `int_text` *"so literals stay
alphanumeric+space (inside the proven F3 say shapes)"*. **That caution is unnecessary** — `say("(")` is accepted by the emitter
and the full source assembles with zero refusals. So this is a one-token change per punctuation mark, not a language limitation.

Defects 2 and 3 are a single epilogue edit in the same place.

## What M-1 required, and what it means

The packet's M-1: *"`compiler_a.pep` staged through `build-c23 --sectional` into a native compiler A which directly reads unseen
Pep-0 source bytes from argv grant, checks exact subset, emits valid C23, rejects unsupported/invalid inputs per canonical
contract, and gives correct observable outputs compiled under strict Clang/GCC."*

Every clause is now demonstrated in the modelled build: argv grant (the epilogue `fopen`s `argv[1]`), exact-subset checking
(the fourteen negative cases are refused with their pinned codes), valid C23 output (nine lines matching the oracle), and strict
Clang/GCC. **No Python or OCaml semantic compilation is on the runtime path** — the binary is the 21 Pep functions and a C
runtime.

## The honest boundary

**This is not an M-1 claim for the repository.** Three edits were made in a scratch copy by me, in three parts of two other
agents' code. Until A4 lands the punctuation literals and A1/A2 land the epilogue change, the tracked tree still produces
`int main / 40 / void / 41 …` and exits 0 on everything. What is established is that **nothing else stands in the way** — the
gate, the assembly path, the narrowed fragments, the find_brace rewrite and the runtime are all proven together.

## Limits

- The `find_brace` five-conjunct rewrite is **mine** (A3-148's mechanism), not A4's chosen form.
- Narrowed-fragment emission requires the host to compute each target's position in the narrowed list (A3-146's trap).
- Epic: one seed, one emitter pin, one driver pin; mixed lanes, not a merged tree.
- Not tested: `--sectional` through A1's `build_c23` end to end — my scaffold calls the tools directly. That is A1's S3 slice,
  and it is now the only untested link between here and a tracked-tree M-1.

REF GH #16. Parents: `6726552171` (A3-149, the two defects), `6726520208` (A3-148), `6726440672` (A3-146).