# Bisect — `ae91bdc` alone breaks the heavy set (independent confirmation of the report's `bff9dad` baseline) (2026-10-30)

Sharpens `REGRESSION-a1-ae91bdc-scale-work.md` from "the three scale
commits" to a **single commit**.

## Measurement (clean detached, sequential, `-v`)

| A1 head | heavy set | result |
|---|---|---|
| `46bf1c0` (pre-series) | 120 tests | 2 known a14 |
| **`bff9dad`** (commits 1–2: `ab79660` chunk streaming + `bff9dad` UTF-8 inputs) | **124 tests** (a13 already at 91 — the +4 tests land here) | **2 known a14 only; zero deep-test failures** (500 s) |
| `ae91bdc` (+ commit 3: parser flattening) | 124 tests | **26 failures** (deep-suite CALL_DEPTH migration ×22, a14 2→4) |

## Verdict

**`ae91bdc` "Make parser flattening handle compiler source scale" is
the sole breaking commit.** The checker chunk-streaming and UTF-8
input work are green at my measurement — matching the report's
`d20537f` baseline (276/3 full-suite) — now with independent heavy-set
confirmation. The +4 added tests are healthy; only their *pre-existing*
deep-nesting siblings fail, via the `PEP_RUNTIME_CALL_DEPTH`
class migration.

**For the debugging builder:** bisect is already done — the fix scope
is the flattening change itself (deep recursion ↔ depth budget), not
the chunker or UTF-8 work, and not the new tests.

Replay **170/170**; corpus/base untouched. No builder movement
elsewhere (A2/report/design quiet; `ae91bdc` response still awaited).
