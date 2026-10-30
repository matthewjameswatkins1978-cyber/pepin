# Report claims verified: four-parameter limit is real but narrow; my wrapper bug disclosed; index_of_between = Wall A (2026-10-30)

Cross-verification of report `c5da9b6` ("family B isolated as a
four-parameter limit with a one-line reproduction") + `c86c7d4`, on the
combined stack (A1 `46bf1c0` + A2 emitter `44d4e0f1`).

## Findings

1. **Their one-line reproduction CONFIRMED:** `sum_four` (4 params) →
   refused with the current message *"Pep C23 functions require
   supported parameters and scalar or record results"* — the
   four-parameter construct limit is real on my stack too.
2. **But "family B = four-param" is over-generalized:** static param
   counts across their 14 named family-B helpers: **{1: 1, 2: 3, 3: 8,
   4: 2}** — only `list_int_first_outside` and `list_int_last_outside`
   are 4-param. The rule explains at most 2 of 14 helpers; the measured
   failure code for the index/index_of methods remains
   `PEP_RUNTIME_STEP_LIMIT` at the Wall A hotspot (my reclassification
   receipt stands for those).
3. **My wrapper bug #3 disclosed:** my first verbatim probe of
   `list_int_index_of_between` passed 4 arguments — the helper is
   **3-param** (`values, lower, upper`); the checker correctly
   rejected *my program* (`PEP_ARGUMENT_COUNT: expects 3, found 4`).
   Corrected 3-arg probe: **REFUSED with `analysis_status=INCONCLUSIVE;
   stage=emitter; code=PEP_RUNTIME_STEP_LIMIT`** — i.e. on the
   combined stack the corrected helper hits **Wall A** (emit budget),
   matching my A2-own TEST measurements (`@ 4435:8` = emitter L24).
4. So the reconciled model: **three failure classes** — (a) family-A
   construct rule: local bindings in returned comparisons (my 9/9);
   (b) four-parameter construct limit (real, narrow: 2/14 family
   helpers + generic programs); (c) budget walls A/B (dominant for the
   index/search methods + the 182 collections step-limits + closures).

## Honest note

This is my third wrapper/probe bug this mission (wrong main type; `>`
nonexistent; assumed param count) — each disclosed at discovery with
the corrected measurement. Pattern: read signatures before wrapping.
