# E6 — Two Emergent Applications (one kept, one deferred)

**Programme:** PEP-A4-RESEARCH-E-20261104, Phase II slice 3. Combines ONLY
accepted semantics (E1 registry, B4 rules, E5 contract). Sketches are
illustrative, not implementations. Labels: ESTABLISHED / INFERRED / UNKNOWN.

## KEPT: hole-driven fill loop (agent proposes, checker adjudicates)

**Scenario (real):** a record gains a field; N construction sites now fail
with `PEP_MISSING_FIELD` at exact spans. Today a human visits each site.
With E5's Q-HOLE-1 + the existing `fill_hole` session op, a host-side loop
can: (1) `check` → collect missing-field diagnostics; (2) `query --holes`
→ candidate fills per site; (3) propose fill; (4) `fill_hole` at the live
revision → `check` adjudicates. The checker never trusts the proposer —
every fill is re-derived (E5 forgery containment).
**Accepted premises:** HoleFact/candidate fields, `check`/`query`/`fill_hole`
session ops, revision stamps, `PEP_MISSING_FIELD` spans. All ESTABLISHED.
**Minimal sketch (host pseudocode, not Pep):**
`for d in missing_field_diagnostics(check(D,R)): cands = query_holes(D,R,offset=d.span); fill_hole(D,R,choose(cands)); assert check(D,R').status != invalid_for_that_span`
**Missing infrastructure:** only the host loop + a choice policy
(first-candidate? type-directed? ask-human-on-ambiguity). Zero language
change, zero checker change.
**Strongest counterexample:** a site where two same-typed bindings are both
visible — the loop fills the wrong one and `check` ACCEPTS (it is well-typed
but semantically wrong). The adjudicator guarantees validity, not intent.
Mitigation: ambiguity (≥2 candidates) routes to human/ask, never auto-fill —
cap auto-fill to single-candidate holes (E5's 50-cap already bounds review).
**Implementation cost:** one host script + two A3 negative probes
(multi-candidate refusal-to-auto-fill; stale-revision fill rejection).
Cheapest useful thing in this whole programme. KEEP in research register.

## DEFERRED (seductive, premature): cross-revision fact-reuse cache

**Idea:** revision-stamped facts with identical source bytes should be
reusable across revisions — skip re-checking unchanged chunks (the
"incremental reuse" dream; AGENTS.md forbids claiming it until measured).
**Why seductive:** B4-AUTH-02 already stamps everything; a content-addressed
cache keyed by (bytes-sha, checker-version) looks trivially sound — same
bytes in, same judgments out.
**Why premature (defer, with the killing observation):** the checker is NOT
a pure function of source bytes — `source_bytes()` reads the live
same-revision document (ambient authority, E1 §4), tool-registry state and
session-admitted externals (BindingPool contents, external callee facts)
vary independently of the chunk bytes. A cache key must therefore capture
the ambient inputs too, and THOSE have no canonical serialization today.
Worse, the checker changes weekly (A1 F1/F3 active) — cache invalidation
tracks a moving target. The E2 F-B measurement (seam-vs-analysis cost split)
must come first: if re-derivation is <5% of gate cost, the cache optimizes
nothing real.
**Strongest counterexample for the cache:** chunk C unchanged, but an
external callee fact it depends on is re-admitted with identical bytes under
a new revision stamp after the R-ID-1 gate lands — byte-keyed cache hits,
semantically stale. Silent unsoundness, exactly the class B4 exists to kill.
**Revisit trigger:** checker stable for one full campaign + F-B shows seam
cost >20% + ambient inputs canonically serialized. Not before.

## Status labels

DECISION: keep the fill loop, defer the cache, both with triggers. Phase II
E4/E5/E6 complete. Next: research bank by value (E7 checker-cost hypothesis
is the natural next READY once F-B-related practitioner answers arrive; E8
stdlib ranking is answerable from E1 counts alone).
