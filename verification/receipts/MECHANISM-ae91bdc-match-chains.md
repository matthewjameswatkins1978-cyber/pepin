# `ae91bdc` mechanism — match-splitting chains trade step budget for call depth (2026-10-30)

Completes the `ae91bdc` analysis: single commit (BISECT receipt) +
exact mechanism with measured positions.

## What the commit did

Split three monolithic `match` dispatchers in `examples/pep_parser.pep`
into sequential fallthrough chains (the same chunking technique A1
applied to the checker, now to the parser — lowering *per-function*
step cost for compiler-scale sources):

| dispatcher | split into | file |
|---|---|---|
| `ast_value_span` | `ast_value_span_part_1 … part_19` | parser L121+ |
| `flat_node` | `flat_node_fast_1..10` + `flat_node_part_1..19` | parser L381+ |
| `ast_set_span` | `ast_set_span_part_1 … part_19` | parser L1668+ |

(0 such functions at `bff9dad`; 19 `ast_value_span_part` + more at
`ae91bdc`.)

## Why deep tests now die at the depth axis

Every `_ =>` handoff is **one host-interpreter call frame**. A span
query that reached one function before now walks up to 5 fallthroughs
(`AstList` sits in `part_6`) — ~6 frames per query instead of 1. On
deep nested-list targets the interpreter is already near the 128-frame
host ceiling from recursing the structure; the chained query tips it
over.

**Measured death positions** (single test
`test_deep_nested_list_calls_match_ocaml`, same test green at
`bff9dad`): `PEP_RUNTIME_CALL_DEPTH … at 632:10` and `646:10` →
bundle-mapped to `examples/pep_parser.pep` **lines 138 and 152 — the
closing braces of `ast_value_span_part_1` and `part_3`**, i.e. dying
mid-chain. Failures: 4 subtests, positions only in the span chain.

## Why a14's countdown tip-over is the same commit

The split reduces *max-per-function* steps but adds per-query call and
re-match overhead, so **total** step spend on the emit path rises
slightly — countdown programs sitting just under the shared 100k
all-in-one budget cross it. Hence a14 2→4 at the same commit (both new
failures emit-stage `STEP_LIMIT`, per the regression receipt).

## One mechanism, two axes

- deep-stack programs → **depth 128** (span-chain frames + structural
  recursion) — 22 a13/nested failures;
- near-budget programs → **step 100k** (added chain overhead) — 2 a14
  failures.

## Fix directions (builder's call)

1. Order the chains common-first (put `AstList`/`AstBlock` early
   variants in the entry match) to cut typical path length;
2. keep hot arms inline in the entry function, chain only rare
   variants;
3. or accept both budgets as the shape and update expectations (the
   Wall B contract decision, now with a named mechanism).

Verified: replay **170/170**; no builder movement elsewhere this
round.
