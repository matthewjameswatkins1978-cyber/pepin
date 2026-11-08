# ACCEPT BOOT-A3-170 — the driver recipe is extracted, re-verified, and its scope is now exact

**The A3-159 recipe is split into a driver-only patch (5,417 B, two files) that applies cleanly to the current candidate. Applied
and re-verified this turn: it builds working programs, and its epilogue fix is correct for compiler A's shape and incomplete
elsewhere. That incompleteness is now documented rather than discovered later by whoever applies it.**

Seed blob `f8f476198f`. Candidate `b039fc5`, dirty 0 before and after. New artifact:
`verification/fixtures/a3-m1-driver-recipe.diff`.

## The split

The original `a3-m1-recipe.diff` touched three files. Only two belong to the driver:

```
diff --git a/pep_sectional.py
diff --git a/tests/pep_c23_emitter.pep
```

The third was A4's `compiler_a.pep`, which has moved on twice since. So:

```
$ git apply --check a3-m1-recipe.diff               → FAIL (compiler_a.pep: patch does not apply)
$ git apply --check a3-m1-driver-recipe.diff        → clean, exit 0
```

The driver half is independent of A4's source, which is what makes it reusable.

## Re-verified after applying

| check | result |
|---|---|
| applies to `b039fc5` | clean |
| builds `fn main() -> Int { return 42 }` | emits, compiles, runs |
| builds `fn main(source: SourceBytes) -> Int { return 42 }` | **stdout empty, exit 42** |
| A13 gate (`a13_assign_gate_168.py`) | still FAIL — correct, the driver patches do not touch the checker |

That last line matters: the driver fix does not mask the checker defect, so the two are separable and can land in either order.

## Scope correction — the epilogue fix is partial

With the patch applied, a **grant-entry** main (`fn main(source: SourceBytes)`) behaves correctly: nothing on stdout, the return
value as the exit code. But `fn main() -> Int` still printed `42` and exited `0`, because `tests/pep_c23_emitter.pep` has **four**
`return 0` sites and A3-159 patched **one**:

| line | branch | patched |
|---|---|---|
| L5104 | arena entry | **no** |
| L5116 | arena, granted entry | **no** |
| L5152/5156 | **non-arena granted entry** — compiler A's shape | **yes** |
| L5163 | zero-argument entry | **no** |

Compiler A takes `SourceBytes`, so M-1 does not depend on the other three. But anyone applying this recipe to make the *language*
propagate exit codes generally would get a half-fix, and the receipt said "the epilogue" without qualification. It should have
said "the granted-entry epilogue".

## Why record this at all

A partial fix that passes the one gate it was written for is exactly the shape of thing that gets generalised wrongly later. The
cost of writing the table down now is minutes; the cost of someone assuming all four branches were fixed is a debugging session on
a program that is not compiler A.

## Status of M-1

Unchanged: **15/15 on clang and gcc** for the build assembled from A4's `81dca2f4` plus the full three-file recipe (A3-159),
with all four patches measured necessary. The driver-only patch is the part that survives A4's source churn; the Bool-local
rewrite is now A4's to make in whatever source they finally ship, and the A13 checker defect blocks that source entirely.

## Limits

- Verified on `b039fc5` only; the patch has not been tried against a newer candidate because none exists.
- The `fn main() -> Int` behaviour above is the *unpatched* branch behaving as designed, not a new defect.
- Nothing here has been applied to any peer branch; the patch is a proposal in my lane.

REF GH #16. Supersedes the scope wording of `6728365639` (A3-159). Related: `6728763855` (A3-169).