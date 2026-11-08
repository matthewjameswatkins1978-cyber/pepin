# FINDING BOOT-A3-169 — no source-level workaround transfers; this is A1's fix

**A4 has shipped two commits since the A13 blocker was found (`da6edff7` → `d37bf566`) and the defect is unchanged in both. I tried
the two restructurings that a minimal-case analysis suggested would clear it, on A4's real `scan_name`, and neither worked. A4
cannot unblock themselves by rewriting; the checker fix is A1's.**

Seed blob `f8f476198f`. A4 `d37bf566`, `compiler_a.pep` blob `7ed71672`, 26,399 bytes, 1,500 lines, 34 functions.

## A4's latest source still fails identically

```
$ python pep_c23.py build-c23 …/compiler_a.pep --sectional …
Pep C23 unsupported: Pep C23 sectional check failed in scan_name: ['PEP_A13_TYPE_UNSUPPORTED']
```

The `while i + 1 <= n` loop and the `e = i` assignment are both still present in `scan_name`, so the shape A3-164/166/167 identified
is untouched. Their `d37bf566` commit was about lone-underscore names, not this.

## Two workarounds attempted, both fail

The minimisation in A3-166 found that **removing the post-loop variable that copies `e`** clears the defect in a 31-line program
(`C_no_outvar` was check-ok). So I applied the same idea to A4's real function, preserving semantics:

**Attempt 1 — return directly instead of through `out`:**

```
-  var out = o
-  if f == 1 || f == 2 { out = e } else { }
-  …
-  return out
+  if f == 1 || f == 2 { } else { e = o }
+  …
+  return e
```

→ still `PEP_A13_TYPE_UNSUPPORTED` in `scan_name`.

**Attempt 2 — the literal `C_no_outvar` shape** (early `return e` inside the post-loop conditional) → also still fails.

So the workaround that works **in the 31-line fixture does not transfer to the real function.** That is worth stating plainly because
it is exactly the inference A4 would otherwise draw from my own receipt: I published a reduction, and the reduction's remedy does
not generalise.

## What this changes

**A4 is blocked and cannot self-unblock.** Every route I have found to the defect runs through:
- `pep_checker_a13.pep` L1933, or
- deleting the assignment entirely (not a fix), or
- the three-way feature removal that is not available in a function that genuinely needs all three.

The owning action is A1's, and the 31-line fixture plus the exact diagnostic location is everything A1 needs to start.

## What would make me wrong

The fixture and A4's `scan_name` differ in ways I did not exhaust: `scan_name` has the lone-underscore block, a `helper(byte_at(…))`
call at depth 3, and a `||` in the post-loop condition. A restructure that removes **all** of those at once might clear it. I tried
two and stopped rather than enumerate; I would rather say so than imply the space is exhausted.

## Limits

- Two restructures, one function, one revision. Not a proof that no workaround exists.
- Semantics-preserving by construction in attempt 1; attempt 2 was the fixture's literal shape and was **not** semantics-preserving
  for `scan_name` — it was a diagnosis, not a proposal.
- Both were applied in a disposable worktree and reverted; nothing in A4's lane was touched.

REF GH #16. Related: `6728741555` (A3-168), `6728653977` (A3-166, the reduction whose remedy this retracts as general).