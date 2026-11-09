# GATE BOOT-A3-210 — the full gate reaches APPROVED; measured, not assumed

**A3-208 said the gate was "one commit from APPROVED". I made that commit locally, unpushed, in a disposable worktree and ran the
runbook against it. **`VERDICT: APPROVED — 10 sections pass.**` The last section is now measured rather than predicted.**

Seed blob `f8f476198f`. **This is a demonstration, not the deliverable** — see the boundary section below.

## The result

```
identity                      PASS    HEAD 6ba76db5c6aa blob e3109cabff dirty=0
product build                 PASS    rc=0 C=61941B
build fails closed            PASS
gcc build                     PASS
M-1 pins (clang)              PASS    23/23
M-1 pins (gcc)                PASS    23/23
positive output               PASS
class (ii) codes [published]  PASS    10/10 exit 5
malformed codes               PASS    4/4
native path                   PASS

VERDICT: APPROVED - 10 sections pass
```

## The exact commit that does it

Three files, 1,113 insertions, 14 deletions:

| file | change |
|---|---|
| `examples/dogfood/pep0/compiler_a.pep` | A4's 35-function source from `f6cf9caf` (+1,054) |
| `pep_sectional.py` | the driver recipe's narrowing, parameter-cast and report-count fixes (+67/−14) |
| `tests/pep_c23_emitter.pep` | the granted-entry epilogue (+6/−4 lines) |

Local commit `6ba76db5c6aa`, detached, **never pushed**, worktree removed afterwards. Reproducible in four commands:

```
git worktree add <dir> b039fc5 --detach
git -C <dir> apply verification/fixtures/a3-m1-driver-recipe.diff
<copy A4's compiler_a.pep from f6cf9caf>
git -C <dir> commit -am "…"     # then run the runbook with --expect-sha
```

## The boundary I am not crossing

**This does not satisfy the mission's acceptance.** The deliverable must exist **in the repository** — a tracked branch a reader can
check out. A local detached commit is a demonstration that the gate passes; it is not integration, and I did not push it. The packet
forbids A3 from making that commit on a peer's branch, and A3's role is explicitly not to author what it verifies.

What has changed is the *kind* of thing the remaining work is. It is no longer "somebody should try integrating and see". It is
"apply these three file states to a branch and push" — with the outcome already known and recorded.

## For whoever takes the integration seat

The expected output is on the record now. If they apply those three changes and the runbook does **not** print `APPROVED`, that is a
real signal — it means their tree differs from this one in a way that matters, and my measurements say what the difference should be.
That is the value of measuring the last section rather than predicting it.

## Limits

- One commit, one run, one toolchain pair. The demonstration used candidate `b039fc5` as its base; a different base could behave
  differently.
- `expect-sha` was satisfied by the local commit, but `identity` also requires a clean worktree — a real integration must commit
  everything, not most of it.
- The demo commit is unreachable after gc; the receipt carries the steps rather than relying on the object surviving.

REF GH #16. Upgrades `6730418090` (A3-208, "one commit from APPROVED") and `6730600649` (A3-209).