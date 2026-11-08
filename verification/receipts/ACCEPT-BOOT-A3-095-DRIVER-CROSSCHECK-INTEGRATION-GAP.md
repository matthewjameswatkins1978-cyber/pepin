# ACCEPT BOOT-A3-095 — A1's sectional driver refuses earlier than A2's emitter, and with A2's emitter it reproduces my first refusal exactly

**Verdict: A1's sectional driver on A1's own branch cannot reach the 9/21 figure at all — it refuses at
`Pep C23 rejects two fallible operands` because A1's branch has no A2 emitter work. Substituting A2's emitter into the same
driver makes it refuse at `Pep C23 calls require a known target` — the exact first refusal my independent instrument
reported. So the first emission blocker on compiler A is now confirmed through two different drivers, and the 21-function
number requires an integrated tree, not a single lane.**

## The divergence, measured

| | A1 `codex/a1-typed-bound-pipeline@9bf18699` | A2 `codex/a2-divergence-spike@bea071a` |
|---|---|---|
| emitter blob | `efedda39` | `da31bd1b` |
| contains `b758c91` (arithmetic `may_fail`) | **no** | yes |
| merge-base | `231caf1` | `231caf1` |

`git merge-base --is-ancestor b758c91 9bf18699` → **not an ancestor**. The two lanes forked at `231caf1` and each carries
its own emitter lineage.

## Same driver, two emitters, two different first refusals

Run through A1's own entry point (`python pep_c23.py build-c23 <compiler_a.pep> --sectional`, which writes C and compiles
with `clang -std=c23 -Werror`):

| emitter in the tree | first refusal | C emitted |
|---|---|---|
| A1's own (`efedda39`) | `Pep C23 rejects two fallible operands because C operand evaluation order is unspecified` | none |
| A2's (`da31bd1b`) | `Pep C23 calls require a known target` | none |

Both runs: ~6.7 s, exit 2, **no C written**.

The second refusal is character-for-character the one my independent instrument reported for `is_ws_at` in BOOT-A3-084.
A different driver, a different call path, the same earliest blocker — so A2-S1's target is confirmed by the sectional
lane as well as by my probe.

## Why this matters for M-1

1. **The 9/21 figure is an integration property, not a lane property.** A1 cannot reproduce it from their branch, because
   their emitter stops one gate earlier. Any statement of the form "compiler A is at N/21" must name the merged tree it was
   measured in — which is precisely what A1-S3's disposable candidate integration exists to produce.
2. **A2-S1 is necessary, not merely nice.** With both lanes' work in the tree, emission still stops at the cross-chunk call.
   Both of my earlier claims survive: 11 functions are step-limited, 1 blocks on the call target.
3. **Integration is not a formality here.** The two branches change the same file (`tests/pep_c23_emitter.pep`) on divergent
   lineages from a common base, so merging them is a real semantic merge, not a fast-forward. Nothing about the order of
   these two refusals is obvious without running it.

## A refinement to my own BOOT-A3-083

A3-083 said `b758c91` "moves nothing for compiler A", measured between `1885566` and `bea071a` on the whole-chunk **check**
path: 10 valid / 11 step-limited at both pins, identical. That stands for the check stage and for the emit *count*.

But this experiment shows the rule is **not** inert on the **emission** path: with A1's emitter, `is_ws_at` refuses on
fallibility; with A2's, it refuses on the call target. So `b758c91` converts one refusal into a different one — it does work,
it just does not change the number, because the next gate catches the same function. "Moves nothing" was too strong a
phrasing for the emission stage; "does not change the count at either stage" is the accurate claim. My earlier sentence is
corrected here rather than left to mislead A2 into thinking the arithmetic work was wasted.

## Method note

The A2-emitter substitution was done in the disposable `wt-a3-d188a1` worktree and **reverted** afterwards
(`git hash-object` confirms `efedda39` restored, worktree clean). I did not edit any A1 or A2 file, and nothing was pushed
to either lane. This was an integration probe, not an integration.

## Limits

- One source (`compiler_a.pep` blob `ca732536`), two emitters, one seed. A different emitter pairing may stop elsewhere.
- The driver aborts at the first refusal, so this says nothing about how many functions would emit in a merged tree — only
  where it stops. My separate instrument's 9/21 still stands for the A2 lineage.
- Substituting one file is not an integration: A2's emitter may depend on companion changes in `pep_c23.py` or the checker.
  The result is consistent with the companion changes being unnecessary for these refusals, not proof.

## Reproduce

```
cd <worktree at 9bf18699>
python pep_c23.py build-c23 compiler_a.pep -o /tmp/cA.exe --emit-c /tmp/cA.c --sectional
# then, to test the integration preview:
git cat-file blob da31bd1b > tests/pep_c23_emitter.pep   # revert after
```

REF GH #16. Lanes: A1 `9bf18699`, A2 `bea071a`. Integration probe and independent driver cross-check: A3.