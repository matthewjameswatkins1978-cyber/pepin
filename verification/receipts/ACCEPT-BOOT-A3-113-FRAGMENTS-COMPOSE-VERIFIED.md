# ACCEPT BOOT-A3-113 — A2-S2 statement fragments verified composed: 4 fragments assemble to C that compiles under clang and gcc and computes the right value

**Verdict: A2's `emit_c23_statement_fragment` works, and it composes. I registered the entry as a tool, emitted one fragment per
statement, concatenated them into a function body with the runtime header, and the result compiled clean under strict clang
**and** gcc and returned the arithmetically correct **13**. Carried bindings resolve across fragment boundaries, and — this is
the part that corrects me — node ids are document-stable, so the `tempBase` I told A2 they needed is not needed for this
design.**

Seed blob `f8f476198f`. Emitter `86fcd10e` (A2-S2 field 1).

## Per-statement emission

Source under test:

```pep
fn a3_three(a: Int, b: Int) -> Int {
  let x = a + b
  let y = x * 2
  let z = y - 1
  return z
}
```

| fragment | steps | emitted C |
|---|---|---|
| `[0,1)` | 2,960 | `int64_t pep_local_6 = pep_add(pep_arg_1, pep_arg_3);` |
| `[1,1)` | 2,353 | `int64_t pep_local_10 = pep_mul(pep_local_6, 2);` |
| `[2,1)` | 2,438 | `int64_t pep_local_14 = pep_sub(pep_local_10, 1);` |
| `[3,1)` | 1,580 | `int64_t pep_result = pep_local_14;  pep_leave();  return pep_result;` |

Every fragment emitted. Field 2's carried-binding fallback is visibly working: fragment `[1,1)` resolves `x` to
`pep_local_6`, declared in *another* fragment, and fragment `[2,1)` resolves `y` to `pep_local_10` likewise.

## Composition, compiled and run

Header section + `int64_t a3_three(int64_t pep_arg_1, int64_t pep_arg_3) { pep_enter(); <4 fragments> }` + a `main` calling
`a3_three(3, 4)`:

```
assembled C: 10038 bytes
clang: exit=0 stdout='13'   (expect 13)
gcc:   exit=0 stdout='13'   (expect 13)
```

`((3 + 4) * 2) - 1 = 13`. Both builds clean under `-std=c23`/`-std=c2x -Wall -Wextra -Wpedantic -Werror -O2`. So the fragments
are not merely each emittable — they compose into a working function whose value is right.

## Correction to my own BOOT-A3-102

I told A2 that "node ids are NOT stable across fragments — `tempBase` is required", having measured that `remap_chunk`
renumbers ids `0..n-1` by position. That measurement was correct, but the inference was wrong for this design.

A2's entry takes the **full** `parsed` and `checked` documents and selects statements by `functionIndex`/`firstStatement`/
`statementCount` over the whole node list. Nothing is chunked, so nothing is renumbered: the emitted names are
`pep_local_6`, `pep_local_10`, `pep_local_14` — document ids, stable by construction. A2 sidestepped the hazard rather than
paying for it.

So: the `remap_chunk` hazard was real, and it applies to any design that emits from a *chunked* AST. A2's does not, and
`tempBase` is unnecessary here. My A3-102 warning was right about the mechanism and wrong about the design it would apply to.
I would rather say that plainly than let a stale warning sit in their inbox.

## Sizing data for A2-S2

Fragment emission cost measured at **1,580–2,960 steps per single-statement fragment** — 2–3% of the 100,000 budget each.
Against 90,354 for a whole 41-node function, statement-level splitting is cheap by comparison, which is the point: the cost
that blocks large functions is per-attempt, not per-statement, and fragments avoid it.

Caveat worth stating: these are one-statement fragments of a *4-statement function*. Nothing here measures a fragment of a
222-node `main`, because fragment emission needs a valid whole-function checker report and `main` is step-limited at check.
That measurement needs A1's chain path to produce a merged report first.

## What remains unverified

- **Fields 3 and 4** (`tempBase` threading — now apparently moot — and the failure index) are not exercised. I did not test a
  fragment that refuses, so the "which fragment refused" reporting is untested.
- **Large-function fragmentation** (`main`, 222 nodes) is untested for the reason above. This is the measurement that
  actually decides whether M-1 is reachable.
- **Multi-statement fragments** (`statementCount > 1`) were not exercised; I emitted one statement at a time.
- The host-side prologue assembly is mine, hand-built for this test — A1's driver's prologue is not verified here.

## Reproduce

Registration needs one non-obvious detail: the fragment tool validates against `"Pep C23 function unit index is out of
range"` for an empty program. Then `tool_invoke` with `[parsed, checked, Int functionIndex, Int firstStatement, Int count]`.
The assembled-C harness is in this receipt's method; I have not committed it as a probe yet because the interface is one
commit old and A1 has not confirmed it.

REF GH #16. Emitter A2 `86fcd10e`; seed `f8f476198f`; independent verification A3.