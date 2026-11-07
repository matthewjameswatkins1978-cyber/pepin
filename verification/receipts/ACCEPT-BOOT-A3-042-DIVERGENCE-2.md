# ACCEPT BOOT-A3-042 — DIVERGENCE-2: input-dependent C is NOT yet achievable, and the blocker is narrow

**Verdict: NOT DEMONSTRATED.** I could not get a Pep program to emit input-dependent C23. The failure is
**not** a grand capability gap: every piece exists, and the block is a **narrow seam** between the
checker and the emitter. That is materially better news than "no capability", and it is precisely
localised.

This was pre-registered at `40fa4bf` before any measurement.

## The chain, each step a precise diagnostic (A1 `86ff953` tree, seed built there)

| # | generator form | result |
|---|---|---|
| 1 | `say(utf8_slice(source, 0, 3))` | **refused**: *"Pep C23 say lowers only string literals, Str parameters, Str locals and Str fields"* |
| 2 | `let part = utf8_slice(source, 0, 3)` then `say(part)` | **refused**: *"Pep C23 cross-chunk call has no resolved call fact"* |
| 3 | `var part = utf8_slice(source, 0, 3)` then `say(part)` | **same refusal** — `let` vs `var` makes no difference |
| 4 | diagnostic on the chunk report | **0 call facts**, 1 function fact |

**Step 4 is the finding.** The checker produces **no resolved-call fact for a builtin call**, while the
emitter's cross-chunk call lowering **requires one** at exactly the sites it supports (the emitter's own
comment lists *"let initialisers, direct return values, and binary operand trees"*).

So the two supported doors are closed in opposite directions:

- `say(...)` accepts only literals, Str **parameters**, Str **locals** and Str **fields** — not call results;
- a **local cannot be initialised** from a builtin call, because no fact is minted for it.

Result: there is today **no expressible path from input bytes to emitted C text**.

## What *does* exist (so this is a seam gap, not a missing world)

- `str_concat` **is a builtin** — the emitter's own source cites A1 `844c8b0`: *"str_concat is a
  BUILTIN: no top-level function node"*.
- `utf8_slice` exists in the **seed interpreter** (`pep_ocaml.ml`, 6 sites) and is used by
  `examples/pep_lexer.pep`, so it lowers in the emitted runtime.
- The emitter handles `Str` (`pep_str`, 25 sites) and `say(Str)`.
- Builtin calls **in conditions and assignments work** — line-scan's `if byte_at(source, o) == 10`
  emits and runs (BOOT-A3-040). It is specifically the **declaration-initialiser** site that fails.

## Why this matters for route choice

My D-route (`36f7b1c`) said both R and S are unproven until source-dependent output is demonstrated,
and nominated Str construction as the critical unknown. **Now measured: the unknown is not Str
construction, it is one seam.** That substantially changes the cost estimate:

- the fundamental capability is **one small fix away** (either the checker mints call facts for
  builtins, or the emitter lowers known builtins without demanding a fact — it already knows how to
  lower them inline elsewhere);
- this is **far cheaper** than route R's requirement to fix the measured quadratic emitter cost
  (~**381n + 35.68n²**, 80.5% quadratic at 44 nodes; a 44-node `main` already exceeds the budget).

So the cheap lever is this seam; the expensive lever is the traversal. Neither route is validated yet.

## Questions I am putting to peers (source-backed, not rhetorical)

- **@A2 (emitter):** the refusal text at `tests/pep_c23_emitter.pep` demands a resolved call fact for a
  call in a declaration initialiser. Since `byte_at`/`byte_length`/`int_text` are already lowered inline
  elsewhere without facts, **what is the smallest change that lets a *known builtin* be lowered at the
  initialiser site** — and does it risk type confusion, or is the fact gate purely an identity check?
  My falsifier: if the fact gate is load-bearing for type safety there, my "small seam" estimate is
  wrong and I will say so.
- **@A1 (checker):** should the checker mint `ResolvedCall` facts for builtin calls, or is "builtins are
  never facts" a deliberate invariant? If the latter, the fix must be entirely A2-side.

## What I did NOT establish

- No input-dependent C was produced, so **the mission's floor is still unproven by anyone**.
- I did not try lowering a builtin call through a **user function** wrapper (`fn slice3(...) -> Str`): the
  inner call would still be an initialiser/return site needing a fact, so I expect the same refusal, but
  **I have not measured it** and it is the obvious next variant.
- This is a capability probe, not a compiler. Passing it would prove only the floor.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/divergence_2_042.py      # D1 pass, D2 refused with the exact texts above
```

## Scope

A3 changed only `verification/**`. A1's checker/contract, A2's emitter and A4's app were read, not
modified. Cap unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-042).