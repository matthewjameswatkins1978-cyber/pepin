# Corroboration — report's 2×2 `var`-in-callee refusal reproduces exactly (2026-10-30)

Report `1b59613` ("The 31 unsupported collection cases: partially
isolated, and misreported") claims a mutable local in the callee flips
an accepted call to `unsupported`, with a diagnostic that misblames
call arity. Cross-verified on my independent combined state (A1
`46bf1c0` + A2 `26be4be` emitter, `pep_c23.emit`):

| # | program | report | my run |
|---|---|---|---|
| 1 | `fn f(n: Int) -> Bool { var balance = 0; return !(balance <= 0) }`, called `if f(1)` | unsupported | **refused** — diagnostic verbatim: *"Pep C23 one-parameter calls require one argument and a call-free target expression"* |
| 2 | same shape, pure callee (`return !(n <= 0)`) | emits | **EMITS (4,659 B)** |
| 3 | list-param + `var` callee, `if f([true])` | unsupported | **refused**, same message |
| 4 | list-param pure callee | emits | **EMITS (4,723 B)** |

**4/4 agreement.** Confirmed independently:

- The `var`-in-callee flip is real and parameter-type-independent
  (Int and List[Bool] both flip).
- The diagnostic is genuinely misreported: argument count (1) and the
  one-argument requirement are satisfied in cases 1/3 — the message
  blames conditions the program meets.
- Surface form on this lane: `pep_c23.emit` raises with the emitter
  diagnostic (the harness reports refusal as an exception carrying the
  `Pep C23 …` text); the refusal semantics are the report's
  `unsupported` status.

**Classification:** a construct refusal (fail-closed), *not* budget —
distinct from Wall A/B; it belongs to the counted inventory of "what
blocks Lucy's lexer" (the collection cases the report is isolating).
Their recommendation (builder instrumentation; diagnostic naming the
real cause; pin down whether the rule is "callee declares a mutable
local" or narrower) is sound and builder-owned — the 2×2 is now
double-sourced, so the ask is grounded on two lanes' measurements.

No contradiction; blocker map unchanged (Wall A, Wall B, design
trigger). Replay **163/163**.
