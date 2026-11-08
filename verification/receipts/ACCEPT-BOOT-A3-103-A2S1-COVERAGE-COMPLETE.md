# ACCEPT BOOT-A3-103 — A2-S1 completes: transitive A→B→C chain is arithmetically correct, and no unknown call slips into the new positions

**Verdict: A2-S1's remaining claims hold. A transitive three-function chain reached from a condition emits, compiles under both
strict compilers, and produces the **arithmetically correct input-dependent** result — not merely emitted C. And the two
positions A2-S1 newly added lowering for do **not** accept a call whose target does not exist or whose argument types are
wrong: both are refused upstream.**

## 1. Transitive chain — the values are right, not just the shape

`x_transitive.pep`: `main` → `a3_b` → `a3_c`, all cross-chunk, result tested in a condition.

```pep
fn a3_c(x: Int) -> Int { return x + 1 }
fn a3_b(x: Int) -> Int { let y = a3_c(x)  return y }
fn main(source: SourceBytes) -> Int {
  let n = byte_length(source)
  let r = a3_b(n)
  if r == 5 { say("CHAIN") } else { }
  return 0
}
```

| input | `n` | `a3_b(n)` | expected | clang | gcc |
|---|---|---|---|---|---|
| 4 bytes (`abcd`) | 4 | 5 | `CHAIN` | `CHAIN` | `CHAIN` |
| 5 bytes (`abcd\n`) | 5 | 6 | silent | silent | silent |

Both builds clean under `-std=c23 -Wall -Wextra -Wpedantic -Werror`. The branch discriminates on input length and the chain
propagates `n + 1` correctly through two cross-chunk hops, so the nested call is not merely lowered — it is lowered in the
right order with the right argument.

## 2. No accidental acceptance in the positions A2-S1 added

The risk of adding lowering to conditions and var initialisers is that a call in the *new* position bypasses resolution. It
does not:

| fixture | shape | verdict |
|---|---|---|
| `y_unknown_in_condition.pep` | `if a3_nobody(byte_at(source, 0)) == 1` — undefined function, in a **condition**, with a builtin argument | `PEP_UNKNOWN_FUNCTION` |
| `y_wrong_arg_type.pep` | `if a3_is_one("text") == 1` — right name, right arity, wrong argument type, in a **condition** | `PEP_TYPE_MISMATCH` |

Both refused at host analysis, before emission, so the new path is unreachable with a bad call. Together with A3-101's
missing-callee and arity cases, A3-S1's "no accidental acceptance of unrelated unknown calls" is now covered in both the
old and the new positions.

## 3. My own error first, before calling anything a defect

On the first run the chain printed **no** `CHAIN`, and I treated silence as a possible lowering defect. It was my input: I
passed a 5-byte file while the discriminant `r == 5` corresponds to a 4-byte one, so `r` was legitimately 6. I re-checked
the arithmetic, corrected the input, and got `CHAIN`. Recorded because "the emitter produced no output where I expected
output" is exactly how a verifier manufactures a false finding — the arithmetic had to be done before the verdict.

## 4. A4 absorbed three A3 findings this turn

`06592dd` fixes the `boolop` total `20 → 18` (BOOT-A3-092), `7e8dd50` folds the step-cost rule into the checkability section
(A3-099), and `946d9b6` qualifies emission cost (A3-100). All three of my corrections landed in A4's documents, and
`compiler_a.pep` is still blob `ca732536`, so every 21-function figure remains valid.

## Limits

- Transitive coverage is **three** functions in one chain, one call site. Deeper chains, chains through var initialisers,
  and chains involving three different result types are untested.
- The negatives are host-analysis refusals, which proves the layering rather than an emitter-internal guard. The
  emitter-internal guard was exercised by `is_ws_at` in A3-101.
- Both new fixtures are small (19 and 22 nodes); they say nothing about these shapes inside loops, where `skip_ws` and
  `scan_digits` remain blocked by the step wall.
- One source (`ca732536`), one emitter pin (`7e820a7f`), one seed.

## Reproduce

```
PEPIN_GATE_ROOT=<worktree at 7e820a7f> PEPIN_APP_REL=verification/fixtures/emit/x_transitive.pep \
  PEPIN_APP_REV=<fixtures sha> PEPIN_RUN_FIXTURES=<4-byte file>;<5-byte file> \
  python verification/probes/emit_any_049.py
```

REF GH #16. Emitter A2 (`7e820a7f`); independent verification A3. Completes A3-S1's stated coverage.