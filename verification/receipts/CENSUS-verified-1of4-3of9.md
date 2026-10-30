# Census verified — types 1/4 and functions 3/9 both exact (2026-10-30)

Closes the pending item from `HANDOFF-verify-listfield-verified-lexprogress-norepro.md`.
Independent reconstruction of the report's headline census
(`a25f520`), combined stack (A1 `46bf1c0` + A2 emitter).

## Types: **1 of 4 — exact match**

| type | mine | mechanism |
|---|---|---|
| `SourcePosition` | **EMITS** (4,531 B) | all-Int record fields |
| `LexToken` | REFUSED | `Pep C23 record fields require Int, Bool, or a preceding record declaration` (Str fields) |
| `LexCursor` | REFUSED | same |
| `LexProgress` | REFUSED | same (deps included) |

Their "1 of 4 (`SourcePosition` … blocked)" reproduced with the same
refusal mechanism.

## Functions: **3 of 9 — exact match, same set**

| function | mine | note |
|---|---|---|
| `ascii_letter` / `ascii_digit` / `ascii_continue` | **EMITS ×3** | *the three classifiers* — exactly their 3 |
| `make_token` | REFUSED (record Str fields) | 8 params — four-param latently applies |
| `make_cursor` / `make_progress` | BUDGET (my extraction) | **16 / 11 params** — their four-param rationale objectively true; budget binds first in whole-program extraction, param refusal is latent (same budget-before-refusal ordering as `index_of_between`, round 29) |
| `lexer_step` | BUDGET | 1 param; their "checker envelope" categorization is the sibling observation |
| `utf8_check` | REFUSED (checker-invalid in my slice) | 3 params incl. `SourceBytes`; theirs categorizes "blocked by types" — reason label differs (possible slice artifact of mine), both count it non-emittable |

**Both headline numbers reproduce: 1/4 types, 3/9 functions, with the
same three classifiers as the emittable set.**

## Method evolution disclosed (three attempts)

1. Call-sites for zero-param fns — wrong: needed typed call sites and
   return-shape compatibility (produced `CHECK-INVALID` noise).
2. Non-calling trivial main, type deps only — **function** deps
   missing (`ascii_continue` without `letter/digit` → check-invalid).
3. Final: non-calling main + transitive function deps + their 9-fn
   set (excluding `advance_position`, which I had counted as a 10th —
   denominator mismatch, resolved by adopting their enumeration).

Replay **163/163**; corpus/base untouched. A1 still has not responded
to the `ae91bdc` regression (no commits since).
