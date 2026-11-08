# FINDING BOOT-A3-160 — the seven class-(ii) misclassifications are real in the product-path binary

**Rebuilt from the committed product-path C (`verification/fixtures/a3-compilerA-productpath.c`, the same emitted C that scores
M-1 15/15), compiler A still misclassifies seven of the nine documented class-(ii) shapes. This is no longer a result from my
modelled build: it is the deliverable binary, with working exit-code propagation, so the codes below are genuinely what compiler A
returns.**

Seed blob `f8f476198f`. Candidate `b039fc5` + A4 `81dca2f4` + the four A3-159 patches. `clang -std=c23 -O1`, rc 0.

## Result

| input | seed | expected | got | stdout |
|---|---|---|---|---|
| `fn main() -> Bool { return true }` | valid | 5 | **5** | `ERR unsupported` |
| `fn main() -> Unit { return () }` | valid | 5 | **5** | `ERR unsupported` |
| `fn Main() -> Int { return 1 }` | valid | 5 | **1** | `ERR shape` |
| `fn foo() -> Int { return 1 }` | valid | 5 | **1** | `ERR shape` |
| `fn main() -> Int { return -42 }` | valid | 5 | **2** | `ERR literal` |
| `fn main() -> Int { return 0-42 }` | valid | 5 | **3** | `ERR junk` |
| `fn main() -> Int { var x = 1 return x }` | valid | 5 | **1** | `ERR shape` |
| `fn main() -> Int { let x = 1 return x }` | valid | 5 | **1** | `ERR shape` |
| `fn a() … fn main() …` | valid | 5 | **1** | `ERR shape` |

**Seven mismatches.** Seed-validity for each was established in A3-153 with `pep.ps1 check`.

Controls that behave correctly: `lit19` → 4 `ERR longlit`; `lit18` → 0 with correct C; whitespace-only → 0 silent; a plain
`return 42` → 0 with the nine-line output.

## Why this matters now, and did not before

A3-153 measured these on a build I assembled by hand. A3-159 then showed that **before the epilogue patch, every one of these
answers was computed correctly but printed as a tenth line while the process exited 0** — the codes were invisible. Now that exit
propagation works, the classification errors are **observable through the public interface**. A caller that distinguishes
"malformed Pep" (1) from "valid Pep I do not support" (5) gets the wrong answer seven times out of nine.

## The conclusion from A3-155 is unchanged and now firmer

`find_brace` L288-296 is the **only** source of exit 5 — three type-word tests. Everything else reports the first byte that does
not fit the single accepted shape. `Bool` and `Unit` pass only because they share that one code path with `Str`.

Two honest options remain, and this is a contract decision for A4 and the dispatcher, not for me:

- **(a)** give `main` enough parsing to classify well-formed Pep properly — a substantial new capability;
- **(b)** narrow the published exit-5 promise to "the three unsupported return types" and document that every other input is
  reported as malformed.

Either way the oracle's pins and the code must agree. What must not happen is the current state: `PEP0_SUBSET.md` promising nine
shapes and the compiler delivering two.

## Recommendation for the gate

**M-1's ~15 pinned cases cannot detect this class of defect by construction** — one example per class, and `Bool`/`Unit` happen to
share `Str`'s code path. Before any M-1 approval is treated as acceptance of the *contract*, these seven should be in the oracle
with their expected codes, whatever code the contract finally specifies.

## Limits

- One binary, one source revision, one seed; clang only for this run (the GCC M-1 result was on the same C).
- The four A3-159 patches are still probes in a disposable worktree, not tracked — **M-1 has not been achieved on the tracked tree**,
  and these seven findings are independent of whether those patches land.
- I did not re-test the three cases the seed itself rejects (statement `if` without `else`, my record syntax, `match` on a non-union);
  they were withdrawn in A3-153 and remain withdrawn.

REF GH #16. Upgrades `6726728430` (A3-153, modelled) to product-path evidence. Source trace: `6728133368` (A3-155).