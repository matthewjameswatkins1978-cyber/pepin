# CORRECTION BOOT-A3-070 — the invalid C is my generator app's fault, not the emitter's

**This retracts the emitter blame in BOOT-A3-068/069. The line breaks come from `say()` appending a newline
after each call, and my DIVERGENCE-2 generator app splits a single C line across five `say()` calls. The emitter
is behaving correctly; my instrument was wrong.**

## The generator app, as written by me

`verification/probes/divergence_2_042.py` L48-58:

```
fn main(source: SourceBytes) -> Int {
  let part = utf8_slice(source, 0, 3)
  say("#include <stdio.h>")
  say("int main(void){puts(")
  say("\"")
  say(part)
  say("\");return 0;}")
  return 0
}
```

Each `say` emits its value **and a newline**. So the generated text is:

```
#include <stdio.h>
int main(void){puts(
"
abc
");return 0;}
```

That is exactly the observed output — and it is what `say` means. A C string literal cannot span physical lines,
so D4 fails. **The emitter did nothing wrong.** I built a generator whose output is invalid C and then blamed the
emitter for emitting it faithfully.

## What this explains, and what it resolves

- "The emitter inserts line breaks" (A3-069): **wrong** — `say` inserts them, by definition.
- "The literal holds `abc` rather than the whole input" (A3-069): `part` is `utf8_slice(source, 0, 3)` — three
  bytes by construction. Not a bounds defect. **My app, my bounds.**
- The escaping theory (A3-068): still worth having eventually for arbitrary bytes, but it is **not** what fails
  this test. An alphanumeric three-byte slice needs no escaping at all.

## Consequence

**A2's `+61`-line three-site patch is not implicated.** `utf8_slice` lowered, produced the right bytes, and the
generator compiled and ran under both compilers (`run:generator-A/B`, exit 0, distinct sha256s). The only failing
checks are a direct consequence of my app's line-splitting.

The fix belongs in **my** file, and is small: build the whole C line as one `Str` and `say` it once, using
`str_concat` (which is emittable — 3 by-name sites):

```
let head = "int main(void){puts(\""
let tail = "\");return 0;}"
let line = str_concat(str_concat(head, part), tail)
say(line)
```

If `str_concat` nests, hoist it; BOOT-A3-063's rule is one fallible operand per expression, so two sequential
`let` bindings are safer than a nest.

## Honest note on this sequence

Three corrections in four turns (061 confound, 069 emitter-inserted newlines, 070 blame direction) is a poor
record for a verification lane, and the common cause is that I built the generator app myself and then
interpreted its output as evidence about someone else's code. The discipline I should have applied: **before
attributing a failure to another agent's file, reproduce the same failure in something I did not write.** That is
what i will do before the next negative claim about the emitter.

## Status

- **Input-dependent C text: proven** (D1-D3, two unseen inputs, distinct generated C).
- **Differing output: unproven**, blocked by my app, not by A2.
- A2 needs no fix from me. The correction is owed to them and is being sent.

REF: GH #16.