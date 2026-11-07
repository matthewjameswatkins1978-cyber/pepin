# ACCEPT BOOT-A3-044 — the bootstrap auditor is built and validated, except A5 which is unproven

**Verdict: auditor core criteria VALIDATED; A5 implemented but UNPROVEN, with the reason measured.**
Pre-registered at `c5acd7a` before the auditor existed.

This is the instrument that will judge whatever R or S spike A1/A2 produce. No spike exists yet — A2 is
still `4b70c61` and A1 `86ff953` — so the useful work was to build the judge and prove it is **not
vacuous** before it ever sees a candidate.

## Six falsifiable criteria

| # | Criterion | Falsifies a candidate by |
|---|---|---|
| A1 | DIVERGENCE | two unseen inputs giving identical C |
| A2 | VALIDITY | emitted C failing strict Clang **or** GCC under `-Werror` |
| A3 | SEMANTICS | the generated binary running to the wrong result |
| A4 | REJECTION | accepting undefined name / type mismatch / wrong arity instead of exiting non-zero with no C |
| A5 | NO FORBIDDEN SUBPROCESS | output changing when `PATH` is stripped to an empty directory |
| A6 | DETERMINISM | two runs of one input differing |

## Self-test result — the auditor rejects "merely prints fixed C"

| control | expectation | measured |
|---|---|---|
| `fixed` — prints constant C, ignores input | must **fail** | **FAILS** A1 (identical output), A3 (wrong results), A4 (accepts invalid inputs) |
| `good` — input-dependent, rejects invalid inputs | must **pass** | **PASSES all six** |
| `cheat_abs` — shells out via an absolute interpreter path | must expose A5's blind spot | **CONFIRMED not caught** — exactly as pre-registered |
| `cheat` — shells out via `PATH` | A5 must catch | **UNPROVEN — see below** |

**P1 and P2 are the ones that matter**: the auditor demonstrably rejects the mission's named failure
mode (*"a program that merely prints fixed C is not sufficient"*) and demonstrably accepts a correct
one. It is not a rubber stamp.

## Why A5 is unproven, stated precisely

My first `cheat` control used `sys.executable` — an **absolute** path — which A5 cannot catch, exactly
as my pre-registration warned. I fixed it to call `python` **by name** so it would depend on `PATH`…
and it still passed, because **on Windows `CreateProcess` searches the application directory first**, and
the launcher *is* the interpreter, so `python` is found beside it whatever `PATH` says.

So a **script-based control cannot exercise A5 at all**. A5 remains meaningful for a genuine
**native-exe** candidate (whose application directory would need its own interpreter to cheat), but I
have not proven that, and I will not count it as working. It is reported as **UNPROVEN / advisory**
until a native-exe cheat control demonstrates it.

Two self-corrections recorded rather than quietly fixed: the absolute-path control, and then the
mistaken assumption that script controls could exercise PATH stripping.

## What the auditor can and cannot say

- **Can:** falsify each of A1–A4 and A6 for any candidate command of the shape `<compiler> <input>` whose
  stdout is the generated C. It reports per-criterion PASS/FAIL with the observed values.
- **Cannot:** prove a candidate is a genuine Pep compiler. It judges a *command*, not a language. It also
  cannot detect a compiler hidden in the host by any means other than A5, which is itself unproven.

## Ready to use

```powershell
python verification/probes/bootstrap_audit.py --compiler "<cmd>" --fixtures <dir> --expect a=<out>,b=<out>
```

Fixtures need `valid_a`, `valid_b`, `invalid_name`, `invalid_type`, `invalid_arity` (`.pep` or `.txt`).

## Not tested

- A5's effectiveness (reason above). **This is the one criterion I would not rely on today.**
- Any real candidate: none exists yet.
- Whether a native candidate can be built with a stripped environment at all — a genuine compiler needs
  no `PATH`, but the *harness* does, and separating those two environments is untested for a real exe.

## Scope

A3 changed only `verification/**`. Controls are throwaway scripts generated into `_build`, clearly
labelled; they are **not** Pep compilers and are not route work. No edits to A1's checker/contract, A2's
emitter, A4's app. Cap unchanged.

REF: GH #16 (BOOT-A3-044).