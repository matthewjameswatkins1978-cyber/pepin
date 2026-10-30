# Refinement — recursion contract at A1 `fd5c5d5`: behavior change, NOT a safety gap (with decisive runtime evidence)

**Status:** refines `FINDING-a14-stale-expectations-fd5c5d5.md`. The
external report `pep/c23-real-lexer-execution-report@80cf4d9` argued the
recursion test is "a legitimate test, not a stale one." It is right on the
contract point and this receipt concedes it with evidence; my prior
"stale" framing was imprecise for failure 2. Failure 1 (the `length`
exemplar) stays stale — both reviews agree. No safety gap exists in
either direction; that is now proven end-to-end, including the arm
neither prior report covered.

## A/B: exact behavior pre-merge (`e9abcd7`) vs post-merge (`fd5c5d5`)

Emit-stage probe, same four programs, both heads (detached read-only):

| program | `e9abcd7` (pre) | `fd5c5d5` (post) |
|---|---|---|
| `loop()` zero-arg infinite | `unsupported`, empty parts, diag **ends `"; recursive calls are unsupported"`** | `unsupported`, empty parts, recursion clause **gone** ("zero-argument calls require a call-free scalar result, …") |
| `loop(value)` param infinite | `unsupported`, empty parts, diag "one-parameter calls require one argument and a call-free target expression" (**no recursion wording even pre-merge**) | **`emitted`** |
| `countdown(510)` guarded | `emitted` | `emitted` |
| `countdown(511)` guarded | `emitted` | `emitted` |

Suite confirmation: `tests.test_a14_c23` = **11/11 OK at `e9abcd7`**
(rerun this turn), **9/11 at `fd5c5d5`** — the two failures are
introduced *exactly* by the merge commit, matching the external report's
sweep. So the regression window is precisely `fd5c5d5`.

## The decisive new arm: what does the emitted binary DO when it compiles?

Neither my first receipt nor the external report ran this. The report
stops at "no bad binary is produced — the compile fails" (strict flags).
I compiled the emitted param-infinite C under **both** flag sets and ran
it, alongside the reference interpreter, on the same program
(`fn main() -> Int { return loop(2) } fn loop(value: Int) -> Int { return loop(value) }`):

| arm | clang 23.1.4 | gcc 16.2.0 | reference interpreter |
|---|---|---|---|
| strict (project flags: `-std=c23 -Wall -Wextra -Wpedantic -Werror -O2`) | compile **FAIL**, `-Winfinite-recursion` (no binary) | compile **FAIL**, `-Werror=infinite-recursion` (no binary) | n/a |
| lenient (`-std=c23 -O1`, no warning flags) | runs, **rc=1, stderr `PEP_RUNTIME_CALL_DEPTH`** | runs, **rc=1, stderr `PEP_RUNTIME_CALL_DEPTH`** | rc=1, stderr `2:37: PEP_RUNTIME_CALL_DEPTH: Maximum function call depth exceeded` |

**The lenient native binaries terminate with exactly the interpreter's
error code and exit status.** The emitted `pep_enter` depth guard (512)
fires; nothing hangs, nothing corrupts, no wrong result is possible. So
the emission is *reference-faithful at runtime* — the interpreter itself
accepts this program as `valid` (`pep.ps1 check` → `status=valid`, no
diagnostics) and fails it at runtime with `PEP_RUNTIME_CALL_DEPTH`;
post-merge native does the same.

## What remains genuinely wrong (agreeing with the report)

1. **Diagnostic quality under the project's own flags.** With strict
   flags the user sees a raw clang/gcc error, not a Pep diagnostic. The
   Pep-native path (`run-c23`, the a14 harness) compiles with
   `-Werror`, so this is what users actually get. Pre-merge they got a
   Pep diagnostic at emit time.
2. **Zero-arg diagnostic lost its recursion clause** (report's
   Regression 2; I previously downgraded it to "wording" — it is a
   precision regression: a compiler author is told about
   zero-argument calls, not about recursion).
3. **The test guards a real behavior change, not rot.** My prior
   receipt called both failures "stale expectations." For failure 2
   that was imprecise: `test_recursive_call_is_rejected_before_native_lowering`
   documents pre-merge emit-time rejection with intent in its name, and
   its assertion now fails because *behavior changed in the merge*.
   Whether the new behavior is intended is a builder design decision,
   with the evidence set out here:
   - for accepting emission: the reference interpreter accepts it and
     fails identically at runtime; guarded recursion is a supported
     feature at both heads; emission is reference-faithful;
   - for restoring the guard: pre-lowering rejection gives a Pep
     diagnostic instead of a raw C error, and keeps the emitter's
     supported-subset promise independent of compiler heuristics
     (`-Winfinite-recursion` coverage is compiler-specific — the
     lenient arm shows what a compiler without that warning would do:
     correct depth-guard behavior, so the guard is belt-and-braces,
     not load-bearing).

My recommendation stands as in the original receipt's "suggested builder
action", now with one amendment: updating the test is defensible for the
param case *if* the builders consciously choose reference-faithful
emission; restoring the guard is defensible *if* they want Pep
diagnostics ahead of native lowering. Either way the fix belongs to the
file's owner.

## Corroboration and pin verification (this turn)

- External report independently reproduced my Lean 4 kernel-check claim
  with **identical results** (`lake build` exit 0, `BrokenVariant.lean`
  exit 1, `#print axioms` = `[propext]` only, token hits all prose,
  toolchain hash-checked via the scoop manifest) — third-party
  confirmation of `MODEL_PROVED`.
- A2 new pin `codex/c23-chunked-parser@770efa0` verified:
  `tests.test_c23_str_contains` = **7 tests OK (3 skipped per contract)**;
  the test's own lexer blob assertion `12bd93a1dfc5dba3b1cab49abefffed5e406b17d`
  matches `git rev-parse HEAD:examples/pep_lexer.pep` at that head.
- Report claim `test_c23_str_contains.py` absent at `fd5c5d5`:
  confirmed (`Test-Path` false) — absence, not failure.
- Adversarial replay: **unchanged inputs** (corpus, `replay.py`, base
  `805062b` untouched this turn) — the recorded 161/161 PASS at
  `ede45d8` remains the current result; no re-run adds information.

## No files outside `verification/` touched; no builder test edited.
