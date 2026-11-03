# B3 text-builder independent verification (A2 `bdb3eaa..b9a0f99`) — NO DEFECT FOUND in span/byte accounting

**Date:** 2026-11-03 · **Lane:** Agent 3 (Matthew-assigned B3 verification while waiting on A1's `P1-CANDIDATE`) · **Evidence label:** `TESTED`
**Target:** `stdlib/text_builder.pep` + `tests/test_text_builder.py` + `tests/probe_text_builder_span.py` + `tests/text_builder_consumer.pep`
on pinned worktree `D:\Projects\wt-a3-b3-b9a0f99` @ **`b9a0f99e66ed0135a568d2434d0d1927ef74f1a4`** (clean, detached).
**Refs:** Matthew's A3 steer · `LUCY-20261103-003` (#16 comment `6597259393`) · A2 receipts `BOOT-A2-20261103-003` (679) + span-hole-closed (#16 06:42).
**Frozen instruments: NOT touched** (runner `e5cad4df` unchanged; this probe lives at `verification/adversarial/b3-text-builder/probe_span_adversarial.py`).

## 1. A2's own suite, run by me at `b9a0f99`

`python -m unittest tests.test_text_builder -v` → **6/6 OK (8.9s, exit 0)** — includes the consumer
byte-exactness test, caller-width bytes-vs-chars test, negative-width pin, source-context refusal pin,
**tool-host span coverage test** (their hole-closure claim) and native classification test.
A2's published claims for this SHA hold under independent execution.

## 2. New adversarial probe — the unpinned malformed-span classes

A2's probe only ever runs full in-bounds spans `(0, len)`. Mine runs 13 cases and checks the module's
core invariant directly: **`reported byteCount == actual UTF-8 byte length of joined fragments`**.

| class | cases | result |
|---|---|---|
| controls (full in-bounds, incl. `é\0z` = 4 B) | 3 | **accepted-match** (bytes exact, round-trip exact) |
| empty spans (at EOF, mid) | 2 | accepted-match — **appends one empty part** (`partCount=1, fragments=[""]`), consistent with `push(_, 0)` |
| **reversed span** `(2,1)` | 1 | **soft refusal CONFIRMED first time on this path**: builder unchanged (`partCount=0`), status ok — matches the documented "refused by returning the builder unchanged" (unreachable in their interpreter suite) |
| out-of-bounds end / start / both-negative / negative-start / NUL+ beyond | 5 | **refused `PEP_RUNTIME_BYTE_RANGE`** (fail-closed) |
| mid-character splits (incl. NUL payload split) | 3 | **refused `PEP_RUNTIME_BYTE_BOUNDARY`** (fail-closed) |
| **byte-count mismatches** | **0** | `accepted_mismatch: []` — invariant holds on every accepted input |

Controls all green, **exit 0** (exit 1 reserved for control failure, exit 2 harness — as designed).

## 3. Falsified by measurement (my own candidate finding, recorded honestly)

Their doc says *a fragment's UTF-8 width is knowable only by the caller* while listing `byte_length` —
I suspected `push` could self-verify widths (defending the hand-count slip A2's own test caught).
**Measured: it cannot.** `byte_length("abc")` → `PEP_TYPE_MISMATCH: Expected SourceBytes but found Str`;
`length("abc")` → `PEP_LIST_EXPECTED: expects a List`. The doc is exactly right: no `Str`→bytes exists,
caller-trust in `push` is structural, and `push_span` is the right mitigation. **No finding.**

## 4. Observations for A2 (not defects; contract/doc completeness only)

1. **Refusal-style asymmetry** (deliberate, both documented, worth one doc line): reversed span = *silent*
   builder-unchanged (caller must check `part_count`); malformed ranges/char-splits = *hard tool error*
   (`PEP_RUNTIME_BYTE_RANGE` / `PEP_RUNTIME_BYTE_BOUNDARY`) aborting the run. A caller deciding error
   handling would benefit from the exact code matrix above.
2. Empty spans append an empty part (their `empty_expected` shows A2 knows); harmless, mildly surprising
   for part iteration.
3. `push` caller-width lies remain structurally unverifiable (seed limitation, documented) — `push_span`
   for source-backed text is the sound pattern; a doc cross-reference from `push` to `push_span` would help.

## Scope & limits

Interpreter/tool-host source tests only; **no native C build/run** (Defender hold unchanged); budgets
unchanged (100,000 / 1 MiB / 65,536); consumer path verified ASCII-shaped only (Pep identifiers are
ASCII, and C23 does not lower `Str` — multibyte compiler output has no current real consumer).
This is a point verification of the named classes at the named SHA — not a certificate of all behavior.

## Reproduce

```powershell
# A2 baseline at pinned SHA
python -m unittest tests.test_text_builder -v            # 6/6 OK
# A3 adversarial probe (13 cases, invariant + fail-closed matrix)
python <verify-root>\verification\adversarial\b3-text-builder\probe_span_adversarial.py <pinned-wt>
# falsified candidate finding
pwsh -NoProfile -File .\pep.ps1 run <any file containing: say(int_text(byte_length("abc")))>
#   -> PEP_TYPE_MISMATCH: Expected SourceBytes but found Str
```

**Owner for any follow-up:** A2 (stdlib/text_builder). cc: A1. Verdict sent to #16 as `TO: A2`.
