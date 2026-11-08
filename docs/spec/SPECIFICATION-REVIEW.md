# Pep Specification Review (v0.1 + 1.0 direction)

- **Status:** reviewer's findings on the core spec, the decision register, and the
  design corpus. Findings are labelled **RISK** (should change), **WATCH**
  (revisit at a stated gate), or **NOTE** (recorded, no action).
- **Verdict pattern:** the inspected corpus is unusually disciplined about
  evidence classes (accepted vs proposed vs implemented vs verified). The main
  dangers are the three places where that discipline slips.

## Must settle before ongoing compiler work (blocking integration, not prose)

1. **RX-01 — SourceBytes/A10 status (RISK).** `docs/DESIGN.md` says the A10 byte
   fragment "remains unaccepted" while the campaign seed at base HEAD implements,
   advertises (`describe`), and tests it. Any A11+ slice built on byte access
   inherits this ambiguity: is `SourceBytes` in the trusted core or not? **Settle
   by:** either an A10 acceptance record or a one-line DESIGN.md correction
   scoping it as campaign-development. Owner: Matthew/Lucy. Until then the spec
   quarantines it in §9, which is the safe posture for cherry-picked compiler
   work.
2. **RX-02 — `?` tokenizer collision (RISK).** Prefix hole `?name`/`?` and proposed
   postfix `?` cannot coexist without a disambiguation rule, and `n??` is already
   in the adversarial matrix. **Settle by:** a lexer fixture at the V0 grammar
   freeze, before any `Result`-shaped syntax is prototyped.
3. **RX-03 — Access-mode proof rules before native/FFI (RISK).** `edit`/`take`
   disjointness, use-after-take, and cleanup ordering are the soundness-critical
   core of DR-05/DR-12. Interpreter slices can proceed with them provisional;
   **no native slice, FFI slice, or ownership-soundness claim** may proceed
   without fixtures. This is correctly sequenced at R2-V5; the risk is only
   impatience.
4. **RX-04 — Numeric edge table before backend parity (RISK).** Overflow,
   `min_int/-1`, truncation direction, NaN/zero/conversions must be fixture-frozen
   (register DR-09, matrix M-6 items 5/10) before interpreter↔C23 differential
   claims outgrow the current Int/Bool subset. Cheap to do, expensive to retrofit.

## Safe to remain provisional (explicitly)

- **PX-01** GC choice (DR-12): "precise tracing GC" is correctly labelled
  provisional; prototypes + adversarial review are the gate, not this register.
- **PX-02** Effect vocabulary and grant transport (DR-07): ceiling-checking can
  freeze at V4 while transport stays open; the two are separable.
- **PX-03** Module path/case rules (DR-10): freeze at V1 before multi-file
  slices; manifest format can wait.
- **PX-04** Test-runner design (DR-13): the manifest-driven dev branch and the
  specified compiler-discovered design must not be conflated, and currently are
  not (REF §13). Keep both visible until one is accepted.
- **PX-05** Concurrency spellings (DR-11): all `async`/`spawn`/`await` surface
  stays *proposed* through V5 without harming interpreter work.
- **PX-06** Refinements (DR-06): advisory-only until the access model freezes.

## Inconsistencies and complexity notes

- **NOTE-01 (resolved, keep annotated):** founding v0.3 reference-like
  collections vs DEC-001/005 value semantics; C11 vs C23. Both supersessions are
  recorded with provenance. Future edits must not silently reintroduce the old
  language (watch for "reference"/"borrow" phrasing in new docs).
- **NOTE-02 (terminology):** the corpus uses "complete/incomplete/invalid",
  "valid/incomplete/invalid", and "parsed/checked" in different files for the
  same trichotomy. The spec standardises on §1's three states; session/CLI
  schema docs should converge on the same words.
- **NOTE-03 (sentence to retire or prove):** SEED_LANGUAGE.md's "Functions
  cannot capture top-level values" is ambiguous against the checker's global-env
  handling of top-level statements (gap report C6). Either verify and specify it
  or delete it; an implementor cannot act on it as written.
- **NOTE-04 (test-count hygiene):** builder-reported counts at named SHAs
  (A8 55/55, A7 50/50, A13 48/48, native 17/17, runner 12+1) are evidence *at
  those SHAs only*. The conformance matrix deliberately cites test *names* at
  *this* base instead of counts. Keep that discipline in future receipts.
- **NOTE-05 (unnecessary complexity risk):** three modelling layers (code +
  notes + comments) plus stage checkpoints plus a semantic map could easily grow
  a second typechecker by accident. The 28-Oct priority (one authority, notes
  advisory-only) is the load-bearing decision — the review endorses holding it
  and flags any "annotation-driven proof/optimisation" proposal as a
  complexity regression until measured against clean-rebuild equivalence.
- **NOTE-06 (grammar surface):** the seed's actual grammar is brace-delimited
  with insignificant newlines; draft language about "newline-based separation"
  describes a *proposed* layout rule, not the implementation. The V0 freeze
  should either adopt it deliberately (with fixtures) or drop the aspiration —
  a half-newline-sensitive grammar is the worst outcome.

## Reviewer confidence

High on the core spec's fidelity to the seed (every normative rule traces to a
cited construct; two behaviours were executed live). Medium on register
completeness, bounded by the DEC re-check queue (full DEC texts unread this
session; summaries cross-checked across FD/REF/LED/Road 2). No consequential
semantic choice was made in this review — RX-01..RX-04 are escalations for
Matthew/Lucy, everything else is ordinary editorial judgement.
