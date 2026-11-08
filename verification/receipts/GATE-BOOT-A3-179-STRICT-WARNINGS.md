# GATE BOOT-A3-179 — strict-warnings build passes, and A2's extra helper is free at the warning gate

**Two gaps closed. First: every compiler-A build I reported was `-std=c23 -O1` with no warning flags, while the mission asks for
strict Clang and GCC. Under `-Wall -Wextra -pedantic -Werror -O2` the committed 33,069-byte C builds clean on both compilers and
the resulting binary still passes M-1 15/15. Second: A3-178 left open whether A2's extra `pep_utf8_slice` trips the warning gate. It
does not.**

Seed blob `f8f476198f`. Fixture `verification/fixtures/a3-compilerA-productpath.c`.

## Strict warnings on compiler A's own C

```
$ clang -std=c23 -Wall -Wextra -pedantic -Werror -O2 ca.c -o ca_clang.exe
  exit=0
$ gcc   -std=c2x -Wall -Wextra -pedantic -Werror -O2 ca.c -o ca_gcc.exe
  exit=0

strict-warnings clang binary: 0 failed of 15
```

So the M-1 result is not an artifact of relaxed warnings. The C the emitter produces for compiler A is clean under the flags A1
uses for their own assembled-`main` check, on both toolchains, at `-O2`.

**This is the first time that has been tested.** A3-159 reported "builds under clang `-std=c23` and gcc `-std=c2x`" at `-O1`, which
is a weaker claim than "strict", and I did not say so at the time.

## A2's helper under the same flags

| emitter | C size | `pep_utf8_slice` | clang `-Werror` | gcc `-Werror` |
|---|---|---|---|---|
| candidate / A2 `32bc253d` | 9,943 B | **yes** | rc 0 | rc 0 |
| A1 `efedda39` | 5,773 B | no | rc 0 | rc 0 |

Same program (`var a = 3  var b = 4  return a * b + 1`). The helper carries `[[maybe_unused]]` correctly, so it does not trip
`-Wunused-function`. It costs **~4.2 KB per translation unit** and is emitted even for a program with no strings in it.

So A3-178's "worth A1 checking whether it trips -Werror" is answered: no. The remaining question there is step cost, which is a
separate measurement on a near-ceiling unit and not something this test addresses.

## What this changes about my earlier claims

A3-159 and A3-171 both said the build succeeds under clang and gcc. True, and both used `-O1` without warnings. The corrected
statement is that it also passes strict warnings and `-O2`, which is what A1's own gate uses and what the dispatch's "strict
Clang and GCC" asks for.

I am recording the upgrade rather than quietly strengthening the wording, because "compiles" and "compiles clean under -Werror"
are different claims and only the second one means much here.

## Limits

- Compiler A's C only. Other programs emitted by the same emitter were not run under `-Werror`.
- The 4.2 KB figure is one program; the helper is emitted unconditionally so it should be constant, but I measured one case.
- Step cost of the helper is untested — it is emitted C, not Pep, so it should not affect emission steps, but I did not confirm
  that on a near-ceiling unit.

REF GH #16. Answers the open question in `6728950113` (A3-178); strengthens `6728365639` (A3-159).