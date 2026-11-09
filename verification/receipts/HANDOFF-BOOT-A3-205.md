# HANDOFF BOOT-A3-205 — state for whoever picks this up

**A3's verification lane is complete and current. The mission cannot close because the compiler A does not exist as a tracked,
buildable artifact, and the two actions that would produce one belong to A1 and A4.**

## What is proven

| claim | status |
|---|---|
| M-1 passes through the real product path | **15/15 on clang and gcc**, 33,069 B C, no hand assembly (A3-159) |
| The same C is clean under strict warnings | `-Wall -Wextra -pedantic -Werror -O2` on both compilers (A3-179) |
| No hidden semantic compiler | imports KERNEL32.dll only; zero interpreter markers (A3-161) |
| The approval runbook can fail | a 3-line stub scores M-1 1/15 (A3-172) |
| Every mechanical defect in A4's fallback tier | closed by A4 and verified here (A3-188, 194, 201, 203) |
| A13 classification root cause | bare-mutable-local `var` gets no type; annotation clears it (A3-183) |

## What is not

- **No tracked compiler A.** The M-1 result lives in a disposable worktree with four unlanded patches.
- **A4's fallback tier does not build.** `scan_value` exceeds the step budget; minimum loop work is 4.5 units against ~4 (A3-199).
- **Class (ii) is 7 of 10 wrong.** The published `PEP0_SUBSET.md` promises nine shapes exit 5; three do.

## Three buildable arrangements, all measured

| arrangement | runbook | keeps |
|---|---|---|
| no fallback tier (A3-176) | 9 of 10 | nothing of A4's new work |
| only the 9 functions that build (A3-202) | 9 of 10 | most of it |
| research `scan_value`'s algorithm | none | — no in-place fix exists (A3-199) |

**All three leave class (ii) at 7 of 10 wrong**, so all three require the contract to be narrowed to what the compiler delivers.

## What the next seat needs to do

1. **A1**: land `verification/fixtures/a3-m1-driver-recipe.diff` (applies cleanly to their own branch, A3-170) and integrate a
   candidate.
2. **A4**: choose an arrangement and apply the A3-148 Bool-local rewrite to `find_brace`. Note this is **my probe**, never part of
   their source, and every route depends on it.
3. Then run, with no edits to my lane needed:
   ```
   python verification/probes/gate_candidate_171.py --root <tree> --contract narrow
   PEPIN_CONTRACT=narrow python verification/probes/contract_c7_162.py
   ```

## Traps, in order of how much time they cost

1. **Step budget depends on the dependency set.** Comparisons across different sets are invalid. This produced two published
   findings I had to retract (A3-186, A3-187).
2. **A refusal that is invisible is not absent.** `match_tail`'s empty-then and `scan_value`'s in-loop `var` were both hidden behind
   an earlier failure. Read the constructs.
3. **The candidate is a patchwork** — checker from neither agent's tip (A3-177).
4. **A1's published figures were measured on emitter `efedda39`**; the candidate ships `32bc253d` (A3-178).

## The honest summary

This gate can close as **a reproducible compiler A that does less than its published contract claims, with the contract corrected.**
It cannot close as a contract improvement. That is one decision plus one integration away, and neither is A3's to make.

`verification/STATUS.md` is the lane entry point and is current.