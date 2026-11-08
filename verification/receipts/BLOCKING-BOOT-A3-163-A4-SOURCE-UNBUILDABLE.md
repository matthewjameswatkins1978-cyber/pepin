# BLOCKING FINDING BOOT-A3-163 — A4's fallback tier cannot be built by either path

**A4's new `compiler_a.pep` (`da6edff7`, blob `784168ee`, 34 functions, 24,745 bytes) reports `valid` from `pep.ps1 check` but
**cannot be compiled at all**: the one-shot path exceeds the 1 MiB JSONL message limit, and the sectional path rejects it with
`PEP_A13_TYPE_UNSUPPORTED`. The sectional rejection is program-wide — simplifying one function only exposes the next.**

Seed blob `f8f476198f`. Disposable worktree `D:\Projects\wt-a3-cand`, restored afterwards, dirty 0.

## Two paths, two walls

```
$ python pep_c23.py build-c23 …/compiler_a.pep --output … --emit-c …
Pep C23 error: Pep C23 session request exceeds the 1 MiB JSONL message limit

$ python pep_c23.py build-c23 …/compiler_a.pep --sectional --output …
Pep C23 unsupported: Pep C23 sectional check failed in scan_name: ['PEP_A13_TYPE_UNSUPPORTED']
```

The first is new and worth stating plainly: **the source grew from 9,639 to 24,745 bytes** (21 → 34 functions), and the one-shot
path can no longer even submit the parse. For anything this size, the sectional path is the **only** route — and today it refuses.

`pep.ps1 check` says `valid` because the one-shot checker accepts the program. The sectional `bound-chunk` checker does not. **Two
checkers disagree on the same source.**

## The rejection is program-wide, not one function

I simplified functions one at a time and re-ran the product path. The failing name **moves down the source** each time:

| change | reported failure |
|---|---|
| none | `scan_name` |
| `scan_name` emptied | `scan_value` |
| `scan_name` emptied, `scan_value` reduced to a pre-loop prefix | `match_tail` |
| same, `scan_value` reduced to a bare `while` | `match_tail` |

**At least three of the thirteen new functions trigger it**, and simplifying one only advances the report. So this is not a defect
in one function that a local edit will fix.

## Three hypotheses tested and falsified

Each is a plausible reading of "empty type shape", and each was tested one variable at a time:

1. **The nested `is_namech(byte_at(source, i))` call** — the `user_fn(builtin(...))` shape I flagged in A3-085. Hoisting the inner
   call into `var ch = …`: **still fails.**
2. **A missing callee signature** — `is_namech` not present in the chunk's external set. Replacing the call with a constant
   comparison: **still fails.**
3. **`var` declarations nested inside a `while` body** (`var hasop`, `var d2` in `scan_value`). Hoisted to function top level:
   **still fails.**

So it is not the call shape, not callee availability, and not nested declarations.

## What `PEP_A13_TYPE_UNSUPPORTED` means, exactly

From `tests/pep_checker_a13.pep` L1410-1414:

```
if shape.kind == "" { return "PEP_A13_TYPE_UNSUPPORTED" } else {}
...
return "PEP_A13_TYPE_UNSUPPORTED"
```

A **type shape came back empty** — the checker could not infer a type for some node, rather than rejecting a type it knows is
unsupported. That is why the code is generic and why it moves between functions: whichever function the checker reaches first
reports it.

## Why this matters more than the seven

A4 chose the harder of the two honest options from A3-155 — implement real classification rather than narrow the contract — and
that is the better outcome for the language. But the result **cannot be built today**, so:

- the contract gate (A3-162) still measures the **old** fixture binary, not A4's work;
- **no tracked compiler A can exist** until this is resolved, so M-1 on the tracked tree is further away, not nearer;
- the four A3-159 driver patches are unaffected and still apply — this is a source/checker problem, not a driver problem.

## What I need from the owners

**A4:** a smaller reproducer, or the construct. I have three falsifications and a moving target; the fastest path is for A4 to run
`build-c23 --sectional` on their own source, which takes about a minute, and bisect from their side with knowledge of what they
added.

**A1:** the two checkers disagree on one source. `pep.ps1 check` → `valid`; sectional `bound-chunk` → `PEP_A13_TYPE_UNSUPPORTED`.
Whichever is right, **a `valid` source that cannot be built sectionally is a trap for every agent after this one**, and the
disagreement itself is worth a decision.

## Limits

- One revision (`da6edff7`), one seed, product path only. No conclusions about which checker is correct.
- I simplified functions to move the report; I did not identify the offending node.
- The four A3-159 patches were applied for these runs so the driver would not obscure the signal; they are irrelevant to the
  check failure, which happens before emission.

REF GH #16. Related: `6728442644` (A3-162, the contract gate this defers), `6728133368` (A3-155, the two options A4 took).