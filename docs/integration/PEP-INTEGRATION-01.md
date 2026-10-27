# PEP-INTEGRATION-01 — Working Components to One Compiler Pipeline

Status: integration-readiness evidence on `exp/pep-performance-03`. This is
an isolated harness/report slice. It does not modify A12, add A13, promote
the C23 experiment to A14, change the JSONL protocol, raise interpreter
budgets, or advance a milestone pointer.

## Current truth

The machine-readable dependency record is
[`PEP-INTEGRATION-01-MANIFEST.json`](PEP-INTEGRATION-01-MANIFEST.json). The
baseline is the reviewed A11 integration candidate
`4e497bf192b33e76cb0fdf59bfc30e9b3ef3127f`.

| component | exact revision | current evidence boundary |
| --- | --- | --- |
| A11 lexer | `3fb83b7fb9eeb82674f12b021b1f21f2d677c795` | accepted lexer evidence; independent differential checks |
| A12 parser | `69a47fe77187666bdd045b8dc8a9f633a7dd49d7` | accepted syntax/parser evidence; read-only disposable checkout |
| Conformance R1 | `731157bb4aff24002b693c78951a2e207b37d392` | independent experimental harness, awaiting review |
| Performance 03 adapter | `fb9cbef4dfcf0e32c6f886cf7a3371cfae3b717a` | experimental measurement adapter, awaiting review |
| C23 Artifact-05 | `ff0ad3fe513419a2317cc0e9616e1c5ce13f3701` | isolated native feasibility experiment, not A14 |
| A13 checker | no accepted SHA | provisional packet only; no executable checker path |

The repository remains the authority for these identities. Board messages are
coordination only.

## Executable A12 boundary

`tests/integration01_lab.py` invokes the real public session route from the
pinned A12 disposable checkout. It sends source bytes to `open_bytes`, starts
the parser, then follows only the exact cursor returned by each
`parser_step`. It collects `FlatAstNode` chunks and records the document,
source revision, status, node count, request/response totals and maxima.

For complete results, the harness independently counts the OCaml AST, checks
node topology and checks every reported span against the original UTF-8 byte
length. It also checks the expected syntax shape for the minimal expression.
The source revision is recomputed from the exact bytes for every row. Invalid
and incomplete results are classified explicitly rather than treated as
successful complete parses.

The real receipt is generated under ignored `_build/` by:

```text
python tests/integration01_lab.py --real-a12 --output _build/integration01/slice1-receipt.json
```

The run completed with five boundary rows and the unchanged resource limit:

| case | bytes | status | nodes | calls | request bytes | response bytes | max response |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| minimal arithmetic | 13 | complete | 8 | 4 | 8,760 | 19,835 | 9,930 |
| record/function | 99 | complete | 16 | 8 | 23,348 | 43,476 | 9,424 |
| unexpected character | 29 | invalid | 0 | 3 | 5,611 | 13,347 | 7,305 |
| unclosed expression | 32 | incomplete | 1 partial | 4 | 10,220 | 16,046 | 6,097 |
| UTF-8 string with CRLF | 39 | complete | 4 | 6 | 15,566 | 25,098 | 5,895 |

The complete rows matched the independent OCaml node counts and passed
topology/span checks. The oversized 65,537-byte probe failed closed with
`PEP_SOURCE_BYTE_LIMIT` (131,149 request bytes, 217 response bytes). No source
cap or tool budget was raised.

This is a real A12 syntax boundary, not a claim that lexer, checker and native
emitter already form one production compiler. A12 syntax IDs are not checker
semantic IDs, and the host does not invent semantic facts from them.

## Integration conformance matrix

[`PEP-INTEGRATION-01-MATRIX.json`](PEP-INTEGRATION-01-MATRIX.json) contains 15
cases and the rule that process exit alone is never an oracle. The five A12
boundary cases above are executable in this slice. The remaining cases retain
explicit expected classifications for the next accepted component:

- revision mismatch and forged continuation: reject or fail closed; a caller
  cannot manufacture parser authority;
- missing chunk and wrong parent role: reject incomplete/mutated topology;
- wrong semantic type identity: defer until A13 owns and independently checks
  semantic identities; a syntax node kind or ID is not a type oracle;
- unresolved binding: blocked until an accepted A13 checker contract;
- union/borrowed-list native paths: controlled unsupported diagnostic in the
  Artifact-05 experiment, not A14 capability;
- checked arithmetic overflow: future first-slice semantic/native equality
  case, not executable without A13 facts;
- resource exhaustion: verified now at the unchanged A12 source boundary;
- failed parse followed by valid input: a required session-recovery contract
  for the next integration slice, not inferred from this receipt.

This separation prevents a planned or experimental case from being reported
as an end-to-end compiler result.

## A13 and C23 boundaries

No accepted A13 checker branch or revision exists in the inspected repository
state. The provisional A13 packet is a design input only. A future checker
bridge must consume the exact A12 document/revision and returned cursor chain,
retain source-spanned syntax IDs as syntax authority, and create its own
stable semantic IDs, resolved calls, checked expression types, hole/binding
facts, exhaustiveness and ownership/lifetime facts. None of those semantic
facts are asserted here.

C23 Artifact-05 at `ff0ad3fe513419a2317cc0e9616e1c5ce13f3701` demonstrates a
restricted checked-fixture/native route with strict toolchain evidence and
controlled unsupported diagnostics. It is not an A14 compiler and is not
composed into this executable A12 path. Union, borrowed-list/ownership and
parameterized-entry paths remain explicit boundaries.

[`PEP-INTEGRATION-01-CONTRACT.json`](PEP-INTEGRATION-01-CONTRACT.json) makes
that seam machine-readable. It lists the syntax facts A12 may provide, the
checker-owned facts required before an A13 consumer is trusted, the additional
facts a future A14 emitter must receive, and the inputs that must be rejected
or deferred. The contract is deliberately a gate: it does not fabricate a
semantic result for any unavailable stage.

## Architecture decision

The earlier P03 measurements remain the relevant performance evidence. On the
pinned 19,425-byte A12 lexer source, one direct run produced 2,030 nodes in
568 invocations, 4,115,879 request bytes and 6,099,807 response bytes; the
largest individual request/response were 17,816/69,118 bytes. Retaining one
session amortised roughly 580 ms of setup across two A11-sized targets. A
test-only host aggregation model kept width 64 below 1 MiB (10 modelled host
calls, 953,944-byte largest grouped response) but width 128 exceeded it
(1,822,472 bytes). Those figures are model evidence, not a protocol change.

| candidate | evidence and consequence | decision |
| --- | --- | --- |
| Separate host lexer/parser streams | easiest audit baseline, but repeats token transport and host round trips | retain as diagnostic baseline |
| Parser-internal bounded composition | A12 already performs lexer/parser work internally, avoiding per-token host transfer; needs accepted checker ownership/error contracts | preferred execution direction |
| One retained local session | setup amortisation is measured; each document still needs a fresh authorised revision and exact cursor chain | safe operational improvement to pursue |
| Host-side response coalescing | width 64 is only a workload-specific model; framing, diagnostics and ordering would need review and width 128 is unsafe | test-only evidence; do not land now |

Recommendation: use bounded composition inside Pep-written compiler stages and
retain a long-lived local session for setup reuse, while keeping document,
revision, cursor and semantic authority explicit. Do not introduce opaque host
AST state, hide work in builtins, raise budgets, or compress the protocol until
an accepted A13 consumer and an independently reviewed envelope exist.

## First native slice plan

The smallest useful first vertical slice remains planned, not implemented:

1. one function with `Int`, `Bool` and `Unit`;
2. one resolved direct call;
3. checked arithmetic failure as an explicit result;
4. A13 supplies stable semantic IDs, bounded source revision/spans, resolved
   call target, checked expression types and explicit ownership/lifetime facts;
5. A14 (when separately authorised) checks deterministic strict C23 output,
   Clang and GCC, interpreter/native result equality and controlled rejection
   of unsupported input.

This plan is a contract for future work, not evidence that the path exists.

## Verification and reproduction

The integration harness and its negative-control tests pass as follows:

```text
python -m unittest tests.test_integration01_lab tests.test_performance03_lab tests.test_performance02_lab -v
```

This focused command passed 37/37 tests. The real A12 command above passed;
the receipt records the five rows and the source-cap rejection. The existing
P03 adapter checks remain separate and continue to cover continuation identity,
topology mutations, source caps and bounded coalescing models. Full repository
regression and `git diff --check` are the next acceptance checks for this
slice. No A12, A13, C23 production/compiler, JSONL schema, budget or packet
pointer files were changed.

## Remaining uncertainty

This slice does not claim isolated interpreter CPU, typed-value construction,
JSON encoding, allocator or memory attribution for A12. The P02 lexer profile
has partial phase evidence, but it does not transfer those timings to the A12
parser. The real semantic checker boundary, session recovery after a failed
parse, and native equality remain unverified until their owners publish
accepted inputs and contracts.
