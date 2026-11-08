# B4 Resume-3 — Audit: Cross-Chunk Identity Proposal vs Forged-Fact Counterexamples

**Assignment:** LUCY-20261104-007 A4 THIRD, task 3. **Branch:** `spec/agent4-spec-lab`
**Proposal audited:** A1 `f4eb231` contract rules 1–7 (name-keyed link,
signature-first, local-first mirroring, chunk-ordinal callers, seam fields,
uniqueness assumption) + disclosed residual (dup fn names).
**Counterexamples:** A3 `a4f2833` S4/O4 (self-consistent forged callee set),
G3 (contradictory fact), BINDING-POOL F1–F3; S2/S3 (one-sided forgeries
refused), S5 (emitter refuses foreign reports).
No implementation changed; audit only.

## 1. Verdict: sound conditional on two unenforced preconditions

The proposal is CORRECT **if** (a) the source has globally unique function
names (rule 7's own condition) and (b) admitted facts are honest and
revision-bound. A3's counterexamples falsify neither rule 1–7's logic nor the
resolver — they falsify the unstated assumption that admitted facts satisfy
(b). S2/S3 prove the resolver cross-checks halves; S4/O4 prove cross-checking
cannot detect a *self-consistent* lie. The defect class is admission, not
resolution — consistent with B4-AUTH-01/02, which already cover it.

## 2. The residual is real and cheap to close (recommendation R-ID-1)

A1's disclosed residual — duplicate fn names across chunk + externals,
local-first, no diagnosis, no harness path — is the call-side twin of the
repaired dup-type hole. Mechanism confirmed by inspection: `find_function`
name-only + rule 4 local-first + no external-vs-local collision check.
**R-ID-1 (PROPOSED, minimal):** at fact-supply time, the host compares
external signature names against chunk-local function names and refuses on
collision (names already present on both sides; no semantic engine, no new
machinery). This is cheaper than the type-side fix and closes the twin hole
by construction. Owner: A1 (host supply path).

## 3. What the forged-fact cases require (no new mechanism)

- S4/O4 + G3 + F1 are ONE hole (facts without identity), not three.
  B4-AUTH-01/02 already specify the single fix: `(document, revision)` on all
  three fact kinds + existing stale guard at ingress.
- S5 shows the emitter already guards its own inputs; the checker side must
  NOT rely on that (different trust position: emitter guards codegen inputs,
  checker guards verdict inputs). Keep single validation point per consumer;
  do not duplicate checks across layers.
- Rejected as over-engineering: per-fact signatures/PKI, name-mangling
  identity schemes, a second resolver, emitter-side re-verification of
  checker facts.

## 4. Complexity account

Total new machinery proposed across this audit: one identity pair on three
fact types, one ingress guard reuse, one supply-time name-collision check,
one contradiction code (B4-C3). Everything else is already built
(S2/S3 cross-checks, S5 emitter guards, B2/B4 owner checks, renumbering).
If a proposal needs more than this, it is solving a different problem.

## 5. Decisions for Matthew/Lucy (flagged, not made)

- D-ID-1: confirm R-ID-1 supply-time collision check (vs leaving the residual
  disclosed-but-open). Low cost, same class as an already-repaired hole.
- D-ID-2: contradiction-code name + whether contradictory facts are ever
  advisory (recommendation stands: never advisory — B4-C3 §2).
- No other new binding decisions: AD-1/AD-2 cover the schema/guard work.

## 6. Status

AUDIT (not implementation): proposal conditionally sound; residual real with
minimal fix; forged-fact cases reduce to the known admission hole.
PROPOSED: R-ID-1, D-ID-1/2. TESTED: A3 S-cases (cited, not rerun).
UNKNOWN: A1's dup-type fix `448c689` independent verdict (pending A3) —
if it lands, re-run S4/O4 shape against duplicate *functions* as the next
discriminating probe (T-CALL-6 already covers it).
