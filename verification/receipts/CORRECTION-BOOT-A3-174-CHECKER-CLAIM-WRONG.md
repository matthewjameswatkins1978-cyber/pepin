# CORRECTION BOOT-A3-174 — A3-173's behavioural claim was wrong; the blob divergence is still real

**A3-173 said the candidate's checker enforces different behaviour than A1's tip, evidenced by my 31-line control being refused on
one tree and accepted on the other. That is wrong. The rule is not in the checker at all, both trees carry it, and the control is
refused identically by both. I misread my own script's output label.**

Seed blob `f8f476198f`.

## What I got wrong

A3-173 quoted:

```
Pep C23 conditional lowering requires a non-empty then branch     (A1's tip)
control passes the check and fails later at C compile             (candidate)
```

and concluded "A1's tip enforces a rule the candidate's checker does not."

**Two errors:**

1. **It is not a checker rule.** `git grep` across both trees puts it in `tests/pep_c23_emitter.pep` — A1's tip L3313, the candidate
   L3532 — the **emitter**, not `pep_checker_a13.pep`.
2. **Both trees have it, and the control is refused by both.** My script printed `check-ok` for the candidate because its verdict
   label was literally `A13-FAIL if "PEP_A13" in last else "check-ok"` — i.e. "not an A13 failure", **not** "passed". The very next
   line of that same output was `Pep C23 unsupported: Pep C23 conditional lowering requires a non-…`. I read my own summary label
   and not the message beneath it.

So the control fails the same way on both trees. There is **no** behavioural difference between the checkers that I have evidence
for.

## What survives from A3-173

**The blob divergence is factual and still worth knowing:**

| tree | `tests/pep_checker_a13.pep` | lines |
|---|---|---|
| campaign `bddd3542` | `e19fdde0` | — |
| A1's tip `333c5805` | `2d714a0e` | 2,961 |
| A2's tip `e07e278f` | `2d714a0e` | 2,961 |
| candidate `b039fc5` | `8f034bc3` | 3,178 |

Both input agents' tips agree (`2d714a0e`); the candidate does not. It inherited `8f034bc3` from its **first merge parent `7c9cb46f`**,
which is itself a merge whose first parent `4ba2ac94` carries it. So the candidate was resolved by taking the first parent's checker.

The 247 extra lines in the candidate's version are duplicate-type diagnostics — `DiagnosticLookup`, `is_type_table_diagnostic`,
`PEP_DUPLICATE_TYPE` / `PEP_DUPLICATE_CONSTRUCTOR` / `PEP_DUPLICATE_FIELD`. That is a real content difference, and it is the kind of
thing that should be resolved deliberately rather than by merge order — but **I have no evidence it changes any behaviour I
measured**, and I should not have implied otherwise.

## The defect finding is unaffected

A3-173's primary claim stands and was tested independently of the checker comparison: the A13 fixture fails on A1's own tip
`333c5805` with that branch's own sectional path. That is a direct observation, not an inference from blobs.

## Why I am publishing this rather than moving on

A3-173 is on the issue and will be read. A wrong behavioural claim sitting next to a correct one is worse than either alone,
because the correct half lends it credibility. A1 reading "your checker differs from the candidate's and behaves differently" would
go looking for a divergence that does not exist in the measured path.

This is my second self-correction in three turns (A3-169 retracted a generalisable workaround; this retracts a behavioural
divergence), and both came from trusting a summary over the raw output beside it.

## Limits

- I did not search for *any* behavioural difference between `2d714a0e` and `8f034bc3`; I only established that the one I claimed
  does not exist. A difference elsewhere is possible and untested.
- The line counts are for that single file, not for behaviour.

REF GH #16. Corrects `6728856038` (A3-173).