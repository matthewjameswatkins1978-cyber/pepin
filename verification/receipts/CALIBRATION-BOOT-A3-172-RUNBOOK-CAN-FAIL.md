# CALIBRATION BOOT-A3-172 — the approval runbook is proven able to fail, and two sections do not measure compiler A

**A gate never seen failing is not evidence. I ran the runbook against a deliberate stub — `fn main(source: SourceBytes) -> Int {
return 0 }`, three lines, replacing all thirty-four functions — and six of ten sections caught it. The two that did not are named
for what they actually measure.**

Seed blob `f8f476198f`. Candidate `b039fc5` + driver recipe + a three-line stub source.

## The calibration run

```
section             result  detail
identity            FAIL    HEAD b039fc5daadf blob 5a336e7f7d dirty=3
product build       PASS    rc=0 C=11093B
build fails closed  PASS    host refusal, compiler-A-independent: rc=2 wrote_c=False
gcc build           PASS    rc=0
M-1 pins (clang)    FAIL    1/15
M-1 pins (gcc)      FAIL    1/15
positive output     FAIL    pos42:BAD pos7:BAD
class (ii) codes    FAIL    10 wrong: str=0/5, bool=0/5, unit=0/5, maincap=0/5, nomain=0…
malformed codes     FAIL    badlit=0/2, badbrace=0/1, longlit=0/4, dup=0/3
native path         PASS    no interpreter markers

VERDICT: NOT APPROVED - 6 of 10 sections failed
```

## What this establishes

**Six sections detect a completely hollow compiler.** M-1 falls from 15/15 to **1/15** — only `a_empty` survives, because empty
input exits 0 with no output and the stub cannot help but agree. Positive output, class (ii) and malformed all fail with the exact
per-case detail. So the runbook's verdict is driven by compiler-A behaviour, not by the build merely succeeding.

## Two sections that a stub also passes, and why that is correct

**`build fails closed`** feeds the *host* a compiler-A source that is itself invalid Pep (`fn main() -> Str { return 1 }`) and checks
that no `.c` is written. A stub compiler A still passes, because this measures A1's build path refusing bad source — not compiler A's
quality. It is a legitimate gate section, since the mission asks for the property, but it is **not compiler-A evidence** and the
label now says so.

**`native path`** confirms the binary has no interpreter markers. A three-line stub is native too. Right property, wrong
discrimination — it rules out a hidden host compiler, not a wrong one.

## Correction to what the runbook's VERDICT implies

"6 of 10 failed" reads as though ten sections each measure the product. They do not:

| measures compiler A | measures the build |
|---|---|
| M-1 pins (clang, gcc), positive output, class (ii), malformed | identity, product build, build fails closed, gcc build, native path |

Four sections are the compiler-A signal. The other six establish that the thing being tested was built by the real path, cleanly,
natively, and that the runbook never fabricates a pass. Those are necessary conditions, not evidence of correctness, and mixing
them in one list invites the reader to count ten passes as ten proofs.

## What would still make an APPROVED verdict wrong

A compiler A that special-cases my forty-nine test inputs would pass every section. The runbook has no defence against that beyond
the inputs being derived from A4's own published contract rather than chosen by me. The unseen subset-S0 forms in the M-1 gate are
the closest thing to a guard, and they are two cases.

## Limits

- One stub, one shape. A partially-correct stub might pass some compiler-A sections and fail others; I did not test a gradient.
- `a_empty` passing at 1/15 shows the M-1 pin set has a tolerance floor: any implementation that exits 0 silently scores one.
- The stub was applied in a disposable worktree and reverted; nothing in A4's lane touched.

REF GH #16. Calibrates `6728818349` (A3-171).