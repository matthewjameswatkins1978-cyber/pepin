# ACCEPT BOOT-A3-142 — first true seed differential: emitted C matches the seed on all 512 byte-value inputs

**Every semantic check in this lane so far has rested on expectations I derived by reading Pep source. This one does not. `is_ws`
and `is_digit` take `Int`, so the seed can execute them — and across all 256 possible byte values, for both functions, the
emitted C agrees with the seed's own answers: **512 comparisons, zero mismatches, clang and gcc.**

Seed blob `f8f476198f`. A2 `e07e278f`. A1 host `07af079d`. Unmodified lanes; probes and scratch deleted after.

## Result

```
clang  lines=512 mismatches=0
gcc    lines=512 mismatches=0
```

| function | seed's true set | emitted C |
|---|---|---|
| `is_ws` | `9, 10, 13, 32` | identical |
| `is_digit` | `48 … 57` | identical |

The seed's answers were produced by running `compiler_a.pep` with 256 top-level `say(int_text(is_ws(i)))` statements appended
(0.7 s, exit 0, 256 lines), and the same for `is_digit`. The C side is the assembled build printing the same 512 values.

## Why this is stronger than everything before it

- **Independent implementation, not my reading.** The seed interprets the Pep; the emitter lowers it to C; two different engines
  arrived at the same answer 512 times. My hand-derived expectations in A3-139–141 were only ever as good as my reading of the
  source — this removes that dependency entirely.
- **Exhaustive, not sampled.** All 256 possible `Int` inputs for each function, so there is no unchosen case left. `is_ws` in
  particular is where an off-by-one in the `32/9/10/13` comparison chain would surface, and it does not.
- **It also independently confirms my own earlier derivation.** A3-139's hand-derived `is_ws`/`is_digit` behaviour and this
  seed run agree, so the oracle I used for the `SourceBytes` functions is corroborated on the two functions where both methods
  are available.

## The bound, stated plainly

Only two of the twenty-one functions are seed-executable. The other nineteen take `SourceBytes`, and `source_bytes()` is
host-gated in run mode:

```
PEP_RUNTIME_SOURCE_CONTEXT: source_bytes is available only for a host-authorised v2 semanticTarget
```

So this exhaustive, independent oracle applies to exactly the two `Int → Int` matchers. For the nineteen `SourceBytes`
functions the oracle remains source-derived, as A3-139–141 state. That asymmetry is the campaign's input-access wall
(A3-073/074) reaching into verification: **if input were reachable, the whole compiler could be differentially tested against
the seed rather than read by hand.**

## Cumulative semantic verification

| function | method | coverage |
|---|---|---|
| `is_ws`, `is_digit` | **seed differential** | exhaustive, 256 values each |
| `skip_ws`, `scan_digits`, `find_fn`, `find_parens`, `is_main4`, `is_bool4`, `is_unit4`, `find_ds`, `check_tail` | source-derived expectations | 28 calls, both toolchains |
| `is_ws_at` | whole-unit control | 2 calls |

Fifteen of twenty-one functions have now been executed and checked. `find_brace` and `main` remain unassembled, gated on A2's
`parentId` index; the four `expect_byte`/`is_fn2`/`is_int3`-family units are covered by the same builds but not individually
asserted.

## What this does not establish

- **No M-1 claim.** `main` is not in this build; nothing reads Pep input or emits C for an unseen source.
- 19 of 21 functions still have no independent oracle; their correctness rests on my reading.
- One emitter pin, one driver pin, one seed; mixed lanes, not a merged tree.

## Reproduce

Append 256 `say(int_text(is_ws(i)))` statements to `compiler_a.pep` and `pep.ps1 run` it; assemble the build as in A3-138 and
print `pep_fn_is_ws(i)` for `i` in 0..255; diff the two 256-line outputs, then repeat for `is_digit`.

REF GH #16. Parents: `6726265019` (A3-141), `6726221333` (A3-139), and the input-wall findings `6728523193`/`6728533491`.