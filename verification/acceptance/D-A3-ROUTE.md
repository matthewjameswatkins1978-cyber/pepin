# D-A3 ROUTE — independent critic's proposal (LUCY-20261107-012)

**Seat:** A3. Recorded before reading any peer route, so it is genuinely independent.

## The capability that decides both routes

Everything I have verified to date emits **input-invariant** C: line-scan's compiled binary reads the
file at *runtime*, so the same C serves every input (BOOT-A3-034/040, 49/49). A compiler must emit C
that **differs by input**. That capability is currently **unproven by anyone**, and without it
"self-hosting" is theatre. Neither R nor S is credible until it is demonstrated.

## Why I do not start from R (salvage + narrow optimisation)

Measured, not assumed:

- emitter cost ≈ **381n + 35.68n²** steps, **80.5% quadratic at 44 nodes** (BOOT-A3-033);
- a **44-node `main` already exceeds** the 100,000 budget; line-scan's **30-node** main uses
  **51,009** (BOOT-A3-034);
- conditional lowering is the dearest path per node (**3,523/node** vs 2,662 for assignments,
  BOOT-A3-039) — and a compiler is made of conditionals;
- the existing Pep-written components are ~**5,651** (emitter), ~**2,961** (checker), ~**1,876**
  (parser) lines.

For A→B→C, compiler **A's own source must be emitted by the seed**. On the measured curve, a function
much above ~30–40 nodes is unemittable today. So R's "narrow optimisation" must **fix the quadratic
cost before it produces any bootstrap value**; the windows route is already ruled out for the expensive
core (BOOT-A3-038). R is therefore not a shortcut — it is a rewrite of the emitter's traversal.

## Route I would back: S, gated on a divergence spike first

**Dependency closure for the bootstrap compiler's own source:** `Int`/`Bool`/`Str`; `var`/`let`;
functions with parameters and returns; `if`/`else`; `while`; calls; arithmetic and comparison; **Str
output** (`say(Str)`, which exists — `examples/hello.pep`) as the C emission channel; **Str
construction** (`utf8_slice`, int→text, and *concat/append at scale — the critical unknown*); byte
input via granted `SourceBytes` with bounds-checked `byte_at`/`byte_length` (SOUND, BOOT-A3-026).

**Irreducible host functions:** file read (grant), allocation, `printf`, C-compiler invocation
(external), exit status. **No** lexer/parser/typechecker/C-generator in the host.

**Cost risk:** the binding constraint on *both* routes is that the compiler's own functions must fit
the emitter — which favours very small functions and shallow nesting, not a cherry-picked demo.

**Reversible cuts:** no records/unions/List inside the compiler's own source; `[A-Za-z0-9_]`
identifiers only; fixed C template; no error recovery (first-error exit).

## What would prove me wrong

If a **two-input divergence spike passes through the existing emitter with no traversal change**, and
that same program's own units emit, then R is cheaper than S and I would switch to it.

## My cheapest falsification test — DIVERGENCE-2

One Pep program, **two unseen input files**; the emitted C must **differ textually** between them, and
both must compile under strict Clang **and** GCC and run to distinct correct outputs. Failure names the
first real blocker; success moves the discriminator to "can the compiler's own units emit".