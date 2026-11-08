# B4 Cycle 2 Slice 6 — Synthesis: Rule → Test → Implementation → Evidence

**Packet:** PEP-WB-A4-20261104-B, Cycle 2 Slice 6 (final). **Branch:** `spec/agent4-spec-lab`
**Head:** this commit. **Base refs:** seed `57fe424`; A1 `2f939a0`; A3 `24cd5b6`;
integration `c69e15d` (unverified); A2 `ea0bc9a`.

## 1. Rule → test → implementation SHA → evidence status

Evidence key: ESTABLISHED / TESTED / INFERRED / UNKNOWN (charter) ×
ACCEPTED / PROPOSED / IMPLEMENTED (design status). "TESTED-failing" means a
test demonstrates the violation — evidence *of* the defect, not of the rule.

| Rule | Test(s) | Implementation SHA | Status |
|---|---|---|---|
| A4-SI-01 (dup-decl staged refusal) | A3 81-B fixture ×4 orders; F1–F3 | A1 `2f939a0` (defect open) | PROPOSED + TESTED-failing |
| A4-SI-02 (fact-order stability, valid) | A3 13-cell valid rows | A1 `2f939a0` | PROPOSED + TESTED-holding |
| A4-SI-03/04 (missing/foreign closure) | A3 matrix + 9-cell G1/G2 | A1 `2f939a0` | PROPOSED + TESTED-holding |
| A4-SI-05 (independent reorder) | A3 matrix row | A1 `2f939a0` | PROPOSED + TESTED-holding |
| A4-SI-06 (boundary + partial refusal) | A3 boundary rows; B4-T5 (proposed) | A1 `2f939a0` | PROPOSED + TESTED-holding |
| A4-SI-07 (invalid/incomplete fail-closed) | A3 9-cell P1–P3 + invalid rows | seed + A1 | PROPOSED + TESTED-holding |
| A4-SI-08 (no unvalidated acceptance) | CE-1 root cause (hardcoded false) | A1 `2f939a0` (violated) | PROPOSED + TESTED-failing |
| B4-CLOSURE-01 (valid ⇒ closure holds) | F1–F5 (proposed; F1 exists as A3 cells) | not implemented | PROPOSED + UNTESTED |
| B4-CALL-01 (signature-first) | A1 cross-call tests | A1 `2f939a0` | PROPOSED + TESTED-holding |
| B4-CALL-02 (no placeholder identity) | A1 placeholder-id tests | A1 `2f939a0` | PROPOSED + TESTED-holding |
| B4-CALL-03 (missing-target refusal) | T-CALL-2 (proposed); A2 refuses today | A2 `ea0bc9a` (behavior, code unnamed) | PROPOSED + partially TESTED |
| B4-CALL-04 (revision-bound sigs) | A3 provenance cells (analogue) | A1 `2f939a0` | PROPOSED + TESTED-holding (analogue) |
| B4-CALL-05 (binding identity) | T-CALL-6 (proposed); A1 aliasing fix | A1 `2f939a0` (in flight) | PROPOSED + UNKNOWN (pending A1) |
| B4-PARSE-01..06 (continuation) | A1 ledger/contract tests (partial); N-U1..U7 (proposed) | A1 `2f939a0` (partial) | PROPOSED + partially TESTED |
| H-B (hole/? adjacency) | P-1..P-9 probes (Agent 4, seed) | not implemented | PROPOSED + TESTED (slot located) |
| C-1..C-4 (transfer consequences) | future shapes only | not implemented | INFERRED + UNTESTED |
| FS-1/FS-2 (no observable aliasing) | a4-own probes (3/4/3…) | seed `57fe424` | ESTABLISHED-subset + TESTED |

## 2. Outstanding binding decisions (owners in brackets)

- AD-1 closure authority + schema duplicate handling [A1/Lucy].
- AD-2 refusal code family: staged codes + contradiction code name [A1/Lucy].
- AD-3 fail-closed subset gate as precondition [Lucy/Matthew].
- AD-4 trailing-token rejection compat break [Matthew].
- U-3 SourceBytes acceptance ruling [Matthew/Lucy].
- Binding-identity encoding [A1]; R-CALL-1 vs BindingPool-id reuse [A1/A2].
- H-B freeze + formatter obligation [Matthew/Lucy, at V0 grammar gate].
- DEC-002 illustration `-> Unit` + DEC-009 wording fixes [Matthew/Lucy, one-liners].

## 3. Research summary (evidence-linked)

Two cycles, six slices + ownership prologue: the staged-checker fail-open is
pinned to a mechanism (no whole-set visibility; flag-copying insufficient per
LUCY-20261104-005), the fix direction is specified without prescribing
implementation (source-wide closure, R1–R5), the call seam is contracted from
real fields (signature-first; text-link gap named with a node-id remedy),
statuses are taxonomized (G3 placed as pair-inconsistent/source-valid), the
hole/? conflict is located by execution (10 probes) not opinion, and the
transfer consequences are derived with missing premises named. Cross-agent
handoffs throughout are falsifiable tests (F1–F5, T-CALL, N-U, B4-T) and
interface recommendations (R-CALL, R1–R5), never code. Self-review recorded
per cycle (S-1..S-5 + experiment-1 review).

## 4. Next two worthwhile investigations

- **Q1 — Entry-point semantics (top-level statements vs `fn main`).**
  A3's open Q1: seed `run` executes top-level statements only (silent exit 0
  with `main` present); C23 treats `main() -> Int` as native entry. The
  self-hosting seam cannot be sound while "what runs" differs by backend.
  Work: pin both behaviors executably, specify the entry rule (DEC-004's
  entry-file top-level statements vs a `main` convention), conformance pair
  for A3, migration cost for existing programs. Dependency: none; value:
  unblocks honest A→B→C claims.
- **Q2 — Numeric edge-table freeze (overflow/NaN/zero/conversions).**
  The interpreter↔C23 differential literature needs a frozen table before
  backend parity claims grow past Int/Bool: `min_int/-1`, truncation
  direction, Float/Float32 literals, NaN ordering exclusion, conversion
  explicitness. Work: fixtures + seed-behavior pinning + backend differential
  requirements for A2/A3. Dependency: none; value: constrains every future
  native claim (RX-04 carried forward).
