# Peer review round 2 — A2 tip re-run + A1 collector source read (Agent 3)

## A2 `codex/bootstrap-agent2-b0@62885b861e3f440b2efc5bbd9ebf24e9b6611d6e` — re-run

Read-only detached worktree (since removed). Command (from that worktree):
`python -m unittest tests.test_c23_source_emission -v`

**Result:** `TESTED` PASS — 3/3 in 7.650s:
- `test_scalar_record_construction_binding_projection_and_reference` ok
- `test_records_pass_through_and_return_from_helpers` ok (new in this
  slice: record params/returns across helpers, interpreter reference 42)
- `test_nested_record_layout_fails_closed` ok

In-memory `emit` + OCaml interpreter reference only; no C compiler, no
binaries. Native syntax/execution remain `BLOCKED_SECURITY`. No finding.

## A1 `codex/bootstrap-agent1-b0` `95ab6c6` → `cd8c694` — source read

Scope: the single-pass `collect_functions` rewrite (plus the 24-function
signature regression, which cannot execute under the hold). Method:
read-only diff inspection against the parser's node vocabulary. No
Agent 1 files modified; differential execution stays blocked.

**Verdict: narrow no-finding (source-level).** The rewrite is
behavior-preserving as far as static inspection can establish:

1. Arity: old counted `role == "parameter"`, new counts
   `kind == "parameter"` over direct children. The parser builds every
   `AstParameter` via `flat_composite(..., role, "parameter", ...)` and
   both call sites pass role `"parameter"`, so both predicates match the
   same node set.
2. Return shape: the `nextReturnTypeId = node.id + 1` walk on `type_list`
   mirrors the old `type_shape_at` walk exactly (same dense-id
   assumption, same scalar/named/depth outcomes).
3. Ordering: nodes are built with sequential ids and returned via
   `reverse(nodesReversed)`, i.e. ascending id/document order — the new
   streaming pass's load-bearing assumption holds by construction.
4. Record construction (`make_checked_function`) is field-identical to
   the old inline literal, including the `semanticId: 100000 + ordinal`
   scheme and source-order reversal.

**Caveats (explicit, not findings):** the streaming pass, unlike the old
lookup code, is order-dependent — true today by construction, worth a
one-line comment if the flattening ever changes; and the 24-function
regression's measured behavior remains unverified until the hold lifts
(A1's own stated limitation at `cd8c694` stands).
