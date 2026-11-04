# B4 Cycle 1 Slice 1 — Source-Wide Declaration Closure + Fail-Closed Obligations

**Packet:** PEP-WB-A4-20261104-B, Cycle 1 Slice 1. **Branch:** `spec/agent4-spec-lab`
**Pins:** seed oracle campaign `57fe424` (`PEP_DUPLICATE_TYPE` at pep_ocaml.ml:396,402);
A1 `2f939a0`; A3 `24cd5b6` (9-cell matrix 8/0/1, minimiser `d7523780` lineage);
integration `c69e15d` (unverified by A3 — claims about it are UNKNOWN here).
No implementation changed; this is specification.

## 1. Definitions (PROPOSED normative language, not yet frozen)

- **D-closure (declaration closure):** for a source revision R, the multiset of
  all top-level type and function declarations in R, each with name, kind,
  payload shape, byte span and revision id. Closure **holds** iff: (a) every
  declared name is unique within its namespace (types vs types, functions vs
  functions; same-name fn/type coexistence is seed-legal per A3 set-21);
  (b) every referenced nominal name is declared; (c) the gathering process
  observed the whole of R (no truncated/partial ingress).
- **Source identity:** exact UTF-8 bytes + SHA-256 revision id. Two checks of
  "the same program" must cite the same revision id; otherwise they are
  different subjects.
- **Fail-closed:** any staged verdict on R that is not grounded in established
  D-closure MUST NOT be `valid`. Allowed non-valid outcomes are defined in §3.

## 2. The core guarantee (PROPOSED rule B4-CLOSURE-01)

**A staged check MUST report `valid` only if D-closure holds for the exact
revision checked.** In particular, a program containing globally duplicate type
declarations MUST NOT be reported `valid` under any partition, fact order, or
`expectReturns` setting. This restates A4-SI-01 as an implementation-facing
contract with the closure mechanism made explicit.

**Why flag-copying is insufficient (ESTABLISHED by A1/LUCY-20261104-005):**
per-declaration producers never observe a duplicate, so a carried
`duplicateType` flag is always false at the point of production. The closure
authority must see the whole declaration set — i.e. a source-wide pass (over
source text, declaration index, or merged chunk manifests) — before or
independent of chunk acceptance. Copying the flag without whole-set visibility
preserves the fail-open.

## 3. Fail-closed obligation table (PROPOSED; codes reuse seed family AD-2)

| Condition | Required staged outcome | Rationale / precedent |
|---|---|---|
| Duplicate type or function name in R | `invalid`, code `PEP_DUPLICATE_TYPE` / `PEP_DUPLICATE_FUNCTION` (byte spans where available) | Seed oracle parity; CE-1/CE-2 |
| Referenced nominal name with no declaration in R | `invalid` (missing-declaration class) | M1 precedent (staged already refuses) |
| D-closure cannot be established (partial ingress, >budget source scan, unproven producer) | `unsupported` (distinct from `invalid`): consumer must not treat as semantic rejection | Prevents H-B-class confusion; see slice 3 taxonomy |
| Facts carry a different revision id than the source under check | refuse (`PEP_STALE_REVISION` family) | Session precedent; A3 R1 |
| Facts foreign to R (undeclared records/fields) | `invalid` (fail-closed) | G1/G2 precedent — labels do not launder provenance |
| Facts contradict R (G3: fact says `Bool`, source says `Int`) | `invalid` with a **contradiction-specific** code, NOT a generic seed code | §4; availability vs soundness made explicit |

## 4. G3 position (PROPOSED recommendation to A1/Lucy/Matthew)

A3 observed staged-`invalid` where the seed says `valid`, and asked whether
facts are authoritative (refuse) or advisory (accept-and-ignore). Recommendation:
**authoritative + fail-closed**, because the staged checker's entire value is
trust in its facts; advisory facts that silently lose to source text create two
semantic authorities (charter violation). The cost is availability (a corrupt
producer blocks a valid program), which is the correct side: corruption must be
loud. Require a dedicated code (e.g. `PEP_FACT_CONTRADICTION`) so a G3 refusal
is distinguishable from a seed-`invalid` — status taxonomy (slice 3) depends on it.

## 5. Minimal requirements for Agent 1 (no implementation prescribed)

- R1: establish D-closure from a source-wide authority (source scan,
  declaration index, or merged chunk manifests with a completeness proof) —
  NOT from per-chunk flags alone.
- R2: emit duplicate diagnostics with seed-compatible codes and byte spans.
- R3: implement the §3 outcome classes as distinct, documented results;
  never return `valid` when closure is unestablished.
- R4: keep per-chunk paths working for unique-declaration programs (no
  whole-program bottleneck smuggled back in); closure is a name-set check,
  not a full re-check.
- R5: state the fact-authority semantics explicitly (recommendation §4 or a
  deliberate alternative with reasons).

## 6. Falsifiable tests for Agent 3 (extends existing instruments)

- F1: 81-byte fixture, both fact orders × `expectReturns` true/false → all four
  must be non-`valid` (extends CE-1/CE-2; currently 2 of 4 fail).
- F2: two chunks individually clean, duplicate across the chunk boundary →
  staged whole MUST be `invalid` with duplicate code (closure, not flags).
- F3: per-declaration producer fed the 81-byte source alone → assert it emits
  NO duplicate signal (documents the insufficiency; guards against
  flag-copying regressions).
- F4: G3 pair (contradictory fact vs source) → assert the dedicated
  contradiction code once R5 is decided (until then, assert non-`valid` only).
- F5: partial-ingress chunk set (one declaration withheld) → assert
  `unsupported`, never `valid` and never a seed-`invalid` code.

## 7. Status labels

ACCEPTED: seed duplicate rejection (DEC-agnostic; seed behavior).
PROPOSED: B4-CLOSURE-01, §3 table, §4 recommendation, R1–R5, F1–F5.
IMPLEMENTED: seed rejection; staged rejection NOT implemented (open defect at
A1 `2f939a0` per campaign preflight).
TESTED: seed side untested at seed level (D-04/O-1 carried); staged side
TESTED-failing (A3 matrices). No passing test is claimed as proof.
UNKNOWN: integration `c69e15d` behavior (unverified); 25+-member union closure
cost (slice 2 of cycle 2 / packet §4).
