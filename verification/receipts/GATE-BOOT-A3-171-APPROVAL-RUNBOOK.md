# GATE BOOT-A3-171 — the independent approval runbook, and two of my own test inputs were wrong

**The dispatch asks A3 to build through the product path, use strict Clang and GCC, exercise positive outputs, the malformed set,
the seven unsupported cases, stdout/stderr/exit and no-C-on-failure, audit the native path, and publish a SHA-bound pass/fail
receipt. That is now one command rather than assembled from twelve receipts.**

Seed blob `f8f476198f`. New: `verification/probes/gate_candidate_171.py`.

```
python verification/probes/gate_candidate_171.py --root <candidate worktree> [--expect-sha SHA]
```

## The run on the one build that passes M-1 today

Candidate `b039fc5` + `a3-m1-driver-recipe.diff` + A4 `81dca2f4` source + the Bool-local rewrite:

```
section           result  detail
identity          FAIL    HEAD b039fc5daadf blob d7d74dd003 dirty=3
product build     PASS    rc=0 C=33069B
no-C-on-failure   PASS    rc=2 wrote_c=False
gcc build         PASS    rc=0
M-1 pins (clang)  PASS    15/15
M-1 pins (gcc)    PASS    15/15
positive output   PASS    pos42:ok pos7:ok
class (ii) codes  FAIL    7 wrong: maincap=1/5, nomain=1/5, unary=2/5, binary=3/5, var…
malformed codes   PASS    4/4
native path       PASS    no interpreter markers

candidate b039fc5daadf source blob d7d74dd003
VERDICT: NOT APPROVED - 2 of 10 sections failed
```

`identity` fails because the worktree carries three unapplied patch files — which is the honest answer, and exactly why that
section exists. On a clean tracked candidate it should pass.

And on the plain candidate, with no patches, the runbook stops at the first section that matters:

```
identity       PASS    HEAD b039fc5daadf blob ca732536d5 dirty=0
product build  FAIL    rc=2 Pep C23 unsupported: Pep C23 fragment 11 of find_b…
```

## Two of my malformed inputs were not valid Pep

First run flagged `badlit=3/2`. My input was `fn main() -> Int { return 1x }` — I invented it. Compiler A never saw it; the *host*
rejected it with `PEP_UNKNOWN_VARIABLE` before emission, so the exit code I measured was the host's, not compiler A's.

The oracle's real fixture is `fn main() -> Int { return ; }` — a return with no value. Replacing my invented cases with the pinned
byte strings (a_badlit, a_badbrace, a_big19, a_dup) gives **4/4**.

I only caught this because the section disagreed with itself; had I trusted my expectation I would have filed a defect against A4
for my own bad input. **Third time this mission that a test input of mine was the error, not the code under test.**

## Design notes

- Sections never roll up silently: each is reported independently, a section that cannot run says so, and the verdict is FAIL
  unless every section passes.
- `no-C-on-failure` is asserted directly — exit non-zero **and** no `.c` written — rather than inferred.
- stdout and exit are compared **separately** for the positive cases, because A3-159 showed a run where the value was right and only
  the stream and status were wrong.
- The native audit scans the binary for interpreter markers; it does not depend on symbol tables, which gave a false clean on
  A3-161's first attempt.
- The malformed bytes are restated locally so the runbook does not break if A4's oracle file moves.

## Limits

- The class (ii) expectations encode the contract **as published today**. If A4 narrows it (A3-155 option b), these ten cases must
  change with it — the runbook pins the promise, not the implementation.
- The M-1, malformed and class (ii) sections all use the clang binary; gcc is used for the M-1 pins only.
- No candidate has passed this runbook. That is the finding, not a gap in the runbook.

REF GH #16. Related: `6728781975` (A3-170, the driver recipe this uses), `6728365639` (A3-159, the M-1 result).