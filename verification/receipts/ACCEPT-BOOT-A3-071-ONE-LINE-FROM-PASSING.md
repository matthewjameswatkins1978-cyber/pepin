# BOOT-A3-071 — DIVERGENCE-2 is one line from passing; the remaining failure is my probe's output capture

**Verdict: 7/11 again, but the failure moved. The generated C is now syntactically plausible and the two unseen
inputs differ correctly. The only remaining defect is that my probe writes the emitter epilogue's `Int` echo into
the `.c` file.**

## Current state on `3ad2bff`

```
PASS D1:host-valid
PASS diag:call-facts
PASS D2:emits              generator C = 11757 bytes
PASS D2b:generator-builds  clean
PASS run:generator-A       exit=0 sha256=622591bf6ee8 bytes=78
PASS run:generator-B       exit=0 sha256=52634683897e bytes=78
PASS D3:generated-C-differs
FAIL D4:generated-A-compiles-clang  line 5: expected identifier or '('
FAIL D4 x4
11 checks, 7 passed
```

Generated C from input A:

```
#include <stdio.h>
int main(void){puts(
"abc_divergence_input"
```

That is **valid C so far** — the literal is complete on its own line, which is exactly what BOOT-A3-070's
line-per-`say` reasoning predicts. The compiler error at line 5 is on the **trailing `0`**:

```
);return 0;}
0
```

## Cause

The emitted program's epilogue prints its returned `Int` to stdout (observed independently in BOOT-A3-064, where
`s_exitcode.pep` produced `stdout='6' exit=0`). My probe captures the generator's **stdout** and writes all of it
to `div2_out_A.c`, so the epilogue's `0` lands in the C file as a stray token.

**This is my probe's capture, not the emitter's output.** The real compiler writes generated C to a file and never
mixes the epilogue's echo into it.

## The fix (one line, mine)

When writing the captured generator output to `div2_out_A.c` / `div2_out_B.c`, drop a single trailing line that
is purely an integer. It should be a documented, narrow strip — `^-?[0-9]+$` on the final line only — not a
general text filter, so nothing else can be silently discarded.

## What the successful run in the previous step established

I had to abandon the `str_concat` line builder: building a single C line with two `str_concat` calls pushed
**emission** over the frozen 100,000-step budget (`PEP_RUNTIME_STEP_LIMIT at 9461:59`), which is a real measured
cost of the `str_concat` lowering in this app's shape. The working approach is cheaper: put the complete C string
literal **in the fixture**, so the generator only needs `utf8_slice` and four literal `say`s:

```
fn main(source: SourceBytes) -> Int {
  let part = utf8_slice(source, 0, 22)
  say("#include <stdio.h>")
  say("int main(void){puts(")
  say(part)
  say(");return 0;}")
  return 0
}
```

Fixtures are now 22 bytes, quotes included: `"abc_divergence_input"` and `"xyz_divergence_input"`.

**Honest limit of this design:** the fixture supplies an already-valid C literal, so arbitrary byte escaping
remains untested, and the demonstration is scoped to inputs that are themselves valid C string literals. That is
a real restriction, not a cosmetic one, and it must travel with any floor claim made from this run.

REF: GH #16.