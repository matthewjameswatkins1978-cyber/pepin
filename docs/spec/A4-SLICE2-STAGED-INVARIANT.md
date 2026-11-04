# Agent 4 Slice 2 — Staged-Compilation Semantic-Preservation Invariant Cluster

**Packet:** PEP-A4-20261104-001, Slice 2. **Branch:** `spec/agent4-spec-lab`
**Pins:** seed oracle = campaign `57fe424` (`pep_ocaml.ml`); staged subject = A13
chunked checker at `bcfa3c0` (`codex/checker-emitter-integration`; typed entry
introduced `49db581`); defect re-confirmed CURRENT at A1 head `97e420b` by A3 (`codex/bootstrap-agent3-verification` @ `d7523780`, same 81-byte flip + same 12/1 matrix); A3 evidence also @ `d720570` (slice 1) and @ `5694f568` (slice 2, 13-cell matrix, 12 pass / 1 fail);
fixture blob `8466adf6…` / sha256 `7848eea5…` (81 bytes, LF-pinned).
No staged checker was built or modified here; all verdicts below are A3-measured.

## 1. The proposed invariant, and why its naive reading is already false

Packet wording: *"For equivalent source, scope and validated semantic facts, the
result of semantic checking must not depend on how the program is partitioned
into checked chunks."*

**Status: FALSIFIED as stated.** A3 CE-1 (slice 1): the 81-byte duplicate-`type D`
program is `invalid` under the seed oracle (`PEP_DUPLICATE_TYPE`) but `valid`
under chunked `analyze_chunk_typed` with `D{a}` facts first, `invalid` reversed.
Partitioning changed the verdict. The defect is open (A1 owns the fix; A3's
requested repair: carry `decl.duplicateType`, refuse repeated names with a
declared code).

**Sharpening (A3 slice 2):** with `expectReturns=false` the same program reads
`valid` in BOTH orders while whole+seed stay `invalid`. Order-dependence is one
symptom; duplicate-tolerant acceptance is the disease. Any invariant that only
demands order-independence (A3's own R4 did this at first, then corrected it)
would pass a broken checker. **Relations must be judged against the oracle, not
against each other.** This methodological correction is part of the cluster.

## 2. Rule cluster (stable IDs; each falsifiable)

Definitions: *equivalent* = identical source bytes, identical revision, identical
scope/roots. *Validated facts* = checker-produced at a pinned SHA, schema-
versioned, duplicate-flagged, revision-bound. *Oracle* = whole-source seed check
at the pinned base, inside the supported subset only.

| ID | Rule | Status + evidence |
|---|---|---|
| A4-SI-01 | A staged check MUST agree with the oracle on every program the oracle rejects for duplicate declarations, under every partition and fact order. | VIOLATED (open defect). CE-1, CE-2. Re-confirmed CURRENT at A1 head `97e420b` (A3 `d7523780`); the new ledger test there asserts nothing about duplicates (good — hole not crystallised). Fix owned by A1, must land on A1's branch. |
| A4-SI-02 | For oracle-valid programs, the staged verdict MUST NOT depend on fact order. | HOLDS where tested (A3: valid record use, fact-order stable). Assumption: facts complete + validated. |
| A4-SI-03 | Chunks with missing facts MUST refuse, never guess. | HOLDS where tested (missing-fact closure refuses). |
| A4-SI-04 | Facts foreign to the revision/scope MUST be refused. | HOLDS where tested (foreign-fact closure refuses). |
| A4-SI-05 | Reordering *independent* declarations MUST NOT change the verdict. | HOLDS where tested. Note: duplicate declarations are NOT independent — A4-SI-01 takes precedence. |
| A4-SI-06 | Body-vs-full-group chunkings of the same valid program MUST agree; partial (under-carried) groups MUST be refused. | HOLDS where tested (A3 corrected R3 to compare against oracle). |
| A4-SI-07 | Oracle-invalid programs MUST be rejected; incomplete programs MUST NOT execute. | HOLDS where tested (unknown-field body refused; incomplete fails closed). |
| A4-SI-08 | No acceptance may rest on unvalidated facts. A hardcoded `duplicateType:false` with no dedupe is not validation. | VIOLATED by construction at `bcfa3c0` (`external_records:2532`, `record_field_type_ext:2561` first-match). Same root cause as A4-SI-01. |

## 3. Assumptions (load-bearing; if any fails, the rules above do not apply)
- S-1: the seed oracle is authoritative ONLY inside its implemented subset
  (spec v0.1). Out-of-subset inputs must be refused as unsupported, never
  accepted (cf. LUCY-20261027-008 fail-closed boundary).
- S-2: facts carry producer SHA, schema version, source revision, and
  duplicate flags. Anything less is unvalidated by definition.
- S-3: global consistency (no duplicate type/function/binding names per seed
  rules; later: no import cycles) is established BEFORE chunk acceptance —
  ownership of this pre-pass is architectural decision AD-1.
- S-4: budgets, performance, and cross-revision reuse are OUT of scope for this
  cluster. No timing or caching claim is made here.

## 4. Counterexamples (for Agent 3's corpus; all pinned)
- CE-1: `dup-decl-order.flip.pep` (81 B, blob `8466adf6…`): seed invalid /
  chunked valid-when-`D{a}`-first. Falsifies naive partition-independence.
- CE-2: same fixture, `expectReturns=false`: chunked valid in BOTH orders.
  Falsifies order-independence as a sufficient condition.
- CE-3 (proof obligation, NOT a claim): stale-revision facts (gathered at R,
  applied at R′) accepted by a staged check. A3 session-layer stale tests exist;
  the staged-path equivalent is requested in §6 (T-stale).

## 5. Explicit limits (what is NOT guaranteed)
- L-1: no universal whole≡chunk equivalence is claimed or claimable from passing
  cells; each cell evidences only its row.
- L-2: duplicate-*scope-binding* parity held (A3), but nested-scope and
  shadowing interactions beyond the tested rows are UNKNOWN.
- L-3: the seed oracle's own duplicate-type path is IMPLEMENTED but
  seed-untested (Slice 1 D-04/O-1); the oracle anchor for A4-SI-01 needs the
  proposed seed fixtures before it is TESTED.
- L-4: cross-revision fact reuse has no justification in this cluster; same-
  revision cache behaviour is separately TESTED (A3 042: parse 2 / typecheck 2 /
  hits 3), cross-revision reuse is refused by the seed session.

## 6. Test requirements for Agent 3 (extends the existing matrix, no new harness)
- T-oracle: every staged relation asserts against the seed verdict, never only
  forward-vs-reversed (A3 R4 lesson, already applied).
- T-partitions: for each fixture class {valid record use, dup type, dup fn,
  dup binding, missing fact, foreign fact, partial group, independent reorder,
  invalid body, incomplete source}: all chunk-boundary permutations × both fact
  orders, recorded as a fixed case × relation table with first-failure cited.
- T-stale (new): CE-3 probe — facts from revision R checked against R′ must
  refuse with a declared code.
- T-codes: every refusal carries a declared diagnostic code; code family is
  AD-2. Unknown/stale/partial inputs must not share one undifferentiated error
  unless the family declares it.
- T-seed-anchor: seed-level dup-type/dup-fn fixtures (Slice 1 D-04) so A4-SI-01
  rests on a TESTED oracle, not a source-read one.
- Reporting: relation table + pass/fail/skip counts + shortest counterexample +
  first failure + code SHAs (A3's current format already satisfies this).

## 7. Architectural decisions required (NOT made here; for Lucy/Matthew/A1)
- AD-1: who validates global consistency — host pre-pass over declarations vs
  chunker-carried `duplicateType` flags — and where it lives in the fact schema.
- AD-2: refusal code family for staged-path rejections: reuse seed `PEP_*`
  codes (e.g. `PEP_DUPLICATE_TYPE` at chunk level) vs staged-specific codes,
  and which family documents the mapping.
- AD-3: confirm the supported-subset fail-closed gate (LUCY-20261027-008) as a
  precondition for ANY staged acceptance claim; without it A4-SI-01..08 are
  unenforceable.

## 8. Relation to the continuing queue
This cluster deliberately does NOT touch ownership transfer, `edit`/`take`
aliasing, or task isolation (queue item 1): those concern what validated facts
*mean*, while this cluster concerns whether staged facts may be *trusted at
all*. Trust first, meaning second. The NEXT ACTION's ownership analysis builds
on A4-SI-01..08 as assumed ground, and must not weaken them.
