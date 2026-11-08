# FINDING BOOT-A3-157 — find_brace's blocker is callee call-site multiplicity, not depth or position (corrects A3-147)

**Three controlled experiments on candidate `b039fc5` + A4 `81dca2f4`, all through the real product path. The refusal follows
`is_str3`, not the statement index; `is_int3` and `is_str3` are byte-structurally identical; and duplicating the single
`is_int3` call makes the *second* site refuse. This falsifies my A3-147 attribution to 5-conjunct conditions, which no longer
holds on the current emitter.**

Seed blob `f8f476198f`. Disposable worktree `D:\Projects\wt-a3-cand`; source restored afterwards, worktree clean.

## What refused, and exactly where

```
Pep C23 unsupported: Pep C23 fragment 11 of find_brace refused: PEP_RUNTIME_STEP_LIMIT
```

Fragment 11 (0-based) is **stmt[11] = L288**:

```
if e0 == 0 && err == 1 && is_str3(source, o) == 1 {
```

A **3-conjunct** condition. stmt[10], immediately before it, is `if err == 0 && is_int3(source, o) == 0` — also 3 conjuncts —
and it **emits**.

## Experiment 1 — conjugate depth is not the driver

A3-147 said find_brace's remaining refusals were 5-conjunct `&&` conditions. On the current emitter the refusing statement has
three conjuncts, and the 5-conjunct conditions in this file are not in find_brace at all — they are in the type-word matchers:

```
is_main4   L52   &&=4
is_bool4   L97   &&=4
is_unit4   L106  &&=4
```

Rewriting find_brace's three long conditions into `let p = <3 conjuncts>` + `if p && <2>` (the A3-148 remedy) **changed nothing** —
still `fragment 11`. So the A3-148 remedy does not address this refusal.

## Experiment 2 — position and binding accumulation are not the driver

Swapping stmt[10] and stmt[11] moved the refusal from **fragment 11 to fragment 10** — it followed the `is_str3` statement to its
new, earlier position. If cost were cumulative over statements, the failure would have stayed at index 11. So neither statement
position nor accumulated carried bindings drive it.

## Experiment 3 — the callees are identical, and call multiplicity decides

`is_int3` and `is_str3` compared line by line differ in **only two things**: the function name and the three byte constants
(73/110/116 vs 83/116/114). Same node count, same shape, same parameter use.

```
fn is_int3(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 3 <= byte_length(source) && byte_at(source, o) == 73 && byte_at(source, o + 1) == 110 && byte_at(source, o + 2) == 116 {
    r = 1
  } else { }
  return r
}
```

Call counts inside find_brace: `is_int3` **1**, `is_str3` **2**, `is_bool4` **2**, `is_unit4` **2**, `is_ws_at` 3, `expect_byte` 6.

Duplicating the `is_int3` statement (semantically a no-op — both copies only set `err = 1` when the type word is not `Int`):

```
Pep C23 unsupported: Pep C23 fragment 11 of find_brace refused: PEP_RUNTIME_STEP_LIMIT
```

Fragment 10 (the first `is_int3` site) **passed**; fragment 11 (the second) **refused**. Giving `is_int3` a second call site put it
in the same class as `is_str3`.

## What this leaves

| hypothesis | verdict | evidence |
|---|---|---|
| conjunct depth | **ruled out** | refusing statement has 3 conjuncts; rewriting depths changed nothing |
| statement position | **ruled out** | swap moved the refusal from 11 to 10 |
| accumulated bindings | **ruled out** | the swapped statement failed *earlier* with fewer carried bindings |
| callee body/structure | **ruled out** | is_int3 and is_str3 differ only in name and constants |
| **callee call-site multiplicity** | **supported** | is_int3 once → passes; is_int3 twice → second site refuses; is_str3 twice → site refuses |

The outstanding detail I cannot yet explain: for `is_str3` the **first** of its two sites refuses, while for duplicated `is_int3`
the **second** does. I am reporting the observations rather than inventing a mechanism that fits all three.

## Why this matters for A2

The A3-125/126 cost law says fragment cost scales with the whole function's node count, and that call-fact lookups are full
scans. These three experiments say the scan becomes decisive when a callee has more than one call site in the chunk — which is
actionable: a per-callee call-fact index, or resolving repeated call sites once, would address it. That is A2's call to make;
I am not proposing an implementation in their file.

It also means **A4 cannot fix this in the source** by splitting conditions. Reordering calls or reducing call-site multiplicity
(`is_str3` is called at L288 and L300; `is_bool4` at L292 and L304; `is_unit4` at L296 and L308) might, and that is worth
A4 trying if A2's route is slower.

## Limits

- Three experiments, one function, one revision, one emitter. Not a general model.
- The `let p = …` rewrite was applied in the disposable worktree only and reverted; A4 owns that source.
- Steps were not instrumented — the driver reports the refusal, not the spend.
- This does **not** change the gate verdict: compiler A still cannot build at `b039fc5`+`81dca2f4`, and the epilogue defects are
  untouched.

REF GH #16. Corrects A3-147. Related: `6728167310` (A3-156, gate report), `6728133368` (A3-155).