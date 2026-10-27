# PEP-PERFORMANCE-03 — Real Compiler Pipeline Laboratory

Status: Slice 1 evidence on an isolated experimental branch. This report is
not an A12 or A13 acceptance document and does not change compiler semantics,
the JSONL protocol, interpreter budgets, or the 65,536-byte source cap.

## Authority and method

The A12 dependency is a disposable Git worktree pinned to
`69a47fe77187666bdd045b8dc8a9f633a7dd49d7`. The current branch does not import
or edit A12 files. `tests/performance03_lab.py` opens the A12 lexer/parser
bundle, registers `parser_start` and `parser_step` through the public session
route, and invokes `parser_step` only with the exact cursor returned by the
previous invocation. It records request/response bytes, per-call wall time,
source offsets, cursor fingerprints, node counts and session setup timings.

The host-side oracle is independent of the parser result: it walks the OCaml
AST returned by `open_bytes`, counts the wire nodes including explicit type
nodes, and checks parser node IDs, parent edges, roles, child indexes, roots,
cycles and document/revision identity. Complete results must match the
independent wire-node count. Incomplete results are classified separately;
partial node streams are not called complete parser evidence.

## Slice 1 measurements

The real campaign used seven complete syntax families, one malformed source,
and four generated declaration sizes. All seven complete hand-written cases
passed the independent count and topology checks. The malformed case returned
`incomplete` and was retained as an expected parser classification.

| workload | bytes | status | nodes | calls | requests | responses | max response |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| expression | 13 | complete | 8 | 4 | 8,760 | 19,835 | 9,930 |
| function | 52 | complete | 11 | 7 | 21,120 | 36,670 | 9,119 |
| record | 99 | complete | 16 | 8 | 23,348 | 43,476 | 9,424 |
| union/match | 122 | complete | 18 | 7 | 22,582 | 43,585 | 12,020 |
| control | 179 | complete | 29 | 17 | 62,472 | 98,974 | 9,188 |
| Unicode/CRLF string | 39 | complete | 4 | 6 | 15,566 | 25,098 | 5,895 |
| list/call | 67 | complete | 10 | 7 | 21,639 | 36,431 | 8,860 |
| malformed | 32 | incomplete | 1 partial | 4 | 10,220 | 16,046 | 6,097 |
| declarations ×8 | 199 | complete | 28 | 14 | 53,070 | 86,730 | 9,585 |
| declarations ×16 | 372 | complete | 52 | 23 | 92,340 | 150,915 | 9,593 |
| declarations ×32 | 724 | complete | 100 | 40 | 168,209 | 275,903 | 9,593 |
| declarations ×64 | 1,428 | complete | 196 | 75 | 322,997 | 529,987 | 9,636 |

The pinned A12 copy of `examples/pep_lexer.pep` is 19,425 bytes. One direct
run produced 2,030 nodes in 568 total invocations (start plus 567 step
invocations), 4,115,879 request bytes and 6,099,807 response bytes. Its
largest observed request/response were 17,816/69,118 bytes. The parser-loop
wall time was 1,269.52 ms; the first session also reported 269.79 ms process
startup and 586.76 ms setup/open/tool-registration time. These are external
wall measurements, not isolated OCaml CPU or allocator measurements.

## Initial attribution

For the real A11-sized run, the continuation loop is 568 JSONL invocations
and about 10.2 MB of aggregate wire traffic. The largest response is only
about 69 KB, so the existing 1 MiB message boundary is not the limiting factor
for this workload. The small-workload rows show that registration and cursor
framing dominate fixed cost, while declaration scaling makes response traffic
and call count grow with emitted AST nodes. The first cold session's setup is
separate from the parser-loop timing; Slice 2 separately measures retained
session reuse.

The evidence supports measuring a larger safe stage batch and retained-session
reuse next. It does not yet justify a production protocol change, cursor
compression, compact AST wire schema, or a changed interpreter budget.

## Slice 2: retained sessions and bounded aggregation model

The retained-session experiment reused one A12 process and one registered
parser pair for three targets (199, 372 and 724 bytes). One run reported
272.60 ms process startup and 550.03 ms one-time setup. The target rows were:

| bytes | nodes | calls | requests | responses | parser loop |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 199 | 28 | 14 | 53,042 | 86,702 | 14.90 ms |
| 372 | 52 | 23 | 92,294 | 150,869 | 24.50 ms |
| 724 | 100 | 40 | 168,129 | 275,823 | 46.88 ms |

The same-session A11-sized control parsed two identical 19,425-byte targets in
1,230.29 ms and 1,211.28 ms after one 580.09 ms setup, with 4,114,743 request
bytes and 6,098,671 response bytes per target. The corresponding cold run had
roughly 586.76 ms setup per target. This is an experimentally verified
benefit of retained session/tool state, not a claim that parser state is safe
to share across documents: every target still received a new document and
revision, and every continuation used the returned cursor for that target.

The test-only coalescing model groups already-produced parser-step responses
without changing execution or the JSONL protocol. On the 19,425-byte A12
lexer source, the model produced these bounds:

| grouping width | modelled host calls | largest grouped response | under 1 MiB |
| ---: | ---: | ---: | --- |
| 1 | 568 | 69,118 | yes |
| 2 | 285 | 83,271 | yes |
| 4 | 143 | 120,301 | yes |
| 8 | 72 | 179,127 | yes |
| 16 | 37 | 358,045 | yes |
| 32 | 19 | 632,778 | yes |
| 64 | 10 | 953,944 | yes |
| 128 | 6 | 1,822,472 | no |

This model identifies 64 as a workload-specific upper candidate under the
existing message limit and 128 as a demonstrated unsafe candidate. It is not
a production improvement: aggregation changes the transport contract and
would need an independently reviewed bounded envelope, ordering/error model
and A13 consumer. The safe near-term improvement is retained session/tool
state where document/revision ownership remains explicit.

## A13 readiness and composition boundary

Read-only GitHub inspection found no `a13`, checker or accepted A13 branch/ref
on `origin` at this slice. The repository contains only the provisional
`docs/packets/A13-PEP-WRITTEN-CHECKER.md` and the accepted A12 consumer
contract. C23's current work is an isolated synthetic checked-fixture/native
artifact lab and is not an A13 implementation. Therefore this report makes no
claim that A11, A12 and A13 have executed as one compiler pipeline.

The accepted A12 contract is sufficient to define a guarded future bridge:
the checker must retain the exact document/revision, consume the exact
`parser_start`/`parser_step` cursor chain, collect chunks by node ID, and keep
syntax IDs separate from checker-owned semantic identities. The performance
measurements do not authorise semantic IDs, ownership facts, type resolution,
or an A13 wire schema.

## Engineering decision

| candidate | measured gain | complexity/risk | A12/A13 impact | decision |
| --- | --- | --- | --- | --- |
| separate host lexer and parser token streams | easy to debug; existing components remain isolated | duplicates token/cursor transport and adds host round trips; no real composition evidence | requires a new token bridge and semantic ownership rules | retain only as a diagnostic baseline |
| parser-internal lexer/parser stage composition | removes per-token host transfer; A12 already demonstrates this shape | needs independent checker contract, error propagation and bounded result envelopes | compatible with A12's internal stream; A13 must consume verified chunks, not syntax IDs as semantics | preferred architecture direction, pending A13 review |
| retained session/tool registration | measured setup amortisation across repeated targets | session lifecycle, document/revision isolation and failure recovery must remain explicit | compatible if every target receives a fresh authorised revision and exact cursor chain | safe improvement to pursue now |
| host-side response coalescing | modelled 568 to 10 calls at width 64 while staying below 1 MiB on this workload | not implemented; changes framing, ordering, diagnostics and failure semantics; width 128 is unsafe | requires A12/A13 consumer agreement and a separate protocol review | test-only planning evidence; no landing now |

Recommendation: keep one long-lived local session for a compiler pipeline,
retain explicit document/revision authority, and let lexer/parser/checker
stages cooperate inside bounded interpreter invocations rather than returning
one host message per token or AST node. Preserve ordinary chunked typed results
and fail-closed continuation validation. A future stage-batching change should
be selected from measured envelopes per workload and independently reviewed;
the current evidence supports a 64-step coalescing candidate only as a
workload-specific experiment, not as a default.

This is the simplest architecture that addresses the measured fixed setup and
transport costs without weakening source access, hiding work in host builtins,
raising budgets, or claiming an unimplemented A13. It keeps A12 compatible and
gives A13 a clear boundary: syntax chunks in, checker-owned revision-scoped
facts out.

## Reproduction

From the repository root, with the disposable `_build/perf03-a12` checkout at
the pinned SHA:

```text
python tests/performance03_lab.py --real-a12 --include-scaling --output _build/perf03/slice1.json
python -m unittest tests.test_performance03_lab tests.test_performance02_lab -v
```

The generated JSON is ignored build evidence. It includes per-call rows and
cursor fingerprints for later continuation and batching analysis.

The retained-session experiment can be reproduced with the module helper:

```text
python -c "from tests import performance03_lab as l; import json; print(json.dumps(l.warm_session_measurement(), indent=2))"
```

## Boundaries

This slice does not claim that A11 and A12 are one production compiler
component, does not implement A13, and does not measure interpreter CPU,
typed-value construction, or allocator memory separately. The OCaml AST is an
independent structural/count oracle, but a complete semantic field-by-field
AST differential remains a later slice. PowerShell invocation and OCaml
compilation are intentionally outside the parser-loop total and need separate
warm-session experiments.

The remaining high-value uncertainty is internal attribution: the current
adapter cannot separate Pep interpreter CPU, typed-value construction, JSON
encoding and allocator behaviour without production profiling hooks. P02's
direct A11 profile supplies those categories for the lexer route, but not for
the pinned A12 parser route. Any production batching or compact representation
should wait for that independent review and a real A13 workload.
