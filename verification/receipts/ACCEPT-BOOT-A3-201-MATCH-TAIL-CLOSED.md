# ACCEPT BOOT-A3-201 — A4's match_tail inversion verified; blockers 2 and 3 are fully closed

**A4's `239d10d2` inverts the empty then-branch in `match_tail`. Verified two ways: the full build no longer reports `match_tail`, and
`scan_name` + `names_equal` + `match_tail` now build together in isolation with rc 0.**

Seed blob `f8f476198f`. A4 `239d10d2`, `compiler_a.pep` blob `1667d076`, 1,546 lines.

## The verification

```
full build:
  Pep C23 unsupported: sectional check failed in scan_value: ['PEP_RUNTIME_STEP_LIMIT']
  fails in match_tail:    False
  empty-then refusals:    False

isolated (scan_name + names_equal + match_tail):
  rc=0, executable produced
```

The isolated build is the stronger check — it shows the three functions actually **emit and compile**, not merely that a later
failure masked them.

## Where the fallback tier now stands

| # | function | state |
|---|---|---|
| 2 | `names_equal` | **closed** — A4's `bytes_eq` (A3-191), verified A3-194 |
| 3 | `match_tail` | **closed** — A4's inversion (A3-193), verified here |
| — | all | bare-name `var` init — A4's annotations (A3-183/188), verified |
| 1 | `scan_value` | **open** — step limit; minimum loop work is 4.5 units against a budget of ~4 (A3-199) |
| 1b | `scan_value` | **open, hidden** — declares `var hasop` and `var d2` inside its loop, which emission refuses (A3-200) |
| 4 | `match_varlet_body` (347 nodes), `is_unsupported_prog` (687) | behind `scan_value`, unmeasurable |

**Two of the three measurable blockers are now closed by the owning agent**, each using a shape this lane measured and each verified
independently afterwards.

## What remains is one function with two defects

`scan_value` needs both a budget solution (research) and a mechanical hoist (A3-200). The hoist is available now and costs nothing;
the budget question has no in-place fix.

## Limits

- The isolated build omits `scan_value`, so it does not prove these functions would survive in a full 34-function build — only that
  they are not themselves blocked.
- `bytes_eq` and `is_op`-style helpers were in the dependency set; I did not vary it.
- One commit, one revision.

REF GH #16. Closes `6729580473` (A3-193's fix, now applied). Related: `6729773967` (A3-200, the hidden second defect).