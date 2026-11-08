# G-A4-7 — Trust-Boundary Costs vs A2 Receipts: NARROW TRIAL (reversed)

**Campaign G, Agent 4 card 7.** Validates E4's N-obligations against A2's
current native receipts (via A3-057 independent re-pin + A3 cold-start
receipt ACCEPT-H-V1 + Campaign G packet; A2's full outbox tail not
re-excavated — depth labeled below). VERDICT REVERSED 2026-11-04 (see
below): the original NO CHANGE conclusion was wrong — a verifier-side
version string does not cover a producer-side identity gap, and the
cold-start receipt proves the gap is real, not theoretical. Labels:
ESTABLISHED / REPORTED / INFERRED.

## Validation

- **N-T4-1 (compiler version in receipt): REVISED — verifier recording is a
  different claim, not a covering one.** A3-057's "Clang 23.1.4, GCC 16.2.0,
  seed rebuilt" attests A3's run (REPORTED, A3 lane). It does NOT attest
  what A2's lane actually invoked: the cold-start receipt documents a
  missing module dependency AND a rebuilt-from-pinned-seed executable whose
  identity no marker authenticated — both invisible to "which version did
  the verifier see." The honest fix binds {input sha256, tool path+version+
  sha256, output sha256} in the PRODUCER's receipt (E4 §4 revised). Trial,
  not demand: one line per identity, measure for one campaign whether any
  receipt ever diverges; downgrade to verifier-only if none does.
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

## Cost accounting (REVISED — the original test mispriced the benefit)

- Process cost of a receipt-identity line: A2 adds one line per build (their
  lane, seconds); A3 changes nothing (no re-baseline — the identities are
  additive, the verdict format untouched); one review cycle only if a
  divergence is ever recorded. Benefit: the cold-start class (missing dep,
  unauthenticated rebuild) becomes receipt-visible instead of
  investigation-visible.
- Verdict: trial WORTH IT for N-T4-1's bound form (measure-and-downgrade
  rule); N-T3-1 stays an A1-host ASK (unchanged — different lane, busier
  owner); N-T4-2 stays future-probe-if-needed (unchanged). The original
  "cheaper correct allocation" claim is withdrawn: it priced A3's recording
  as covering A2's gap, which the cold-start receipt falsifies.

## Status labels

DECISION (revised 2026-11-04): narrow producer-identity trial for N-T4-1
(one line per identity, downgrade if never diverges); A1-host ASK for
N-T3-1 stands; N-T4-2 future-probe stands. E4 §4 revised to match. Next:
G-A4-8 synthesis (which already cites this card — read the revised
verdict, not the title).
