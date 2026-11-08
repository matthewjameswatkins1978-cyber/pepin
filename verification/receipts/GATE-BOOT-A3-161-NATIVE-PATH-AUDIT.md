# GATE EVIDENCE BOOT-A3-161 — no hidden semantic compiler in the native execution path

**The mission requires proving that compiler A's binary is genuinely native. It is. The executable links `KERNEL32.dll` and
nothing else, contains zero occurrences of any Python, OCaml, opam or interpreter marker, and fails closed when it cannot obtain
its byte grant.**

Binary: 147,456 bytes, built `clang -std=c23 -O1` from the committed product-path C
(`verification/fixtures/a3-compilerA-productpath.c`, the same C that scores M-1 15/15).

## Imports

```
DLL Name: KERNEL32.dll
```

No `python3*.dll`, no OCaml runtime, no `libffi`, no JIT. A Win32 program with the C runtime and nothing else.

## String scan of the binary image

| marker | occurrences |
|---|---|
| `python` / `Python` | **0 / 0** |
| `ocaml` / `OCaml` | **0 / 0** |
| `pep_ocaml` | **0** |
| `opam` | **0** |
| `libpython` | **0** |
| `.py` | **0** |

## Fail-closed without its grant

```
$ ./ca.exe
PEP_RUNTIME_SOURCE_CONTEXT      (stderr)
exit 1
```

No `argv[1]`, no bytes, no work — the program refuses before the entry runs, exactly as the grant contract specifies. It cannot
conjure source.

## What this establishes, and what it does not

**Establishes:** the M-1 15/15 result in A3-159 was produced by native code executing Pep semantics, not by a host process
compiling Pep underneath. Every one of the 21 functions is compiled C; the classification, the number parsing and the output are
the binary's own work.

**Does not establish:** that the binary is *correct beyond* its pinned contract — A3-160 shows seven class-(ii) misclassifications
in this same binary — and it says nothing about the tracked tree, since the four A3-159 patches remain probes in a disposable
worktree.

## Method note

An earlier check using `nm` reported zero `pep_fn_` symbols and I flagged it as inconclusive, because a stripped or
non-symbol-bearing binary would also produce zero. This PE import table and the byte-level marker scan are the checks that
actually answer the question.

REF GH #16. Supports `6728365639` (A3-159, the M-1 result). Related: `6728382343` (A3-160, the seven in this same binary).