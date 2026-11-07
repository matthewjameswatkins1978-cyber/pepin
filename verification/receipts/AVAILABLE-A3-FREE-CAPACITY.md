# AVAILABLE — A3 free capacity, and the R-vs-S cross-check table filled to date

**Seat:** A3. **Branch:** `codex/bootstrap-agent3-verification` @ `a5f0fae`. Worktree
`D:/Projects/wt-a3-gate`, clean. **Safe paths:** `verification/**` only.

## Why I am announcing rather than working

My lane is blocked in the only way that matters: I cannot author the change I have to verify. The mission
says a verifier must not certify its own work, and every remaining question in my lane needs either (a) an
emitter change, or (b) a peer artifact I have not already audited.

Current live state, checked this turn: A2 `4b70c61` (**worktree clean, no `.pep` touched in 45 min**), A1
`86ff953`, A4 `59c3207`. The one-item change that unblocks the mission's floor is **unowned right now**.

## The R-vs-S cross-check table, as far as measurement can fill it

| gate | R (salvage) | S (small bootstrap) | source |
|---|---|---|---|
| source-dependent C23 output | **untested** | **untested** | blocked on one lowering (A3-042/055) |
| a lexer-shaped function emits | **yes**, under decomposition | **yes**, under decomposition | A3-051/053 |
| that program runs natively (strict Clang + GCC) | **yes** — 0/1/2 on three fixtures, two deliberately invalid | same | A3-053 |
| `Str` concatenation | works, inline and in initialisers | same | A3-054 |
| `bytes → Str` | **blocked**: `utf8_slice` has no by-name lowering (0 sites vs str_concat 3) | same | A3-054/052 |
| control-flow cost as blocker | **no longer on the critical path** given decomposition | same | A3-051 |
| checker/emitter consistency | **one contradiction**: all-nested-return functions are unrepresentable (`require a return statement` vs `PEP_UNREACHABLE`) | same | A3-051 |
| two-fallible-operand comparison | **refused**; hoist sentinels into locals | same | A3-053 |
| A→B→C stage audit instrument | **ready**: `bootstrap_audit.py`, A1–A6 validated incl. native-exe A5 | same | A3-044/050 |

**Neither route can be selected on evidence yet**, and the reason is the same for both: no agent has
produced input-dependent C text. The differentiator the mission wants — fewest unproven dependencies —
cannot be measured until that one output exists.

## What I can do immediately, for any agent (bounded, reversible)

1. **Audit an emitter change in ~3 seconds.** `emit_any_049.py` reports per-function check status, the
   exact first refusal, and can compile + run natively. I will run it on any candidate SHA and report
   without authoring.
2. **Produce reference oracles.** I hold independent Python oracles for the line-scan counts, the
   identifier-start-run counts, A4's cursor kinds and A4's T2 `0/1/2` contract — all verified against
   committed bytes. Any implementation can be checked against them instead of against itself.
3. **Build negative fixtures.** I have already built NUL-sensitive, divergent-input, loop-free-helper,
   deep-nesting and distributed-helper fixtures; more are cheap.
4. **Review a design on paper** against the measured constraints (≤~32–34 nodes/function, loop bodies with
   ≤1 conditional, assign + one reachable trailing return, hoisted sentinels, no `Str` production yet).
5. **Run the staged decisive test** the moment a `utf8_slice` lowering exists.

Preference order if someone wants to hand me work: (1) then (5), then (4).

## What I am not doing

Not implementing the `utf8_slice` lowering myself. Not because it is hard — it is one by-name lowering plus
a small C helper — but because **A3 cannot independently verify a change it authored**, and this campaign
has already been well served by keeping that line sharp.

## Honest note for Matthew, one line

The mission is parked on a single unowned change; if no peer picks it up, it needs either a reassignment
decision or a pause. I am not asking for that yet — the stall is ~2 h old and peers are alive.

REF: GH #16.