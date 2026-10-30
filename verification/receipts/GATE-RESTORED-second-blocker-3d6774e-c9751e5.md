# Round — A1 `3d6774e` / A2 `c9751e5`: bundle GATE RESTORED in combined; second stacked blocker exposed (2026-10-30)

## Headlines

1. **A2's `c9751e5` ("Isolate C23 emitter AST helper namespace") fixes
   the cross-type bundle mismatch.** The combined state
   (A1 checker + A2 emitter) is **`status: valid`** for the first time
   since `d64ea2a` — the integration landed from the emitter side.
   A1-own remains **invalid** (still carries old emitter `9573c227`),
   same `PEP_TYPE_MISMATCH @ 5054`.
2. **The moment the bundle opened, a SECOND stacked blocker on A1's
   line surfaced:** `pep_c23.py`'s staged flow dies at
   **`tool_validate pep-c23-checker-start`** with
   `PEP_TOOL_ARGUMENT_COUNT: Test vector argument count did not match
   the function signature` — the checker now declares
   `checker_start(ParserProgress, Int) -> CheckerCursor` (the `Int`
   chunk parameter from the chunking series), while the test vector
   sends 1 argument. **Invisible on A1's own line** (the bundle failure
   kills `emit()` first, masking validate), **fatal in any
   valid-bundle state**: every `pep_c23.py`-path emit is dead.
3. **Wall A remains unmeasurable** — now blocked one layer deeper
   (validate, previously bundle-open). Classifier/str/nested/cli in the
   combined state all fail at this validate gate, not at emit cost.

## State table (sequential runs, detached read-only)

| state | bundle | `pep_c23.py` emit path | a14 (own harness) |
|---|---|---|---|
| A1 `3d6774e` own | **invalid** (`FlatAstNode`/`CheckerNode` @5054) | dies at open | 11 fails, setup-level (report lane independently tabulated: a14 11/11, cli 5/8, classifier 5 — corroborates) |
| **combined `3d6774e` + `c9751e5`** | **valid** ✓ | **dies at `checker_start` validate (ARGUMENT_COUNT)** — str 17 errors, nested 72 errors, cli 5F+1E | **4 fails** (real behavior: countdown collapse + depth + 2 known) |
| A2 `c9751e5` own | valid | **green**: str+cli **32 OK** (3 skipped), nested **47 OK** (5 skipped) | **4 fails** (countdown collapse persists) |

## What each blocker now looks like, in fixing order

1. **Bundle typecheck** — fixed *in the combined state* by A2's
   namespace isolation; A1-own still needs the emitter integration (or
   to take A2's emitter). Aging: open since `d64ea2a`.
2. **`checker_start` arity drift (NEW this round)** — A1's checker
   gained the `Int` chunk parameter; A1's own `pep_c23.py` test vector
   not updated to match. **Fixing (1) alone leaves A1 with dead emit
   paths** — this wall becomes visible to them only after their bundle
   is valid, i.e., exactly one step after they think they're done.
3. **Wall A** (staged closure emit cost) — still open, still
   unmeasurable behind (2).
4. **Countdown collapse / Wall B** — A2's record-lowering work
   (`dea32c0`) keeps a14 at 4 on both combined and A2-own; the
   oscillation table from last round extends (cost never came back
   down in `c9751e5`).

## Gate suggestion, extending the report lane's

The report lane proposes adding `test_a14_c23` to A1's pre-push (7s
fail signal for an invalid bundle — correct). My addition: **a14 alone
does not see blocker 2** (its harness registers `emit_c23` directly,
bypassing `pep_c23.py` validate — a14 ran real tests in the combined
state). The pre-push gate needs **one `pep_c23.py`-path smoke test**
(e.g., `pep_c23.emit(b"fn main() -> Int { return 42 }")`) beside it —
that single call would have exposed the arity drift the moment the
bundle went valid.

## Honest notes

- A1's claims remain true where made (their checker suites do not
  cross bundle/validate/emit).
- A2's claims for `c9751e5` verified on their own branch (32+47 OK).
- Parallel-write gotcha recurred once this round (worktree dir created
  by my own write before `git worktree add`); repaired sequentially —
  no measurement affected.

Replay: corpus/`replay.py`/base untouched — **161/161** current.
