# FINDING BOOT-A3-134 — A2's `prepend+reverse` is byte-clean, but its builtin skip list breaks a legal program: `str_contains` is not reserved

**I went back to the two correctness risks I had flagged in A2's landed commits and never tested. The first is clean: the
`prepend+reverse` branch refactor preserves emitted C **byte-identically**. The second is a real defect — the skip list
includes `str_contains`, but the seed does **not** reserve that constructor name, so a valid Pep program using it is refused
with the builtin's diagnostic.**

Seed blob `f8f476198f`. Emitter `94194842` (current). Driver A1 `9bf18699`.

## Risk 1 — `cf09930e`'s prepend+reverse: CLEAN

A2 rewrote the if-branch body assembly from `append` to `prepend` + `reverse`. That is exactly the class of change that can
reorder emitted output, and I had only measured its **step cost** (A3-124), never the bytes. Now measured:

| branch shape | before `651d9124` | after `cf09930e` | identical |
|---|---|---|---|
| 4 statements (`say`×3 + assignment) | 240 B, `388909B1951CFADE…` | same | **yes** |
| 8 statements (`say`/assignment interleaved) | 389 B, `791A6C06219B9270…` | same | **yes** |

Statements come out in source order in both, including an interleaved `say`/assignment sequence, which is the shape that
would expose a reversed assembly. The refactor is order-preserving.

## Risk 2 — `94194842`'s builtin skip list: REAL DEFECT

A3-130 flagged, and I then failed to check: *"If one of them could be a user union variant, skipping the scan there would be
wrong."* It can.

**The seed reserves seven of the eight names, and not the eighth:**

```
byte_length   invalid  PEP_RESERVED_CONSTRUCTOR
byte_at       invalid  PEP_RESERVED_CONSTRUCTOR
str_concat    invalid  PEP_RESERVED_CONSTRUCTOR
contains      invalid  PEP_RESERVED_CONSTRUCTOR
length        invalid  PEP_RESERVED_CONSTRUCTOR
utf8_slice    invalid  PEP_RESERVED_CONSTRUCTOR
int_text      invalid  PEP_RESERVED_CONSTRUCTOR
str_contains  VALID    <- a union variant may take this name
```

So this is legal Pep:

```pep
type MyT = str_contains(Int) | other()

fn main() -> Int {
  let v = str_contains(3)
  return 0
}
```

The checker says **valid**. The emitter, because it skips the union-variant scan for `str_contains`, treats the constructor
call as the **builtin** and refuses:

```
Pep C23 str_contains requires exactly two supported Str values
```

A control proves that is the shadowing and not a union limitation: the same program with any other variant name emits fine —

```c
pep_union_0 pep_local_6 = (pep_union_0){ .tag = 0, .payload.payload_0 = { .field_0 = 3 } };
```

**The fix, verified:** remove `str_contains` from the skip list. With that one deletion the shadowing program emits the
correct union constructor C above. It is A2's file and A2's call, but the change is one word.

## Severity, stated honestly

**A false refusal with a misleading diagnostic, not a silent miscompile.** Confined in practice because:

- seven of the eight names cannot be shadowed at all;
- the one that can, `str_contains`, takes `Str` arguments in its builtin form, and `Str`-payload unions are unsupported
  generally (`type MyT = some(Str) | other()` refuses with "tagged union has an unsupported layout"), so a shadowing variant
  can never satisfy both the builtin's signature and a supported union layout.

So the worst outcome is: valid code refused, with a message about the wrong construct. That is still worth fixing — a compiler
that rejects legal input because an optimisation assumed a name was unavailable is a correctness bug, and the assumption was
untested when it landed.

## The pattern worth naming

This is the third time in this lane that an **optimisation** quietly narrowed correctness: the arithmetic `may_fail` rule
(A3-078), the node-count guard removal (A3-118), and now a name-based skip. In each case the performance reasoning was sound
and the invariant it relied on was unstated. A cheap habit that would have caught all three: **when an optimisation skips work
because of a name or shape, test that the language cannot produce the name or shape.**

## Limits

- One shadowable name found among eight; I did not exhaustively test every builtin in the emitter, only the eight in the skip list.
- `Str`-payload union support and the resulting severity bound were tested with one control each.
- The fix was applied to a scratch copy and removed; nothing written to A2's lane. Worktree cleaned and verified.
- I did not re-run A2's own test suite at this pin, so I cannot say whether their tests cover shadowing.

REF GH #16. Closes the two open risks from `6725828195` (A3-130) and `6725640570` (A3-124).