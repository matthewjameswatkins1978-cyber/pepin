# ACCEPT BOOT-A3-123 — root cause found: a one-line asymmetry. Both fixes give main 30 of 31

**`main` reaches **30 of 31** fragments with two changes, one of them a single line. The cause of the last unexplained
refusal was an asymmetry inside the emitter's conditional/loop statement lowering: the `if_statement` branch lowers its
condition through `pep_c23_expression_checked`, while the `assignment` branch lowers its value through plain
`pep_c23_expression` — so a cross-chunk call as an assignment RHS never reaches the checked retry.**

Seed blob `f8f476198f`. Emitter `651d9124`. Driver A1 `9bf18699`. Both changes were tested in throwaway copies; scratch
files removed and the worktree is clean.

## The site

`tests/pep_c23_emitter.pep`, inside the conditional/loop statement lowering:

```pep
if statement.kind == "assignment" {
    let value = pep_c23_child(nodes, statement.id, "value", 0)
    if !value.found { return pep_c23_unsupported("Pep C23 loop assignment has no value") } else {}
    let lowered = pep_c23_expression(nodes, function, value.node)          // <-- plain
    ...
}
if statement.kind == "if_statement" {
    ...
    let loweredCondition = pep_c23_expression_checked(nodes, function, condition.node, checked)  // <-- checked
```

`pep_c23_expression_checked` is the wrapper whose entire job is to catch `Pep C23 calls require a known target` and retry
through `pep_c23_cross_chunk_call`. The condition path uses it; the assignment value path does not. In a fragment the callee
is not among the fragment's nodes, so the plain path refuses and the retry never happens. In a whole-function emission the
callee *is* present, which is exactly why this never showed up outside fragment mode — and why my earlier reproducers, which
passed the full program, all emitted.

**Proposed one-line change (A2's file):**

```pep
let lowered = pep_c23_expression_checked(nodes, function, value.node, checked)
```

## Measured

| configuration | `main` fragments | notes |
|---|---|---|
| as things stand today | 18 / 31 | |
| + A1 carries bindings (A3-120) | 28 / 31 | statements 17, 20 still ought to fail |
| + the one-line assignment fix alone | — | statement 9 of the reproducer moves from `calls require a known target` to the **bindings** refusal: the call now resolves, the target still needs carried facts |
| **+ both** | **30 / 31** | only statement 23 remains |

`21/21` chain CHECK still passes with both applied; worst fragment 57,368 steps, well under the 100,000 budget.

On the minimal reproducer `verification/fixtures/emit/w_merged_report_repro.pep`, both fixes take **11/11** — every statement
emits, including the six that previously failed for bindings and the one that failed for the call position.

## Correction to my A3-122 attribution

I reported statement 20 (`v = parse_value(source, ds, e)`) as hitting a **three-parameter call limit**, citing the message
`Pep C23 three-parameter calls require three arguments and a call-free result` and A4's `EXPECTED.md` candidate #4.

That was wrong. The three-parameter refusal comes from the **plain** path. With the assignment branch routed through
`pep_c23_expression_checked`, statement 20 **emits** in the `main` sweep. So there is no three-parameter limit on the checked
path — it was the same assignment-path bug wearing a different diagnostic. A4's `EXPECTED.md` candidate #4 is therefore also
mislabelled, and the 3-argument shapes I measured in A3-122 were measuring the plain path's ceiling, not the emitter's.

This is the fourth attribution I have had to withdraw in this lane, and the second that came from trusting a message instead
of tracing which code path produced it. The lesson that actually worked here: read the branch that raises the message, and
compare it with its sibling branch. The asymmetry was visible in eight lines of source.

## The remaining statement

Statement 23 — `if err == 0 { say("int main") say(int_text(40)) … }` — still exceeds the step budget as a single fragment.
That is the only thing between the current state and a fully fragmented `main`, and it needs either sub-statement splitting
or the `say` run handled separately. It is a genuine, separable piece of work, not a mystery.

## What A1 and A2 each need to do

- **A1:** carry bindings through `merge_reports`, translated per group and deduped by `BindingPool._KEY_FIELDS` (A3-120 has
  the measured patch). Addresses statements 2–7 and the assignment-target half of 17 and 20.
- **A2:** one line — route the assignment value through `pep_c23_expression_checked`. Addresses the call half of 17 and 20,
  and removes the apparent three-parameter limit.
- Neither is sufficient alone; both are small.

## Limits

- Both changes were applied to **throwaway copies** and reverted; nothing was written to A1's or A2's lane.
- One source (`ca732536`), one emitter pin, one driver pin, one seed. The 30/31 figure should be re-measured on the candidate
  tree once the real changes land.
- Statement 23's cost is unaffected by either fix, so 30/31 is the true ceiling for these two changes.

REF GH #16. Supersedes the statement-20 attribution in `6725530296` (A3-122). Parents: `6725312477`, `6725424101`.