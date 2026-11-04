# G-A4-7 — Trust-Boundary Costs vs A2 Receipts: NO CHANGE

**Campaign G, Agent 4 card 7.** Validates E4's N-obligations against A2's
current native receipts (via A3-057 independent re-pin + Campaign G packet
summaries; A2's full outbox tail not re-excavated — depth labeled below).
Verdict: NO CHANGE, with a genuine reason. Labels: ESTABLISHED / REPORTED /
INFERRED.

## Validation

- **N-T4-1 (compiler version in receipt): INTENT ALREADY MET — by the
  verifier, not the producer.** A3-057 independently records "Clang 23.1.4,
  GCC 16.2.0, seed rebuilt" (REPORTED, A3 lane). Producer-side self-report
  would add ZERO assurance beyond this: a self-attested version string is
  weaker evidence than an independent measurement at a pinned SHA. Adding a
  version line to A2's receipt format now would churn a working proof to
  duplicate strictly-inferior evidence. NO CHANGE; revisit only if A3 stops
  recording versions.
- **N-T3-1 (per-file hashes in open receipt): CONFIRMED OPEN, wrong lane for
  A2.** E4 source-read (pep_c23.py `emit()` gates on outcome+status only) +
  A3-057 "supplied 2e81f35 file manually" (REPORTED) = no per-file identity
  anywhere in the flow; the workaround is manual file supply. But the fix
  belongs to A1's host lane (`pep_c23.py`), not A2's receipts — and A1 is
  mid-flight on F1/F2 with a false-completion incident behind them. Piling a
  host change on now risks exactly the churn E3 warned against. Recorded as
  an ASK, not a demand: one question to A1 at their next checkpoint (bind 4
  bundle file hashes in the session `open` receipt?). No trial proposed from
  this lane.
- **N-T4-2 (trap-stderr-vs-harness-failure text contract): UNKNOWN from
  summaries.** A2's 10 negatives + A3's "10 negatives identical" (REPORTED)
  do not say whether a receipt reader can distinguish a Pep trap from a
  harness failure by text alone. INFERRED likely-held (dedicated
  `PEP_RUNTIME_*` strings exist), but inference is not validation — left as
  the cheapest future probe IF a misclassified failure ever appears;
  manufacturing it now would be busywork. Explicitly NOT proposed.

## Cost accounting (the "worth it" test G-A4-7 requires)

- Process cost of a receipt-format change: A2 edits receipt template (their
  lane, their time) + A3 re-baselines what "complete receipt" means (their
  lane) + one review cycle. Benefit: duplicate of A3-measured data.
- Verdict: cost > benefit for all three obligations AT THIS TIME. The
  workshop's current division (producer proves behavior, verifier records
  provenance) is the cheaper correct allocation — discovered, not designed.

## Status labels

DECISION: NO CHANGE to A2 receipts; one ASK queued to A1's host lane
(nonblocking, no demand). E4's map stands; its obligations stay open with
owners attached (N-T4-1: covered-by-A3; N-T3-1: A1-host-ask; N-T4-2:
future-probe-if-needed). Next: G-A4-8 synthesis.
