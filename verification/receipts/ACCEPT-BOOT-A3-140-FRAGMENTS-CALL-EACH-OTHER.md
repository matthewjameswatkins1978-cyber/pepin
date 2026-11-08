# ACCEPT BOOT-A3-140 — fragment-assembled functions call each other and compute correctly: 8 of 8, both toolchains

**The previous run showed a fragment-assembled body computing correctly in isolation. This one shows them calling *each other*:
`find_fn` invokes `skip_ws`, `is_fn2`, `is_ws_at` and `is_main4` — every one of them also fragment-assembled or unit-emitted —
and all eight calls return exactly what the Pep source implies, under clang and gcc.**

Seed blob `f8f476198f`. A2 `e07e278f`. A1 host `07af079d`. Unmodified lanes; harness generated into scratch, deleted after.

## Result

| call | expectation from source | clang | gcc |
|---|---|---|---|
| `find_fn("fn main() -> Int { return 42 }\n")` | `7` (index of `(`) | **7** | **7** |
| `find_fn("  fn main() {}")` | `9` | **9** | **9** |
| `find_fn("fn main")` | `7` | **7** | **7** |
| `find_fn("")` | `-6` | **-6** | **-6** |
| `find_fn("xx fn main() {}")` | `-1` | **-1** | **-1** |
| `find_parens("()", 0, 0)` | `2` | **2** | **2** |
| `find_parens("()", 0, 1)` | `-1` | **-1** | **-1** |
| `find_parens("( )", 0, 0)` | `3` | **3** | **3** |

Eight of eight, both toolchains, exit 0. 24,227 bytes of C from `header + prototypes + 10 units + 9 fragment-assembled
functions + harness`.

## What this adds over A3-139

- **Cross-function calls resolve between fragment-assembled bodies.** `find_fn` is 14 statements assembled from 14 fragments,
  and it calls `skip_ws` (8 fragments), `is_fn2`, `is_ws_at` and `is_main4` — so this is fragment-assembled code calling
  fragment-assembled code at three depths.
- **Sentinel and error paths work.** `-6` is the "empty source" sentinel set by `err = 6`; `-1` is the default `out` that
  survives when an early check fails. Both come out exactly, so the error-propagation chain of guarded `if err == 0` statements
  — reassembled from separate fragments — behaves as written.
- **`find_parens` with `err_in = 1` returns `-1`**, showing the incoming error state correctly suppresses every subsequent
  guarded block across fragment boundaries.
- **Whitespace skipping inside a call chain**: `find_parens("( )", …)` returns `3` because it calls `skip_ws` between the two
  `expect_byte` checks, which is the second-level call inside a fragment-assembled body.

## Coverage so far

Executed and correct: `skip_ws`, `scan_digits`, `find_fn`, `find_parens` — plus `is_ws_at` as a whole-unit control. Not yet
executed though assembled: `is_main4`, `is_bool4`, `is_unit4`, `find_ds`, `check_tail`; and `find_brace`, `main` remain
unassembled pending A2's `parentId` index.

## Method and its limit, unchanged

The oracle is the Pep source read by hand, not the seed: `source_bytes()` is host-gated in run mode
(`PEP_RUNTIME_SOURCE_CONTEXT`), so the seed cannot execute any of these functions. For `find_fn` the derivation is: skip
whitespace; require `fn`; require whitespace; skip; require `main`; advance four; return the offset, with `-6` for empty input
and `-1` for any failed check. Each of the eight expectations follows directly from that, and two of them (`-6`, `-1`) are the
error sentinels rather than happy-path offsets.

Still weaker than a seed differential, and still much stronger than compiling.

## What this does not establish

- **No M-1 claim.** `main` is omitted from this build; nothing reads Pep input or emits C.
- Five of nine fragment-assembled functions remain unexecuted, and none taking a record, union or `match` was tested — this
  source has none.
- One emitter pin, one driver pin, one seed. Mixed lanes, not a merged tree.

REF GH #16. Parent: `6726221333` (A3-139, the first execution harness).