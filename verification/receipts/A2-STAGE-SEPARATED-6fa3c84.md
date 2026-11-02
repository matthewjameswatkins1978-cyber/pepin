# A2 `6fa3c84` — stage-separated integration probe verified (units beat whole-program at unchanged limits; checker boundary cross-checked)

**Date:** 2026-11-02 · **Lane:** Agent 3 independent verification · **Evidence label:** `TESTED`
**Target:** `codex/a2-bounded-emission` @ `6fa3c8414cde1a77ca93f79dc8e38abb72bbbd16`
(clean pinned worktree `D:\Projects\wt-a3-a2b-6fa3c84`).

## 1. A2's new instrument, run 3× — **identical every time**

`python tests/probe_integration_case.py --case all`, bundle sha256
`6db62539361cf171b99b546afd068f1edba9935ea5778617ec62047239d6a488` (same across runs —
rows are bound to an emitter revision as A2 designed):

| case | bytes | nodes | checker | unit 0 | whole |
|---|---|---|---|---|---|
| lexer-chunk (`LexToken`+`make_token`) | 488 | 55 | **STEP_LIMIT** | — | — |
| regression (`d158044` shape) | 440 | 66 | **STEP_LIMIT** | — | — |
| synthetic-8 | 302 | 36 | valid | **emitted** | emitted |
| synthetic-12 | 442 | 52 | valid | **emitted** | **STEP_LIMIT** |

**The headline reproduces: `synthetic-12` — checker valid, bounded unit emitted, whole
program dies at `PEP_RUNTIME_STEP_LIMIT`,3/3 runs identical.** This is the first
stage-separated evidence that the bounded contract beats whole-program emission at
unchanged limits (corpus-wide prior: such failures were one ambiguous number).
A2's N=12 self-correction (emitter, not checker, was the earlier failure) is consistent
with this table.

## 2. Cross-check `probe_c23_sections.py --sizes 12`

Reproduced: **`all`/`header`/`main` all `PEP_RUNTIME_STEP_LIMIT`** while **units 0..12
all `emitted`** (105–106 bytes each, `unit_calls: 13`) — their "every unit emits while
the three assembling paths fail" claim. `byte_identity: not-checked` at this size
(cannot assemble when header/main refuse — expected, not a gap).

## 3. Checker-boundary numbers — third independent data point, consistent with my earlier receipt

A2 measures **55-node lexer chunk FAILS / 66-node regression FAILS / 52-node synthetic
PASSES** in the checker, concluding "shape matters more than count". This agrees with my
`VOLUME-CORRELATION-real-lexer-05add76` findings: no universal node ceiling; cost
constants are kind/shape-dependent (function-body regime bound at pass@55/fail@59;
declaration regime ≤1315 steps/node), which is why A1's ~100-node synthetic figure and
A2's 55-node lexer failure coexist without contradiction. Recorded as cross-lane
triangulation, not a new measurement of mine.

## 4. My probes, unchanged, at this SHA

| probe | result |
|---|---|
| `bounded_emitter_attacks` | exit 0, **claim_falsified=0** (5 cases) |
| `prereq_closure_attacks` | exit 0, **claim_falsified=0** (8 cases) |
| `per_unit_cost_baseline` | exit 0, ratio **0.80** (series band 0.63–0.80; wall-clock noise), byte identity True |
| `declaration_emittability_agreement` | exit 1, **claim_falsified=1** — **my UNION_EMPTY first-refusal text finding is still OPEN at this SHA** (`check: tagged union has an unsupported layout` vs `whole: does not lower empty records`); A2's new commits did not address it (finding posted `#16 6589615167`, awaiting their response) |

Suites: `tests.test_c23_bounded_emission` **16/16 OK (5.4s)**.

## Honest scope

Stage labels trusted as printed by A2's instrument and reproduced byte-identically over
3 runs; I did not independently instrument step counters (not exposed). Checker-boundary
numbers are A2's measurement re-observed through their probe, not re-derived from raw
fuel. One head; no native work in this slice; no builder files touched.

## Reproduction

```powershell
python tests\probe_integration_case.py --case all         # x3, identical
python tests\probe_c23_sections.py --sizes 12             # units 0..12 emitted; all/header/main STEP_LIMIT
python -m unittest tests.test_c23_bounded_emission        # 16/16
python verification\probes\declaration_emittability_agreement.py <wt>   # exit 1 (open finding)
```
