# B4 Cycle 1 Slice 3 — Status Taxonomy, G3 Placement, Conformance Links, Self-Review

**Packet:** PEP-WB-A4-20261104-B, Cycle 1 Slice 3. **Branch:** `spec/agent4-spec-lab`
**Pins:** seed `57fe424`; A1 `2f939a0` (contract codes); A3 `24cd5b6` (9 cells);
session protocol (PEP_STALE_REVISION / PEP_DOCUMENT_NOT_FOUND precedent).

## 1. Status taxonomy (PROPOSED normative definitions)

| Status | Meaning | Emitted by | Precedent |
|---|---|---|---|
| `valid` | complete program, checks clean (whole); chunk clean AND D-closure established (staged) | checker / staged+closure | seed `check`; A3 C0a/C0b |
| `invalid` | fails checking: type error, duplicate, missing/contradictory declaration, unresolvable call | checker / staged | seed `PEP_*`; A3 G1/G2/M1 |
| `incomplete` | parses, holes remain; execution refused; NOT a defect | checker / staged (P1–P3: survives staging) | seed hole states |
| `unsupported` | closure/capability cannot be established (partial ingress, over-budget scan, unimplemented subset) | staged/host | A4-SI-06 partial groups; B4-C1 §3 |
| `transport_refusal` | host-level refusal: stale revision, malformed envelope, unknown schema/version | host only, never the checker | `PEP_STALE_REVISION`, `CHUNK_*` plan codes |

Rules: (a) `unsupported` ≠ `invalid` — consumers must not treat "cannot check"
as "checked and wrong". (b) `transport_refusal` carries no semantic content
about the program. (c) `incomplete` is a stable front-end state, not a
diagnostic code (A3 honest-scope note). (d) No silent promotion in any
direction: incomplete→valid and unsupported→invalid are both violations.

## 2. G3 placement (answers the packet's slice-3 question)

A3's G3 (fact contradicts source: `P.x: Bool` vs `Int`): staged `invalid`
where seed says `valid`. Placement: **`invalid` with a contradiction-specific
code** (B4-C1 §4 recommendation stands). Reasoning: the (source + facts) pair
 presented to the staged checker IS inconsistent, so `invalid` is the honest
verdict *about the pair*; the seed's `valid` is the verdict about the source
alone. Both true, different subjects — no contradiction once subjects are
stated. What must NOT happen: reusing a seed code (implies the source is
wrong) or `unsupported` (implies incapability). The dedicated code keeps
availability debugging (corrupt producer hunt) separate from soundness.

## 3. Conformance links (extends CONFORMANCE-MATRIX.md)

| B4 row | Requirement | Covering test today | Proposed fixture |
|---|---|---|---|
| B4-T1 | dup-type staged refusal, all orders | A3 minimiser + F1 (dev) | seed dup-type fixture (D-04/O-1, still open) |
| B4-T2 | missing-declaration refusal | A3 M1 | staged M1-equivalent at A1 head |
| B4-T3 | incomplete survives staging | A3 P1–P3 | P1–P3 shapes at A1 head |
| B4-T4 | G3 contradiction code | none (code undecided) | G3 pair asserting dedicated code once named |
| B4-T5 | partial ingress → `unsupported` | A4-SI-06 (partial groups) | withheld-declaration chunk set |
| B4-T6 | cross-chunk call via signature | A1 cross-call tests | T-CALL-1..6 (B4-C2 §4) |
| B4-T7 | text-link disambiguation | A3 set-21 (seed) | T-CALL-3 same-name fn/ctor |

## 4. Self-review (findings against Cycle-1 work)

- S-1: B4-CLOSURE R1–R5 prescribe a source-wide authority without costing it;
  25+-member union closure cost is UNKNOWN (packet cycle-2 §4 exists for
  exactly this). The requirements are directionally right, procedurally
  unpriced.
- S-2: R-CALL-1 (node-id on ResolvedCall) may be superseded by A1's BindingPool
  identity work already in flight; if BindingPool yields stable cross-chunk
  binding ids, the callee link should reuse that identity, not add a second
  one. Watch A1's next slice before hardening R-CALL-1.
- S-3: H-B (hole/?) stands conditional from experiment 1; Cycle-1 did not
  re-probe it. If A1's grammar work touches `?`, re-verify P-1..P-9.
- S-4: The taxonomy's `unsupported` class has exactly one staged producer
  (partial groups); if no producer emits it within one cycle, it risks becoming
  dead vocabulary — tie B4-T5 to A1's next staged slice explicitly.
- S-5: All Cycle-1 rules are PROPOSED; the only ACCEPTED items invoked are
  seed duplicate rejection and fail-closed refusal. No freeze claimed.

## 5. Cycle-1 close

Delivered: B4-C1-CLOSURE, B4-C2-CALL-CONTRACT, this taxonomy; A1 requirements
R1–R5 + R-CALL-1..3; A3 falsifiables F1–F5 + T-CALL-1..6 + B4-T1..T7; open
decisions AD-1..AD-4, U-3 (carried). No implementation, no freeze, no
master/CURRENT changes.
