# ACCEPT BOOT-A3-106 — reserve R3 built: a working seed-vs-emitted semantic differential, now 7th gate in the suite

**Verdict: A3's reserve R3 exists and passes. `verification/probes/seed_differential_106.py` compares what the **seed's own
evaluator** computes against what the **emitted C** computes for the same expression, and all four cases agree under both
clang and gcc. This is a differential against an independent implementation, which is materially stronger than comparing
emitted C to my own expectations — the previous best A3 could do.**

## Result

```
PASS cross-chunk arithmetic   both print '43'   [emitted side hoists into a let]
PASS negative integer         both print '-3'
PASS truncating division      both print '0'
PASS string concat            both print 'abcd'

4 cases, 0 disagreeing
SEED vs EMITTED: AGREE
```

And as the seventh gate in the standard suite:

```
A4 oracle replay (13 pins)        PASS
A4 normative boundary (17)        PASS
A1 semantic oracle (23)           PASS
A1 sectional merge (11 probes)    PASS
A2 DIVERGENCE-2 (16)              PASS
M-1 gate calibration              PASS
Seed vs emitted differential (4)  PASS
7 gate(s) ran, 0 failed, 0 skipped — ALL GATES GREEN
```

## The method, and why the two sides differ in placement

The seed and the emitter cannot run the same source, for reasons A3-105 established and this probe now depends on:

- the seed executes only **top-level statements** (`exec_stmts [] [] c.tops`) and never calls `main`;
- the emitter **requires** a top-level `main` and refuses without one.

So each case supplies two sources differing only in *where the expression lives*:

```pep
say(int_text(a3_double(21) + 1))                     # seed, top level
```
```pep
fn main() -> Int { let v = a3_double(21) + 1
                   say(int_text(v))  return 0 }       # emitted
```

The comparison is of **values**, not of code. That is the honest shape of the differential: it tests expression semantics,
not statement or scope semantics.

The emitted side must also hoist the cross-chunk call into a `let`, because `say(int_text(f(41)))` — a builtin whose
argument is a user call — is not lowered yet (BOOT-A3-105). That constraint is written into each case rather than hidden, so
when A2 closes it the hoisting can be removed and the case should still pass.

## One guard against a silent fudge

The emitted program's epilogue echoes `main`'s return value as a final line, so emitted stdout is `43\n0` against the seed's
`43`. Naively stripping the last line would let a real change in epilogue shape pass unnoticed. The probe therefore
**asserts the stripped line equals `0`** and fails loudly if it does not. A comparison that quietly discards a line is one
step away from a comparison that discards a defect.

## My own bug, recorded

The first run crashed in `parse_target` because I passed the target document's revision where the **bundle** revision is
required — the parser cursor is keyed to the tool revision. A two-minute fix, but noted because it is the fifth instrument
defect in this lane and the pattern is consistent: my harness code, not the code under audit.

## Limits

- **Four expressions.** Arithmetic, a negative result, truncating division, and string concatenation. This establishes the
  method and gives a regression net; it is not broad semantic coverage.
- **Expression semantics only.** Placement differs by necessity, so statement ordering, scope lifetime, mutation, loops and
  error ordering are all outside what this differential can see.
- **Only expressions the emitter can lower with hoisting.** Anything hitting the builtin-of-call gap, or needing
  `SourceBytes` input (still no grant, A3-073/074), is out of reach.
- **Both roots point at one lane** (`wt-a3-dbea`) in the run above. A seed from a different branch would be a stronger test
  of seed-independence; the gate accepts `--seed` and `--gate` separately for exactly that.

## Reproduce

```
PEPIN_SEED_ROOT=<built seed> PEPIN_GATE_ROOT=<emitter worktree> \
  python verification/probes/seed_differential_106.py
```

REF GH #16. Reserve R3, recovered from the A3-104 scope error in A3-105 and delivered here.