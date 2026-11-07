# ACCEPT BOOT-A3-046 — the last structural alternative is inexpressible; the prerequisite is now precise

**Verdict: no list indexing exists, so a branchless dispatch-table lexer cannot be written. Combined with
BOOT-A3-045 this closes every structural workaround and leaves exactly one prerequisite for the mission.**

No spike exists yet (A2 still `4b70c61`, A1 `86ff953`), so this is the "smallest prerequisite" report the
mission asks for when a route cannot yet be demonstrated.

## Measured: the language has membership but no element access

`pep.ps1 check` on the seed (`a7d3ee1`):

| program | result |
|---|---|
| `let t = [1,2,3]` then `return t[0]` | **invalid** — `PEP_TYPE_MISMATCH`, *"Expected Int but found List[Int]"* |
| `if contains(t, 2) { ... }` | **valid** |
| `return length(t)` | **valid** |

Source confirms the same list: the seed's only list builtins are `length`, `append`, `contains`,
`prepend`, `reverse` — **no `nth`/`at`/subscript**. `t[0]` is not indexing syntax at all; the checker sees
`t` (a `List[Int]`) where an `Int` is expected.

**So the dispatch-table lexer I nominated as the one remaining alternative cannot be written.** You cannot
look up a byte in a table; classification must go through `contains` (Bool membership) or conditionals.

## What this closes, together with BOOT-A3-045

| route around the cost problem | status |
|---|---|
| nest conditionals (natural lexer) | **fails** — depth-2 refuses at 44 nodes (A3-045/A3-038) |
| flatten into sequential conditionals | **fails** — two sequential already refuse at 48 nodes (A3-045) |
| branchless dispatch table | **inexpressible** — no list indexing (this receipt) |
| emit `Str` output to generate C text | **blocked** — `utf8_slice` is not a lowered builtin (A3-043) |

There is no structural escape. **A compiler-shaped function cannot be emitted today, by any design.**

## The smallest prerequisite, stated exactly

Both routes converge on the same pre-work. Ordered by leverage:

1. **Make emission cost ~linear in node count.** Today `steps ≈ 381n + 35.68n²` (A3-033). At 48 nodes the
   fit predicts **100,495** — precisely the boundary A3-045 measured. Removing the quadratic term would
   cost **~18,300**: a **5.4× margin** under the unchanged cap.
   **Success criterion I will audit:** a single function containing
   `while { if/else; if/else; o = o + 1 }` (48 nodes) emits below 100,000 steps.
2. **Add a by-name `utf8_slice` lowering** plus a small C runtime slice helper, and let known builtins
   lower without a resolved-call fact (A3-042/043). Needed for a compiler to produce C *text*.
3. **Watch the checker ceiling.** It bit at 62 nodes (A3-045 Q3), so after (1) the chunk size must stay
   ≤ ~48 nodes or the checker needs the same treatment.

## Recommendation to the team

Route selection cannot be made on evidence until (1) lands; every candidate spike will be blocked in the
same place. **This is not a reason to stop the mission — it is the shortest path through it**, and it is
already quantified with a pass/fail criterion I can audit independently.

## HANDOFF OFFER → A2 (emitter, bounded, no ownership transfer)

- **Target:** a single-function program `while !(byte_length(source) <= o) { if ...; if ...; o = o + 1 }`
  (≈48 nodes, two sequential conditionals) emits under 100,000 steps without raising the cap.
- **Measurement:** `python verification/probes/flatten_vs_nest_045.py` — its Q2 row is exactly this shape.
- **Expected:** Q2 moves from `refused ≥100,001` to `emitted`, ideally near the ~18,300 linear prediction.
- **A3 will audit** with that probe and the bootstrap auditor; A3 will not author the change.
- **Reply `CLAIMED` / `DECLINED`** in your own outbox.

## Honest limits

- One family, one seed build, one machine; cost counts, not compiled programs.
- I have not measured a `List[Int]` loop at all (only that indexing is invalid); a `contains`-based
  classifier would still need a conditional per test, so I do not expect it to help, but I have not
  measured that either.
- Setting a cap is not mine. If the recommendation turns out to require raising it, that is Matthew's
  decision and must go to him, not be slipped in.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953; cd <t>
pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
# t[0] -> invalid (PEP_TYPE_MISMATCH); contains/length -> valid
python verification/probes/flatten_vs_nest_045.py
```

## Scope

A3 changed only `verification/**`. No edits to A1's checker/contract, A2's emitter, A4's app. Cap
unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-046).