# E5 — One Compiler-Derived Query: Hole Fill Candidates

**Programme:** PEP-A4-RESEARCH-E-20261104, Phase II slice 2 (Campaign F
"next if fast"). No new engine, no new authority — a read-only contract over
facts the checker ALREADY emits. Labels: ESTABLISHED / INFERRED / UNKNOWN.

## The one query

**Q-HOLE-1:** "For the typed hole at byte offset N in document D revision R,
which in-scope bindings are type-compatible, and what proves it?"

**Exact data (all fields exist at seed `57fe424`):** `HoleFact` carries
`semanticId, syntaxId, name, expectedType, scopeId, visibleBindingIds,
candidateBindingIds, startByte, endByte` (ESTABLISHED — E1 counts, B4-R1
reads). The session `query --holes --offset` op returns it (ESTABLISHED —
`pep.ps1` forwards `query`; `describe` lists `query_holes`). The answer to
Q-HOLE-1 is therefore a PROJECTION of an existing fact, not a new analysis:
`{hole, expectedType, candidates: [{bindingId, name, typeName, visibleFrom}],
provenance}`.

## Provenance (what makes an answer trustworthy)

- Answer MUST echo `document, revision, scopeId, syntaxId` of the HoleFact it
  projects. Consumer re-issues `check` on (D,R) and confirms the hole still
  exists at the same span before acting — the fact is evidence, not command.
- `candidateBindingIds ⊆ visibleBindingIds` MUST hold in every answer; a
  candidate outside the visible set is a malformed response, refused by the
  consumer (cheap structural invariant, no re-analysis).

## Invalidation (when the answer expires)

- Revision change (R' ≠ R): the hole's span, scope contents, or expected type
  may have moved — re-query, never reuse. (Follows B4-AUTH-02; same rule as
  bindings.)
- Scope edit within R is impossible by construction (revision-stamped
  source); any answer citing (D,R) after an edit op is stale by definition.

## Bounded response

Cap: at most 50 candidates, at most 4 KiB JSON per hole, holes listed in
byte order. Rationale: keeps the answer inside the 64 KiB transport with
headroom for 10+ holes; a scope with >50 visible same-type bindings is a
code smell the caller should narrow with a name prefix, not a reason to grow
the cap. (INFERRED sizing — no measurement; mark for A3 if disputed.)

## Forgery threat (the reason this is safe to specify)

Transported `HoleFact`s are labels, not authority (B4-R1 §1, B4-C5 residual):
a same-revision forgery can inflate `candidateBindingIds` with an
incompatible or out-of-scope binding. The consumer-side guards above
(subset check + re-`check` before acting) reduce the forgery to a
denial-of-usefulness: the worst case is a suggested fill that `check`
refuses. The query MUST NEVER auto-apply a fill — application goes through
the existing `fill_hole` session op against the live revision, which
re-derives. No new trust is created; the threat is contained by construction.

## Why this one (and not call graphs / coverage / effects)

- Hole facts are the ONLY checker facts already shaped as a question
  (expected type + candidates); call graphs and coverage need new consumers
  and new staleness rules. Smallest delta from current reality.
- It serves Matthew's "one compiler-derived semantic/checkpoint model"
  without building a parallel engine: the checkpoint IS the checked report,
  the query IS a projection.
- Effects/authority queries are EXCLUDED — B4-C5 established callee facts
  carry no identity, so any authority answer today would launder labels as
  proof. Revisit only after the A1-F2 callee-ABI lands.

## Status labels

CONTRACT (not an implementation ask): one query, five guards, all enforceable
client-side today. No builder work imposed; A3 could lock N-guards with two
negative probes (forged-candidate rejection, stale-revision re-query) if a
lane wants it. Next: E6 or research bank.
