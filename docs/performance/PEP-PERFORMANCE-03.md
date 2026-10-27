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
separate from the parser-loop timing; the current Slice 1 adapter does not yet
claim a warm-session result because each workload starts a fresh process.

The evidence supports measuring a larger safe stage batch and retained-session
reuse next. It does not yet justify a production protocol change, cursor
compression, compact AST wire schema, or a changed interpreter budget.

## Reproduction

From the repository root, with the disposable `_build/perf03-a12` checkout at
the pinned SHA:

```text
python tests/performance03_lab.py --real-a12 --include-scaling --output _build/perf03/slice1.json
python -m unittest tests.test_performance03_lab tests.test_performance02_lab -v
```

The generated JSON is ignored build evidence. It includes per-call rows and
cursor fingerprints for later continuation and batching analysis.

## Boundaries

This slice does not claim that A11 and A12 are one production compiler
component, does not implement A13, and does not measure interpreter CPU,
typed-value construction, or allocator memory separately. The OCaml AST is an
independent structural/count oracle, but a complete semantic field-by-field
AST differential remains a later slice. PowerShell invocation and OCaml
compilation are intentionally outside the parser-loop total and need separate
warm-session experiments.
