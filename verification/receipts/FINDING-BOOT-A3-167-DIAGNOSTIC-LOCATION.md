# FINDING BOOT-A3-167 — the diagnostic's own location confirms the statement

**A3-164 identified `e = i` by deleting it. The diagnostic carries its own location, and it names the same statement. That closes
the loop from code to message to exact node without relying on my bisection.**

Seed blob `f8f476198f`. Fixture: `verification/fixtures/a13-assign-target-reduced.pep`.

## The diagnostic, in full

```
code      PEP_A13_TYPE_UNSUPPORTED
message   Assignment target has no supported concrete type
syntaxId  20
startByte 218
endByte   223
```

## What those bytes are

```
bytes 218..223 = 'e = i'

line 13, column 9

   10|   while i + 1 <= n {
   11|     if f == 0 {
   12|       if i == 1 {
   13|         e = i   <<< diagnostic
   14|       } else {
   15|         i = n
```

**The checker flags the assignment target `e`, at that exact statement, inside the loop.** Which is what A3-164 found by deleting
the line and what A3-166 showed only reproduces when the pre-loop conditional and the post-loop `out` variable are also present.

Two independent methods — deletion bisection and the diagnostic's own byte range — agree on the same node. That is as far as I can
take it without reading the inference code.

## One detail worth passing on

`syntaxId` is `20` and typed as an **Int carrying a JSON string**, the same protocol quirk that cost me a run on A3-159. Anyone
comparing it against document ids should know it is a chunk-local rank id, not a document id.

## Summary of the whole chain, for A1

| receipt | contribution |
|---|---|
| A3-163 | A4's source is unbuildable by either path (1 MiB limit one-shot, A13 rejection sectional) |
| A3-164 | the code is eight diagnostics merged; this one is **L1933**, "Assignment target has no supported concrete type" |
| A3-165 | 41-line three-function reproducer, seven eliminations, control passes |
| A3-166 | 31-line reproducer; three-way interaction, removing any one feature clears it |
| **A3-167** | the diagnostic's own byte range names the same statement my bisection did |

Run it in about a minute:

```
python pep_c23.py build-c23 verification/fixtures/a13-assign-target-reduced.pep --sectional --output /tmp/x.exe
```

## Limits

- One seed, one checker revision, product path only.
- I have not read the type-inference path, so the *mechanism* remains a hypothesis (A3-166): loop-assigned binding not visible to a
  post-loop assignment check once an earlier conditional introduced another binding.
- The 31-line fixture no longer reproduces the separate parameter-binding cast bug; the 41-line pair in A3-165 still does.

REF GH #16. Completes `6728653977` (A3-166).