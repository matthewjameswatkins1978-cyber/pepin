# V1 model ↔ implementation correspondence (Agent 3, V3 scoping)

Status: `DRAFT`. This note records exactly what the Lean model in
`Verification/` claims about real Pep, and where the correspondence
is strong, loose, or missing. It is a bridge *obligation* register,
not a bridge proof. Nothing here upgrades any `DRAFT`/`TESTED` label.

## What the model formalizes

`ValueCopy.lean` models DEC-001 for `Int`/`Bool`/nested-`List` values
with a checked single-cell rewrite (`set`) and a copy-then-edit
snapshot (`Snap`/`editOrig`), proving `edit_takes_effect` (edits land)
and `copy_preserved` (the copy is untouched by construction).
`AliasedCounterexample.lean` shows the same statement FAILS under
shared-backing writes, so the theorems are model-dependent, not
vacuous.

## Correspondence, claim by claim

| model element | real-Pep counterpart | strength |
|---|---|---|
| `PepVal` scalars + nested lists | seed `Int`/`Bool`/`List[T]`, record payloads | STRONG for scalars/lists (P1–P3, S4, U-probes); records covered separately (P3, RECORDS_AND_UNIONS.md), not in the model |
| `copy` (bind the same value twice) | `let b = a` (P1–P3 TESTED) | STRONG — identical shape |
| `editOrig` (rewrite in place-shape) | `append` producing a new list + `var` rebinding (P1–P3 TESTED) | LOOSE — see gap G1 below |
| `copy_preserved` | "editing the original does not touch the copy" | inherits G1's looseness; constructional, disclosed in-file |
| aliased counterexample | a CoW/aliasing bug in a runtime | UNTESTED — no such bug observed; the seed runs on OCaml immutable values, and native codegen is BLOCKED |
| `#eval` expectations | interpreter outputs P1 (`3/3/4`), N4 diagnostics | STRONG — same numbers, TESTED both sides |

## Gap G1 (explicit): `set` has no direct seed counterpart

The seed surface offers no in-place scalar edit: there is no indexed
assignment and no `edit`-mode parameter (N2: `edit` is parse-rejected).
The model's `set` (checked rewrite at an index path) therefore
abstracts what `append` + `var`-rebind *achieve* (a new value for the
original binding, old bindings untouched) rather than any primitive the
seed actually executes. A kernel-checked `copy_preserved` would prove
the model internally consistent and non-vacuous (via the executable
examples + the aliased refutation), but it would NOT by itself prove
anything about `pep_c23`-generated C23 or a future CoW runtime.

## What would close the bridge (concrete, gated)

1. Kernel-check the model on the approved host (`MODEL_PROVED`).
   Blocked on workflow registration.
2. Bind one real operation to `set`/`get` semantics with a differential
   test: e.g. a reference `List` copy-and-rewrite routine whose
   observable behavior is asserted equal to the model's `get`/`set`
   outcomes on the same inputs (`IMPLEMENTATION_REFINED`, narrow scope).
   Blocked on nothing technical — but adds value only after (1).
3. If Agent 2's runtime ever uses CoW/shared backing, re-run the
   aliased-counterexample argument against its actual sharing contract.
   Conditional; no such runtime today.

## Decision

V3 stays DEFERRED per the mission's explicit out ("if not valuable,
explicitly defer"): the correspondence obligations above are the
deliverable for now. No full verified-compiler work, no GC proofs,
no Mathlib. The model remains a checked specification of DEC-001 for
the subset it covers, with its exact distance from the implementation
written down here instead of hand-waved.
