# FINDING BOOT-A3-184 — A4's fallback tier has four distinct blockers, and scan_value is the keystone

**With the A13 workaround applied (annotations) and the driver patch in place, I measured each of A4's new functions in isolation.
Three of the eight now build; the rest fail for four different reasons, none of which is the A13 defect. `scan_value`'s step limit
is inherent to the function and three others depend on it.**

Seed blob `f8f476198f`. A4 `d37bf566` source, annotations applied, driver patch applied, each function built with its own callees.

## The map

| function | lines | result |
|---|---|---|
| `is_var3`, `is_let3`, `is_true4`, `is_fals4`, `is_namech` | 8–20 | **builds** |
| `match_return_ws` | 34 | **builds** |
| `scan_string` | 40 | **builds** |
| `scan_name` | 64 | **builds** |
| `names_equal` | 27 | **refused: "rejects two fallible operands because C operand evaluation order is unspecified"** |
| `match_tail` | 99 | inherits that refusal — it calls `names_equal` |
| `scan_value` | 113 | **`PEP_RUNTIME_STEP_LIMIT`** — inherent, see below |
| `match_varlet_body` | 201 | depends on a function outside my dependency set; not independently measurable |
| `is_unsupported_prog` | 374 | depends on `scan_value` |

## scan_value is the keystone

Isolated to six functions — primitives, `expect_byte`, `skip_ws`, `scan_digits`, `scan_value`, `main` — `scan_value` still exceeds
the 100k step budget:

```
annotated  STEP  sectional check failed in scan_value: ['PEP_RUNTIME_STEP_LIMIT']
plain      A13   sectional check failed in scan_value: ['PEP_A13_TYPE_UNSUPPORTED']
```

So it is **not** an artifact of compiler A's 34-function context and **not** an artifact of the annotations: 113 lines of nested
`while`/`if` with many statements is over budget on its own. Since `match_tail`, `match_varlet_body` and `is_unsupported_prog` all
reach it, **nothing downstream of `scan_value` can be verified until it is split.**

## What this changes for A4

The fallback tier is not one wall. It is four:

1. **annotations** — clears A13 (A3-183), A4 can do this now
2. **`names_equal`** — an emitter refusal on a 27-line function, which also blocks `match_tail`
3. **`scan_value`** — inherent step limit, blocks three functions
4. **`match_varlet_body`, `is_unsupported_prog`** — downwind of the above

The 100k budget is frozen, so (3) means splitting `scan_value`. That is structural work on a 113-line function, not a tweak.

## Two harness errors I made and corrected

Reporting these because both produced plausible-looking tables:

- **First run** omitted callees, so `match_tail`, `match_varlet_body` and `is_unsupported_prog` reported `PEP_UNKNOWN_FUNCTION`.
  That was my dependency set, not A4's code. I nearly wrote it up as three defects.
- **Second run** fixed that by including *every* function as a dependency — including `scan_value` — so all five targets then
  reported `STEP` at `scan_value`. Also my harness: the failing dependency masked the target.

Only the third pass, with each function's own callees, gives the map above. **Two wrong tables before the right one**, both from the
same mistake: not thinking about what my harness contributes.

## Limits

- Annotations were blanket `Int` (A3-183's caveat applies) — some may be type-wrong and would surface as `PEP_TYPE_MISMATCH`, not
  as the results above. The three that build did so with those annotations, so they are at least self-consistent.
- `match_varlet_body` is not independently measured; its dependency set includes a function I excluded.
- Isolated builds are not the same as a full 34-function build; a function can pass alone and still fail in context.
- I did not re-measure step counts, only pass/fail.

REF GH #16. Follows `6729170885` (A3-183, the workaround).