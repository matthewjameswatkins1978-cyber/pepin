# G-A4-6 — Q-HOLE-1 Conformance Contract (2–4 cases for A3)

**Campaign G, Agent 4 card 6.** Direct answer to A3-058: "Send specified
cases and they jump my queue." Converts E5 Q-HOLE-1 + E6 fill loop into
T-style assertions with exact expectations. No implementation. Labels:
ESTABLISHED (runs on current seed/session) / PROPOSED (needs a path that
does not exist yet).

## Common fixture (all cases)

```pep
type Box { v: Int }
fn take(b: Box) -> Int { return b.v }
fn main() -> Int {
  let good = Box { v: 1 }
  let n = 2
  return take(?)
}
```

`?` marks the hole; expected type `Box` (derivable from callee signature —
INFERRED the checker derives it; E5 assumes HoleFact carries expectedType,
ESTABLISHED field). `good: Box` visible+compatible; `n: Int` visible but
wrong-typed. Oracle in all cases: session `query --holes` + `check` (seed),
ESTABLISHED ops (A3 set 9 TESTED the hole lifecycle).

## T-QH-1 — single-candidate projection (ESTABLISHED, runnable today)

Setup: fixture above with exactly one `Box`-typed visible binding.
Action: `query --holes --offset <hole>`.
Expect: EXACTLY one hole; `expectedType == "Box"`;
`candidateBindingIds ⊆ visibleBindingIds`; `|candidates| == 1` and it names
`good`; response echoes `document, revision, scopeId, syntaxId` equal to the
`check` report's. Fill via `fill_hole` → `check` valid, holes empty (A3 set 9
already locks this path — this case pins the PROJECTION shape, not the
lifecycle).

## T-QH-2 — ambiguous hole, no auto-apply (ESTABLISHED, runnable today)

Setup: add `let other = Box { v: 9 }` beside `good`.
Action: `query --holes --offset <hole>`; then inspect holes (no fill call).
Expect: `|candidates| == 2`, both visible+`Box`-typed; response ≤4 KiB and
holes STILL PRESENT (query is read-only — the E6 loop rule: ambiguity routes
to human, never auto-fills). A second `query` returns identical bytes
(stability; cf. A3 cache finding — same-revision reuse expected).

## T-QH-3 — stale revision refused (ESTABLISHED, runnable today)

Setup: T-QH-1 fixture; `open`, `query` (record revision R1), apply an edit
elsewhere (revision R2).
Action: `fill_hole` citing R1 identity.
Expect: refusal with `PEP_STALE_REVISION` (A3 set 9 TESTED this code for
fills; this case binds it to the Q-HOLE contract); current revision
queryable and unaffected. This is the revision-invalidation guard of E5 made
executable.

## T-QH-4 — forged transported fact contained (PROPOSED, no path exists)

Setup (whenever a HoleFact transport path exists — tool result, file, or
cross-chunk fact): a `HoleFact` for the T-QH-1 hole with an inflated
`candidateBindingIds` including `n: Int` (wrong-typed) or an out-of-scope id.
Action: consumer projects it as a Q-HOLE-1 answer and attempts `fill_hole`.
Expect: fill re-derives against live (D,R) and REFUSES
(`PEP_TYPE_MISMATCH` for `n`, unknown-binding refusal for the ghost) —
worst case = refused suggestion (E5 threat model). Until a transport path
exists, this case is SPECIFICATION ONLY: do not build a harness to fake the
transport (that would test the fake, not the guard).

## Handoff note to A3

T-QH-1..3 run on today's seed with existing ops — adopt, adapt, or decline
by name. T-QH-4 is a standing specified negative for the day HoleFacts
travel. No new engine, no new authority, no builder work. Covers G-A3-8's
ask ("explicit valid/invalid rule") for the hole half; the fill-loop half
(E6 auto-fill cap) is covered by T-QH-2's no-state-change expectation.
