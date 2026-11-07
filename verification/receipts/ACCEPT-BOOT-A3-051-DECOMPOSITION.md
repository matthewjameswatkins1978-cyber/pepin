# ACCEPT BOOT-A3-051 — decomposition DOES escape the ceiling; I must partly retract A3-045/046

**Verdict: a lexer-shaped classification program **fully emits today** when decomposed. My published
conclusion that "no restructuring gets a compiler-shaped function under the budget" was **too strong**, and
I am correcting it.**

Pre-registered at `71ba732`, with T4 explicitly named as the claim that "cuts against my own published
conclusion".

## The result

```
app: verification/fixtures/emit/split_helpers.pep (847 bytes)
host analysis: status=valid []
  chunk is_ws       nodes=24  valid      emit OK (484 C bytes)
  chunk is_letter   nodes=32  valid      emit OK (578)
  chunk is_digit    nodes=16  valid      emit OK (299)
  chunk classify    nodes=25  valid      emit OK (486)
  chunk main        nodes=27  valid      emit OK (458)
RESULT: FULLY EMITTED - every function lowered
```

`main` iterates the granted bytes with a loop body containing **zero conditionals** — just
`n = n + classify(byte_at(source, o))` and `o = o + 1`. All classification lives in loop-free helpers.

## How the three refusals on the way there changed the picture

1. **Loop-free helpers DO emit.** A `classify` with a single `if/else` and **no loop** emitted cleanly.
   This contradicts what I had carried from a BOOT-A3-033 refusal ("functions require … supported loops"),
   and it is the fact that reopened the whole question.
2. **The boundary is per-function SIZE, not loop-ness.** `is_letter` at **32 nodes** with nested
   conditionals emitted; a combined `classify` at **35 nodes** refused with `PEP_RUNTIME_STEP_LIMIT`.
   So nesting is affordable in a loop-free function up to roughly 32 nodes.
3. **A real layer contradiction, which A1/A2 should know about.** A function that returns from every
   branch is **unrepresentable**:
   - nested returns only → emitter refuses: *"Pep C23 functions require a return statement"*;
   - adding a trailing `return` → **checker** refuses: **`PEP_UNREACHABLE`**.
   The only idiom that satisfies both is **assign a result variable, then one reachable trailing return** —
   which is what finally emitted. This is an emitter/checker inconsistency, not a language rule.

## What was right and what was wrong in BOOT-A3-045/046

**Right:** conditionals *inside a loop body* are the expensive thing — two sequential ones refuse at 48
nodes, nesting refuses at 44, and a real cursor primitive (`cursor_kind_v1`, 52 nodes) refuses at
emission. Those measurements stand.

**Wrong:** the inference "no restructuring can work". Decomposition does work, provided:

| constraint | measured basis |
|---|---|
| every function ≤ ~32 nodes | 32 emits, 35 refuses |
| loop bodies contain **zero** conditionals | 045 two-sequential refuses at 48 nodes |
| classification dispatched through helper calls | this program: 5 functions, all emit |
| `var` result + one reachable trailing return | `PEP_UNREACHABLE` / "require a return statement" otherwise |
| no `Str` production | **still blocked** — `utf8_slice` is not a lowered builtin (A3-043) |

## What this means for the mission

- **A2 does not need to fix control-flow cost** for a lexer-shaped design to emit; the design constraint is
  sufficient. That removes a large piece of work from the critical path.
- **A4's design guidance is now concrete**: emit-sized functions, conditional-free loops, helper dispatch,
  assignment + trailing return. `cursor_kind_v1/v2` (BOOT-A3-049) should be restructured this way — the
  same semantics, decomposed.
- **The real remaining blocker is `Str` production** (A3-043): a compiler must emit C *text*, and
  `utf8_slice`/`str_concat` cannot be bound and printed today. **That** is now the shortest path.

## Honest limits

- **Emission only.** Nothing was compiled or run, so this is not a working program and says nothing about
  its generated binary's correctness. The auditor (A3-044/050) would be needed for that.
- One shape, one seed build, one machine. The ~32-node boundary is where these two data points fell.
- The assignment idiom is a **workaround for an inconsistency**, not a language rule; if A1/A2 fix the
  emitter/checker mismatch, the natural form should be preferred.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953; cd <t>
pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
$env:PEPIN_APP_REL = 'verification/fixtures/emit/split_helpers.pep'; $env:PEPIN_APP_REV = 'dc7e2be'
python verification/probes/emit_any_049.py
```

## Scope

A3 changed only `verification/**`. No edits to A1's checker, A2's emitter or A4's app. Cap unchanged; no
`CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-051).