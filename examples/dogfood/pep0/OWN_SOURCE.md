# Own-source census — compiler_a vs its own Pep-0 subset (A4 lane, S3)

Method: mechanical marker scan per function block (`_build/s1/census.py`;
scratch, not committed) over frozen rev-3 (`d78735e`), spot-checked by
reading. S0 = exactly `fn main() -> Int { return DECIMAL }`.

## Per-function out-of-S0 constructs (21/21 fail S0; 0 exact-S0 shapes)

```
fn             params  SBtype  var  while  if  boolop  arith  calls  strlit
is_ws          1       -       x    -      x   x       -      -      -
is_digit       1       -       x    -      x   x       -      -      -
is_ws_at       2       x       x    -      x   x       x      x      -
is_fn2         2       x       x    -      x   x       x      x      -
is_main4       2       x       x    -      x   x       x      x      -
is_int3        2       x       x    -      x   x       x      x      -
is_ret3        2       x       x    -      x   x       x      x      -
is_urn3        2       x       x    -      x   x       x      x      -
is_str3        2       x       x    -      x   x       x      x      -
is_bool4       2       x       x    -      x   x       x      x      -
is_unit4       2       x       x    -      x   x       x      x      -
expect_byte    3       x       x    -      x   x       x      x      -
skip_ws        2       x       x    x      x   -       x      x      -
scan_digits    2       x       x    x      x   -       x      x      -
parse_value    3       x       x    x      -   -       x      x      -
find_fn        1       x       x    -      x   x       x      x      -
find_parens    3       x       x    -      x   x       x      x      -
find_brace     3       x       x    -      x   x       x      x      -
find_ds        3       x       x    -      x   x       x      x      -
check_tail     3       x       x    -      x   x       x      x      -
main           1       x       x    -      x   x       x      x      x
```

Totals: params 21/21, `var` 21/21, non-literal `return` 21/21, `if`
21/21 (18 with `&&`/`||`; the three without are the loop fns), SourceBytes-typed 19/21, arithmetic 19/21,
cross-fn/builtin calls 19/21, `while` 3/21, string literal 1/21 (main).

## First self-input failure (hand-trace, to confirm natively in S2)

Native A reading `compiler_a.pep`: `find_fn` matches `fn`, skips ws,
then `is_main4` fails on the first definition (`is_ws`) → err 1 →
**exit 1 `ERR shape`**. The program never reaches a second gate. This
is the M-2 attempt oracle: input = canonical source, expected first
observable = exit 1 shape.

Native confirmation gated on statement-granular emission: the trace
depends on `is_main4` (49 nodes) and `main` (222), both step-limited
(BOOT-A3-092). Do not attempt M-2 before that lands, and do not mistake
the cost wall for a semantic failure.

## Extension ladder (minimal rung first; each unlocks the next failure)

- R1 multi-fn skip-to-main (== Slice-3 `pos_twofn`, already planned).
- R2 `main` with a `SourceBytes` parameter (new type word + params).
- R3 `var` + Int params/locals + assignment.
- R4 calls with arguments + builtins (`byte_at`, `byte_length`, `say`,
  `int_text`).
- R5 `if`/`&&`/`||`/comparisons + arithmetic in conditions and bodies.
- R6 `while` loops. R7 string literals.
- Net: full own-source ≈ everything except records/`match` — M-2 needs
  ~full A6-expression Pep, proposed one rung at a time as each failure
  lands. No rung is approved here; each needs its acceptance case.

## Handoff

- A1: M-2 attempt input is the canonical blob; first expected refusal
  above. Oracle/parser coverage unaffected (no S0 change).
- A3: gate the census method (re-run `census.py` logic) rather than the
  table; challenge the hand-trace in S2 with the native run.
