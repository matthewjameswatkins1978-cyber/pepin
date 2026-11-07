# PRE-REGISTRATION A3-036: is A1's new `shared_spine` admission rule sound?

**Seat:** A3. Campaign `LUCY-20261107-007`, lane item 3. **Written and committed before measurement.**

## Why this is the right target now

A1's `231caf1` ("shared-spine sub-function windows in plan_ids") is brand-new code in the critical
path of the only proposed remedy to the capacity blocker, and **nobody has independently tested it**.
It relaxes a previously absolute invariant: before it, a node could belong to more than one chunk
only if it sat inside a declared **shared root**, which carries its whole subtree. Now a bare
`shared_spine` id may repeat across chunks **with no subtree attached**.

`_plan`'s remaining invariants (read, not assumed): per chunk ids must be non-empty, strictly
ascending, all nodes known, every node's parent must be in the same chunk, no duplicate within a
chunk; cross-chunk overlap refused unless shared root/spine; each shared root must be wholly inside
some chunk; **every document node must be in some chunk**; signature provenance ids must be known.

The structural reason the spine exists: `parent-in-chunk` forces a function node into *every* window
that contains any of its descendants, so a sub-function split necessarily shares the ancestor chain.

## Predictions

| # | Claim | Falsified if |
|---|---|---|
| S1 | An honest two-window split of the app's `main`, sharing only the function node as spine, is **accepted** | refused |
| S2 | That plan still covers **every** document node (completeness holds with a spine) | `CHUNK_PLAN_INCOMPLETE` |
| S3 | Each window is itself a legal chunk (ascending ids, parent present, no in-chunk duplicate) | any per-chunk refusal |
| S4 | The **only** node appearing in two chunks is the declared spine node — i.e. duplication equals the spine, and no undeclared node leaks into both | any non-spine node in ≥2 chunks |
| S5 | Declaring a spine does **not** relax per-chunk `OPEN_PARENT`: a window whose child lacks its parent still refuses | accepted |
| S6 | Undeclared overlap still refuses (`CHUNK_PLAN_OVERLAP`); an unknown spine id still refuses (`CHUNK_UNKNOWN_NODE`); an in-chunk duplicate still refuses | accepted |
| S7 | A spine id does not license incomplete coverage — dropping a node still refuses (`CHUNK_PLAN_INCOMPLETE`) | accepted |

## The design question I expect to raise (not a bug claim)

If S1–S4 hold, then the host can legitimately produce a plan in which the **function node appears in
two chunks**. What the emitter then does with it is *not* the contract's business: nothing in
`_plan` prevents the shared node from being emitted twice. A duplicated *function definition* would
be rejected by C (fail-closed), but a duplicated *statement* node emitted inside two different
functions could compile while misplacing code. I will report this as an **open question for A1/A2**
about the consuming side, with the plan-level evidence, and will **not** claim it is exploitable
without a constructed case.

## Method

- `DocumentIndex` built from the **pinned frozen app** parse (`4a44dd65…`) through the same chunk
  pipeline A3 uses for gates, on A1's `86ff953` (which carries `shared_spine`).
- Windows are honest: split `main`'s direct children into two groups, each window = function node +
  the full subtree of its group, spine = the function node id.
- Every prediction is checked by the contract's own refusal codes; no test asserts on internal state.
- A3 implements nothing in the contract. This is read-only probing of A1's code.

## Scope guard

A3 owns only `verification/**`. No edits to A1's contract, A2's emitter, A4's app, frozen gates,
budgets, `CURRENT`, manifest, master or release labels.
