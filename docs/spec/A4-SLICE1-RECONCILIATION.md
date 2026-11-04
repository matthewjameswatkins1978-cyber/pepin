# Agent 4 Slice 1 — Specification Reconciliation Register

**Packet:** PEP-A4-20261104-001, Slice 1. **Branch:** `spec/agent4-spec-lab`
**Base:** `736453a` (four draft docs as reviewable proposal, not approved semantics).
**Compiler subset pin:** campaign `57fe424` seed (`pep_ocaml.ml`) + seed tests at base.
**Fresh evidence this slice:** DEC notes read directly in Basic Memory project `main`
(checksums below); A3 dup-decl-order finding (`codex/bootstrap-agent3-verification`
@d720570, defect pinned at bcfa3c0); LUCY-20261104-001/002.

**Label key:** ACCEPTED = Matthew-approved design decision. PROPOSED = draft direction
without frozen grammar. IMPLEMENTED = present in the seed at the pinned base.
TESTED = exercised by a named seed test at base. UNKNOWN = none of the above, or
evidence not inspected. Labels overlap and are not interchangeable.

## 1. DEC verification outcomes (closes prior G13)

| DEC | Directly read (checksum) | Status confirmed |
|---|---|---|
| DEC-001 values | `3105b002…` | ACCEPTED principle; seed List behaviour compatible but partial → IMPLEMENTED (subset), TESTED (a6 aliasing/examples) |
| DEC-002 read/edit/take | `bc76b966…` | ACCEPTED shape + spellings; NOT IMPLEMENTED; illustration omits `-> Unit` (see D-03) |
| DEC-003A bidirectional | `e5dfe2a7…` | ACCEPTED; IMPLEMENTED in seed; TESTED (a6/13 differentials) |
| DEC-003G errors/postfix `?` | `748ff102…` | ACCEPTED operator + exhaustive-match recovery; grammar explicitly NOT frozen; "grammar can distinguish positions but requires formal tests" |
| DEC-003B/C/D/E/F/H, 003 (008T), 005, 006, 007, 008, 009-packet rest | via FD/REF/ledger summaries | ACCEPTED direction, NOT IMPLEMENTED — re-check deferred to the slice that needs each |
| DEC-004 modules | `b30315cf…` | ACCEPTED direction; NOT IMPLEMENTED (no imports/visibility in seed) |
| DEC-009 surface | `f8f15fa0…` | ACCEPTED draft directions; engineering non-finalities listed explicitly |
| 28-Oct priorities | `e2a6888d…` | 1/2/5 kept, 3/4/6 deferred; says NOTHING about Semantic Notes (see D-02 correction) |

## 2. Discrepancy and uncertainty register

### D-01 Statement-`if` else: ACCEPTED vs IMPLEMENTED conflict (material)
- DEC-009 ACCEPTED: "Statement `if` permits no `else`" (else omissible); FD §2 and
  REF §4 agree ("may omit else").
- Seed IMPLEMENTED + TESTED-absence: statement `if` without `else` is a parse
  error (`PEP_PARSE_ELSE`); no seed test asserts either behaviour (matrix M-2
  proposes the fixture).
- Disposition: direction ACCEPTED, seed NOT IMPLEMENTED. Spec v0.1 §5.3 is
  correctly scoped to the seed. No silent reconciliation: a future grammar change
  here alters every existing seed program with statement-`if/else` only by
  *loosening* (compatible direction), but the parser change needs fixtures first.
  Decision needed from Matthew/Lucy: only priority, not semantics.

### D-02 Semantic-Notes demotion: correct the provenance (self-correction)
- Prior gap report C2 (and REF §14) attribute the annotation-demotion to "the 28
  October priority correction". The priority note (`e2a6888d…`) contains NO
  statement about Semantic Notes; it defers rabbit/Rust/paradigm-freedom work.
- Actual authority chain: Road 2 precedence section ("Annotation-centred #@ …
  superseded as the core direction", published at Matthew's request per
  LUCY-20261028-003) + FD §11's "separately reviewed proposal" framing + ledger
  "SUPERSEDED as architectural priority".
- Disposition: the *conclusion* (notes are advisory/provenance-only; `#@` has no
  executable meaning) stands; its *citation* is corrected here. Labels: advisory
  role ACCEPTED (via Road 2); `#@` grammar PROPOSED (PEP-SN-001 unmerged);
  seed IMPLEMENTED status: comments only. No implementation impact.

### D-03 DEC-002 illustration contradicts DEC-003A contract (minor, owner-owned)
- DEC-002's illustrative `fn increase(edit number: Int, amount: Int)` omits a
  return type; DEC-003A REQUIRES explicit named-function return types; DEC-002
  itself notes "current Pep seed requires explicit return types (including Unit)".
- Disposition: illustration NOT NORMATIVE; the contract rule wins. Recommend
  Matthew/Lucy amend the illustration to `-> Unit` (one-line Basic Memory edit,
  no implementation effect). Not acted on here: another agent's owned note is
  read-only to me.

### D-04 Duplicate declarations: IMPLEMENTED but seed-untested (supports Slice 2)
- Seed source IMPLEMENTS `PEP_DUPLICATE_TYPE` (pep_ocaml.ml:396,402) and
  `PEP_DUPLICATE_FUNCTION` (:423); A3's 81-byte counterexample confirms the seed
  rejects `type D… type D…` while the staged chunked checker at bcfa3c0 accepts
  (order-dependent).
- Seed TESTED status: NOT FOUND — test_cli covers DUPLICATE_FIELD/BINDING/
  PARAMETER/MATCH_ARM but no duplicate-`type` or duplicate-`fn` fixture.
- Disposition: add seed-level fixtures (`type D{a} type D{b}` →
  `PEP_DUPLICATE_TYPE`; `fn f… fn f…` → `PEP_DUPLICATE_FUNCTION`) — proposed in
  conformance mapping (Slice 3), executable by Agent 3 as the seed-oracle anchor
  for the staged-checker invariant.

### D-05 SourceBytes/A10 status: unchanged from prior C1 (carried, not resolved)
- No new evidence this slice; DESIGN.md "A10 unaccepted" vs seed-implemented +
  `describe`-advertised + test_a10-present stands as UNKNOWN acceptance state.
- Disposition: keep quarantined (spec §9); needs Matthew/Lucy ruling (RX-01).

### D-06 `?` conflict: the DEC is honest — no conflict established yet
- DEC-003G: "grammar **can** distinguish prefix/infix/postfix positions but
  parser and diagnostics require formal tests." FD §2/§14 and matrix agree the
  disambiguation is open.
- Current seed grammar: `?`/`?name` occur ONLY in prefix (expression-start)
  position; a postfix `?` is currently trailing-input rejection. So positional
  disambiguation is *plausible but unproven*; edge cases (`f(?)`, `x??`,
  `?` alone, newline-adjacent `?`) have no fixtures.
- Disposition: Slice 3 answers the packet's question ("determine whether the
  conflict actually exists") with lexer/parser probes, not prose. No freeze
  recommended until then.

## 3. Duplicated rules across the four docs (no contradictions found)
- Budgets (1M/512 CLI, 100k/128 tool): spec §4.3 = matrix M-6 = review NOTE-04.
  Consistent; single source of truth is `describe` output + seed constants.
- Hole states and `run`-refusal: spec §1/§8 = matrix M-5. Consistent.
- Value semantics: correctly stated ONLY as target (register DR-09, REF §6,
  FD §4); v0.1 core does not overclaim beyond immutable lists. Consistent.
- Terminology drift (NOTE-02 in review) persists in the wild (valid/incomplete/
  invalid vs parsed/checked) but the four docs are internally consistent.

## 4. Omissions confirmed
- O-1: seed-level duplicate-type/function fixtures (D-04) → proposed for Agent 3.
- O-2: statement-`if`-without-`else` fixture either way (matrix M-2 item 2).
- O-3: first-error singularity assertion (matrix M-5 item 5) — the "first error
  only" rule is source-read, never asserted by a test.
- O-4: DEC-003B/C/D/E/F/H, 005, 006, 007, 008 texts not yet directly read;
  register rows citing only FD/REF summaries stay marked *reported*.

## 5. Implementation assumptions exposed (for Slice 2)
- A-1: staged checkers assume gathered facts are duplicate-free and ordered;
  A3 falsified this (accepts what the seed rejects). Invariant work starts here.
- A-2: `external_records` hardcodes `duplicateType: false` (A3 line refs) —
  fail-open by construction, not by accident.
- A-3: whole-program seed checking is order-sensitive ONLY in that duplicates
  are rejected wherever they appear; no evidence of order-dependent *acceptance*
  in the seed. Staged checkers must preserve rejection under all partitionings.

## 6. Unresolved (carried to Slice 2 / Slice 3 / owners)
- U-1: staged-checker semantic-preservation invariant with exact equivalence,
  provenance, and fail-closed limits (Slice 2).
- U-2: hole-vs-`?` recommendation with probe evidence (Slice 3).
- U-3: SourceBytes acceptance ruling (Matthew/Lucy).
- U-4: DEC-002 illustration fix (Matthew/Lucy one-line edit).
- U-5: remaining DEC direct reads (as needed, not speculative).
