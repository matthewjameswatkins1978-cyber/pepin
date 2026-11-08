# FINDING BOOT-A3-173 — the A13 defect is A1's at their own tip, and three checkers are in circulation

**I had been treating the A13 rejection as a property of the merged candidate. It is not. It reproduces on A1's own branch tip
`333c5805` with that branch's own sectional path, so it is not a merge artifact and not something A2 or A4 introduced.**

Seed blob `f8f476198f`. Tested in `D:\Projects\wt-a1-fix` (A1 tip `333c580`, dirty 0), read-only.

## The attribution

```
$ cd D:\Projects\wt-a1-fix            # A1's own branch, their own driver
$ python pep_c23.py build-c23 …/a13-assign-target-reduced.pep --sectional …
Pep C23 unsupported: Pep C23 sectional check failed in scan: ['PEP_A13_TYPE_UNSUPPORTED']
```

Same fixture, same message, same function. So the defect is present at A1's tip and does not depend on the merge into `b039fc5`.

## Three different checkers are in circulation

| tree | `tests/pep_checker_a13.pep` blob |
|---|---|
| campaign branch `bddd3542` (tracked) | `e19fdde0` |
| A1's tip `333c5805` | `2d714a0e` |
| candidate `b039fc5` | `8f034bc3` |

**None of the three match.** The candidate — which is nominally A1's work merged with A2's — does **not** carry A1's tip checker.
That is worth A1 and A2 knowing: whichever branch is authoritative, the integration is currently running a checker from neither
named input, and behaviour differs between them.

Concrete evidence of that difference: on the candidate the 31-line control passes the check and fails later at C compile (the
parameter-cast bug). On A1's tip the same control is refused earlier with

```
Pep C23 conditional lowering requires a non-empty then branch
```

because the control has `if i == 1 { } else { i = n }` — an empty then-branch. So A1's tip enforces a rule the candidate's checker
does not.

## Two consequences

**1. This is a repository-level defect, not a project-level one.** The campaign branch has no `pep_sectional.py` at all — the
sectional path is entirely branch work — but it already carries the `"Assignment target has no supported concrete type"` text at
L1933. So the code path that misfires is tracked; only the driver that reaches it is not.

**2. "It works on my branch" is not available to anyone here.** A1 cannot discharge this as an integration issue, and A4 cannot
work around it in source (A3-169 tried two restructures on the real function; neither transferred).

## What I did not do

I did not test whether A2's branch tip, merged alone with A1's, changes anything, because no such candidate exists and building one
is integration work that belongs to A1.

## Limits

- One fixture, two trees, product path only.
- Blob identity is not behavioural identity; I confirmed the difference in behaviour only for the control case above.
- The campaign branch cannot run the sectional path at all, so I could not test the fixture against tracked code directly.

REF GH #16. Related: `6728741555` (A3-168, the gate), `6728763855` (A3-169, no workaround transfers).