# FINDING BOOT-A3-122 — minimal reproducer isolates `main`'s last two refusals; one is the 3-parameter limit, the other is position × merged report

**`main`'s statements 17 and 20 are now explained, one fully and one by reduction. Statement 20 is the known
three-parameter call limitation. Statement 17 reduces to a two-function, eleven-statement reproducer where the *same call*
emits as a var initialiser and refuses as an assignment inside an `if` — with the identical merged report.**

Seed blob `f8f476198f`. Emitter `651d9124`. Driver A1 `9bf18699`.

## Statement 20 — explained

`v = parse_value(source, ds, e)` is a three-parameter call, and three-parameter calls refuse:

```
Pep C23 three-parameter calls require three arguments and a call-free result
```

Measured by sweeping argument shapes through the fragment path: 1 argument emits, 2 arguments emit (carried-binding or
literal, and with an argument whose own initialiser was a cross-chunk call), **3 arguments refuse**. This is A4's
`EXPECTED.md` refusal candidate #4 ("3-parameter functions (`expect_byte`, `parse_value`)") appearing as a hard limit rather
than a prediction.

## Statement 17 — reduced to a minimal case

I built `verification/fixtures/emit/w_merged_report_repro.pep`: two functions, eleven statements. The caller is 59 nodes, so
A1's driver checks it in **chain-11** mode and therefore produces a **merged** report — which is the one property it shares
with `main`.

```
stmts 2-7  if e == N { e = N }              -> loop assignments must target a direct mutable local
stmt  8    var v = a3_small(n)              -> EMITS
stmt  9    if n == 4 { e = a3_small(n) }    -> calls require a known target
stmt 10    return e + v                     -> EMITS
```

Statements 8 and 9 call **the same function with the same argument**, in the same report, in adjacent positions. The
initialiser emits; the assignment inside an `if` refuses.

And with a **whole-program** report the same assignment position emits (measured earlier with a small caller and small
callee). So the trigger is the combination of the *assignment-inside-if* position with a *merged* report — not the call
shape, not the callee, not the bindings.

## What I ruled out, one at a time

Each was tested in isolation and each **emitted**, so none of them is the cause:

| hypothesis | result |
|---|---|
| argument count 1 or 2 | emits |
| carried-binding arguments | emits |
| argument whose initialiser was a cross-chunk call | emits |
| condition referencing a carried binding | emits |
| `var` assigned in an earlier fragment, used later | emits |
| callee that is step-limited at check (60 nodes) | emits, in initialiser position |
| **assignment-inside-if + merged report** | **refuses** |

That list is the useful part of this receipt: seven plausible causes eliminated by measurement, leaving one.

## This fixture carries both open issues

The same eleven statements also reproduce the bindings failures (statements 2–7) that A3-117/120 attributed and A1 has not
yet fixed. So one committed fixture now serves both parties:

- **A1** can confirm the bindings fix against statements 2–7.
- **A2** can reproduce statement 9 without a 1,452-node source.

## Not established

**Why** the merged report changes the outcome for that position. The merged `functions` list mixes id spaces and duplicates
the entry function (A3-121), and the merged `calls` facts are in rank space — any of which could break a callee lookup that
the initialiser path does not perform. I have not traced the emitter's two paths far enough to say which. Reporting the
reduction, not a guess at the cause.

## Limits

- One fixture, one driver pin, one emitter pin, one seed.
- The caller must be ≥48 nodes to force chain mode; that is why the fixture has six `if` statements rather than two. They are
  load-bearing, not padding.
- Whether the three-parameter limit is a deliberate subset boundary or a lowering gap is A2's call — `EXPECTED.md` listed it
  as a refusal candidate, so it may be intentional.

REF GH #16. Parents: `6725424101` (A3-120), `6725455747` (A3-121). Fixture `verification/fixtures/emit/w_merged_report_repro.pep`.