# CORRECTION BOOT-A3-069 — the newlines are inserted by the emitter, not carried by the input

**This corrects the diagnosis in BOOT-A3-068.** I claimed the emitted literal contained the input's raw
newlines. That was wrong: with **newline-free inputs** the generated literal still spans multiple lines, so the
line breaks are produced by the emitter's own literal formatting.

## The experiment

I rewrote the divergence fixtures to single line, no trailing newline (`abc_divergence_input` /
`xyz_divergence_input`, 20 bytes each, no `0a` anywhere) and re-ran against `3ad2bff`. D4 failed identically:

```
FAIL D4:generated-A-compiles-clang  error: missing terminating '"' character
FAIL D4:generated-A-compiles-gcc
FAIL D4:generated-B-compiles-clang
FAIL D4:generated-B-compiles-gcc
```

The generated C, read directly from `_build/div2_out_A.c`:

```
1: #include <stdio.h>
2: int main(void){puts(
3: "
4: abc
5: ");return 0;}
```

Line 4 reads `abc` even though the input is `abc_divergence_input`. So the literal is **not** a raw dump of the
input either — it is a formatted multi-line literal containing a shortened value. Two separate facts:

1. **The emitter writes a string literal across physical lines** (a real newline after the opening quote and
   before the closing quote), which is invalid C regardless of the input.
2. **The value inside is shorter than the input**, so the slice bounds — not just the escaping — are part of the
   same defect area.

## What still holds from 068

- D1-D3 pass: two unseen inputs produce **different** generated C, and the *generator* itself compiles and runs
  cleanly under both compilers (`run:generator-A/B`, exit 0, distinct C sha256s).
- D4 is the only failing group, so **differing output remains unproven**.

## What changes

My instruction to A2 was "escape the input bytes". That is necessary but **insufficient**: the emitter must stop
emitting a literal that spans lines at all, and the slice bounds feeding it need checking. I have stated this as
a correction rather than leaving a precise-sounding but incomplete bug report in place.

## Fixture state, disclosed

`verification/fixtures/divergence/input_a.txt` and `input_b.txt` are now **single-line, no trailing newline**
(20 bytes each), committed with this receipt. The previous two-line versions were what the original
DIVERGENCE-2 design used; both are equally valid *unseen inputs*, and the change is recorded here rather than
made silently. If the original two-line fixtures are preferred as the canonical pair, say so and I will restore
them.

## Honest limits

- One run, one branch (`3ad2bff`), one seed build.
- I did not read A2's divergence test app source, so I cannot yet say why the literal holds `abc` rather than the
  full input; that is the next thing to inspect.

REF: GH #16.