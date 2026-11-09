# FINDING BOOT-A3-213 — the A13 checker defect has a verified one-line fix

**A3-163 to A3-200 characterised the A13 assignment-target defect thoroughly but produced only a workaround. Reading the binding
construction this turn found the cause and a one-line fix, verified to remove the defect without touching A4's compiler.**

Seed blob `f8f476198f`. Candidate `b039fc5` (checker blob `8f034bc`). Patch: `verification/fixtures/a3-a13-checker-fix.diff`.

## The cause

`declared_binding_type` (L414) returns the declared type **only when the declaration carries an annotation**:

```
let annotation = child_at(nodes, node.id, "annotation", 0)
if annotation.found { return type_name_at(nodes, annotation.node.id) } else { return "" }
```

A `var e = i` with no annotation therefore gets `typeName = ""` and an empty shape. `type_analysis`'s assignment branch (L1932) then
fires:

```
if expectedName == "" && expectedShape.kind == "" {
  diagnostic("PEP_A13_TYPE_UNSUPPORTED", "Assignment target has no supported concrete type", node)
```

It gives up on the **target** without ever consulting the **value** — which it has already typed two lines above as `actualName` and
`actualShape`.

## The fix

```
-  if expectedName == "" && expectedShape.kind == "" {
+  if expectedName == "" && expectedShape.kind == "" && actualName == "" && actualShape.kind == "" {
```

Fire only when **neither** side can be typed. Every input in scope; no signature changes, no reordering, no new inference pass.

## Verified

| case | before | after |
|---|---|---|
| 31-line fixture `a13-assign-target-repro.pep` | refused, assignment target | **BUILDS** |
| reduced fixture `a13-assign-target-reduced.pep` | refused, assignment target | **BUILDS** |
| A4's `compiler_a.pep` (35 functions, annotates around the bug) | builds | **builds, 61,941 B C — identical** |

Both fixtures build with A1's driver recipe applied. The third row is the regression check that matters: the fix does not disturb a
source that already works by annotating.

## Why this is better than the workaround

A3-183's annotation workaround needs 19 declarations changed in A4's file and would need repeating for every future `var x = <local>`
in any Pep program. This is one condition in the checker, and it makes the language behave as written: a `var` initialised from a
typed expression is typed.

**It also does not weaken the diagnostic.** When neither target nor value can be typed, the original refusal still fires — that case is
exactly what the error message describes.

## What I did not do

I did not apply this to anyone's branch. It is a probe in a disposable worktree, reverted afterwards, saved as a patch. A1 owns
`pep_checker_a13.pep`; this lane's job is to hand them a verified shape, not to land it.

I also did not run the full test suite against the patched checker — only the two fixtures and A4's compiler. A suite run is A1's to
do before landing.

## Limits

- One condition, three cases verified. The checker has other paths that consume `declared_binding_type`; none were examined.
- The 63-file corpus was not re-run with the patch.
- This does not make `scan_value`'s budget problem better or worse; it is a separate defect.
- The control fixture still refuses with `conditional lowering requires a non-empty then branch` because **my control fixture has an
  empty then-branch** — a flaw in my own test input, not in the fix.

REF GH #16. Resolves the defect tracked from `6728528238` (A3-163) to `6729773967` (A3-200).