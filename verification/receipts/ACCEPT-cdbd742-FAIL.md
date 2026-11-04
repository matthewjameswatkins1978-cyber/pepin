# Integrated candidate `cdbd742` — Full-v2 **FAIL 14/15**, duplicate-type repair **verified closed**, one residual kind-crossing hole

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-007 (A3 first slice) · **Evidence label:** `TESTED`
**Candidate:** `codex/checker-emitter-integration` @ **`cdbd742095edb02f7a512039355698a3e86455ce`** — "Merge codex/p1-checker-cost-fix: duplicate-type closure + call contract (INTEGRATED-CANDIDATE-4)"
**Tree:** `D:\Projects\wt-a3-int-cdbd742` (detached, clean, created for this run) · **Instrument:** `verification/**` on `codex/bootstrap-agent3-verification` @ `a4f2833` (manifest `b464e00e`… runner, `688042d7`… probe, v1 `e5cad4df`/`e819607c`)

## Ancestry verified BEFORE the run

Parents `c69e15d` + `f4eb231`. Contains `8396b63`, `e0e49e5`, `0c5f12b`, `97e420b`, `f4eb231`.
**Does NOT contain `ea0bc9a`** — A2's lane is still absent from the integrated line (as routed; A2's native work
is not in this candidate, and nothing here tests it).

## Verdict: FAIL 14/15 — sole red gate is the 66-node row, unchanged by the repair

| gate | result |
|---|---|
| frozen manifest (13 entries) | **ok** 13/13 |
| acceptance baseline v2 (v1 preserved) | **ok** v1 archive intact |
| pack parse-check | **ok** exit 0 |
| combined emitter suites | **ok** 53 tests, `Ran 53 tests in 150.124s OK` |
| stage probe ×3 | **ok** byte-identical bundle `1a223920c051de5e4b157c65fb6743c3a321607708dd807f9bf5b968a35c27b4` (≠ `92167083…` at `c69e15d`: staged output changed, per-row verdicts did not) |
| **discriminating rows** | **FAIL** — `lexer=valid regression=PEP_RUNTIME_STEP_LIMIT`; `check=valid unit0=emitted all=PEP_RUNTIME_STEP_LIMIT` |
| synthetic-12 bounded-beats-whole | ok `check=valid unit0=emitted all=PEP_RUNTIME_STEP_LIMIT` |
| synthetic-8 fully green | ok |
| 7 probes (declaration_emittability, bounded_emitter, prereq_closure, per_unit_cost, refusal_code_coverage, hostile_chunk_scalar_types, lextoken_make_token) | ok, **0 falsified** across all |
| pack run at integrated SHA | ok — exit 0, **`NOT_OBSERVED=3 PROVEN=0`** |

`first_fail = discriminating rows: lexer=valid / regression=valid`, exit 1. No gate skipped. **The duplicate
repair moved the budget row zero nodes** — exactly as predicted; the row is the same 66-node boolean-chain
case that fails at `c69e15d`.

## Repair #1 (duplicate type declaration) — **VERIFIED CLOSED**

Mechanism at `cdbd742`, `tests/pep_checker_a13.pep`:
- producer: `chunk_type_declarations` collects a whole-source duplicate scan over `resolve_all_records`
  (`:2511–2530`) and emits `duplicateType: contains(duplicateNames, resolved.recordName)` (`:2549`);
- consumer: `analyze_chunk_typed` `:2622–2634` and `analyze_chunk_typed_bound` `:2648–2660` refuse with
  `PEP_DUPLICATE_TYPE` on a carried `duplicateType` flag **or** a repeated external name (the cross-chunk path).

Evidence:

| probe | at `c69e15d` | at `cdbd742` |
|---|---|---|
| `dup_decl_minimiser.py` (81-byte fixture, seed `PEP_DUPLICATE_TYPE`) | flip reproduced (fail-open) | **no flip reproduced**; control M2 order-stable, seed `valid` |
| `staged_metamorphic_matrix.py` | 13 cells, 12 pass **1 fail** (`dup_decl`) | **13/13 pass, 0 fail** — `dup_decl R4 forward=invalid reversed=invalid whole=invalid seed=invalid`; `incomplete` cell now passes R1 (both paths fail closed) |
| `staged_partial_provenance.py` | 9 cells 8/0/1 | unchanged 9 cells **8 pass 0 fail 1 observed** |

## FINDING — residual fail-open at the kind boundary (record vs union namesake)

`dup_decl_cross_chunk.py` (new probe, 7 claims, **2 falsified**):

| case | claim | result | seed |
|---|---|---|---|
| X1 | distinct same-shape records stay valid (no over-refusal) | **HELD** valid, flags `[False,False]` | valid |
| X2 | duplicate record split across two chunks is refused | **HELD** refused `PEP_DUPLICATE_TYPE` (each chunk's own flag was `False`; the consumer's repeated-name count refused) | invalid `PEP_DUPLICATE_TYPE` |
| X4 | both declarations in ONE chunk refused/flagged | **HELD** refused, flag `[True]` | invalid `PEP_DUPLICATE_TYPE` |
| **X3** | **`type D {a: Int}` + `type D = Left() \| Right()`** split across chunks must be refused | **FALSIFIED — staged `valid`** | invalid `PEP_DUPLICATE_TYPE` |
| X5 | control: same shapes, distinct names stays valid | **HELD** valid | valid |
| **X6** | same namesake, union first then record | **FALSIFIED — staged `valid`** | invalid `PEP_DUPLICATE_TYPE` |
| X7 | observation: does a union declaration chunk yield a type fact? | `facts=0`, body with a `F` parameter → **`PEP_UNKNOWN_TYPE`, invalid** | **valid** |

**Mechanism:** only records are resolved into external facts (`resolve_all_records`), so a record/union
namesake contributes exactly one external `ResolvedTypeDecl`; the consumer's repeat-count and the producer's
`duplicateType` flag both need two facts, so neither fires. X5 shows duplication is the only variable; X3 and
X6 show it is order-insensitive.

**Second consequence (fail-closed, not a soundness hole):** X7 — a chunk whose function takes a **union**-typed
parameter is refused with `PEP_UNKNOWN_TYPE` on a program the seed accepts, because union declarations emit no
external type fact. Union-crossing chunk work is therefore blocked; the refusal is honest but the capability
is missing.

## What A1 needs to close it

Emit union declarations as external type facts too (same `ResolvedTypeDecl` shape with `typeKind: "union"`),
then the existing repeat-name count in both consumers covers record/union mixes for free — and X7 flips from
`PEP_UNKNOWN_TYPE` to `valid` at the same time. Rejecting the duplicate in `record_field_shape_ext` alone would
not help: the duplicate is invisible to the body chunk.

## Reproduce

```powershell
pwsh -NoProfile -File verification\tools\run_acceptance_gates.ps1 -Mode Full `
  -CombinedWorktree D:\Projects\wt-a3-int-cdbd742 -OutJson _build\accept-cdbd742.json
python -X utf8 verification\probes\dup_decl_minimiser.py  D:\Projects\wt-a3-int-cdbd742
python -X utf8 verification\probes\staged_metamorphic_matrix.py D:\Projects\wt-a3-int-cdbd742
python -X utf8 verification\probes\staged_partial_provenance.py D:\Projects\wt-a3-int-cdbd742
python -X utf8 verification\probes\dup_decl_cross_chunk.py D:\Projects\wt-a3-int-cdbd742
python -X utf8 verification\probes\binding_pool_attacks.py D:\Projects\wt-a3-int-cdbd742
```

## Stale binding facts — still open at `cdbd742` (A1's assigned next repair)

`binding_pool_attacks.py`: 13 cases, **3 falsified**, unchanged from `c69e15d`:
- `O1c` `seed=invalid with_stale=valid without=invalid` — a stale binding fact still flips a verdict;
- `O1b` cross-revision binding facts still **accepted** (`BindingFact` has no document/revision);
- `A1b` `add()` still cannot distinguish a conflict from an identical duplicate (`first=1 identical=0 conflict=0`).

## Row-level bounded negative at `cdbd742` (the red gate, unattributed drift check)

`exact_node_ladder.py` at this pin: **62 nodes `ok`, 64 nodes `PEP_RUNTIME_STEP_LIMIT`** — the same
measurement band recorded before the duplicate repair (62 pass / 64 refuse). The repair therefore costs the
row nothing and moves it nothing; the 66-node target needs 4 more effective nodes, ≈6 % of the per-node
budget.

`checker_pass_attribution.py` at this pin — `chunk_signatures` and the **new whole-source duplicate scan in
`chunk_type_declarations`** stay `ok` at every rung measured (including 484-node boolean chains);
`analyze_parsed` is the only pass that refuses (from 84 nodes on the boolean-chain axis). So the new
declaration-closure scan is not the cost driver, and the bound is unchanged where it was.

## Composition check: does the repair hold when A2's lane is merged in?

Scratch both-lane tree `D:\Projects\wt-a3-seam2` = `git merge-tree --write-tree cdbd742 ea0bc9a` →
`4915a76c…`, wrapped in local commit `8356373a05252217ed40d3b0621b0369ae611408` (never pushed, a measurement
fixture only; integration remains A1's).

- `seam_cross_chunk_attacks.py`: **7 cases, 0 falsified** — S0 honest facts `valid`, S1 missing callee
  `not-valid`, S2 forged arity `not-valid`, S3 forged callee name `not-valid`, S4 self-consistent forgery still
  indistinguishable (structural, unchanged), S5 emitter emits for the matching document and **`REFUSED:PEP_STALE_REVISION`** for a foreign report. A1's call contract did not weaken any seam guard.
- `dup_decl_cross_chunk.py`: **9 claims, 2 falsified** — X2 (duplicate records across chunks) refused and X1
  control valid exactly as at `cdbd742`, and X3/X6 (record/union namesake) still **accepted**. So the repair
  composes with A2's lane, and the residual hole is present in the merged tree too. Validate any union-fact fix
  against this merged shape, not only against `cdbd742`.

## Primitive shadowing: refused on both sides (diagnostic divergence only)

`dup_primitive_shadow.py` (seed oracle, no harness): the seed refuses **even a single** `type Int { a: Int }`
or `type Bool { a: Int }` with `PEP_DUPLICATE_TYPE`. The staged path also refuses, but through
`PEP_A13_TYPE_UNSUPPORTED` + `PEP_UNKNOWN_FIELD` — because primitive-named declarations are deliberately
excluded from external facts. Same verdict, different cause: **fail-closed, not a hole**, but the diagnostic
codes do not match the seed's, and the reason (no fact emitted) is the union gap's sibling.
