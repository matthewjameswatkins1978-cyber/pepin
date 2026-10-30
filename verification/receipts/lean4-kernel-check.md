# Lean 4 kernel-check receipt — value-copy model (DEC-001)

**Label change:** `DRAFT`/`BLOCKED_SECURITY` → **`MODEL_PROVED`**.
The previously blocked local build is now executed: issue #22 cleared
native build-and-execute on this host (Defender protection on, no
exclusions), which lifts the binary-install hold that blocked `elan`.

## Host and toolchain

- Host: the same Windows worktree, no sandbox, Defender protection
  enabled, **no exclusions added** (`scoop install elan` completed with
  zero detections; the Lean toolchain download likewise).
- Toolchain: `leanprover/lean4:v4.35.0` — exactly the pin in
  `verification/lean4/lean-toolchain`, installed via `elan 4.2.4`
  (`lean version 4.35.0, x86_64-w64-windows-gnu, commit eb6cafb7290e,
  Release`).
- Worktree: `codex/bootstrap-agent3-verification`, proof tree at
  `verification/lean4/`.

## Commands and results (2026-10-30, all run locally)

| # | command | result |
|---|---|---|
| 1 | `lake build` | **PASS** — "Build completed successfully (5 jobs)"; `#eval exEdited` prints `some (PepVal.list [PepVal.int 99, PepVal.int 2, PepVal.int 3])` |
| 2 | `lake env lean Verification/ValueCopy.lean` | **PASS** — exit 0 |
| 3 | `lake env lean Verification/AliasedCounterexample.lean` | **PASS** — exit 0 |
| 4 | `lake env lean BrokenVariant.lean` | **REJECTED as required** — exit 1 with a type error (`?m.3 = ?m.3` vs `aread cxStore' cxCopy = aread cxStore cxCopy`): the intentionally unprovable variant does not elaborate, so the build does check proofs |
| 5 | `#print axioms` on `edit_takes_effect`, `copy_preserved`, `editOrig_copy`, `idx_upd_same`, `idx_upd_other`, `pepDecEq` | every one: **`[propext]` only** — Lean core's standard propositional-extensionality axiom. No `sorryAx`, no custom `axiom`, no `native_decide`, no `Quot.sound` beyond core |
| 6 | token scan `sorry` / `admit` / `axiom` / `native_decide` over `*.lean` | 2 hits, both documentation prose (the rules text in `ValueCopy.lean` header and the guard text in `BrokenVariant.lean` header); zero code occurrences |

## Kernel-check amendments (instances/tactics only — statements verbatim)

The draft had never been elaborated, as its `DRAFT` label said. Two
genuine draft defects surfaced and were fixed **without touching any
theorem statement** (per the file's own rule: "fix tactics there, never
the theorem statements"):

1. **No `DecidableEq` deriving handler for nested inductives** — core
   Lean 4.35 cannot derive `DecidableEq` for `PepVal` (a type
   containing `List PepVal`). Replaced `deriving DecidableEq` with a
   hand-written structural mutual decision procedure
   (`pepDecEq`/`listDecEq`); `Repr` deriving works and is kept.
2. **`set`/`get` are ambiguous in tactic position** with core
   `MonadStateOf.set`/`MonadState.get` — bare names in `simp` clauses
   failed to elaborate. Tactics now fully qualify `_root_.set` /
   `_root_.get`; definitions themselves are unchanged.
3. Minor proof repairs in `editOrig_copy` (hypothesis-directed `simp`)
   and `edit_takes_effect` (induction-hypothesis argument order after
   the `cases` split). No statement, no definition body altered.

## Scope reminder (unchanged)

`MODEL_PROVED` applies to the **model**, not the implementation: the
theorems prove the value-copy property for the pure functional model
defined in `ValueCopy.lean`. Correspondence between model and real Pep
execution stays `TESTED` (OCaml interpreter probes P1–P3 in
`../adversarial/cases/VALUE_COPY_DEC001.md`). `AliasedCounterexample.lean`
remains the negative control: the analogous property FAILS for
shared-backing semantics.

## Supersedes

`lean4-build-BLOCKED_SECURITY.md` (historical record of the hold period;
the blocker was removed by the #22 clearance, not by weakening any
control — Defender stayed on, exclusions off).
