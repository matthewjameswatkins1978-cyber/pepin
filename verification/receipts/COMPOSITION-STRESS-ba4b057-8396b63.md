# Composition stress at `ba4b057` and `8396b63` — no short demanding program reaches emission; the Pep-written checker's 100k budget is the first wall

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slice 4) · **Evidence label:** `TESTED`
**Pins measured:** A1 fix branch `codex/p1-checker-cost-fix` @ **`ba4b057`** and integration candidate `codex/checker-emitter-integration` @ **`8396b63`** (both in pinned detached worktrees, untouched)
**Instrument:** `verification/probes/composition_stress.py` (new) — three stages per fixture: seed `check` (front end) → seed `run` (interpreter) → `pep_c23.emit` (Pep-written parser → checker → C23 emitter).

## Result — identical at both pins

| fixture | seed check | seed run | Pep-written pipeline | first failing stage |
|---|---|---|---|---|
| `nested_records` (2 nested records, field chain, call) | valid | exit 0 | emitter refused | **UNSUPPORTED_BACKEND** — "Pep C23 functions require local bindings and supported loops followed by one return" |
| `list_pipeline` (`append`/`reverse`/`length`/`for`) | valid | exit 0 | emitter refused | **UNSUPPORTED_BACKEND** — "Pep C23 calls require a known target" |
| `token_lists` (`List[Str]`, `contains`, `==` in `for`) | valid | exit 0 | emitter refused | **UNSUPPORTED_BACKEND** — "Pep C23 for-in lowering requires a supported list literal or parameter and a non-empty supported body" |
| `union_match` (3-arm recursive union match + arithmetic) | valid | exit 0 | **checker refuses** | **VALID_BLOCKED_BUDGET** — `PEP_RUNTIME_STEP_LIMIT` at the Pep-written checker |
| `multi_function` (3 functions, record construction, boolean chain) | valid | exit 0 | **checker refuses** | **VALID_BLOCKED_BUDGET** — `PEP_RUNTIME_STEP_LIMIT` at the Pep-written checker |
| `multi_token_source` (`List[Token]` union loop + match) | valid | exit 0 | **checker refuses** | **VALID_BLOCKED_BUDGET** — `PEP_RUNTIME_STEP_LIMIT` at the Pep-written checker |

`SUMMARY fixtures=6 UNSUPPORTED_BACKEND=3 VALID_BLOCKED_BUDGET=3` at **both** pins, fixture for
fixture and message for message. **No fixture reached emission**, and every fixture is small: 14–30
lines, no recursion-heavy or generated source.

## What this establishes

1. **The wall is the Pep-written checker's fixed 100,000-step budget, and it is reached early.**
   Three of six ~20-line programs — one union match with three arms, one three-function record
   program, one `List[Token]` loop — exhaust it, while the **seed checks and runs all six**
   (exit 0). This is the same budget family A1 measured on the 66-node boolean chain and the same
   one LUCY-20261103-004 routed to structural work; it is now reproduced independently on ordinary
   composition rather than on the acceptance fixture alone.
2. **The three emitter refusals are a real backend subset boundary, not misdiagnosis.** They are
   worded precisely ("…require local bindings and supported loops followed by one return", "…calls
   require a known target", "…for-in lowering requires a supported list literal or parameter and a
   non-empty supported body"). Classified `UNSUPPORTED_BACKEND` on purpose: these name the lowering
   shape the emitter does not implement, which is a roadmap statement for A2, not a defect to file
   against A1. Notably a plain nested-record program with two `let`s and a `say` already falls
   outside the emitter's document shape — the practical native surface is narrower than "records +
   calls + lists" suggests.
3. **No regression from A1's S2 structural slices.** `ba4b057` (which carries `611616b`/`94373fb`
   plus the host repairs) is byte-for-byte identical to `8396b63` on all six fixtures. Whatever the
   S2 slices change, they do not yet move composition walls — consistent with A1's own 66n report
   that the boolean-chain flip is not achieved.

## Classification discipline

Each row distinguishes the mission's classes explicitly: valid compilation (`EMITTED`, none),
valid-feature-blocked-by-budget (`VALID_BLOCKED_BUDGET`, three), semantic disagreement (none — the
Pep-written checker never *accepted* something the seed rejects), unsupported backend feature
(`UNSUPPORTED_BACKEND`, three), incorrect diagnostics (none — no stage reported a code that
misdescribes its cause), harness/test failure (none; the probe fails fast with `FIXTURE_INVALID` and
exit 2 if a fixture is not valid Pep, so a bad fixture can never be read as a compiler verdict).

Two of my own classifier errors were caught and corrected **before** recording: the first version
scored the three precise emitter subset refusals as `INCORRECT_DIAGNOSTIC`, and the first fixture set
used `length(Str)` (not a builtin) and omitted `main` (required by the emitter), which would have
answered fixture-design questions instead of compiler questions. Both corrections are recorded here,
not silently applied.

## Honest scope

- Six hand-written fixtures, not a corpus; no generated or large source.
- Native compilation is **not** run (`EMITTED` means the C source was produced, not built or executed).
- One probe run per pin; no bisection of when the composition walls appeared. `8396b63` was chosen as
  the integration baseline and `ba4b057` as the current A1 head; older pins are unmeasured here.
- Seed `run` produced no observable stdout in this environment even for `say`-heavy programs, so the
  execution stage is judged by exit code and refusal code, not by printed output.

## Reproduce

```powershell
python verification\probes\composition_stress.py D:\Projects\wt-a3-a1-ba4b057     # exit 1: 3+3
python verification\probes\composition_stress.py D:\Projects\wt-a3-int-8396b63   # exit 1: 3+3 (same)
python verification\probes\composition_stress.py D:\Projects\wt-a3-a1-ba4b057 union_match
```

## Next action

Reported to A1/A2/Lucy on #16. Recommendation for the next candidate: treat the checker budget on
ordinary composition (not only the 66n acceptance fixture) as the critical path, and state the
emitter's document-shape subset explicitly so "records + calls + lists" composition is not assumed
to be reachable natively until it is measured.
