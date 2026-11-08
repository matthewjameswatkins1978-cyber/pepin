# ACCEPT BOOT-A3-084 — independent emit table: 9/21, corroborating A1 exactly, with the 12 failures split into two distinct walls

**Verdict: measured independently, 9 of 21 compiler-A functions emit — reproducing A1's reported 9/21 by a different
instrument. The 12 non-emitting functions fall into exactly two disjoint causes: 11 blocked earlier by the 100,000-step
limit, and 1 blocked by the cross-chunk call target. A2-S1 and A2-S2 are each necessary and neither is sufficient alone.**

## Method

`PEPIN_UNITS_ONLY=1 python verification/probes/emit_any_049.py` — a new mode on my own instrument that measures per-function
`pep-c23-unit` emission for every chunk that checked valid, instead of demanding all 21 before emitting anything. Same app
(`5f62e4b:examples/dogfood/pep0/compiler_a.pep`, blob `ca732536`), same seed, pin `bea071a`.

## Result

```
partial mode: 10/21 checked valid; measuring emission for those only
  unit is_ws            EMITTED (328 bytes)
  unit is_digit         EMITTED (286 bytes)
  unit is_ws_at         FIRST REFUSAL: Pep C23 calls require a known target
  unit is_fn2           EMITTED (452 bytes)
  unit is_int3          EMITTED (512 bytes)
  unit is_ret3          EMITTED (513 bytes)
  unit is_urn3          EMITTED (513 bytes)
  unit is_str3          EMITTED (512 bytes)
  unit expect_byte      EMITTED (441 bytes)
  unit parse_value      EMITTED (556 bytes)

PARTIAL RESULT: 9/10 check-valid functions emit
```

**9 of 21.** A1 independently reported 9/21. Two separate instruments, two separate code paths, same number. That is what
corroboration should look like, and it means A1's figure can be relied on.

## The two walls, disjoint and individually necessary

| wall | count | functions | fix needed |
|---|---|---|---|
| `PEP_RUNTIME_STEP_LIMIT` at whole-chunk CHECK | **11** | `skip_ws`, `scan_digits`, `is_main4`, `is_bool4`, `is_unit4`, `check_tail`, `find_parens`, `find_fn`, `find_ds`, `find_brace`, `main` | statement-granular emission (A2-S2 / A1-S2) |
| cross-chunk call target unresolved at unit EMIT | **1** | `is_ws_at` | A2-S1 |
| emitted | **9** | `is_ws`, `is_digit`, `is_fn2`, `is_int3`, `is_ret3`, `is_urn3`, `is_str3`, `expect_byte`, `parse_value` | — |

11 + 1 + 9 = 21. No overlapping cause and no unexplained residue.

## The one refusal is A2-S1's own named reproducer

`is_ws_at`, at `5f62e4b:examples/dogfood/pep0/compiler_a.pep`:

```pep
fn is_ws_at(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 1 <= byte_length(source) && is_ws(byte_at(source, o)) == 1 {
    r = 1
  } else {
  }
  return r
}
```

`is_ws(byte_at(source, o))` — a cross-chunk call whose argument is a builtin call, inside an `&&` in an **if condition**.
The dispatch names exactly this as A1's smallest reproducer and the target of A2-S1. It refuses with
`Pep C23 calls require a known target`, which is the condition-position variant of the section path's
`Pep C23 cross-chunk call has no resolved call fact` I measured in A3-055/072. So the dispatch's A2-S1 target is real,
still open at `bea071a`, and now has an independent reproduction from the emit side as well as A1's from the check side.

Worth noting: this function also contains `o + 1 <= byte_length(source)` — the arithmetic-with-call shape. It refuses on the
*call target*, not on fallibility, which is consistent with A3-083's finding that the arithmetic `may_fail` work moves
nothing.

## What this changes for the plan

- A2-S1 alone unblocks **one** function. A2-S2 alone unblocks the emission of up to 11 but cannot help until they check.
- `main` is among the 11, so M-1 is unreachable until statement-granular handling works, whatever A2-S1 achieves.
- The 9 already emitting are the small leaf helpers, which is why DIVERGENCE-2 could pass on this emitter at all.

## Limits

- Emission is measured per function unit, not as an assembled program. A unit emitting does not prove the header/epilogue or
  the linkage is sound; the full build needs `main`.
- No step counts for the 11 (the refusal returns the code, not consumed steps). A1 measures those; I do not and will not
  guess.
- One source revision, one emitter pin. A4 or A2 moving invalidates the exact counts and the receipt must be re-run.

## Reproduce

```
PEPIN_GATE_ROOT=<worktree> PEPIN_APP_REL=examples/dogfood/pep0/compiler_a.pep PEPIN_APP_REV=5f62e4b \
  PEPIN_UNITS_ONLY=1 python verification/probes/emit_any_049.py
```

Instrument change this turn: `PEPIN_UNITS_ONLY=1` measures units for the check-valid subset; the default full-build path is
untouched, so A3-083's numbers still reproduce unmodified.

REF GH #16. Input SHA `bea071a`; source `5f62e4b:examples/dogfood/pep0/compiler_a.pep`. Source A4, emitter A2, independent
run A3.