# FINDING BOOT-A3-183 — root cause and a workaround: annotate `var x = <bare local>`

**The A13 defect fires because the binding for `var e = i` — where `i` is a mutable local — records no type at all. An explicit
annotation clears it. Applied to A4's real source, annotating 107 bare-name declarations removes the A13 rejection entirely and the
build advances to a different blocker.**

Seed blob `f8f476198f`. Candidate `b039fc5` + A4 `d37bf566` source.

## The mechanism, read from the checker

`pep_checker_a13.pep` L1920-1935, the `assignment` branch:

```
let expectedName  = binding.binding.typeName
let expectedShape = if binding.binding.typeShape.kind != "" { … } else { legacy_type_shape(nodes, expectedName) }
…
if expectedName == "" && expectedShape.kind == "" {
  diagnostic("PEP_A13_TYPE_UNSUPPORTED", "Assignment target has no supported concrete type", node)
}
```

The diagnostic fires when **the target's binding has neither a type name nor a type shape** — i.e. the binder never recorded a type
for `e`. The assignment check is the messenger; the defect is in binding construction.

## Confirmed by substitution on the 31-line fixture

| declaration | result |
|---|---|
| `var e = i` (as written, `i` a mutable local) | **A13 failure** |
| `var e = 0` (literal initialiser) | passes the check |
| `var e = o` (parameter initialiser) | passes the check |
| **`var e: Int = i`** (annotated) | **passes the check** |

So: a `var` whose initialiser is a **bare mutable local name** gets no type; a literal, a parameter, or an annotation does not.
That is a precise, testable statement about the binder, not about the assignment check.

## Applied to A4's real source

```
annotated 107 bare-name var declarations
build: Pep C23 unsupported: Pep C23 sectional check failed in scan_value: ['PEP_RUNTIME_STEP_LIMIT']
```

**The A13 rejection is gone from `scan_name`.** The build now stops one function later, on the step limit — a different and
already-characterised class of blocker (A3-147/166).

## What this means for each lane

**A4 — a workaround exists and needs no checker fix.** Annotating bare-name `var` declarations clears the A13 rejection. That is a
source-level change entirely inside A4's ownership, and it is the first route out of the block that does not depend on A1.

**A1 — the root cause is upstream of the check.** If the binder could type `var x = <local>`, the defect disappears without touching
L1933. That is a better fix than relaxing the diagnostic, which would turn a real gap into a silent untyped binding.

## Honest limits on the workaround

- My script annotated **all 107** bare-name initialisers as `Int`. Where the initialiser is a `Str`, `Bool` or `SourceBytes` local,
  that annotation is **wrong**, and the check would report `PEP_TYPE_MISMATCH` rather than an A13 code. The build stopped at
  `scan_value`, so only the annotations the checker reached are confirmed. **A4 must annotate with the real type, not copy my
  blanket `Int`.**
- The build still fails — on the step limit — so this does not produce a compiler A. It removes one blocker and reveals the next.
- I applied this in a disposable worktree and reverted. The 107-annotation script is not committed as a patch; A4 should annotate
  deliberately.
- Two defects remain between here and M-1: the step limit at `scan_value`, and the epilogue (A3-159).

## Why I did not stop at the diagnosis

A3-163..169 established the defect thoroughly but every one of those receipts ended by handing it to A1. This turn I read the check
instead of only measuring its output, and the root cause plus a workaround fell out in one step. **Diagnosing thoroughly is not the
same as locating the cause**, and I had been treating them as equivalent for six turns.

REF GH #16. Supersedes the "no workaround transfers" conclusion of `6728763855` (A3-169) — that search tested restructuring, not
annotating.