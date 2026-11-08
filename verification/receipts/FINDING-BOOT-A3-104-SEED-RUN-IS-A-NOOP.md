# FINDING BOOT-A3-104 — `pep.ps1 run` executes nothing for function-only Pep programs, so the seed is not a semantic oracle

**Verdict: `pep.ps1 run FILE` silently does nothing for every Pep program in this repository. It exits 0, prints nothing, and
surfaces no runtime errors — because `run` calls `execute` with no entry, and with no entry the seed executes only
**top-level statements**, never `main`. All Pep here is function-only, so there is nothing to execute. This matters beyond a
missing feature: any test or agent that uses `run` to validate behaviour gets an unconditional pass, and A3's own reserve R3
(seed-vs-emitted semantic differential) is not achievable.**

## Measured three ways

All against the seed built in `wt-a3-dbea` at A2's tip (`7e820a7f`), which `check` handles correctly, so `pep.ps1` itself
works.

| program | expected under execution | observed |
|---|---|---|
| `fn main() -> Int { say("hello")  return 7 }` | prints `hello` | **exit 0, no stdout, no stderr** |
| `fn main() -> Int { let z = 0  let x = 1 / z  return x }` | `PEP_RUNTIME_DIVISION_BY_ZERO` | **exit 0, no stdout, no stderr** |
| `fn a3_add(a,b) …` + `main` calling it, `say("seed-runs")`, `return x` | prints `seed-runs` | **exit 0, no stdout, no stderr** |

The second row is the decisive one: a program that must abort on division by zero does not abort. Nothing is running.

## The mechanism, from the seed's own source

Call site, `pep_ocaml.ml` (~L2070), the `run` branch:

```ocaml
else if checked.holes<>[] then (...)
else ignore (execute checked)
```

`execute`'s signature defaults `?(entry=None)`, and with `None` (~L941):

```ocaml
match entry with
| None -> ignore(exec_stmts [] [] c.tops); VUnit
| Some (function_id, arguments) -> ...  (* only here is a function body run *)
```

So `run` executes **top-level statements only**. A function body — `main` included — is reached solely through
`Some (function_id, arguments)`, which only the tool-invocation path (`tool_invoke`) supplies. Since `compiler_a.pep` and
every fixture are pure function declarations with no top-level statements, `c.tops` is empty and the execution is a no-op.

`say` is not at fault: it is `print_endline text` (~L881) and is available outside tool execution (`allow_say=true` by
default). It is simply never reached.

## Why this is worse than a missing feature

- **It gives false confidence.** `run` returns success for a program that cannot run. Anything validating Pep behaviour
  through `run` — a test, a script, or an agent — passes unconditionally. That is the same failure class as a gate that
  cannot fail.
- **The documented contract is misleading.** The project's own instructions say *"Only `run` executes Pep code"*. It does
  not, for any program in this repository.
- **No seed observable exists, so reserve R3 is unavailable.** A3's reserve was *"side-by-side generated output semantic
  comparison to seed (do not demand C byte identity)"*. There is nothing to compare against: the seed produces no output and
  no exit status that depends on the program. The only semantic reference available is hand-derived expectation, which is
  what A4's `EXPECTED.md` provides.

## Correction to my own BOOT-A3-097

In A3-097 I wrote that I had not run compiler A under the seed interpreter because *"that needs `SourceBytes` input access,
which A3-073/074 established is unavailable"*. The input grant is indeed unavailable, but that was not the binding reason —
even with perfect input access, `run` would not call `main`. My earlier explanation was wrong in a way that pointed at the
wrong blocker, and it is corrected here.

## What would fix it, and whose call it is

Selecting an entry for `run` — `execute ~entry:(Some (id, args))` after resolving `main` — is a **seed change**. That is
A1/A2's file, it touches the accepted seed contract, and it may raise the question of how a no-argument `main` receives a
`SourceBytes` grant. So I am not proposing it as an A3 task; I am reporting that the capability assumed to exist does not.

Practically, this does not block M-1. M-1 judges the *emitted C*, compiled and run natively — which is what A3's gates
already do, and why DIVERGENCE-2 works. It blocks only the idea of using the seed as a behavioural reference.

## Limits

- I read the mechanism from `pep_ocaml.ml` at the seed on A2's tip. A different seed revision on another lane could differ;
  the 143,092-byte seed on A1's ledger branch was not re-tested for this specific behaviour.
- I did not construct a program with genuine top-level statements to confirm positive execution through `exec_stmts`. The
  inference that `c.tops` is empty for function-only programs follows from the parser shape and from three measurements
  showing nothing executes, but that positive control was not run.
- This is a *capability* finding, not a defect report against a person: nobody claimed `run` worked for these programs, and
  no test in the lane depends on it.

REF GH #16. Seed `pep_ocaml.ml` on A2 lane `7e820a7f`. Investigation: A3. Reserve R3 recorded as unavailable rather than
silently dropped.