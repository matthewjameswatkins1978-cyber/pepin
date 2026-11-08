# FINDING BOOT-A3-149 — a complete Pep-authored compiler A runs end to end, and its output does not match the oracle: two defects

**I built the first complete compiler A. All 21 functions assembled with zero refusals (10 whole units + 11 fragment-assembled),
both toolchains link it, and it reads an unseen Pep file and emits input-dependent text. But its stdout does not match
`EXPECTED.md`: it prints decimal character codes where punctuation belongs, and a trailing line the oracle does not have.**

Seed blob `f8f476198f`. Emitter `e07e278f`. A1 host `07af079d`. Source `compiler_a.pep` blob `ca732536` **with one modelled
rewrite** (below). Scratch deleted; A4's lane untouched.

## What was built

| stage | result |
|---|---|
| chain CHECK on the source | **21/21 valid** |
| assembly | 10 whole units + 11 fragment-assembled, **0 refusals** |
| `find_brace` | 27/27 statements (after the modelled rewrite) |
| `main` | 31/31 statements |
| assembled C | 31,151 bytes |
| clang `-std=c23 -O1` | **build OK** |
| gcc `-std=c2x -O1` | **build OK** |

The rewrite is A3-148's validated fix, modelled in a scratch copy only: each of `find_brace`'s three 5-conjunct conditions is
split into `let p = <3 conjuncts>` followed by `if p && <2 conjuncts>`. The seed checks the modified source **valid**, and
`find_brace` then emits 27/27 where it was 21/24.

## It runs, and it is input-dependent

```
_a3_unseen1.pep  "fn  main() -> Int {\n  return 42\n}\n"   exit=0
_a3_unseen2.pep  "fn main() -> Int { return 7 }\n"          exit=0

clang-built:  int main 40 void 41 123 return 42 59 125 0
              int main 40 void 41 123 return 7  59 125 0
gcc-built:    identical
```

The literal changes with the input (`42` vs `7`), both toolchains agree, and exit is 0. So the compiler genuinely reads, checks
and emits input-dependent text.

## Defect 1 — decimal character codes instead of characters

`EXPECTED.md` for `a_ok` requires exactly:

```
int main
(
void
)
{
return
42
;
}
```

The compiler prints `40` where `(` belongs, `41` for `)`, `123` for `{`, `59` for `;`, `125` for `}`. The cause is in A4's
source, which does:

```pep
say(int_text(40))
say(int_text(41))
say(int_text(123))
say(int_text(59))
say(int_text(125))
```

**`int_text` renders a decimal number, and Pep has no int-to-character builtin.** The seed's builtin list is `append`, `byte_at`,
`byte_length`, `byte_slice`, `contains`, `int_text`, `length`, `prepend`, `reverse`, `say`, `source_bytes`, `str_concat` — there is
no way to turn 40 into `"("` except by writing the literal. So this is not a lowering defect and no emitter work can fix it: the
source as written cannot produce valid C for any input. The fix is `say("(")` and four siblings, in A4's lane.

## Defect 2 — the epilogue echoes `main`'s return value as an extra line

The emitted C ends with:

```c
(void)printf("%lld\n", (long long)(pep_fn_main((pep_source_bytes){ .data = …, .length = … })));
```

so the binary always prints one more line than the compiler said. `EXPECTED.md` pins "stdout exactly these 9 lines", and we see
**10**. This is the runtime epilogue A1/A2 emit, not A4's source, and it needs a decision: either the epilogue stops echoing the
return, or the oracle accepts the extra line. As written, no compiler A can satisfy the oracle.

## Why this is the useful result rather than a setback

Both defects are cheap, precisely located and in different lanes — one source constant, one runtime epilogue. Before this run
nobody knew whether a complete compiler A would produce correct output; now the answer is "it runs and is input-dependent, and it
fails on output form for two named reasons".

**No M-1 claim**: the output is not valid C23, so the milestone is not met. But the gap is now two lines of work rather than an
open question.

## Limits

- The `find_brace` rewrite is **mine, modelled in scratch**, not A4's. A4 may split differently; the mechanism is A3-148's, the
  exact form is not authorised.
- Run on two small S0-shaped inputs only. No negative inputs, no CRLF/NUL/NBSP, no `a_str`/`a_dup` cases from the oracle.
- The narrowed-fragment emission requires the host to compute each target's position in the narrowed list (A3-146's trap); the
  scaffold does that.
- One seed, one emitter pin, one driver pin. Mixed lanes, not a merged tree.

REF GH #16. Builds on `6726520208` (A3-148) and `6726440672` (A3-146). Oracle: A4 `EXPECTED.md` @ `5f62e4b`.