# FINDING BOOT-A3-192 — the two-fallible-operand pattern occurs exactly once in A4's file

**A3-191 fixed `names_equal`. The obvious follow-up was whether the same shape recurs. Across 1,535 lines and 34 functions it occurs
**exactly once** — the line A3-191 already diagnosed and fixed. Nothing else in the file needs it.**

Seed blob `f8f476198f`. A4 `8025f7c8` source.

## What I searched for, and why the obvious pattern was wrong

My first sweep looked for lines with two or more fallible builtin calls and found **16** — every `is_*` matcher qualifies
(`byte_at(source, o) == 102 && byte_at(source, o + 1) == 110 && …`). But those functions **build**, so call count is not the
pattern.

The real shape is **a call on both sides of one operator**, where C must choose which to evaluate first:

```
call(...)  OP  call(...)
```

Across comparisons and arithmetic alike: **1 occurrence**.

| function | line | expression |
|---|---|---|
| `names_equal` | 704 | `byte_at(source, a1 + k) == byte_at(source, b1 + k)` |

That is the line A3-191 diagnosed. Its fix is verified and it is the only one.

## Why the matchers are safe

In `is_fn2`'s condition each `byte_at(...)` is compared against a **literal** (`== 102`), not against another call. Several calls
joined by `&&` are sequential in C's short-circuit order — the ambiguity the emitter refuses requires two fallible operands in a
**single** binary operation.

`find_brace` L300/L304/L308 do combine three calls in one condition (`is_str3`, `is_ws_at`, `expect_byte`), but joined by `&&`, and
they build once the Bool-local rewrite is applied (A3-148).

## Consequence

**Blocker 2 is fully cleared by one fix.** A4 does not need to hunt for a family of these; there is one. That is worth stating because
a pattern search that returns one hit is the answer someone hesitating over a large refactor needs.

## Limits

- One revision. If A4 adds code the pattern may reappear; the sweep is four lines of regex and cheap to repeat.
- Regex over source text, not the checked AST. It cannot see a two-call expression split across lines — I checked the file's
  conditions are single-line, but a future multi-line one would evade this sweep.
- "Fallible" here means the emitter's notion, inferred from observed refusals rather than read from its analysis. I identified the
  rule by experiment (A3-191's three variants), not from the emitter source.

REF GH #16. Completes the follow-up named in `6729534712` (A3-191).