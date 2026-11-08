# FINDING BOOT-A3-164 — the A13 rejection is "Assignment target has no supported concrete type"

**A3-163 published `PEP_A13_TYPE_UNSUPPORTED` as the blocker on A4's fallback tier. That code is shared by eight different
diagnostics, so the code alone was not actionable. I have extracted the message and located the statement.**

```
[scan_name] PEP_A13_TYPE_UNSUPPORTED: Assignment target has no supported concrete type
```

Seed blob `f8f476198f`. A4 `da6edff7`, `compiler_a.pep` blob `784168ee`. Disposable worktree, restored, dirty 0.

## Why the message was missing

`check_slice` collects `{fields_map(d)["code"]["value"] for d in report["diagnostics"]}` — **codes only, deduplicated**. Eight
distinct diagnostics share `PEP_A13_TYPE_UNSUPPORTED`:

| line | message |
|---|---|
| L1933 | **Assignment target has no supported concrete type** |
| L1957 | This built-in call has no type rule in the current checker slice |
| L1958 | Constructor payload and nominal identity checks are not implemented |
| L1994 | This expression form has no type rule in the current checker slice |
| L1411/1414/1420/1546/2857 | type-shape resolution failures |

I re-ran the bound-chunk tool directly and printed full diagnostics, which named L1933.

## The statement

In `scan_name`:

```
  var e = i
  while i + 1 <= n {
    if f == 1 {
      if is_namech(byte_at(source, i)) == 1 {
        i = i + 1
        e = i            <-- this assignment is the trigger
      } else {
        f = 2
        i = n
      }
    } else {
      i = n
    }
  }
```

## Three experiments

| change | result |
|---|---|
| as written | `scan_name` fails |
| **delete `e = i`** | **`scan_name` passes**; the failure moves on to `scan_value` |
| change the RHS to `e = i + 0` | **still fails** `scan_name` |
| move `var e = i` up with the other locals | still fails (variant may also have been malformed — see limits) |

The third row is the discriminating one: the **RHS form does not matter**, so this is not about the expression. `i = i + 1` in the
same nested block is fine. It is the assignment **target** `e` that the checker cannot type — exactly what the message says.

`e` is declared `var e = i` mid-function, after an earlier `if` block that reassigns `i`, and is assigned only from inside a
`while`→`if`→`if` nest.

## What I have not pinned

The exact rule. Candidates consistent with the evidence: a `var` whose initializer is a bare name, declared mid-body, then
assigned only inside a deeper block; or a binding registered in a scope the assignment-type check does not consult. I did not
isolate which, and my `e_declared_early` variant may have been malformed, so I am not claiming it.

## What this means per lane

**A1 — this is a checker scope limitation, not a compiler-A defect.** The message is emitted by `pep_checker_a13.pep` L1933.
Every one of A4's thirteen new functions is written in the same nested-`if`/`while` style with cross-block assignments, which is
why the failure migrates between `scan_name`, `scan_value` and `match_tail` as each is simplified — it is not one bad function.
A `valid` one-shot verdict and a sectional rejection for the same source is the thing to resolve.

**A4 — a workaround may exist** (declare the variable at the point of use, or avoid assigning a mid-function `var` only from
inside a nested block), but I have not proven one, and the real fix belongs in the checker.

## Why this is worth the effort

A4 chose the harder of the two options I offered in A3-155 — implement real classification instead of narrowing the published
contract — and the resulting source is now **unbuildable by either path**: one-shot exceeds the 1 MiB JSONL message limit at
24,745 bytes, sectional rejects at the check. No tracked compiler A can exist until this is resolved.

## Method note

Two of my own tools misled me this turn and are worth recording:

- A scratch file named `bisect.py` in `%TEMP%` **shadowed the Python standard library module** and broke an unrelated import.
- The build's `codes[:3]` deduplication hid three diagnostics behind one code, which is why the message had to be extracted by
  calling the bound-chunk tool directly rather than reading the build output.

## Limits

- One revision, one seed, product path only; message extracted via a monkeypatched `check_slice` in a disposable worktree.
- The `e_declared_early` variant is not trustworthy — its replacements were chained and may have produced malformed Pep.
- I did not test whether the same statement shape fails in a minimal two-function program.

REF GH #16. Refines `6728528238` (A3-163).