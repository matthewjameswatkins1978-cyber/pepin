# ACCEPT BOOT-A3-143 — per-function coverage complete: 19 of 21 functions executed and correct, 19/19 assertions both toolchains

**The last seven unexecuted functions now pass: `is_fn2`, `is_int3`, `is_ret3`, `is_urn3`, `is_str3`, `expect_byte`, `parse_value`
— 19 assertions, zero mismatches, exit 0 under clang and gcc. With this, every function that can be assembled for `compiler_a`
has been executed and checked. Only `find_brace` and `main` remain, both gated on A2's `parentId` index.**

Seed blob `f8f476198f`. A2 `e07e278f`. A1 host `07af079d`. Unmodified lanes; harness generated into scratch, deleted after.

## Result

```
--- clang exit=0 ---   TOTAL MISMATCHES: 0 of 19
--- gcc   exit=0 ---   TOTAL MISMATCHES: 0 of 19
```

Coverage added by this run:

| function | assertions |
|---|---|
| `is_fn2` | `"fn"`→1, `"f"`→0 (too short), `"xfn",1`→1 |
| `is_int3` | `"Int"`→1, `"int"`→**0** |
| `is_ret3` | `"ret"`→1, `"re"`→0 |
| `is_urn3` | `"urn"`→1, `"ur"`→0 |
| `is_str3` | `"Str"`→1, `"str"`→**0** |
| `expect_byte` | match→1, wrong byte→0, out-of-range→0, `'}'`/125→1 |
| `parse_value` | `"42"`→42, `"123x",0..3`→123, `"0"`→0, empty range→0 |

## Three properties worth naming

**Every type-word matcher is case-sensitive and rejects the lowercase form**: `is_int3("int")=0`, `is_str3("str")=0`, and from
A3-141 `is_bool4("bool")=0`, `is_unit4("unit")=0` while `is_main4("main")=1`. So the compiler distinguishes `Int`/`Str`/`Bool`/`Unit`
(type words, capitalised) from `main`/`fn`/`return` (keywords, lowercase) exactly as Pep requires — and all four matchers are
verified independently.

**`parse_value` does arithmetic across a loop**: `v = v * 10 + (byte_at(source, i) - 48)`. Digits `"42"`→42 and `"123x"` in range
`0..3`→123 both land, so fragment/unit emission preserves integer arithmetic with a loop-carried accumulator. The empty range
`0..0` returns `0`, not garbage.

**`expect_byte` bounds-checks before reading**: `"A"` at offset `1` returns `0` because `o + 1 <= byte_length` fails, rather than
reading past the end. A missing bounds guard here would have been a genuine memory defect, and it is present and working.

## Full coverage tally — 19 of 21

| function | method | source of verification |
|---|---|---|
| `is_ws`, `is_digit` | **seed differential, exhaustive** | A3-142 (256 values each) |
| `is_ws_at` | whole-unit control | A3-139 |
| `skip_ws`, `scan_digits` | source-derived | A3-139 |
| `find_fn`, `find_parens` | source-derived | A3-140 |
| `is_main4`, `is_bool4`, `is_unit4`, `find_ds`, `check_tail` | source-derived | A3-141 |
| `is_fn2`, `is_int3`, `is_ret3`, `is_urn3`, `is_str3`, `expect_byte`, `parse_value` | source-derived | this receipt |
| `find_brace`, `main` | **not assembled** | gated on A2's `parentId` index |

**Every assemblable function in `compiler_a.pep` has now been executed and checked against a stated oracle.** Of these, 2 are
verified exhaustively against the seed's own interpreter, 17 against expectations derived from the Pep source.

## What this does not establish

- **No M-1 claim.** `find_brace` and `main` are absent from the build, so nothing reads Pep input or emits C for an unseen
  source.
- The seventeen source-derived checks are only as good as my reading of the Pep. A3-142 is the only independent oracle, and only
  two functions admit it because `source_bytes()` is host-gated in run mode.
- Assertions are chosen cases, not exhaustive, for the seventeen. `expect_byte` was checked at one boundary; a fuller test would
  sweep offsets across the length.
- One emitter pin, one driver pin, one seed; mixed lanes, not a merged tree.

## Reproduce

Assemble as in A3-138, omit gapped functions, append a harness that builds `pep_source_bytes` over literal byte arrays and
asserts each call against the value its Pep source implies.

REF GH #16. Parents: `6726287172` (A3-142), `6726265019` (A3-141), `6726240063` (A3-140), `6726221333` (A3-139).