# B4 Cycle-6 — Evidence Matrix: Rules → Builder SHAs → Oracle Tests

**Assignment:** LUCY-20261104-008, A4 task 3. **Branch:** `spec/agent4-spec-lab`
**Method:** synthesis of session-read artifacts only (B4-C1/C2/C3/R1/R2/R3/C4/C5,
A1 `9ad7d95` + `f4eb231` diff-reads, A3 reports at `0e94029`/`a4f2833` as
reported, seed `57fe424`). No new probes run, no implementation changed.
**Reading key:** ESTABLISHED = seed behavior or session source-read;
REPORTED = builder/A3 stated, SHA-bound, not independently rerun here;
INFERRED = follows from cited reads; UNKNOWN = no evidence either way.

## 1. Rule → implementation → oracle matrix

| Rule (status) | Builder SHA (status) | Oracle test (status) | Standing |
|---|---|---|---|
| B4-CLOSURE-01: no `valid` without whole-R D-closure | A1 dup-record repair lineage (REPORTED fixed; independent verdict pending at `81398fa`) | A3 `dup_decl_minimiser` 81-byte both-orders (REPORTED 0-flip at `cdbd742`); `staged_metamorphic_matrix` 13/13 (REPORTED) | HOLDING-WHERE-REPORTED; gate `81398fa` pending |
| B4-CLOSURE-02/03: single type namespace, unions as facts (B4-C4) | NONE — no builder SHA implements it (ESTABLISHED absent by source-read at `9ad7d95`) | T-REC-1..5 specified, unrun (UNKNOWN at every pin) | OPEN DEFECT; pre-fix baseline due at `81398fa` |
| B4-AUTH-01/02 bindings: stamped + stale-guarded | `9ad7d95` (ESTABLISHED by diff-read: production stamps, `PEP_STALE_REVISION`, single ingress) | T-ADM-1 O1c/O1b retest (REPORTED green by builder 4+4; independent rerun pending) | CLOSED-BY-CONSTRUCTION; independent verdict pending |
| B4-AUTH-03/04: conflict-raise + deepcopy | `9ad7d95` pool (ESTABLISHED by diff-read) | T-ADM-2/3 locks specified, unrun | CLOSED-BY-CONSTRUCTION; probe-due |
| B4-AUTH-01 callee side / R-ID-1 collision check | NONE (ESTABLISHED absent — `9ad7d95` touches no fn path) | T-ADM-4 documents expected-accept of S4/O4 (specified, unrun); T-CALL-6 (B4-C2, unrun) | OPEN BY DESIGN; next repair candidate |
| B4-CALL-01..05 cross-chunk call contract | `f4eb231` rules 1–7 (REPORTED, audited B4-R3: conditionally sound) | S2/S3 cross-checks (REPORTED holding); S4/O4 forgeries (REPORTED open) | CONDITIONAL — see §2 |
| B4-PARSE-01..06 / O-U/N-U union obligations | NONE in staged checker scope | Parser probes P-side (B4-C2S4, prior) | OPEN, lower priority than closure+identity |
| Entry E-1+E-3 (document + warn, no behavior change) | NONE (no builder asked to change) | T-ENTRY-1..5 (specified B4-R2, unrun) | PROPOSED, awaiting owner decision, not a defect |

## 2. Conditional-soundness ledger (what "conditionally" currently rests on)

- Call contract soundness rests on (a) globally unique fn names + (b) honest
  revision-bound facts (B4-R3). Per §1: (b) now holds for BINDINGS at
  `9ad7d95` (construction), still fails for CALLEE facts (no SHA), and (a)
  relies on R-ID-1 which has no SHA. Net: contract is sound for
  binding-mediated calls, UNSOUND-by-construction for forged-callee calls.
- Closure soundness rests on whole-set name visibility. Holds for
  record/record (REPORTED repaired), FAILS for record/union and union/union
  (ESTABLISHED absent). Net: closure is kind-partial.
- No claim in this matrix upgrades a REPORTED to TESTED. Only A3's rerun at a
  pinned SHA can do that; only the seed can anchor ESTABLISHED behavior.

## 3. Ordered verification backlog (for A3/Lucy scheduling, not new work)

1. `81398fa` Full-v2 + T-REC baseline (expect T-REC-1/2 fail-open, T-REC-4
   false-reject) + adapted T-ADM-1..3 (expect pass) + T-ADM-4 (expect-accept).
2. First repair SHA for B4-CLOSURE-02/03 → rerun T-REC-1..5 (expect all pass).
3. First R-ID-1 / callee-identity SHA → rerun S4/O4 + T-CALL-6 + T-ADM-4
   (expect flip to refuse).
4. Entry T-ENTRY-1..5 once any party touches entry semantics (no urgency).

## 4. Status labels

SYNTHESIS (not new evidence): every cell cites the prior doc where its claim
was established; nothing here is independently probed. PROPOSED: order §3.
UNKNOWN: all gate outcomes. Next A4: highest-value READY is whichever of §3
rows 2–3 stays unowned after the `81398fa` gate — or the Q1/Q2 investigations
(B4-C2S6) if both land. No freeze, no master/CURRENT changes.
