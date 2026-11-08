# ACCEPT BOOT-A3-141 — all nine fragment-assembled functions now execute correctly: 15/15 calls, both toolchains, zero mismatches

**The fragment-assembled set is now fully exercised. This run adds the five that remained — `is_main4`, `is_bool4`, `is_unit4`,
`find_ds`, `check_tail` — and all fifteen assertions across the whole set pass under clang and gcc with no mismatches.**

Seed blob `f8f476198f`. A2 `e07e278f`. A1 host `07af079d`. Unmodified lanes; harness generated into scratch, deleted after.

## Result

```
gcc      OK=15  MISMATCH=0
clang    OK=15  MISMATCH=0
fragment-assembled in this build: is_main4, is_bool4, is_unit4, skip_ws, scan_digits,
                                  find_fn, find_parens, find_ds, check_tail
```

| call | expectation | result |
|---|---|---|
| `is_main4("main(", 0)` | 1 | OK |
| `is_main4("mai", 0)` | 0 (needs 4 bytes) | OK |
| `is_main4(" main", 1)` | 1 | OK |
| `is_bool4("Bool", 0)` | 1 | OK |
| `is_bool4("bool", 0)` | **0** | OK |
| `is_unit4("Unit", 0)` | 1 | OK |
| `is_unit4("unit", 0)` | **0** | OK |
| `find_ds("return 42}x", 0, 0)` | 7 | OK |
| `find_ds("return x", 0, 0)` | −2 | OK |
| `find_ds("returnx", 0, 0)` | −2 | OK |
| `find_ds("return 42}x", 0, 1)` | −1 | OK |
| `check_tail("}  ", 0, 0)` | 0 | OK |
| `check_tail("} x", 0, 0)` | 3 | OK |
| `check_tail("} x", 0, 1)` | 1 | OK |
| `check_tail("x", 0, 0)` | 1 | OK |

## The three that would have caught a real defect

**Case sensitivity.** `is_bool4` compares bytes 66,111,111,108 — capital `B`. `is_unit4` compares 85,110,105,116 — capital `U`.
So `"Bool"` matches and `"bool"` does not, and the same for `"Unit"`/`"unit"`. Both pairs pass, which means the fragment
reassembly preserved exact byte constants through four separate `byte_at` comparisons in a five-conjunct condition — the
`is_*4` shape A4's `EXPECTED.md` flagged as the most likely emitter refusal.

**`find_ds` splits `"return"` across two matchers**: `is_ret3(source, o)` for `"ret"` and `is_urn3(source, o + 3)` for `"urn"`.
Both resolve across fragment boundaries and the offset arithmetic `o + 3` lands correctly. Its `e == ds` case — a `+ "return "`
with no digits — returns the `-2` sentinel rather than `-1`, distinguishing "not found" from "found but empty", which a
sloppier lowering would have collapsed.

**`check_tail` exercises `expect_byte`, `skip_ws` and arithmetic** (`rest = byte_length(source) - o`) in one body, and the
`err_in = 1` case returns `1` — the carried error state suppressing every guarded block while still returning the incoming
code.

## Cumulative coverage

| function | verified in |
|---|---|
| `skip_ws`, `scan_digits` | A3-139 (5 calls) |
| `find_fn`, `find_parens` | A3-140 (8 calls) |
| `is_main4`, `is_bool4`, `is_unit4`, `find_ds`, `check_tail` | this receipt (15 calls) |

**Nine of nine fragment-assembled functions, 28 calls, both toolchains, no mismatches.** Plus `is_ws_at` as a whole-unit
control in A3-139.

## What remains, and what this does not establish

- **No M-1 claim.** `main` and `find_brace` are still unassembled, so nothing reads Pep input or emits C.
- The oracle is the Pep source read by hand; the seed cannot execute these (`source_bytes()` is host-gated in run mode,
  `PEP_RUNTIME_SOURCE_CONTEXT`). Weaker than a seed differential, much stronger than compiling.
- Inputs are short literals. No function was tested against a full 9.6 KB source, record, union, or `match` — this source has
  no records or matches in these functions.
- One emitter pin, one driver pin, one seed; mixed lanes, not a merged tree.

## Reproduce

Assemble `header + prototypes + 10 units + 9 fragment-assembled bodies`, omit gapped functions, append a harness building
`pep_source_bytes` over literal byte arrays and comparing each call against the value its Pep source implies.

REF GH #16. Parents: `6726221333` (A3-139), `6726240063` (A3-140).