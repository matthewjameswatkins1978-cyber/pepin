# PRE-REGISTRATION A3-042: DIVERGENCE-2 — does a Pep program emit INPUT-DEPENDENT C23?

**Seat:** A3, mission LUCY-20261107-012. **Written and committed before any measurement.**

## Why this single test decides the mission's route

Every natively-verified Pep program so far emits **input-invariant** C: the compiled binary reads the
file at *runtime*, so one C program serves every input (BOOT-A3-034/040, 49/49). A compiler must
instead produce **C that differs by input**. Nobody has demonstrated that. Until someone does, both
route R (salvage) and route S (small bootstrap) are unproven in the only way that matters, and
self-hosting would be theatre.

## Capability evidence gathered first (read-only, A1 `86ff953`, seed `a7d3ee1`)

- `str_concat` is a **builtin** — the emitter's own source says so: *"str_concat is a BUILTIN
  (A1 844c8b0; seed @2ad750b): no top-level function node"*.
- `utf8_slice` exists in the seed interpreter (`pep_ocaml.ml`, 6 sites) and is used by
  `examples/pep_lexer.pep`, so `SourceBytes -> Str` slicing is a real path.
- The emitter handles `Str` (`pep_str`, 25 sites) and `say(Str)`.
- `say(Str)` prints to stdout — which is exactly how a native compiler delivers generated C.

So a source-dependent C generator *may already be expressible* in the current stack. This test asks
whether it actually is.

## The test (one program, two unseen inputs)

```
fn main(source: SourceBytes) -> Int {
  say("#include <stdio.h>\nint main(void){puts(\"")
  say(utf8_slice(source, 0, 3))
  say("\");return 0;}\n")
  return 0
}
```

Two unseen input files whose first three bytes differ. The program's **stdout is the generated C**.

## Predictions

| # | Claim | Falsified if |
|---|---|---|
| D1 | checks `valid` under host analysis | not valid |
| D2 | emits as a C23 unit | refused |
| D3 | **the two generated C texts differ** | identical text for different inputs |
| D4 | both generated programs compile under strict Clang **and** GCC | either fails |
| D5 | the two compiled binaries print **different** strings matching the input prefixes | same output |

**The discriminating claim is D3.** D4/D5 keep it honest: differing text is worthless if it is not
valid C23.

## What each outcome means

- **D1–D5 all pass** → the fundamental capability exists today. The route question then reduces to
  "can the compiler's own units emit", and S becomes credible immediately.
- **D2 fails** → the emitter cannot lower this shape; the exact diagnostic names the first real
  blocker, and both routes inherit it.
- **D3 fails while D2 passes** → `utf8_slice`/`say` lower but produce constant output; that would
  falsify my prior reading of the emitter and be a major finding.
- **D4 fails** → generated C is not valid C23; the blocker is in the emitter's Str lowering.

## Honest scope

This is a **capability probe**, not a compiler, and passing it does **not** constitute self-hosting: the
generated C here is a fixed template with one variable substring. It proves only that Peg-written
programs can produce input-dependent valid C23 — the necessary floor. It says nothing about lexing,
parsing, checking or code generation logic, which remain to be built or salvaged.

## Scope guard

A3 owns only `verification/**`. No edits to A1's checker/contract, A2's emitter, A4's app. Cap
unchanged; no `CURRENT`, manifest, frozen-gate, master or release change. Generated inputs are A3
fixtures under `verification/fixtures/divergence/`.