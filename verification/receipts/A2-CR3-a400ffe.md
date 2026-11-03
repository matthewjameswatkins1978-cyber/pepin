# A2 CR3 candidate `a400ffe` — **CR3 GATE PASSED** (agreement exit 0); bounded emission unregressed

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (integration-lead cycle) · **Evidence label:** `TESTED`
**Candidate:** `codex/a2-bounded-emission` @ `a400ffe1b6fdcbebf6c1357bdc36fea5420d94e8`
(clean pinned worktree `D:\Projects\wt-a3-a2b-a400ffe`; parent `2148b5d`).
**Mapping:** mission action "on A2 CR3 SHA: `declaration_emittability_agreement` (exit 0)".

## THE gate: CR3 restored

`verification/probes/declaration_emittability_agreement.py` (frozen blob `c5a0dec8…`,
unchanged) at `a400ffe`: **exit 0, `SUMMARY cases=4 claim_falsified=0`** (was exit 1 at
`6fa3c84`/`2148b5d`).

The exact divergence pair is gone — UNION_EMPTY now reports on **both** paths:

| path | diagnostic at `2148b5d` (before) | at `a400ffe` (after) |
|---|---|---|
| declarations-check | `Pep C23 tagged union has an unsupported layout` | **`Pep C23 does not lower empty records`** |
| whole emission | `Pep C23 does not lower empty records` | `Pep C23 does not lower empty records` (unchanged) |

All six fixtures now agree on verdict **and** exact text (CTRL ok/emitted; EMPTY,
UNION_EMPTY, REC_UNION, MUTUAL, ORDER text-identical). Matches A2's stated mechanism:
first refusal follows **emission order** (records before unions, each source order)
instead of closure discovery order — verdicts unchanged, nothing new became supported
(confirmed: every fixture's verdicts are byte-for-byte what they were, only the
UNION_EMPTY *text* moved). Scope check: my probe still exercises the function-closure
scope; no whole-program scan was smuggled in (their claim; consistent with results).

## No-regression battery at `a400ffe`

| gate | result |
|---|---|
| `tests.test_c23_bounded_emission` | **18/18 OK (9.7s)** (17→18: their new before/after control test) |
| `probe_integration_case --case all` ×3 | **byte-identical** (bundle `885d8781a4f7ff1fa96b5b22e5bd4699f5438616c84cb58949996f9b218486d6`); discriminating table **unchanged** — lexer 55n / d158044 66n die in checker; **synthetic-12 = valid + unit emitted + whole STEP_LIMIT**; synthetic-8 green → bounded-beats-whole unregressed |
| `probe_c23_sections --sizes 12` | header **4,558 B emitted**, main **83 B emitted**, all still STEP_LIMIT, units 0..12 emitted → the `2148b5d` header/main capability **preserved through the CR3 fix** (diff touches only `pep_c23_declaration_check` ordering) |
| `bounded_emitter_attacks` | exit 0, **5/0** |
| `prereq_closure_attacks` | exit 0, **8/0** |
| `per_unit_cost_baseline` | exit 0, `byte_identity=True`; ratio point **1.04** this run — N=2 wall-clock (1–2 ms) is noise-dominated; observed band across SHAs 0.63–1.04. **Stated plainly: the point ratio carries no information at this size; byte identity and the stage table are what I gate on.** No constant-cost or O(1) claim made. |

## Disclosure

A2's report was read *after* my gate run was designed (mapped in `BOOT-A3-20261103-001`
before their push) — the exit-0 criterion predates their fix, so this is a genuine
pre-registered gate, not a post-hoc fit. Their control claim ("fails with your exact text
pair against `2148b5d`") matches my own before-measurement from the previous cycle.

## Acceptance legs status (integration lead)

| leg | state |
|---|---|
| CR3 agreement restored | **VERIFIED at `a400ffe`** (gate exit 0) — closes pending combination |
| Bounded emission unregressed | **VERIFIED** (18/18, stage ×3, size-12 header/main intact) |
| P1 / discriminating checker cases progressing | **OPEN** — A1 has 0 commits after `05add76` |
| Combined coexistence set | **NOT RUNNABLE** until A1 lands |
| Whole-program success / constant-cost claims | **NONE MADE** (whole still STEP_LIMIT at 52+ nodes and size 13+) |

**Recommendation: still HOLD** — one acceptance leg (P1/A1) plus the combined run remain.
On A1's fix SHA: pack (`NOT OBSERVED = 3`, exit 0, frozen-blob verified) + stage ×3 +
discriminating four + agreement (re-check at combined SHA) → SHA-bound recommendation.

## Reproduction

```powershell
python -m unittest tests.test_c23_bounded_emission -v                 # 18/18
python tests\probe_integration_case.py --case all                     # x3, bundle 885d8781…
python tests\probe_c23_sections.py --sizes 12                         # header/main emit, all STEP_LIMIT
python verification\probes\declaration_emittability_agreement.py <wt> # exit 0 (CR3 closed)
python verification\probes\bounded_emitter_attacks.py <wt>            # exit 0, 5/0
python verification\probes\prereq_closure_attacks.py <wt>             # exit 0, 8/0
```
