# Refined rule matrix 9/9 confirmed — my two R6 probe bugs disclosed + a parse-failure mislabel observed (2026-10-30)

Cross-verification of the report's sharpened local-binding rule
(`618befb` + `203a0a1`) on my combined state (A1 `46bf1c0` + A2
emitter `44d4e0f1`).

## Final matrix result: 9/9 with the report

| row | prediction (report) | result |
|---|---|---|
| R1 `let b = 0; return b <= n` | unsupported | unsupported ✓ (arity message) |
| R2 two lets, `return b <= c` | unsupported | unsupported ✓ |
| R3 `var b = 0; return b <= n` | unsupported | unsupported ✓ |
| R4 `var b = 0; return !(b <= n)` | unsupported | unsupported ✓ |
| R5 `var b = true; return b` | emits | **emits 4,699 B** ✓ |
| R6 `let b = 7; return b` (Int) | emits | **emits** ✓ *after my probe fix — see disclosure* |
| R7 `return 0 <= n` | emits | **emits 4,656 B** ✓ |
| R8 `return n <= m` (two params) | emits | **emits 4,727 B** ✓ |
| R9 `let b = n; return b <= n` | unsupported | unsupported ✓ |

**Rule confirmed independently:** comparisons in returns may reference
parameters and literals, never local bindings (even locals copying
parameters) — and the arity-misblamed diagnostic accompanies every
refusal.

## My two R6 probe bugs (disclosed, both mine)

1. **Wrong call-site type:** I reused a Bool-condition main
   (`if f(1)`) for an Int-returning callee → *my program* was
   type-invalid (`valid Pep checker report` refusal).
2. **Invalid syntax on retry:** my "fixed" main used `f(1) > 40` —
   **the seed has no `>` operator**: interpreter and checker both
   reject with `PEP_UNEXPECTED_CHARACTER: Unexpected character '>'
   at 5:28` (check: `invalid`). The report's R6 used a valid call
   site; their EMITS result stands.

## Bonus observation (same diagnostic-quality family)

Through this I observed: when the target program **fails to parse**,
`pep_c23.emit` surfaces *"Pep C23 emission inputs do not match the
authorised source revision"* — raised by the shared guard at
`pep_c23_emitter.pep:2817-2820`, whose third arm is
`syntaxNodeCount != length(parsed.nodes)` while the message names only
revision. The true cause (parse failure) is named nowhere. Reproduced
3× deterministically (staged path twice + all-in-one path). This is a
third instance in the report lane's diagnostic-mislabel thread —
builder-owned; reported as an observation, not a defect claim about
semantics (the refusal itself is fail-closed and correct).

Blocks unchanged (Wall A, Wall B, design trigger). Replay
**163/163**.
