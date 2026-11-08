# E3 — One-Page Verdict: NO ARCHITECTURE CHANGE NOW; Measure First

**Programme:** PEP-A4-RESEARCH-E-20261104, Phase I slice 3 of 3. Decides on
E1 (closure map) + E2 (three routes + falsifiers F-A/F-B/F-C). No probes run,
no implementation. Labels: ESTABLISHED / REPORTED / INFERRED / UNKNOWN.

## Verdict: NO CHANGE NOW — with a genuine reason and a gated trigger

Do NOT trial any of routes (a)/(b)/(c) now. Reasons:

1. **The fact schema is being renegotiated while we speak.** A1 Campaign-F F2
   + A2 F2 are deciding `document`/`revision` on `CheckedFunction`/
   `ResolvedSignature` and batch callee-ID uniqueness RIGHT NOW. Route (b)
   (one authoritative checkpoint) prescribes the shape of exactly the artifact
   under negotiation — recommending it now risks ruling against evidence that
   lands next slice. (INFERRED timing risk; ESTABLISHED that F1/F2 are active.)
2. **Gates are live.** A3 is gating Candidate-6 `46b6712`; A1's signature-ID
   repair (F1) and A2's re-pin (F1) are in flight. An architecture trial now
   competes for the same review bandwidth as soundness blockers. Cost/benefit
   is negative until the lanes are between gates.
3. **None of the three falsifiers has been measured.** E2's F-A/F-B/F-C exist
   precisely so this verdict is evidence-gated, not taste-gated. Recommending
   (b) on the bug-class argument alone would repeat the error B4-R3 was
   written to prevent: prescribing mechanism without a priced cause.

## The cheapest reversible experiment (approved for later, not now)

Run the three falsifiers as MEASUREMENT-ONLY slices — no code changes, no
schema changes, existing harnesses only:

- **F-A:** count staged-checker lines serving features compiler A never
  invokes on its bundled sources. Threshold: <10% kills route (a).
- **F-B:** A3 emits seam-cost vs total-step fraction at the 66-node row.
  Threshold: <5% means (b) is purity-only; a single cross-stage identity
  disagreement means (b) is necessary regardless of cost.
- **F-C:** `int_text`-as-Pep-library vs builtin on fixed inputs; step ratio +
  span equality. Threshold: >10× steps or any divergence kills (c) for byte
  builtins; `int_text` is the softest target, try it first.

**Metric:** trusted semantic LOC + staged steps on the compiler's own sources
+ preserved byte-diagnostics + native proof, as in E2 §4.
**STOP condition:** if all three falsifiers come back negative, CLOSE routes
(a)/(b)/(c) for this cycle and return to the research bank (E7 first);
re-open ONLY on new evidence (new bug class, new gate data, post-Candidate-7
schema stability). **Revisit trigger:** any falsifier positive AND all builder
lanes between gates AND Matthew's explicit go-ahead.

## Practitioner questions (F2, asked via own outbox this campaign)

1. **A1:** at the 66-node gate, which pass dominates — lookup, traversal, or
   serialization? (Decides F-B without guessing.)
2. **A1:** signature-ID collision (`sigs_from_tool` zero-based per header) —
   fixture-only, or does the host path share it? (Decides whether the A1-F1
   fix location matters to (b).)
3. **A2:** which consumed checked fact is most awkward (missing field, weak
   identity, re-derivation)? What native cost dominates? (Grounds (b)/(c)
   from the consumer side.)
4. **A3:** which trust failure recurs most — stale, forgery, ingress, or
   gate-instrument confusion? What single measurement would settle a cost
   argument fastest? (Prioritises F-A/F-B/F-C.)

Nonblocking; no reply assumed. Answers feed E4, not this verdict.

## Status labels

DECISION (reversible, evidence-gated): NO CHANGE NOW + measure-first trigger.
Nothing frozen; E2 routes stay open as specified hypotheses. Next: Phase II
E4 (honest trusted base) — which the F2 answers will sharpen. Phase I review:
E1 inventory → E2 alternatives with refuters → E3 gated verdict; each slice
found a real dependency or decision, none restated another.
