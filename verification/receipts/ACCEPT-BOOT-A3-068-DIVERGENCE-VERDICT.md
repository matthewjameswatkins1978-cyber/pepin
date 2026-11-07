# BOOT-A3-068 — DIVERGENCE-2 against A2's spike: input-dependent C EXISTS, but it is not valid C23

**Verdict: 7 of 11 checks pass. The floor's hard half is demonstrated — two unseen inputs now produce
DIFFERENT C text from a Pep-authored emitter. The failure is narrower and concrete: the emitted C does not
compile because input bytes are written into a string literal without escaping.**

Run: disposable worktree `D:\Projects\wt-a3-spike` @ `3ad2bff` (A2's `codex/a2-divergence-spike`), seed
`_build` reused from the existing gate tree, `PEPIN_GATE_ROOT` pointed at the spike tree,
`verification/probes/divergence_2_042.py`.

```
11 checks, 7 passed
DIVERGENCE-2: NOT DEMONSTRATED
  D4:generated-A-compiles-clang / -gcc
  D4:generated-B-compiles-clang / -gcc
```

## What passed — this is the important part

D1-D3 pass. The two **unseen** inputs produced **byte-different generated C**:

```
input A -> int main(void){puts(
"
abc
");return 0;}
input B -> int main(void){puts(
"
xyz
");return 0;}
```

That is input-dependent C23 text produced end to end. **Until this run, no input-dependent C existed anywhere in
this campaign** (BOOT-A3-042 through 066 all recorded it as absent). A2's `+61`-line three-site patch plus its
pinned tests changed that.

## What failed, exactly

`puts("` + newline + `abc` + newline + `");` is not a valid C string literal — the newline terminates it. Both
compilers reject with `missing terminating " character`. So:

- The failure is **not** in the input→C path, which works.
- The failure is **not** in the slice lowering, which produced the right bytes.
- The failure is **C string-literal escaping**: the emitter must escape at minimum `"`, `\`, and newlines
  (and ideally all bytes outside printable ASCII) when lowering a `Str` value into a C literal.

That is a small, well-bounded defect in the same lowering A2 just added — and it is the last thing between this
branch and a compiling, differing-output binary.

## Scope discipline

- This is A3 verifying A2's slice, which is the correct direction: **A2 wrote it, A3 did not touch it.**
- I did not fix the escaping. It is A2's file, and a verifier's patch cannot be certified by the verifier.
- Not yet run: the five acceptance criteria from the amended proposal, `s5_slice_local.pep`,
  `iso_int_text.pep`, and the native build/run of the two divergent binaries. D4 blocked the run stage, so
  **differing *output* is still unproven** — only differing *C text* is proven.

## Also still true

- `source_bytes` remains at **0** sites; the input here reached the program through whatever path A2's test
  establishes, and whether that path is the v2 host grant of BOOT-A3-066 is **not yet established by me**.
- The branch base is `231caf1`, not `86ff953`, so it still needs a rebase before merge.

REF: GH #16.