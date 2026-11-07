# PRE-REGISTRATION A3-044: the bootstrap auditor, and why it must catch "fixed C"

**Seat:** A3, mission LUCY-20261107-012. **Written before the auditor exists.**

## Purpose

My lane is to pre-register tests that separate a **native scanner** from a **native source-to-source
translator** from **real self-hosting**, and to judge whatever R or S spike peers produce. No spike
exists yet, so the useful thing I can build now is the **auditor itself**, and prove it is not vacuous
before it is ever pointed at a real candidate.

The mission names the failure mode explicitly: *"A scanner or a program that merely prints fixed C is
not sufficient."* An auditor that passes a fixed-C program would be worthless, so **that is the first
thing it must be tested against.**

## Audit criteria (each one falsifiable)

| # | Criterion | Fails the candidate if |
|---|---|---|
| **A1 DIVERGENCE** | two unseen inputs produce **different** emitted C | identical output |
| **A2 VALIDITY** | every emitted C compiles under strict **Clang and GCC** (`-Werror`) | any build fails |
| **A3 SEMANTICS** | each generated binary **runs** and returns the expected result | wrong/absent result |
| **A4 REJECTION** | three invalid inputs — **undefined name**, **type mismatch**, **wrong arity** — exit non-zero and emit **no** C | any invalid input is accepted |
| **A5 NO FORBIDDEN SUBPROCESS** | re-running with `PATH` stripped to an empty directory produces the **same** output | output changes or the compiler fails without a semantic helper on PATH |
| **A6 DETERMINISM** | the same input twice gives **byte-identical** output | any difference |

A4 is what separates a translator from a scanner that ignores validity; A5 is what prevents *"a
compiler hiding in the host"* — if the candidate cannot run with no `ocaml`, `python`, `pwsh` or
`dune` on `PATH`, it is not doing the work itself.

## Two controls, so the auditor cannot be vacuous

- **Negative control (must FAIL):** a "compiler" that ignores its input and prints fixed C. AUDIT A1 must
  reject it. **If the auditor passes this control, the auditor is broken and nothing it says is usable.**
- **Positive control (must PASS):** a "compiler" that emits input-dependent C, rejects the three invalid
  inputs, and needs no subprocess. If the auditor fails this, the criteria are wrong or too strict.

The controls are throwaway Python scripts generated into `_build`, **clearly labelled as auditor
controls** — not Pep compilers, not route work, and never committed as an implementation.

## Predictions

| # | Prediction | Falsified if |
|---|---|---|
| P1 | the negative control **fails** A1 | the fixed-C program passes |
| P2 | the positive control **passes** all six criteria | it fails any |
| P3 | A5 catches a candidate that shells out to a helper, demonstrated by a third control that invokes `python` | that control passes A5 |

P3 matters: A5 is the criterion most likely to be implemented incorrectly (silently doing nothing). A5
is only credible if a *deliberately cheating* control is caught by it.

## Honest limits stated up front

- The auditor judges a **command**, not a language. It cannot prove a candidate is a genuine Pep
  compiler; it can only falsify the specific claims above.
- A5 strips `PATH`, which is strong but not a sandbox: a candidate could hard-code an absolute
  interpreter path. I will say so in every report rather than overclaim "no forbidden subprocess".
- A3 must never audit a change it authored. The controls are the only "implementations" A3 writes here,
  and they exist solely to test the auditor.

## Scope guard

A3 owns only `verification/**`. No edits to A1's checker/contract, A2's emitter, A4's app. Cap unchanged.