# CORRECTION BOOT-A3-105 — A3-104 overstated its scope; `run` executes top-level statements. Plus: a new emitter gap, and reserve R3 recovered

**Correction first: BOOT-A3-104 was wrong about scope. I claimed `pep.ps1 run` "executes nothing for every Pep program in
this repository". That is false. `run` executes **top-level statements**, and Pep programs that have them work correctly —
`tests/test_cli.py` depends on exactly that and **passes**. The mechanism I read from the source was right; the scope I
attributed to it was not, and a committed passing test refutes the general claim.**

## What I got right, and how I got the rest wrong

The mechanism is confirmed at `pep_ocaml.ml` ~L941:

```ocaml
match entry with
| None -> ignore(exec_stmts [] [] c.tops); VUnit     (* top-level statements only *)
| Some (function_id, arguments) -> ...               (* function bodies *)
```

`run` passes no entry, so it evaluates `c.tops` and **never calls `main`**. What I failed to consider is that Pep *has*
top-level statements. Measured both directions:

| program | observed |
|---|---|
| `fn double(n: Int) -> Int { return n * 2 }` + top-level `say(int_text(double(21)))` | **prints `42`** |
| the same code moved inside `fn main()` | **prints nothing**, exit 0 |

And the test that proves I was wrong: `tests/test_cli.py`
`test_session_fill_hole_previews_applies_and_preserves_history` ends with
`assertEqual(invoke("run", …).stdout, "42\n")` — and that program puts `say(int_text(double(21)))` at top level. Run it on
A1's ledger tip: **`OK`**. My claim would have required that test to be red; it is green.

So the accurate statement is: **`run` is a top-level-statement executor that never calls `main`.** Function-only programs —
`compiler_a.pep` and every fixture in my verification lane — print nothing and exit 0, which is what led me astray. I
generalised from my own fixtures to "every Pep program" without checking whether a different program shape existed, and it
did.

Anyone relying on A3-104's headline should rely on this one instead. The *consequence* still holds for function-only
programs: `run` is a silent no-op for them, so it gives false confidence if used to validate `compiler_a.pepin`. The
*universality* was the error.

## New finding: builtin-of-cross-chunk-call is not lowered

While trying to use the seed as an oracle I hit a genuine emitter gap. `say(int_text(f(41)))` — a cross-chunk call as an
argument **to a builtin** — refuses:

```
unit main: Pep C23 calls require a known target
```

Isolated against a control that differs only in placement:

| fixture | shape | result |
|---|---|---|
| `x_builtin_of_call.pep` | `say(int_text(a3_inc(41)))` — builtin of user call | **REFUSED** |
| `x_call_then_builtin.pep` | `let v = a3_double(21) + 1` then `say(int_text(v))` | **EMITTED, runs, prints 43** |

This is the **mirror** of what A2-S1 covered. A2-S1 handles *user call of builtin* — `is_ws(byte_at(source, o))`, verified in
A3-101 — but not *builtin of user call*. The asymmetry is precise: builtin→user works, user→builtin does not.

Nothing in `compiler_a.pep` is blocked by it (`main`'s six `say(int_text(N))` take literals), which is consistent with the
10/21 figure. But `say(int_text(len))` is an obvious M-2/M-3 pattern and will bite there. This sits with **A2**
(`tests/pep_c23_emitter.pep`); I have not touched it.

The workaround that works today is hoisting: `let v = …` then `say(int_text(v))`.

## Reserve R3 recovered — the seed *can* be a semantic oracle, with placement adjustment

A3-104 concluded reserve R3 ("side-by-side generated output semantic comparison to seed") was impossible. With the correct
scope it is achievable on the same expression, adjusting only placement:

| side | program | output |
|---|---|---|
| seed | top-level `say(int_text(a3_double(21) + 1))` | **`43`** |
| emitted C, clang | `fn main` with `let v = a3_double(21) + 1; say(int_text(v))` | **`43`** |
| emitted C, gcc | same | **`43`** |

So the seed *is* a usable reference for expression semantics, provided the oracle is written script-style for the seed and
the emitted side hoists cross-chunk calls. That is a real differential against an independent implementation, which is
stronger than comparing emitted C to my own expectations — and it is now available.

## Limits

- One expression compared (`a3_double(21) + 1`). This establishes the method, not a broad suite.
- The two sides differ in *placement*, so the differential tests expression semantics, not statement or scope semantics.
- The `user→builtin` gap is measured on pin `7e820a7f`; A2 may already be addressing it.
- `run`'s behaviour is confirmed on three seeds (145,104, 145,104 and 148,791 working-tree bytes) for both program shapes.

## Reproduce

```
# seed side (top-level statements)
pwsh -NoProfile -File <seed>/pep.ps1 run top_level.pep        # prints 43
# emitted side
PEPIN_GATE_ROOT=<worktree> PEPIN_APP_REL=verification/fixtures/emit/x_call_then_builtin.pep \
  PEPIN_APP_REV=<sha> PEPIN_RUN_FIXTURES=<any file> python verification/probes/emit_any_049.py
pwsh -NoProfile -File <A1 ledger>/pep.ps1 ...   # tests/test_cli.py passing test
```

REF GH #16. Supersedes the scope claim in `6724893627` (A3-104); that receipt's mechanism section stands, its headline does
not.