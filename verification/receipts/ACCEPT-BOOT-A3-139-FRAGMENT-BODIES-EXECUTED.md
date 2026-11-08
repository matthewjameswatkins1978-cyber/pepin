# ACCEPT BOOT-A3-139 — fragment-assembled function bodies compute correctly, including `while` loops

**Fragment-assembled functions have only ever been shown to *compile*. I executed them. `skip_ws` and `scan_digits` — both
fragment-assembled, both containing `while` loops with mutable state carried across fragment boundaries — produce exactly the
values the Pep source implies, under clang and gcc.**

Seed blob `f8f476198f`. A2 `e07e278f`. A1 host `07af079d`. Unmodified lanes; harness generated into scratch, deleted after.

## Result

| call | expectation from source | clang | gcc |
|---|---|---|---|
| `skip_ws("  ab", 0)` | `2` | **2** | **2** |
| `skip_ws("\n\n", 0)` | `2` (all whitespace → `n`) | **2** | **2** |
| `scan_digits("123x", 0)` | `3` | **3** | **3** |
| `is_ws_at(" ab", 0)` | `1` | **1** | **1** |
| `is_ws_at(" ab", 1)` | `0` | **0** | **0** |

Five of five, both toolchains, exit 0. A 23,879-byte C file built from `header + prototypes + 10 whole units + 9 fragment-assembled functions + a harness`.

`is_ws_at` is a whole-unit function and serves as a control — it is correct, so the harness itself is sound.

## Why this is not a trivial result

`skip_ws` and `scan_digits` are exactly the shape fragmentation was invented for and the shape nobody had executed:

```pep
fn skip_ws(source: SourceBytes, o: Int) -> Int {
  var i = o
  var n = byte_length(source)
  var pos = o
  var f = 0
  while i + 1 <= n {
    if is_ws(byte_at(source, i)) == 1 { i = i + 1 }
    else { pos = i  f = 1  i = n }
  }
  var out = n
  if f == 1 { out = pos } else {}
  return out
}
```

Eight top-level statements, and each was emitted as a **separate fragment** and reassembled. So this run verifies:

- **mutable locals carried across fragment boundaries** (`i`, `pos`, `f`, `out` are declared in one fragment and mutated in
  later ones — the carried-binding machinery working on genuine state, not a toy);
- **`while` loop lowering inside a fragment** — the loop body assigns two different mutable targets, which is the shape A3-131
  showed costs the most;
- **the all-whitespace path**, which exercises the `f == 0` branch where `out` stays `n` rather than `pos` — the branch a
  straight-line test would never reach.

The second row (`"\n\n"`) is the one I would have got wrong by guessing: it returns `n = 2`, not `0`, because the loop exits on
`i + 1 <= n` failing without ever setting `f`. That is why I derived expectations from the source rather than assuming.

## Method, and its honest limit

The seed cannot execute these functions: `source_bytes()` is host-gated in run mode
(`PEP_RUNTIME_SOURCE_CONTEXT: source_bytes is available only for a host-authorised v2 semanticTarget`, the same wall as
A3-073/074). So the oracle here is **the Pep source read by hand**, not the seed:

- `is_ws` matches 32/9/10/13 only;
- `skip_ws` returns the index of the first non-whitespace byte, or `n` if the remainder is all whitespace;
- `scan_digits` is the same shape for digits;
- `is_ws_at` is `1` iff `o + 1 <= n` and the byte at `o` is whitespace.

That is weaker than a seed differential. It is still much stronger than "it compiles", and for these five cases the semantics
are unambiguous enough that a mismatch would have meant a real defect.

## What this does not establish

- **No M-1 claim.** `main` and `find_brace` are omitted from this build; nothing reads Pep input or emits C.
- Five calls into three functions. `find_fn`, `find_parens`, `find_ds`, `check_tail`, `is_main4`, `is_bool4`, `is_unit4` are
  assembled but unexecuted — their inputs are multi-byte source shapes I did not construct.
- No `match`, record, or union-taking fragment-assembled function was executed; this source has none.
- One emitter pin, one driver pin, one seed.

## Reproduce

Assemble `header + prototypes + units + fragment-assembled bodies` as in A3-138, omit functions with fragment gaps, and append a
`main` that builds `pep_source_bytes` values over literal `unsigned char` arrays and prints the calls above.

REF GH #16. Parents: `6726190175` (A3-138, the assembly scaffold), `6726161829` (A3-137), `6725863459` (A3-131 on loop-body cost).