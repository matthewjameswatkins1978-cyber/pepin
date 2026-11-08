# GATE REPORT BOOT-A3-156 — candidate `b039fc5`: the product path works, compiler A still cannot build

**Independent result on A1's candidate `b039fc5daadf0e82e2dcbe19b3f8baebe4d1adbd` in a clean disposable worktree
(`D:\Projects\wt-a3-cand`, detached, dirty 0). The real product path exists and works; compiler A is refused at `find_brace`
fragment 11, and both A3-149 epilogue defects reproduce through the product path itself. The gate cannot be satisfied at this
revision.**

Seed blob `f8f476198f`. No peer file edited; the worktree is disposable.

## The product path is real

`pep.ps1 --help` does **not** list `--sectional`, but `pep_c23.py` accepts it (L526) and routes to `pep_sectional.build_c23`
(L461-463). The help text is stale, not the capability.

**Control — a trivial Pep program through the same path:**

```
$ python pep_c23.py build-c23 _build/ctl/trivial.pep --sectional \
      --output _build/ctl/trivial.exe --emit-c _build/ctl/trivial.c
C23: …\trivial.c
Executable: …\trivial.exe
$ .\trivial.exe
42
```

rc 0. So the sectional path checks, emits, assembles, compiles and runs.

## Compiler A is refused

```
$ python pep_c23.py build-c23 examples/dogfood/pep0/compiler_a.pep --sectional \
      --output _build/ca_test.exe --emit-c _build/ca_test.c
Pep C23 unsupported: Pep C23 fragment 11 of find_brace refused: PEP_RUNTIME_STEP_LIMIT
rc=2   elapsed 13s   emitted C: no   executable: no
```

The diagnostic is good — it names the function and the fragment index, which is a real improvement on the bare
`PEP_RUNTIME_STEP_LIMIT` that `build_c23` raised when I tested it at A1-151. But it stops there: `find_brace` fragment 11 is the
**first** failure under fail-closed ordering, so any later ones are not enumerated by this run.

This is the same wall A3-147/148 measured: `find_brace`'s remaining statements are **5-conjunct `&&` conditions**, growth is
superlinear (~n^1.7: 2→29,807, 3→57,476, 4→94,773, 5→100,001), and the only formulation that emits is a `let` Bool local holding
three conjuncts followed by `if p && <two more>` (max 67,129). Pruning the node list does not help (A3-147).

## Both epilogue defects reproduce on the product path

The emitted C for the control program ends:

```c
int main(void) {
  (void)printf("%lld\n", (long long)(pep_fn_main()));
  return 0;
}
```

- **Defect 2 (A3-149):** the return value is echoed to stdout as an extra line. For the trivial program that `42` is the echo —
  and for compiler A, `EXPECTED.md` pins exactly **nine** lines, so a tenth makes the oracle unsatisfiable.
- **Defect 3 (A3-149):** `return 0` is hardcoded, so no exit code can propagate. Whatever compiler A computes, the process exits
  0 — and the contract's 0/1/2/3/4/5 distinctions are unreachable.

Both are runtime-epilogue issues in the emission path, not compiler-A source issues.

## Fail-closed behaviour holds

```
$ python pep_c23.py build-c23 _build/ctl/bad.pep --sectional --output _build/ctl/bad.exe
Pep C23 unsupported: Pep C23 sectional check failed in main: ['PEP_TYPE_MISMATCH']
```

No C, no executable. **no-C-on-failure is verified on the product path.**

## My own instrument is stale — correcting it

`verification/probes/emit_any_049.py` reported *"REFUSED BY THE CHECKER"* on `find_brace` (288 nodes) while the product path got
past checking to emission. Cause: the probe invokes the older `pep-c23-checker-chunk` tool with empty bindings and no
`expect_returns`, whereas A1's driver calls `bound-chunk` with carried bindings, `expect_returns` and a `fact_closure`-restricted
external set. **Different tools, so the probe's check verdict is not evidence about the product path.**

From here I treat the product path as authoritative for check status and will retire or re-point that probe rather than quote it.

## Gate verdict at `b039fc5`

**NOT PASSED.** Reasons, in dependency order:

1. `find_brace` fragment 11 — `PEP_RUNTIME_STEP_LIMIT`. Owned by A4 (source rewrite) or A2 (cost), per the A3-148 measurement.
2. The runtime epilogue — return echo and hardcoded `return 0`. Owned by A1/A2.
3. Consequence of 1: no compiler A binary exists to test, so input-dependent output, the seven unsupported cases, the malformed
   set and stdout/stderr/exit distinctions are all **untested on the product path** at this revision.

## What I will run the moment a buildable candidate exists

Clean checkout; `build-c23 --sectional` only, no overlays or hand assembly; strict `clang -std=c23` and `gcc -std=c2x`; the
thirteen pinned oracle cases; both unseen forms; the seven unsupported cases from A3-153; the malformed set; stdout, stderr and
exit code checked separately; the no-C-on-failure property; and an audit that no Python or OCaml semantic compiler is reachable
from the native binary's execution path.

## Limits

- One revision, one worktree, one toolchain run for the control (`--compiler` default Clang).
- Fragment enumeration is fail-closed, so "fragment 11" is the first, not the only, failure.
- The seven unsupported cases were not re-executed here — there is no binary. Their source-level trace stands (A3-155).

REF GH #16. A1: the exact command above reproduces this in 13 seconds from a clean checkout. A2/A1: the epilogue text is quoted
from the emitted C, not from my model.