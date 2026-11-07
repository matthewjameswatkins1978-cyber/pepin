# PRE-REGISTRATION A3-037: do windowed (partial-function) chunks still CHECK valid?

**Seat:** A3. Follows BOOT-A3-036, which tested A1's `shared_spine` **plan admission** but explicitly
left the checker untouched. **Written and committed before measurement.**

## Why this is the next question, and why it could sink the remedy

The capacity remedy on the table is: split the frozen app's 44-node `main` into sub-function windows so
each chunk emits inside the 100k budget. BOOT-A3-036 proved the *host* will accept such a plan
(`[46,54]` spine, windows 16 vs 30, 90/90 coverage, only declared duplication).

But a window is a **structurally partial function**: a `while` whose body has been divided, branches
whose children live in another chunk. The emitter can only work on chunks the **Pep-written checker**
declares `valid`. If the checker requires structural completeness, every window is refused and the
whole window remedy is dead on arrival — which would be far better to know now than after A2 builds it.

## Prediction

| # | Claim | Falsified if |
|---|---|---|
| W1 | both deep-split windows (`[46,54]` spine, 16 and 30 ids) check **`valid`** with zero diagnostics | either is not `valid` |
| W2 | the three predicate chunks (whole functions) still check `valid`, i.e. the harness is sound before the interesting case | any is not `valid` |
| W3 | a window that is *deliberately* orphaned (its parent removed from the chunk while the plan is bypassed) is **not** `valid` — the control that stops W1 from being vacuous | it comes back `valid` |

W3 matters: without a case that *must* fail, two `valid` windows prove little.

**My honest expectation is W1 holds** — BOOT-A3-031 showed the checker accepts empty branches
(`if c { } else { }` is check-`valid`), so partial structure is probably tolerated. But I am not
confident, which is exactly why it gets measured rather than assumed.

## Method

- Frozen app `pepin-source-scan.pep` (blob `4a44dd65…`), A1's `86ff953` tree (carries `shared_spine`),
  fresh worktree, seed built there.
- Window construction is identical to BOOT-A3-036's deep split: spine `[46, 54]`, windows 16 / 30 ids,
  plus the three predicate functions whole.
- Each chunk is checked with `analyze_chunk_typed`, the other functions supplied as external
  `CheckedFunction`/`ResolvedSignature` facts — the same call the mission's gates use.
- Diagnostics are recorded verbatim. A refusal is a result, not a failure of the probe.

## Scope guard

A3 owns only `verification/**`. No edits to A1's contract/checker, A2's emitter, or A4's app. Cap
unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.
