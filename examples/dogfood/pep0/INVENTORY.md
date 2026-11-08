# Own-source static inventory (A4 lane, R3 — description only, no claim)
Status: independently verified to the node by A3 (BOOT-A3-087:
12/12 kinds, 8/8 operators, totals exact) — treat as verified fact.

Source: `compiler_a.pep` rev-3 (`d78735e`). Counts scripted
(`_build/r2/inventory.py`, `_build/r2/astc.py`; scratch, not committed);
AST via seed `inspect --json`.

## File totals

511 lines (477 code, 12 comment, rest blank), 9639 bytes, 21 functions,
44 parameters, 55 `var`, 21 `return` sites (AST).

## Source-measured construct counts

| construct | count | note |
|---|---|---|
| `==` | 139 | dominant predicate |
| function/builtin calls | 112 (AST) | `byte_at` 31, `byte_length` 14, `say` 14, `skip_ws` 12, `expect_byte` 10 |
| `if` / `if_statement` | 84 | filled-then + empty-else idiom |
| `&&` | 67 | matchers + guards |
| `+` | 52 | offsets, accumulators |
| assignments | 87 (AST) | incl. `var` initializers |
| `<=` | 18 | bound guards |
| `-` (binary) | 17 | sentinels (`0 - 1`), offsets |
| `\|\|` | 3 | `is_ws`, `is_digit` only |
| `while` | 3 | `skip_ws`, `scan_digits`, `parse_value` |
| `*` | 1 | `parse_value` (`v * 10`) |
| `/` (division) | 0 | none in source |
| string literals | 8 | all in `say` args (`main` + finders) |
| integer literals | 293 (AST) | mostly byte codes + small consts |

## AST node census (seed, 1387 nodes)

`name` 348, `binary` 297, `int` 293, `call` 112, `assignment` 87,
`if_statement` 84, `var` 55, `Int` 25, `function` 21, `return` 21,
`SourceBytes` 19, `expression` 14, `string` 8, `while` 3.

Type-mention rule: `Int` 25 / `SourceBytes` 19 count parameter
annotations only (25+19=44 params); including the 21 `Int` returns,
all mentions are Int 46, SourceBytes 19. Total reconciles as
1343 kind-nodes + 44 param-type annotations = 1387.

Counting rule: keyed walk (dicts carrying a type/kind/node string
field); raw dict count is 4161. A1's sectional parse counts 1452 (every
`FlatAstNode` incl. params, type scalars, separators) on the same blob
`ca732536`; per-function subtotals agree exactly (main 222, find_brace
288, find_fn 101, find_ds 122, find_parens 82, check_tail 66). Cite
per-function counts when precision matters.

Tri-lane bridge (A1 corroboration): 1343 kind-nodes + 44 `parameter`
nodes + 65 `type_scalar` nodes = 1452; the 65 are exactly the 65 type
mentions (46 `Int` + 19 `SourceBytes`).

## S0-gap ordered by frequency (extension economics, not a proposal)

`==`/calls/`if`/`&&`/`var`/params first; `while` (3), `*` (1),
strings (8) last. Full own-source needs all rows — consistent with the
OWN_SOURCE.md ladder R1–R7.

## Cross-checks absorbed this turn

- A3 BOOT-A3-078: `/`-divisor narrowing hazard needs a `/` in source;
  count is **0**, so no EXPECTED pin changes. Prepend/byte-identity
  results do not touch A4 artifacts.
- A1 subset cross-check: AGREEMENT with PEP0_SUBSET.md, no correction.
- A1 oracle ingest: R1 fixtures absorbed, 18/18 green.

## Whole-chunk checkability (measured by A3, BOOT-A3-083)

Independent whole-chunk CHECK on rev-3 source (blob `ca732536`):
10/21 valid (all <=41 nodes), 11 step-limited (all >=48). Sharp
boundary between 41 and 48 nodes; identical at `1885566`/`bea071a`.
Node counts per fn: is_digit 18, is_ws 26, is_ws_at 26, expect_byte 27,
is_fn2 33, parse_value 34, is_int3/is_ret3/is_str3/is_urn3 41,
skip_ws/scan_digits 48, is_main4/is_bool4/is_unit4 49, check_tail 66,
find_parens 82, find_fn 101, find_ds 122, find_brace 288, main 222.
Stage note: whole-chunk CHECK differs from A1's chain path (21/21)
and from sectional EMIT (9/21) — three stages, three numbers, no
conflict. Binding constraint per A3: the 100k-step budget.
