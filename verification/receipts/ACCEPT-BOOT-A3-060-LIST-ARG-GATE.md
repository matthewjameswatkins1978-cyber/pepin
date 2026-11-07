# ACCEPT BOOT-A3-060 — List ARGUMENTS cannot cross chunk boundaries: a third S-route gate

**Verdict: falsified as stated. A cross-chunk call carrying a `List` argument cannot be emitted, while the
same call with no argument or with an `Int` argument emits cleanly. A1 reported a List *result* gate; this is a
List *argument* gate, which is a different and structurally worse limit for the S route.**

A1's receipt (`#16 6707793442`) reported A4's List probe passing natively 4/4 but left its driver in gitignored
`_build/`, so the claim had no committed artifact (BOOT-A3-059). I therefore rebuilt the shape as durable
fixtures and drove them with a committed instrument. The controls changed the answer.

## Measured matrix — every row committed, every row rerun

| fixture | shape | chunk check | emission |
|---|---|---|---|
| `ctl_no_arg.pep` | cross-chunk call, **no args** | both valid | **FULLY EMITTED** |
| `ctl_int_arg.pep` | cross-chunk call, **Int arg** | both valid | **FULLY EMITTED** (main 239 B) |
| `list_probe_060.pep` | cross-chunk call, **List arg via local** | both valid | **REFUSED**: `Pep C23 cross-chunk call has no resolved call fact` |
| `var_list_inline.pep` | cross-chunk call, **inline list literal** | both valid | **REFUSED**: `Pep C23 expression lowering does not support this expression` |

The two controls are what make this a finding rather than an artifact: cross-chunk call facts **do** resolve in
this harness when the argument is absent or `Int`. The refusal is therefore **specific to the `List`
argument**, not to my plumbing, not to chunk validity (all four pairs check valid), and not to function size
(15/18, 15/10, 10/9, 6/6 nodes — all far under the ~32-node limit).

## Why the first attempt misled, and why that matters

My first Int-arg control used `var y = x; y = y + y; return y` and was refused at the **callee** with
`Pep C23 functions require local bindings and supported loops followed by one return`. That is an unrelated
body-shape rule — it would have looked like "cross-chunk calls are broken generally", which is false. Rewriting
the callee as `let y = x + x; return y` made it emit. **A control that fails for the wrong reason is worse than
no control**, and the correct conclusion only appeared after fixing it. Both versions were committed.

## Consequence for route selection

A1's S plan passes a `List` into a cross-chunk helper (`sum(values)`, for-in inside the callee). That shape
**cannot be emitted today**. Since a lexer-shaped Pep program must move a token list or a byte buffer across
chunk boundaries, this is a **structural gate on S**, comparable in weight to the missing `utf8_slice` lowering,
and it was not in A1's two-gate list. A1's 4/4 pass is therefore **not** a demonstration that the S shape works;
it can only have exercised a shape without a List argument — which is consistent with it being described as
"List, literal init, for-in, cross-chunk Int call" with the list never actually crossing the boundary.

Anyone planning S must now either (a) keep the list in `main` and loop there, (b) pass an Int handle/offset
instead of a list, or (c) get a List-argument lowering in the emitter (A2's file).

## Also measured, cheaply, on the way

- `fn main()` must return `Int`, not `Unit`: `Pep C23 main function must return Int`.
- A callee using `var` + reassignment without a loop is refused: `Pep C23 functions require local bindings and
  supported loops followed by one return` — so the "assign + one reachable trailing return" recipe from
  BOOT-A3-053 is narrower than I stated: the assignment must be inside a supported loop, or be an immutable
  `let`.

## Honest limits

- One seed build, one machine, one instrument, one chunk-check path. I did not test `List[Str]`, a `List`
  returning helper, or a record containing a list.
- These four fixtures test **emission and refusal**, not native execution: no binary was run this turn, because
  three of the four shapes never reached code generation.
- I have not tested whether a List argument works when the callee loop is absent, so the interaction between
  the two rules above is unmeasured.

REF: GH #16. Fixtures: `verification/fixtures/emit/{ctl_no_arg,ctl_int_arg,list_probe_060,var_list_inline}.pep`.