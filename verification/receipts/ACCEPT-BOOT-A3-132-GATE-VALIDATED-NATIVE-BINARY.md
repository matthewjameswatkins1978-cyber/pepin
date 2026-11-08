# ACCEPT BOOT-A3-132 — the M-1 gate now validated against a native binary, not just Python stubs

**A3-081 calibrated the M-1 gate against deliberate Python stubs. Compiler A will be a compiled native executable, which is a
different class of input — process spawn, real exit codes, buffered stdout, argv handling. I built a native C stub with a known
contract and the gate scored it exactly: **5 PASS, 10 FAIL**, with the five passes being precisely the cases whose contract the
stub satisfies.**

Seed blob `f8f476198f`. Oracle `afd2d7e2:examples/dogfood/pep0/EXPECTED.md`. Gate `verify_m1_081.py`.

## The stub and the expected result

A 12-line C program compiled with `clang -std=c23 -Wall -Wextra -Wpedantic -Werror -O2`:

```c
int main(int argc, char **argv) {
  (void)argv;
  if (argc < 2) { return 3; }
  fputs("ERR shape", stdout);
  return 1;
}
```

It satisfies one oracle contract — **exit 1, stdout `ERR shape`** — and nothing else. Five of A4's thirteen pinned cases
require exactly that: `a_badbrace`, `a_u8`, `a_nul`, `a_foo`, `a_gfn`.

## Result

```
PASS a_badbrace.pep   exit=1 stdout 9 chars
PASS a_u8.pep         exit=1 stdout 9 chars
PASS a_nul.pep        exit=1 stdout 9 chars
PASS a_foo.pep        exit=1 stdout 9 chars
PASS a_gfn.pep        exit=1 stdout 9 chars
FAIL a_ok.pep         exit=1 (want 0) stdout='ERR shape' (want 'int main…42…')
FAIL a_badlit.pep     exit=1 (want 2) stdout='ERR shape' (want 'ERR literal')
FAIL a_str.pep        exit=1 (want 5) stdout='ERR shape' (want 'ERR unsupported')
FAIL a_empty.pep      exit=1 (want 0) stdout='ERR shape' (want '')
FAIL a_crlf.pep       exit=1 (want 0) stdout='ERR shape' (want 'int main…42…')
FAIL a_big19.pep      exit=1 (want 4) stdout='ERR shape' (want 'ERR longlit')
FAIL a_dup.pep        exit=1 (want 3) stdout='ERR shape' (want 'ERR junk')
FAIL a_grt.pep        exit=1 (want 2) stdout='ERR shape' (want 'ERR literal')
FAIL u_single_space   exit=1 (want 0) …           <- the two unseen forms
FAIL u_tab_indent     exit=1 (want 0) …
15 cases, 10 failed — M-1 COMPILER A: FAIL
```

Exactly the five cases the stub satisfies pass; every other case fails with its own observed-versus-wanted line. No crashes, no
mis-captured exit codes, no stdout truncation, and no case silently skipped — the two *unseen* forms I predicted from S0's
grammar behave like ordinary cases and fail for the right reason.

## What this adds over A3-081

A3-081 proved the gate could fail, using `sys.executable` scripts. That left a real question: would it behave when the
"compiler" is a native executable with Windows path handling, `argv[1]` as a file path, and buffered stdout? This closes it.

It also demonstrates the property that matters for real use: **partial implementations are scored partially.** A compiler A
that handles the reject cases but not the accept cases would show exactly this shape — five passes and a list of specific
failures — rather than an all-or-nothing verdict.

## Limits

- One stub with one contract. It does not exercise a binary that emits the valid 9-line C, so the gate's handling of a
  *positive* pass is still only shown by the earlier Python stub (A3-081 case [1], where `a_ok` and `a_crlf` passed).
- The stub never reads its argument, so argv-path handling is exercised only as far as passing the path does not crash it.
  Compiler A must actually read the file, which this does not test.
- Native behaviour verified on Windows/clang only; no gcc-built stub was run through the gate.
- Both stubs are throwaway; nothing committed, worktree clean.

## Reproduce

Write the stub above, `clang -std=c23 -Werror -O2 stub.c -o stub.exe`, then load `verify_m1_081.py` as a module and call
`gate([exe], PINNED, …)` and `gate([exe], UNSEEN, …)`. Passing the JSON `--compiler-cmd` through PowerShell mangles the
backslashes, so call the functions directly from Python.

REF GH #16. Extends `READY-BOOT-A3-081` (the gate's original calibration) to native executables.