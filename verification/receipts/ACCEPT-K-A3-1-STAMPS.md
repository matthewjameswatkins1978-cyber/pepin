# K-A3-1: A1 `727f8af` stamp schema gated without a false victory

**Date:** 2026-11-05 · **Mission:** LUCY-20261105-001 / Campaign K, A3 card K1 · **Evidence label:** `TESTED`
**PIN: A3 | `codex/bootstrap-agent3-verification` | tested at A1 `727f8af` (detached `D:/Projects/wt-a3-a1-727f8af`) | probe committed separately**
**First next action:** K2 — trace the admitted same-target forgery to the native boundary through an existing reachable API.

## Why the old probe could not answer this

`fact_laundering.py` fetches facts from one `open` and checks a chunk from a **different** `open`. At `727f8af` that fires the new cross-target ingress rule, and a re-run would report "refused" — reading as *forgery fixed* when only the cross-target policy fired. Card K1 called this out in advance; this probe keeps the questions apart.

Source read that defines the split (`tests/pep_checker_a13.pep` @ `727f8af`):

- `chunk_signatures` (2493): `if parsed.document != authority.document || parsed.revision != authority.revision { return [] }`, then stamps `authority.document`/`authority.revision` (2499).
- `analyze_chunk_typed` (2679-2694) and `analyze_chunk_typed_bound` (2722-2733): refuse with `PEP_STALE_REVISION` when `extFunction.document/revision != parsed.document/revision`, likewise for `extSignature`.

So the producer guards *parsed == snapshot* and the consumer guards *fact == parsed*. **The stamp is a consistency gate between producer and consumer identity, not an integrity gate on content.**

## Result: 10 claims, 9 held, 1 falsified

Oracle first (whole source via `pep.ps1 check --json`): INVALID → `invalid [PEP_TYPE_MISMATCH]`; VALID → `valid []`.

| # | claim | verdict |
|---|---|---|
| P | producer stamps the target it was asked about | **HELD** — stamp `doc-3` / `sha256:d442a279…` == invocation target |
| A1 | same-target honest **positive** is valid | **HELD** `valid` |
| A2 | same-target honest **negative** is invalid + `PEP_TYPE_MISMATCH` | **HELD** `invalid [PEP_TYPE_MISMATCH]` |
| A3 | same-target **forged param** (retyped Str, honest stamps kept) is refused | **FALSIFIED** — `valid`, no diagnostics |
| A4 | same-target duplicate fact refuses | **HELD** `invalid [PEP_DUPLICATE_FUNCTION]` |
| B1 | foreign **document** stamp refused | **HELD** `invalid [PEP_STALE_REVISION]` |
| B2 | foreign **revision** stamp refused | **HELD** `invalid [PEP_STALE_REVISION]` |
| B3 | **omitted** stamp fields fail closed | **HELD** transport `PEP_TOOL_ARGUMENT_FIELDS` "Record fields do not match the checked record type" |
| A5 | **aliased synthetic ids** (distinct names, same target) | **HELD** `invalid [PEP_DUPLICATE_FUNCTION]` — added after the first pass to close the gap this receipt originally deferred |
| C1 | **cross-target** facts refused (policy test, kept separate) | **HELD** `invalid [PEP_STALE_REVISION]` |

A2 is the load-bearing control: identical slicing and identical fact provenance to A3, differing **only** in the fact's parameter type — honest facts reproduce the whole-source diagnostic, forged facts erase it. So the divergence is caused by fact content, not by the harness.

## Exact threat model (what this does and does not close)

- **NOT reachable through the normal producer.** `chunk_signatures` derives the signature from the same parsed bytes it stamps, and refuses when `parsed != authority`, so it cannot emit a fact contradicting its own source. Verified by P + A2.
- **Reachable by any host that can send JSONL.** A `tool_invoke` carrying hand-built `List[CheckedFunction]` / `List[ResolvedSignature]` values with correct same-target stamps is admitted (A3). Whoever can supply facts already controls the batch, so this is a trust-boundary property rather than an escape — but it means **the schema answers "which source revision is this fact from?", not "does this signature describe the declaration?"**
- Therefore the earlier H-V3 finding stands *at this SHA*, in the same-target form. A1's own commit message documents the residual; this is the independent measurement behind that sentence.
- Cross-target refusal (C1) is a genuine new guarantee and is recorded as such — not as a forgery fix.

## Reproduce

```powershell
python -X utf8 verification\probes\stamp_schema_k1.py D:\Projects\wt-a3-a1-727f8af
# exit 0 expected only when A3 is also held; today it exits 0 with one FALSIFIED line printed
```

Probe reuses `tests/chunk_helper.py` from the pinned tree and `pep_chunk_contract.py` from that tree's root; session + tool registration code follows the proven register→validate→activate sequence. No peer file edited; A1 worktree read-only and left clean; main checkout `57fe424` untouched by this slice apart from the pre-existing dirty `tests/test_a14_c23.py`.

## Honest limits

- One two-function program, one forged axis (parameter type). Return-type forgery is covered separately in the Campaign-H probe and behaves the same way by the same code path — not re-measured here.
- Aliased synthetic ids with distinct names (the old E1 shape) were **added in the same probe** as A5 and refuse on one target; no longer deferred.
- No native stage: K2 owns the question of what a `valid` forged chunk does downstream.

## Signal v0.1 handoff to A1 (K8, handoff 1 of 2)

```text
PIN: A3 | codex/bootstrap-agent3-verification | 08e1e8b (+this commit) | pushed+remote-verified | clean
RESULT: 727f8af stamps gated independently: honest same-target valid/invalid correct, foreign doc+rev refused PEP_STALE_REVISION, omitted fields refused at transport, duplicate refused; SAME-TARGET forged param still ADMITTED. TESTED.
REPRO: python verification\probes\stamp_schema_k1.py D:\Projects\wt-a3-a1-727f8af
FALSIFIER: if A3 (forged param) ever refuses without a content-binding check, this reading is wrong.
NEEDS: A1 — decide content-binding vs documented trust boundary; no code change requested yet.
```
