# Agent 4 Independent Three-Slice Review (PEP-A4-20261104-001, experiment 1)

**Reviewer:** Agent 4, reviewing own slices 1–3. **Branch:** `spec/agent4-spec-lab`
**Slices:** `eeeca1f` (reconciliation), `c16ae48` (invariant), `017862d`
(mapping + hole/?). **Standard:** a finding against my own recommendation counts
double; an unresolved question is a legitimate finding.

## Findings FOR the work
- F-1: Slice 1 closed the DEC provenance gap with direct reads + checksums; the
  C2 self-correction (priority note is silent on notes; authority is Road 2)
  strengthens rather than weakens the register.
- F-2: Slice 2's core move — judging staged relations against the oracle, never
  forward-vs-reversed — is validated by A3's own R4 correction history. CE-2
  (both-orders-valid) is the experiment's sharpest single result.
- F-3: Slice 3's probe table (P-1..P-9, all executed) converts the hole/`?`
  question from a prose disagreement into a located, bounded collision.

## Findings AGAINST my own recommendations
- X-1 (against H-B): whitespace-adjacency as a semantic rule contradicts the
  layout-robustness the AI-first doctrine wants — a reflow formatter turning
  `f(1)?` into `f(1) ?` would change program meaning. H-B is acceptable ONLY
  with a formatter-robustness obligation (formatters MUST preserve `?`
  adjacency, enforced by fixture). If owners judge that obligation too fragile,
  H-A (pure positional, with documented migration of incomplete programs) is
  the honest fallback. Downgrade: H-B = conditional recommendation.
- X-2 (against R-B): I have NOT quantified the corpus that relies on silent
  splitting. Shipped `examples/*.pep` shows no trailing-`?` and no
  `)`-juxtaposition (grep, this review), but numeric juxtaposition (`1 2`) and
  the wider corpus were not exhaustively excluded. R-B stays a routed question
  (AD-4), and my "recommended regardless" phrasing in Slice 3 §3 overstates —
  read it as "recommended pending corpus scan", which Agent 3's fixture sweep
  can supply in one pass over the repo.
- X-3 (against the cluster's "HOLDS" rows): A4-SI-02..07 each rest on a narrow
  fixture set (12 passing cells, mostly single-shape). "HOLDS where tested" is
  accurate; "holds" without the qualifier would be fabrication. The cluster
  needs breadth before any architectural reliance — T-partitions exists for
  exactly this reason.
- X-4 (against Slice 1 D-01): DEC-009's "Statement `if` permits no `else`" is
  itself ambiguously worded (it must mean "else omissible", since "allow else
  if" follows — but the sentence can be misread as a prohibition). Recommend
  the DEC sentence be reworded by its owner regardless of the seed's direction.

## Verdict
Slices 1–3 meet the acceptance bar as research: traceable reconciliation,
falsifiable invariant with stated assumptions, counterexamples + Agent-3
requirements, mapping rows, evidence-based (conditional) recommendation, and a
documented unresolved list. No language change was made or frozen; no
implementation path was touched. The experiment's weakest points are named
above, not hidden.
