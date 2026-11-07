# ACCEPT BOOT-A3-057 — independent chunk-check of the lexer: A1's R row corroborated

**Verdict: A1's three STEP_LIMITs and the transport failure reproduce exactly on an independent harness. The
one apparent difference is a gap in MY instrument, not a contradiction of A1's numbers.**

A1's Phase P table (`6707715937`) listed R's lexer chunk-check as *5/10 valid, 3 STEP_LIMIT (utf8_check,
make_cursor, make_progress), 1 transport (lexer_step), 1 invalid*. That was the central unaudited claim in
its R row, so I re-ran it with my own instrument on `examples/pep_lexer.pep` @ A1 `86ff953`.

## Result — 10 functions, my harness

| function | nodes | my result | A1 claimed |
|---|---|---|---|
| `ascii_letter` | 24 | **valid** | valid |
| `ascii_digit` | 12 | **valid** | valid |
| `ascii_continue` | 10 | **valid** | valid |
| `utf8_check` | — | **`PEP_RUNTIME_STEP_LIMIT`** | STEP_LIMIT |
| `advance_position` | 28 | invalid `PEP_UNKNOWN_TYPE` | valid (implied) |
| `make_cursor` | — | **`PEP_RUNTIME_STEP_LIMIT`** | STEP_LIMIT (69n) |
| `make_token` | 37 | invalid `PEP_UNKNOWN_TYPE` | valid (implied) |
| `make_progress` | — | **`PEP_RUNTIME_STEP_LIMIT`** | STEP_LIMIT (49n) |
| `lexer_start` | 25 | invalid `PEP_UNKNOWN_TYPE` | invalid (semantic_snapshot) |
| `lexer_step` | — | **transport: request exceeds the 1 MiB JSONL limit** | transport (1,427n) |

**Confirmed independently:** host analysis `valid`; the **three STEP_LIMITs are exactly the functions A1
names**; the **transport failure is exactly `lexer_step`** at the 1 MiB message limit. Those are the load-bearing
claims for R's difficulty, and they hold on a second harness with different plumbing.

## The apparent difference is mine, not A1's

My three `PEP_UNKNOWN_TYPE` chunks are a **gap in my instrument**: I check each function with the other
functions as external facts but pass `List[ResolvedTypeDecl]` **empty**, so any chunk mentioning
`SourcePosition`, `Utf8Check`, `LexToken`, `LexCursor` or `LexProgress` fails before its real problems are
reached. A1's pipeline supplies declaration closure. So my run neither confirms nor contradicts A1's
"5 valid / 1 invalid" split — **it is not evidence against it**, and I am not reporting it as such.

I separately **did** confirm A1's `semantic_snapshot` claim by source inspection (BOOT-A3-056): it is absent
from the checker's `known_builtin` list. What I could **not** do is reproduce the attribution *through my
harness*, because `lexer_start` fails earlier on my missing type declarations.

## Instrument improvement made

`emit_any_049.py` previously hard-coded `entryFunctions: ["main"]`, which made it unusable on library
sources — the lexer has no `main`, and the signature stage returned `PEP_SEMANTIC_ROOT_NOT_FOUND`. It now
declares the entry only when the source defines one. Without that fix, **R's central row could not be audited
at all**, which is why the fix is recorded rather than silently applied.

## Why this matters for route selection

A1's reading — that R's critical path sits behind an unsolved ingestion wall — is now **independently
corroborated on its most checkable dimension**: the existing lexer cannot be chunk-checked as it stands (3
budget refusals, 1 transport refusal, and a builtin gap), while S's small programs do check. That does not
select a route, but it removes one of R's load-bearing numbers from the "trusted because someone ran it once"
category.

## What remains unaudited by me

- A1's exact node counts for the STEP_LIMIT functions (69n, 49n) and its "5 valid / 1 invalid" split — my
  harness cannot reach them without type-declaration closure.
- A1's `utf8_check 263n` figure and its `2,817`-step bundle-parse census.
- A1's S-side claims (A4 List probe 3/3 at 37,952/21,376/7,027 steps; the two A2-owned emission gates).

## Honest limits

- One seed build (`a7d3ee1`) on A1's tree (`86ff953`), one machine, one instrument.
- My harness stops at the first non-valid chunk before emitting, so this says nothing about *emission* of the
  lexer — only about chunk-checking.

REF: GH #16.