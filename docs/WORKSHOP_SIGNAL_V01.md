# Workshop Signal v0.1 — trial conventions

Source: Practitioner Council J (4 Nov 2026). Authority: mission packet
Workshop Signal v0.1. Status: TRIAL PROPOSAL — adopt for one campaign, then
KEEP / MODIFY / REVERT. Changes nothing in the compiler, packets, branches,
or review cadence. Basic Memory stays the detailed channel; #16 stays the
pointer channel; Git objects stay the authority. No daemon, polling,
notifications, or second task database.

## A. Consequential handoff block

Use for interface changes, dependency answers, integration decisions, and
significant findings. Five lines, in this order:

```text
PIN: ROLE | BRANCH | SHA | PUSHED STATUS (pushed+remote-verified | local-only | clean/dirty)
RESULT: What changed / what happened. Evidence grade: TESTED | SOURCE-READ | INFERRED | BLOCKED | NOT-VERIFIED.
REPRO: Exact command or evidence path (probe file + argv + tree), or NONE with a reason.
FALSIFIER: Cheapest observation that would disprove the claim, or why none exists yet.
NEEDS: Recipient + specific action, or NONE.
```

Rules:

- A claimed pushed SHA is verified **in the claim**: `git cat-file -t <sha>`
  locally plus `git ls-remote <remote> refs/heads/<branch>` matched to the
  branch. Helper: `scripts/Confirm-WorkshopSha.ps1`. Print exit codes; never
  let a PowerShell conditional swallow them (a real SHA was once reported
  absent this way). A remote branch advancing does **not** invalidate a
  historical commit still in its ancestry — check `merge-base --is-ancestor`,
  not equality.
- Never report success from a planned but unexecuted command.
- Grades: TESTED = ran it; SOURCE-READ = read the bytes, did not run;
  INFERRED = reasoning beyond what was read/run; BLOCKED / NOT-VERIFIED as
  stated. A SOURCE-READ claim must not be written as TESTED; an INFERRED
  claim must not be written as established. Applies to builders, verifiers,
  researchers, and coordinators alike — including "peer has not responded"
  and "this SHA does not exist".
- Longer prose stays appropriate for decisions, significant failures,
  counterexamples, and architectural consequences. Rule of thumb from the
  Council: prose that records a **decision** stays; prose that states a
  **prediction** carries its falsifier.
- No time-based expiry of claims. Reassess a claim when its underlying
  evidence, source revision, or assumptions change.

## B. Pickup procedure (compact, ephemeral)

At slice start / pre-commit / pre-exit, establish:

```text
NEW EVIDENCE: <peer SHA + one-line result + link, since last checkpoint>
ACTION NEEDED FROM ME: <open asks addressed to me, or NONE>
BLOCKED DEPENDENCIES: <what genuinely blocks my next task + owner, or NONE>
INFORMATION ONLY: <pointers, no action>
NEXT READY WORK: <highest-priority READY slice per CURRENT.md, or stop>
```

Implementation rules:

- Reuse existing tools only (BM search/read, `gh issue view`, git).
- Prefer message IDs, checksums, and line-anchored tail reads over repeated
  full-outbox reads. After a checksum change, a tail read is sufficient.
- **Never treat a failed keyword search as proof a message is absent.**
  A search for a string is not a census of a lane (multi-term queries miss
  real messages). Confirm absence against the actual outbox tail or the
  authoritative document — the same existence-proof discipline as §A.
- Link to original messages; do not copy their full text.
- No second authoritative task database, no persistent message store, no
  automatic polling/wakeups/notifications.

## C. GitHub #16 conventions

- BM outbox = full receipt. #16 = short pointer: summary + verified SHA +
  result + required recipient/action + BM message ID / link.
- No title-only handoffs (SHA + verdict in the title or first line).
- No full-text duplication across both channels.

## D. Trial plan (one campaign)

Measure, against the previous campaign as qualitative baseline:

1. Time to find an actionable peer handoff.
2. Unnecessary full-outbox reads.
3. Handoffs needing follow-up clarification.
4. Incorrect claims of published commits or absent messages (target: zero).
5. Extra communication/tool overhead introduced.
6. Whether significant counterexamples reach the responsible agent without a chase.

Ask at least two practitioners from different roles to evaluate. Keep the
conventions only if they improve clarity or reliability without materially
increasing overhead.

## E. Before / after example

Before (real shape, title-only + buried action): a #16 comment titled
"G-A1-2" whose branch, SHA, required re-pin action, and evidence live several
paragraphs deep in two channels.

After (same content, §A block):

```text
PIN: A1 | codex/p1-checker-cost-fix | 727f8af | pushed, ls-remote-verified, clean
RESULT: CheckedFunction/ResolvedSignature carry document+revision; foreign/stale stamps refused (TESTED: pins 4/4 + parity 132/132 + A13 72/72 + C23 CLI 20/20).
REPRO: new pins in tests/test_chunk_* at 727f8af; `python -m unittest tests.test_a13 -q`
FALSIFIER: re-run the G-A1-1 probe battery at 727f8af — any valid verdict on foreign-stamp input disproves it.
NEEDS: A2 — re-pin probe to 727f8af, drop helper workaround; A3 — differential-gate at 727f8af.
```

A recipient gets SHA, result, evidence, and their action without reading the
message history. Full receipt stays in the author's BM outbox.

## F. Rollback

Delete or ignore this file and `scripts/Confirm-WorkshopSha.ps1`; resume the
pre-trial prose conventions. No data migration, no config to unwind, no
projections to regenerate. The `workshop-next` skill file itself is
**unchanged** by this trial — a skill patch is proposed only if the trial
verdict is KEEP.
