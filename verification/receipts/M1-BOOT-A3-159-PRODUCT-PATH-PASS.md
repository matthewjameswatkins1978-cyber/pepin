# M-1 ACHIEVED THROUGH THE REAL PRODUCT PATH — BOOT-A3-159

**Compiler A now builds through `pep.ps1 build-c23 --sectional` with no overlays and no hand assembly, and passes the full M-1
acceptance gate **15 of 15** under strict Clang **and** GCC: thirteen pinned oracle cases plus both unseen forms, correct exit
codes 0/1/2/3/4/5, correct stdout, correct stderr.**

This is on A1's candidate `b039fc5` + A4 `81dca2f4` plus **four patches** in a disposable worktree, each of which I measured to be
necessary. The patches are A1's and A2's to land — I do not certify my own fixes, and the gate result is only as good as those
four changes being applied by their owners.

## Result

```
--- pinned ---                                  --- unseen ---
PASS a_ok       exit=0  stdout 33 chars         PASS u_single_space  exit=0
PASS a_badlit   exit=2  stdout 11 chars         PASS u_tab_indent    exit=0
PASS a_badbrace exit=1  stdout  9 chars
PASS a_str      exit=5  stdout 15 chars         0 failed of 15
PASS a_empty    exit=0  stdout  0 chars
PASS a_crlf     exit=0  stdout 33 chars         M-1 COMPILER A: PASS
PASS a_u8       exit=1  stdout  9 chars
PASS a_nul      exit=1  stdout  9 chars         GCC cross-check on the same emitted C:
PASS a_big19    exit=4  stdout 11 chars         0 failed of 15 -> M-1 PASS
PASS a_foo      exit=1  stdout  9 chars
PASS a_dup      exit=3  stdout  8 chars
PASS a_gfn      exit=1  stdout  9 chars
PASS a_grt      exit=2  stdout 11 chars
```

Emitted C: **33,069 bytes, 745 lines**. Native binary: **147,968 bytes**. No Python or OCaml semantic compiler on the execution
path — the program is 21 Pep functions and a C runtime.

## The four necessary patches

Each was isolated; each removal reproduces a specific failure. The full diff is `verification/fixtures/a3-m1-recipe.diff` and the
emitted C is `verification/fixtures/a3-compilerA-productpath.c`.

**1. Per-statement narrowing in `build_fragmented_function` (A1).** This is A3-146's recipe. Without it: `find_brace` refuses at
statement 11. With it: statement 11 → 14, and emission completes. Two protocol facts cost me a run each and are worth recording:
- The emitter guards `checked.syntaxNodeCount == length(parsed.nodes)`, so **the report's count must be narrowed alongside the
  progress**, not only the progress.
- **Int values travel as JSON strings.** A raw Python `int` count is rejected with `PEP_TOOL_ARGUMENT_VALUE` before the emitter
  runs (the same trap `tests/probe_seam_chunked.py` documents at L695).

**2. Parameter bindings must not be cast as locals (A1).** `find_ds` binds ids 1/3/5 — its parameters. The carried-binding loop
emits `(void)pep_local_<id>` for every carried binding whose id appears anywhere in the slice, and parameter ids do, so it emitted
`pep_local_1/3/5` where the C declares `pep_arg_1/3/5`:

```
error: use of undeclared identifier 'pep_local_3'
20 errors generated.
```

The check `if _bsid not in declared` cannot catch this because `declared` is the full node set, which contains parameters. This is
a **pre-existing latent defect in A1's driver** that nothing reached before, because emission never completed.

**3. Epilogue: drop the echo, propagate the exit code (A1/A2).** `tests/pep_c23_emitter.pep` L5145-5149 emits
`printf("%lld\n", pep_fn_main(...)); return 0;`. Before this patch every one of the 15 cases was **already computed correctly** —
`ERR literal` with the value 2, `ERR shape` with 1, `ERR unsupported` with 5 — and every one failed only because the answer was
printed as a tenth line while the process exited 0.

**4. The A3-148 Bool-local rewrite in `compiler_a.pep` (A4).** Moves the three 5-conjunct `find_brace` conditions to
`let p = <3 conjuncts>` + `if p && <2>`. Without it, narrowing alone stops at fragment 14, the first 5-conjunct statement.

## What this means

The gate is **reachable and now measured end to end**. The remaining work is not discovery:

| owner | change | measured effect of omitting it |
|---|---|---|
| A1 | narrowing (+ report count, string Ints) | find_brace refuses at statement 11 |
| A1 | parameter-binding cast | 20 C compile errors, no binary |
| A1/A2 | epilogue echo + exit code | 15/15 fail on stdout and exit code |
| A4 | Bool-local rewrite | refuses at fragment 14 |

## Limits — read these before quoting the result

- **Not the tracked tree.** Four patches live in a disposable worktree; I authored them as probes and **do not certify them**. The
  product-path claim is conditional on A1 and A4 landing their own versions.
- One candidate, one source revision, one seed (`f8f476198f`), one emitter pin.
- I did **not** run A1's `pep.ps1` wrapper end to end, only `python pep_c23.py build-c23 … --sectional`, which is the command the
  wrapper delegates to with the same arguments.
- The seven A3-153 class-(ii) cases were **not** re-run here; that defect is in `compiler_a.pep`'s classification and is untouched
  by these four patches.
- The six pre-existing A13 failures are unrelated and still open.
- `nm` reported no `pep_fn_` symbols (the binary is stripped or nm is unavailable), so the "no hidden semantic compiler" audit here
  rests on the construction: 21 Pep functions, a C runtime, `malloc`/`fopen` and no interpreter.

REF GH #16. Recipe: `verification/fixtures/a3-m1-recipe.diff`. Emitted C: `verification/fixtures/a3-compilerA-productpath.c`.
Supersedes the modelled result in `6726592523` (A3-150), which was hand-assembled. Related: `6728295887` (A3-158).