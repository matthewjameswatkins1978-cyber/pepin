# FINDING BOOT-A3-116 — main fragments 18/31 with the right input; two genuine if-body-assignment gaps and one oversized statement

**Verdict: with A1's sliced progress as the input, `main` emits **18 of 31** statements, worst fragment **36,770 steps** (under
budget), and the transport problem is solved natively. Twelve statements refuse on **two genuine lowering gaps, both about
assignments inside `if` bodies**, localised by putting the declaration in the same fragment so cross-fragment binding cannot
be the cause. One statement exceeds the step budget on its own.**

This also **corrects my own A3-115 recommendation**, which was wrong.

Seed blob `f8f476198f`. Emitter `d02f0f4a`. Driver A1 `9bf18699` (mixed-lane; see method note).

## Correction: the right input is A1's sliced progress, not a trimmed document

In A3-115 I recommended passing `parsed` trimmed to the function subtree **keeping document ids**, and noted the
`syntaxNodeCount` guard would need changing. Both parts were wrong.

`merge_reports` translates facts into **slice-rank** space — its docstring says so. Measured on `main`:

| | ids |
|---|---|
| `main`'s **document** ids | 1230–1451 |
| merged `calls` syntaxIds | 23, 38, 53, 74, 105, 127, 132 |
| merged `expressionTypes` syntaxIds | 5–221 |
| overlap with document ids | **0 of 222** |
| overlap with rank range 0–221 | **7/7 calls, 161/161 types** |

A1 already produces the matching `ParserProgress` for every function — `slices[name]`, with ids **0..221**. Feed that plus
`reports[name]` and everything lines up with no guard change at all:

```
A1 sliced main: 222 nodes, ids 0..221 (rank space)
syntaxNodeCount in report: 222  vs  len(sliced.nodes) 222     <- guard passes as written
estimated request 275,807 B  (limit 1,048,576)                <- fits with 772 KB spare
```

So the fix is not a signature change. **The fragment entry works today if the host passes its own sliced progress**, which
A1's driver already builds for sectional emission. My A3-115 "trim and keep document ids" advice would have required
modifying the guard *and* produced a report/node id mismatch — it is withdrawn.

## Result at the correct id space

| outcome | count |
|---|---|
| **EMITTED** | **18** |
| `Pep C23 loop assignments must target a direct mutable local` | 10 |
| `Pep C23 calls require a known target` | 2 |
| `PEP_RUNTIME_STEP_LIMIT` | 1 |
| worst emitted fragment | **36,770 steps** (37% of budget) |

So the step budget is **not** the binding constraint for `main` at statement granularity — 18 fragments emit comfortably. The
blockers are two lowering gaps and one oversized statement.

## The two gaps, localised so cross-fragment binding is excluded

| fragment | outcome |
|---|---|
| `[0,2)` `var err = 0` + `var neg1 = 0 - 1` | EMITTED |
| `[0,7)` declaration **and** the first `if` together | `loop assignments must target a direct mutable local` |
| `[6,1)` the `if` alone | same refusal |
| `[16,1)` `var e = 0` | EMITTED |
| `[16,2)` `e`'s declaration **and** its `if` together | `calls require a known target` |

Because `[0,7)` and `[16,2)` contain the declaration in the same fragment and still refuse, **carried-binding resolution is
not involved**. These are statement-lowering gaps:

1. **`if` body assigning to a `var`** — `if h1 == neg1 { err = 1 } else { }` refuses with a message about **loop**
   assignments. The diagnostic names loops for an `if` statement, which suggests either a shared code path or a misapplied
   message; either way the construct is unsupported. 10 statements affected.
2. **`if` body assigning a cross-chunk call result** — `if err == 0 { e = scan_digits(source, ds) } else { }` refuses with
   `calls require a known target`. A2-S1 covered cross-chunk calls in conditions and var initialisers; a call as an
   **assignment RHS inside an if body** is a third position. 2 statements affected.

Both sit with **A2** (`tests/pep_c23_emitter.pep`). Together they account for 12 of `main`'s 31 statements.

## The one oversized statement

Statement `#23` — `if err == 0 { say("int main") say(int_text(40)) … }` — hits `PEP_RUNTIME_STEP_LIMIT` as a single fragment.
So at least one statement of `main` needs sub-statement handling, or the `say(int_text(...))` run needs its own treatment.
This is the only place today where the step budget genuinely binds.

## My errors in this investigation, recorded

Three, all mine, all caught before publishing:

1. I read field index 0 of a `ResolvedCall` as `syntaxId`; it is `callerId`. The `100000` values I saw are the checker's
   semanticId base (`activeFunctionId = 100000 + ordinal`), not syntax ids.
2. My first trim experiment reported 17 refusals that were **artifacts** of feeding document-id nodes to rank-space facts.
   I nearly published them as emitter gaps. The tell was that `cross-chunk call has no resolved call fact` should not have
   survived A2-S1 — checking why it did revealed the mismatch.
3. A3-115's recommendation was wrong, as above.

## Method note — still a mixed lane

A1's `pep_sectional.py` (`9bf18699`) driving A2's checker and emitter (`d02f0f4a`). It reproduces 21/21 chain CHECK, but the
combination is not a real integration and these numbers should be re-measured on the candidate tree. The *relative* picture
(which statements refuse and why) should hold, since each refusal is attributed to a specific emitted construct.

## Limits

- Statement-level only. Multi-statement fragments were used to localise, not to look for a working split.
- `main` has 31 top-level statements; I did not attempt sub-statement splitting of `#23`.
- One source revision (`ca732536`), one emitter pin, one seed.

REF GH #16. Supersedes the recommendation in `6725226403` (A3-115). Emitter A2 `d02f0f4a`; driver A1 `9bf18699`. Finding: A3.