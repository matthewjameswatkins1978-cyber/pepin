# ACCEPT BOOT-A3-064 — S dispatch shape runs natively: stdout `6` under strict Clang AND GCC

**Verdict: the S route's core shape executes end-to-end. List construction, a `for` loop in `main`, and a
per-element cross-chunk `Int` call all lower and run, producing the correct result on both compilers. This is
the first *output*-proven result of this lane, and it needed no `int_text`.**

## Result

`verification/fixtures/emit/s_exitcode.pep` (17-node `main`, 12-node `add`):

```
fn add(a: Int, b: Int) -> Int { let s = a + b; return s }
fn main() -> Int {
    let data = [1, 2, 3]
    var t = 0
    for v in data { t = add(t, v) }
    return t
}
```

```
chunk add   valid   emit unit add  OK (262 B)
chunk main  valid   emit unit main OK (380 B)
build clang OK   run clang -> stdout='6' exit=0
build gcc   OK   run gcc   -> stdout='6' exit=0
```

`6` is the correct sum of `[1, 2, 3]`, reached through a cross-chunk helper call per element.

## Why this matters

BOOT-A3-063 concluded that `int_text` blocks output-proof. **That was too pessimistic.** The emitted program
surfaces its `Int` result without `int_text`, so the verification suite can be output-proven *today*, on
committed fixtures, under both compilers. The `int_text` gap remains real for programs that must print an
arbitrary computed value, but it is **not** blocking native verification.

This also independently confirms two things I had only measured as emission:
- a **List argument or List value stays usable inside `main`** while helpers are called with `Int` args;
- **cross-chunk call facts resolve correctly** for repeated calls inside a loop — not just once.

## What is still NOT proven

- **The mission floor**: this program's output does not depend on input *text*. It is a fixed program, so it
  demonstrates the execution path, not input-dependent C text. `divergence_2_042.py` still fails.
- No `Str` production beyond what BOOT-A3-054 measured; `utf8_slice` still has no by-name lowering.
- `stdout='6'` with `exit=0`: I report the observed values rather than asserting which C epilogue prints them.
  The epilogue's mechanism is unexamined this turn.
- One seed build, one machine, `-O2`, `-Wall -Wextra -Wpedantic -Werror`; no sanitizers, no optimiser variation.

REF: GH #16.