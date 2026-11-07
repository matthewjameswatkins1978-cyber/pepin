# PRE-REGISTRATION A3-039: which CONSTRUCTS cost the emitter, not just how many nodes?

**Seat:** A3. Follows BOOT-A3-033 (cost is quadratic in chunk nodes) and BOOT-A3-038 (partition
cannot reduce the frozen app). **Written and committed before measurement.**

## Why this is the remaining actionable question

A2 must reduce the emitter's cost on the frozen app's 44-node `main`, because partition is ruled out.
"Cost is quadratic in node count" tells them *that* it is expensive but not *what to optimise*: node
count is an outcome, not a cause. A ranked list of constructs — control flow vs calls vs assignments
vs locals — is what turns the measurement into a change.

## Design

One family, one function, constant envelope:

```
fn main(source: SourceBytes) -> Int {
  var n = 0
  var o = 0
  while !(byte_length(source) <= o) {
    <BODY>
    o = o + 1
  }
  return n
}
```

`<BODY>` varies so that each variant adds **one construct kind** to the previous baseline. Exact step
counts come from `{"op":"metrics"}` `last_execute_steps` after a single `pep-c23-unit` invocation.

| variant | BODY | adds |
|---|---|---|
| V0 | `n = n + 1` | baseline |
| V1 | V0 + three more assignments | assignments |
| V2 | V0 + `if byte_at(source, o) == 1 { n = n + 1 } else { n = n + 2 }` | one flat `if/else` |
| V3 | V2 with a second `if` nested in the then | nesting depth |
| V4 | V0 + `if byte_length(source) == 0 { n = n + 1 } else { n = n + 2 }` | `if/else` with a call in the condition |
| V5 | V0 + an extra unused local `var k = byte_length(source)` | a local binding |

## Predictions

| # | Claim | Falsified if |
|---|---|---|
| P1 | V0 lands in **18,000–26,000** steps (it is essentially the 20-id window of BOOT-A3-038, which measured 21,972) | outside that band |
| P2 | one flat `if/else` (V2) costs **more per added node** than four assignments (V1) — control flow is the expensive construct | V1's marginal cost per node ≥ V2's |
| P3 | nesting depth 2 (V3) costs **more than twice** the marginal cost of one `if` (V2−V0) | V3−V2 ≤ 2·(V2−V0) |
| P4 | adding a call in the condition (V4) costs **less** than adding an `if/else` (V2−V0) | V4−V0 ≥ V2−V0 |
| P5 | an extra local binding (V5) costs **less than a control-flow construct** at comparable node growth | V5−V0 ≥ V2−V0 |

P2–P5 are the ranking claims that would actually guide A2's work. **I may be wrong about the ranking**
— I have never measured per-construct cost, and node counts alone do not predict it. A falsified
ranking is a useful result and will be reported as such.

## What this will and will not establish

- It gives **marginal step cost per construct kind** on one family, one seed build, one machine.
- It will **not** prove a mechanism inside A2's code. Correlations with node counts will be labelled;
  no claim will be made about *why* a construct is expensive beyond what the numbers support.
- Variants are A3 cost probes, not language test cases. They assert nothing about program meaning and
  nothing will be compiled or run.

## Scope guard

A3 owns only `verification/**`. No edits to A1's checker/contract, A2's emitter, or A4's app. Cap
unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.
