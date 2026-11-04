# A2 native claims verified at `ea0bc9a` — suite executed natively and the canonical idiom matches the interpreter; two divergences found (unconditional return-value print, `say` of an expression refused)

**Date:** 2026-11-04 · **Mission:** PEP-WB-A3-20261104-B priority 5 ("independently verify newly pushed repairs and native execution claims") · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Pin:** `codex/a2-bounded-emission` @ **`ea0bc9a`** (worktree `D:\Projects\wt-a3-a2-ea0bc9a`, clean)
**Toolchain present:** clang (`scoop\llvm`), gcc (`scoop\mingw`), ocamlopt/opam (`pepin-5.5.2`)

## 1. A2's own native suite executes and passes — `18 tests, OK, 11.5 s`

`python -m unittest -v tests.test_c23_bounded_emission` at this pin. The native tests are **not
skipped**: `test_reassembled_unit_output_compiles_and_runs_under_clang_and_gcc`,
`test_record_dependent_assembly_compiles_and_runs_natively`,
`test_arena_dependent_assembly_compiles_and_runs_natively` all report `ok`. That is the builder's claim
reproduced through the builder's own harness — necessary but not sufficient, hence part 2.

## 2. Independent native check (my own emitter call, my own compile/run, no A2 harness)

Program A — the idiom the corpus uses:

```pep
fn answer() -> Int { return 20 + 22 }
fn main() -> Int { return answer() }
say(int_text(main()))
```

| observer | output |
|---|---|
| Pep interpreter (`pep.ps1 run`) | `42\n` |
| emitted C, `clang -std=c23 -Wall -Wextra -Wpedantic -O1` | `42\n` — **matches** |
| emitted C, `gcc -std=c2x -Wall -Wextra -Wpedantic -O1` | `42\n` — **matches** |

**So the say-lowering claim holds for the supported idiom**, independently reproduced under strict flags on
both compilers.

## FINDING 1 — native output prints the entry return value; the interpreter never runs it

Program B:

```pep
fn main() -> Int { say("in-main") return 0 }
```

| observer | output |
|---|---|
| Pep interpreter | **`""`** — it executes top-level statements only; function bodies never run |
| emitted C (clang **and** gcc) | **`"in-main\n0\n"`** — the in-body `say` runs, **and** the wrapper prints `main`'s return value |

Attributed in the generated source: both programs carry exactly one numeric print site,
`int main(void) { (void)printf("%lld\n", (long long)(pep_fn_N())); }`. In Program A that wrapper *is* the
`say(int_text(main()))` idiom, so the outputs coincide; in Program B the same wrapper prints `0` on top of
the in-body `say`.

**Precise statement:** native output equals the interpreter's only for the canonical
`say(int_text(main()))` shape. For anything else the emitter's entry wrapper adds `<return-value>\n` and
executes `say` inside function bodies that the reference never executes. A2's own tests compare exactly the
canonical shape, which is why they pass. **Owner question, not a verdict:** is the wrapper print intended
as a run-and-report convention (then it should be documented as *not* program semantics) or as program
output (then it diverges from the interpreter)? Either answer is fine; the current state is undocumented.

## FINDING 2 — `say` of an expression is refused, and the corpus is full of it

`say(int_text(answer()))` — the form used throughout `examples/*.pep` — is rejected at emit:

```
ValueError: Pep C23 say lowers only string literals, Str parameters, Str locals and Str fields
```

So native execution of real example programs is blocked by the `say` argument grammar, not by the budget.
The supported subset is narrow (literal / `Str` param / `Str` local / `Str` field); a call expression is not.
A2's own fixture uses the top-level `say(int_text(main()))` shape, which the emitter folds into its wrapper
and therefore never exercises the general case. Suggested: either lower `say(<any Int expression>)` via
`int_text`, or state the restriction in the emitter docs and note that corpus examples are outside it.

## Honest scope

- Two programs, one pin; no native run of the seam probe's full declaration-chunk assembly (that path is
  covered by A2's native suite in part 1, which I ran but did not re-derive).
- The interpreter's "does not run function bodies" behaviour is measured here (`say` in `main`, in a helper,
  and at top level), not read from documentation — it is the reference this comparison depends on.
- Emitted C is 4.9 KB for trivial programs (the runtime prelude dominates); nothing here is a performance claim.
- Not acceptance evidence. The integrated candidate verdict remains FAIL 14/15 (`ACCEPT-c69e15d-FAIL.md`).

## Reproduce

```powershell
python -m unittest -v tests.test_c23_bounded_emission        # in D:\Projects\wt-a3-a2-ea0bc9a -> 18 OK
python verification\_build\tm\native_check2.py D:\Projects\wt-a3-a2-ea0bc9a
python verification\_build\tm\dump_c3.py        D:\Projects\wt-a3-a2-ea0bc9a
```
