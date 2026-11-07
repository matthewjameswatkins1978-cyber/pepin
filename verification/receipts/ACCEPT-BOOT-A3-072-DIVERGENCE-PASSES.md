# ACCEPT BOOT-A3-072 — DIVERGENCE-2 PASSES: 16/16, input-dependent C23 produced, compiled and run

**Verdict: DIVERGENCE-2 is demonstrated. Two unseen inputs produce byte-different generated C, which compiles
under strict Clang AND GCC and runs to different outputs. This is the first time in the campaign that the
input-dependent C sub-claim holds end to end.**

## The run

`codex/a2-divergence-spike @ 3ad2bff`, disposable worktree, `verification/probes/divergence_2_042.py`:

```
PASS D1:host-valid
PASS diag:call-facts
PASS D2:emits              generator C = 11757 bytes
PASS D2b:generator-builds  clean
PASS run:generator-A       exit=0 sha256=29eee68f4a58 bytes=76
PASS run:generator-B       exit=0 sha256=e72d299afce6 bytes=76
PASS D3:generated-C-differs
PASS D4:generated-A-compiles-clang / -gcc      clean
PASS D5:generated-A-runs-clang    stdout='abc_divergence_input' exit=0
PASS D5:generated-A-runs-gcc      stdout='abc_divergence_input' exit=0
PASS D4:generated-B-compiles-clang / -gcc      clean
PASS D5:generated-B-runs-clang    stdout='xyz_divergence_input' exit=0
PASS D5:generated-B-runs-gcc      stdout='xyz_divergence_input' exit=0
PASS D5:outputs-differ
16 checks, 16 passed
DIVERGENCE-2: INPUT-DEPENDENT C PRODUCED
```

## Exactly what this proves

1. A Pep-authored program reads **unseen input bytes** and emits **different C23 text** for different inputs.
2. That C **compiles** under strict Clang and strict GCC (`-Werror`).
3. The resulting binaries **run** and print the corresponding input.

This required A2's `+61`-line three-site patch (`utf8_slice`, `int_text` by-name lowering). Without it the test
refused at emission; that is why the floor was unproven from BOOT-A3-042 to A3-071.

## Exactly what this does NOT prove — read this before quoting the result

- **No lexing, parsing or checking by Pep.** The generator app is five statements: slice 22 bytes, four `say`s.
  It is a slice-and-emit, not a compiler. The campaign floor also requires the program to lex, parse and check
  an unseen Pep input; **none of that is exercised here.**
- **The emitter itself is not self-hosted.** Code generation is done by the seed's existing C23 emitter. This run
  shows a Pep program *driving* that emitter over input, not a Pep-written emitter.
- **Scoped to inputs that are valid C string literals.** The fixture supplies the complete literal
  (`"abc_divergence_input"`), so no escaping or arbitrary-byte handling is tested. Feeding real text with quotes,
  backslashes or newlines would fail — measured, in A3-068/069/070.
- **One machine, one seed build, `-O2`, no sanitizers.**

## Two instrument facts worth keeping

- `str_concat` used to build a single C line pushed **emission** past the frozen 100,000-step budget
  (`PEP_RUNTIME_STEP_LIMIT at 9461:59`). The working design avoids it by putting the literal in the fixture. So
  `str_concat` is functional but expensive in this app's shape — a real measured constraint.
- The emitted program's epilogue prints its returned `Int` to stdout, so a captured "generated C" stream ends
  with a bare integer line. The probe now strips exactly one such trailing line, narrowly, and says so.

## Honest record of how this took four corrections

A3-068 blamed the emitter for unescaped input; A3-069 blamed emitter-inserted newlines; A3-070 found the real
cause was my own multi-`say` line building. The standing rule adopted: **before attributing a failure to another
agent's file, reproduce the failure in code I did not write.** Applying it here produced the pass.

REF: GH #16.