# ACCEPT BOOT-A3-138 — 19 of 21 functions built and running from fragments + units; only `find_brace` and `main` stubbed

**A3-137 claimed "19 of 21 compilable". I built it. Ten whole-function units plus **nine fragment-assembled functions**
produce a 24,506-byte C file that **builds under clang and gcc and runs**, with only `find_brace` and `main` stubbed because
those are the two with fragment gaps. That proves the fragment-assembly contract works across nine functions at once, not just
for `main`.**

Seed blob `f8f476198f`. A2 `e07e278f`. A1 host `07af079d`. Unmodified lanes; scaffold assembled by A3 and deleted after.

## Result

```
whole units: 10; fragment-assembled: 9; stubbed (fragment gaps): ['find_brace', 'main']
assembled 24506 bytes
clang: BUILD OK    run exit=0 stdout='0\n'
gcc:   BUILD OK    run exit=0 stdout='0\n'
```

Structure check on the generated file: **33 function definitions**, of which **19 contain `pep_enter()`** — exactly the ten unit
functions plus the nine fragment-assembled ones. The two stubs (`find_brace`, `main`) are plain `{ return 0; }` bodies carrying
the emitted prototypes, so the call graph still type-checks and links.

## The nine fragment-assembled functions

`is_main4`, `is_bool4`, `is_unit4`, `skip_ws`, `scan_digits`, `find_fn`, `find_parens`, `find_ds`, `check_tail` — every one of
these is step-limited as a whole unit and **fully fragmentable**. Each was assembled as:

```
<emitted prototype> {
  pep_enter();
  <one emitted fragment per statement, in source order>
}
```

The emitted prototype carries the real parameter types (`pep_source_bytes pep_arg_1, int64_t pep_arg_3, …`), which is why using
it verbatim matters — my first attempt guessed `int64_t` for all parameters and the compiler caught the conflict.

So the claim A3-137 made from a per-function table is now a working binary: **fragmentation unlocks nine functions that the
whole-unit path cannot emit at all.**

## What this establishes, and what it does not

**Establishes:**

- the fragment contract composes across nine functions simultaneously — no duplicate declarations, no ordering problems, no
  prologue conflicts, consistent parameter naming;
- the assembly recipe is mechanical: prototype verbatim + `pep_enter();` + fragments in order;
- the only thing standing between this scaffold and a real compiler A is **two functions' missing fragments** — `find_brace`
  (7 statements) and `main` (1 statement, #23);
- both toolchains accept the result, so this is not a clang-specific artefact.

**Does not establish:**

- **any M-1 claim.** `main` is a stub returning 0, so the binary does not read Pep input, does not check, does not emit C. It
  prints `0` and exits. This is a *scaffold proving the assembly path*, not a compiler A.
- that the nine functions are semantically right — they link and compile, and their mutual calls resolve, but nothing exercises
  them because the entry point is stubbed.
- anything about the host-side slicing or prologue policy A1 will choose; my wrapper is one plausible assembly, not their
  contract.

## Why it was worth building

A1's next slice is prologue+epilogue assembly. Doing it first in a throwaway showed that the recipe works and that the remaining
gap is precisely two functions — so that slice can be aimed at eleven functions with nine already proven, instead of being
scoped around `main` alone and discovering the other nine afterwards.

It also cost nothing in A1/A2's lane: everything was generated from their unmodified branches into scratch files, now deleted.

## My two bugs, both caught by the compiler

1. I built fragment-assembled signatures assuming `int64_t` for every parameter; the emitted prototype says `pep_source_bytes`
   for the first. Conflict caught at compile time.
2. My stubs kept the prototype's trailing `;`, producing `prototype; { return 0; }`. Also caught immediately.

Both are the same lesson as the rest of this lane: the compiler is a cheaper reviewer than I am, so generate and build rather
than reason about what should work.

## Limits

- Two of 21 functions stubbed, and the stubbed `main` is the entry point, so the binary exercises nothing.
- One source (`ca732536`), one emitter pin, one driver pin, one seed.
- The scaffold C was generated into scratch and deleted; it is reproducible from the recipe above but is not committed as an
  artefact.
- I did not test permutation of fragment order or a prologue that declares locals up front — the fragments declare their own.

REF GH #16. Parents: `6726161829` (A3-137, whose claim this proves), `6726084796` (A3-135), `6725694094` (A3-126).