# ACCEPT BOOT-A3-101 — A2-S1 independently verified: cross-chunk calls in conditions and initialisers work, correctly, with no regression

**Verdict: A2's `7e820a7f` cross-chunk fix **works and is correct**. `is_ws_at` now emits, emission moves **9/21 → 10/21**,
three behavioural fixtures I built for the exact shapes compile under **both** strict clang and gcc and produce correct
input-dependent output, all three previously-proven lowerings are still **byte-identical**, and the fail-closed layering is
intact. The 146-line emitter change disturbed nothing.**

## 1. The blocker is gone

| function | `bea071a` | `7e820a7f` |
|---|---|---|
| `is_ws_at` (26 nodes, the `is_ws(byte_at(...))` in a condition) | `Pep C23 calls require a known target` | **EMITTED (406 bytes, 58,008 steps)** |

`PARTIAL RESULT: 10/10 check-valid functions emit` (was 9/10). Total emission **10/21** (was 9/21).

## 2. My forecast from A3-085 held exactly

A3-085 predicted the `user_fn(builtin(...))` condition shape occurs in **three** functions — `is_ws_at`, `skip_ws`,
`scan_digits` — so one fix should cover all three, and that `skip_ws`/`scan_digits` would remain blocked by the step wall
rather than by the call target. Confirmed: `is_ws_at` emits; `skip_ws` and `scan_digits` are still
`PEP_RUNTIME_STEP_LIMIT` at 48 nodes. A2-S1 did what it should and no more.

## 3. No regression — the previous proofs still hold byte for byte

A 146-line change to `tests/pep_c23_emitter.pep` (`da31bd1b` → `fff87963`) could easily disturb unrelated lowering. It
did not:

| fixture | lowerings | C sha256 @ `1885566` | @ `7e820a7f` | identical |
|---|---|---|---|---|
| `d_a_byte_builtins.pep` | `byte_at`, `byte_length`, `utf8_slice` | `7D4AE57B7373…` | `7D4AE57B7373…` | **yes** |
| `d_b_int_text.pep` | `int_text` | `B234213E1076…` | `B234213E1076…` | **yes** |
| `d_c_arith.pep` | binary `+ * <=` | `5215C9F63D60…` | `5215C9F63D60…` | **yes** |

## 4. Behavioural correctness, not just "it emits"

Emitting is not the same as computing the right thing, so three fixtures were compiled and **run** under strict clang and
gcc with two differentiating inputs (a file starting `0x01`, and one starting `'a'`):

| fixture | shape | clang | gcc |
|---|---|---|---|
| `x_crosscond_var.pep` | helper call in a condition, local argument | `HIT` on `0x01`, nothing on `'a'` | same |
| `x_crosscond_builtin.pep` | **the `is_ws_at` shape**: `a3_is_one(byte_at(source, 0))` in a condition | `HIT` on `0x01`, nothing on `'a'` | same |
| `x_crossinit_builtin.pep` | cross-chunk call in a **var initialiser**, builtin argument | `8` for a 4-byte input | same |

All four builds clean with `-std=c23 -Wall -Wextra -Wpedantic -Werror`, and every run produces the arithmetically correct
answer. The condition genuinely discriminates on input bytes, which is what a correct lowering of a cross-chunk call in a
condition must do.

## 5. Fail-closed layering intact

`y_missing_callee.pep` (calls a function that does not exist) → `PEP_UNKNOWN_FUNCTION`; `y_arity_mismatch.pep` (two
arguments to a one-argument function) → `PEP_ARGUMENT_COUNT`. Both refused at **host analysis, before emission**, so the new
code path cannot be reached with a bad call. Honest scope: these verify the *layering*, not an emitter-internal guard — the
emitter-internal guard is the one `is_ws_at` used to trip, and the fix exercises it.

## 6. All six lane gates still green at the new pin

```
A4 oracle replay (13 pins)      PASS
A4 normative boundary (17)      PASS
A1 semantic oracle (23)         PASS
A1 sectional merge (11 probes)  PASS
A2 DIVERGENCE-2 (16)            PASS
M-1 gate calibration            PASS
6 gate(s) ran, 0 failed, 0 skipped — ALL GATES GREEN
```

## What this does not change

**M-1 is still blocked.** 11 functions remain step-limited, and `main` is one of them, so no compiler A can be built. A2-S1
removed one of two walls; the other (statement-granular emission, A2-S2/A1-S2) is untouched. Emission is 10/21, and a
C build needs `main`.

Also, for the record: emission step costs at this pin are ~30 steps higher than BOOT-A3-100 reported for `bea071a`
(`is_int3` 90,354 → 90,384), a small constant overhead from the new code. A3-100's figures are correct for `bea071a`;
anyone re-using them against `7e820a7f` should re-measure or add ~30.

## Limits

- Correctness is demonstrated on **three** hand-built shapes with **two** inputs each. That is a proof of the mechanism, not
  exhaustive coverage of every call position the fix touches (A2 also changed var initialisers and, per their commit,
  transitive chains I did not exercise).
- I did not run A2's own `tests/test_c23_cross_chunk_condition.py` (225 lines); my verification is independent of it by
  design, and theirs may cover positions mine does not. Both together are stronger than either.
- Behavioural tests use `int_text`/`say` and small functions, so they say nothing about cross-chunk calls inside loops
  (`skip_ws`/`scan_digits` are still unschedulable).
- One source (`ca732536`), one seed.

## Reproduce

```
PEPIN_GATE_ROOT=<worktree at 7e820a7f> PEPIN_APP_REL=examples/dogfood/pep0/compiler_a.pep \
  PEPIN_APP_REV=5f62e4b PEPIN_UNITS_ONLY=1 PEPIN_STEPS=1 python verification/probes/emit_any_049.py
PEPIN_GATE_ROOT=<worktree at 7e820a7f> PEPIN_APP_REL=verification/fixtures/emit/x_crosscond_builtin.pep \
  PEPIN_APP_REV=<fixtures sha> PEPIN_RUN_FIXTURES=<one.bin>;<abc.bin> python verification/probes/emit_any_049.py
```

REF GH #16. Emitter A2 (`7e820a7f`), independent verification A3.