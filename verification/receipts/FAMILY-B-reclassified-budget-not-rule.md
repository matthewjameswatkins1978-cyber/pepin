# Family B reclassified — the "second unsupported rule" is budget at the same Wall A hotspot (2026-10-30)

Cross-verifies the report's `673e6ea` ("unsupported class is at least
two distinct rules") against current pins. All runs sequential;
combined stack = A1 `46bf1c0` + A2 emitter `44d4e0f1` (a1x), A2-own =
`26be4be` (a2m).

## Measurements

| probe | stack | result |
|---|---|---|
| verbatim `list_int_count_between` + wrapper, all **5 test cases** (incl. `[]`, negatives) | combined | **all 5 EMIT** (5,184–5,228 B) |
| verbatim `list_int_first_or` / `list_int_index_of` / `list_int_last_index_of` | combined | **all EMIT** (5,152 / 5,220 / 5,187 B) |
| `test_pep_written_count_between…` (the report's **counter-example**) | A2-own | **1 failure — but it is the embedded 4-parameter probe's STALE EXPECTED MESSAGE**: asserts `"…supported scalar parameters and results"`, actual = newer `"…supported parameters and scalar or record results"`. **All 5 differential subtests passed.** |
| `test_pep_written_int_first_or…` | A2-own | **OK (24.9 s)** — passes at current pin |
| `test_pep_written_int_index_of_between…` | A2-own | **14 subtests FAIL — `PEP_RUNTIME_STEP_LIMIT @ 4435:8`** |
| `test_pep_written_int_index_of_outside…` | A2-own | **14 subtests FAIL — same code** |

**Position (hand-recomputed; my first script had an `total = n`
offset bug):** a2m bundle = lexer 494 + parser 1,875 + checker 2,042 +
emitter 3,334 → bundle L4435 = **emitter line 24 = `pep_c23_child`'s
scan loop — the exact Wall A hotspot** (round 17).

## Correction to the two-rules claim

1. **Family B is budget, not a construct refusal.** The index/search
   failures carry `PEP_RUNTIME_STEP_LIMIT` at the known hotspot —
   the same wall as the classifier/`ascii_continue` failures, reached
   here through A2-own's emit flow. No second refusal rule is needed
   for them.
2. **The count_between "counter-example" dissolves**: that method's
   single failure is a stale expected-message in its embedded
   4-parameter probe (the a14 stale-expectation class); the helper
   itself emits on all 5 cases on the combined stack, and
   `first_or` passes as a full method at the current pin.
3. What remains of the report's family-A rule is unchanged and
   independently confirmed (my 9/9 round 26): **local bindings in
   returned comparisons are refused** — one construct rule plus the
   budget walls explains the observed classes.

## Honest scope

- My helper-verbatim probes ran on the **combined** stack; the failing
  test methods run on **A2-own** (older bundled checker + A2's
  `pep_c23.py`). The reclassification holds regardless: the recorded
  failure CODE is budget (`STEP_LIMIT`) in both of the two failing
  methods measured, and no refusal code appears.
- Whether A2-own's emit flow is all-in-one (Wall B contract) or
  staged is not separately established here — the position lands in
  the emitter either way, and exhaustion-position caveat applies.

Blocker map unchanged (Wall A, Wall B, design trigger) — with family B
now folded into the budget walls rather than a new rule. Replay
**163/163**.
