# Walls A and B die in different emitter regions — different fix logic (2026-10-30)

Measurement at current combined pins (A1 `46bf1c0` + A2 `26be4be`
files), continuing the hotspot work from
`HOTSPOT-emitter-pep_c23_child-5114.md`.

## Positions

| wall | contract | program | death position | maps to |
|---|---|---|---|---|
| **A** | staged (`emit_c23_checked`, emit-only budget) | classifier closure, `ascii_continue` | `compiler-bundle:5114:8` | emitter **L25** — `pep_c23_child` scan loop |
| **B** | a14 all-in-one (`emit_c23`, shared 100k) | `countdown(6)` | `8374:92` | emitter **L3285** (tail region) |
| **B** | same | `countdown(100)` / `(510)` | `8360:55` (identical for both) | emitter **L3271** (tail region) |

(Emitter = 3,327 lines; L3271–3285 sit in the final ~60 lines — the
`emit_c23_checked` assembly tail.)

## Interpretation (with the exhaustion-position caveat applied consistently)

- **Wall A:** an emit-ONLY invocation exhausts its whole budget inside
  the `pep_c23_child` scan — consistent with the fan-out evidence
  (186 call sites) from last round; the scan phase is where the money
  goes for closure-shaped programs.
- **Wall B:** the two-path reconciliation already proved countdown's
  **emit-only cost fits 100k at every size** (staged path emits
  `countdown(510)` everywhere). Its shared budget is consumed by
  parse+analyze+emit combined, and execution merely *reaches* the tail
  when it runs dry — identical death lines for 100 and 510 confirm the
  path is structure-driven, not literal-driven. The tail position
  names where the shared budget emptied, **not** a tail cost center.

## Consequence for fix planning (the point of this receipt)

1. **Wall A → emitter cost work** (`pep_c23_child` bucketing) directly
   attacks its measured region, and incidentally helps B (cheaper emit
   leaves more shared headroom).
2. **Wall B → contract change** (stage-separated budgets, or a14
   migrating to `emit_c23_checked`) is the structural fix; emitter
   cost reductions only shift its oscillation boundary (the
   `f184580`→`7b69964`→`dea32c0` swing already showed that).
3. The two walls therefore should NOT be planned as one fix: one
   hotspot, two contracts. The bucket-index work closes A; only the
   contract decision closes B's green/red instability.

Honesty: both rows are exhaustion positions (stated limitation from
the hotspot receipt); the Wall A row is strengthened by fan-out
density, the Wall B rows by the independent two-path proof that
emit-only cost fits.

Replay: corpus/`replay.py`/base untouched — **163/163** current.
