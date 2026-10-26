# PEP-PERFORMANCE-02 compiler pipeline laboratory

Status: Slice 1 measurement foundations on the isolated `exp/pep-performance-02`
branch. This report is experimental evidence only. It does not change Pep
semantics, the JSONL schemas, execution budgets, source cap, revision authority,
or A12/A13/A14 implementation status.

## Scope and evidence boundary

`tests/performance02_lab.py` reuses the accepted R2 session client and lexer
runner for a genuine A11 end-to-end profile. It also contains local-only cursor,
AST, checker and C23-emitter fixtures. The latter are synthetic and are not
measurements of an A12 parser, A13 checker or A14 emitter. A12 is now accepted
at exact SHA `69a47fe77187666bdd045b8dc8a9f633a7dd49d7`, but its source remains
isolated from this branch.

A disposable worktree pinned to that SHA was independently exercised with the
parser's differential test adapter. On the current 19,425-byte A11 source it
produced 2,030 flattened nodes through 567 parser continuations, 4,183,287
request bytes and 6,100,090 response bytes. The largest request and response
were 67,408 and 69,118 bytes respectively. This is accepted-version measurement
evidence, not an import of A12 implementation files; the source cap and protocol
remained unchanged.

The lab records the clock source in every result. Python host timings use
`time.perf_counter_ns`; the opt-in internal profile uses an isolated executable
with `Unix.gettimeofday`. Internal profile phases are therefore elapsed wall time,
not certified CPU time.

## Stage accounting model

The real A11 profile has two deliberately separate ledgers:

1. Host request encoding, pipe write/flush, response wait, Python JSON decoding,
   process startup and sampled memory from the accepted R2 harness.
2. Internal OCaml profile phases for request decode, revision/grant lookup,
   interpreter execution including typed-value construction, result encoding and
   response formatting.

The ledgers overlap while the host waits for an internal response. The report and
JSON output do not subtract them or claim an additive CPU decomposition. Typed
construction remains included in interpreter execution; separating it requires
additional production instrumentation and is intentionally deferred.

`source_acquisition` measures host UTF-8 decode, SHA-256 revision calculation and
byte length separately. It is preparation cost, not a claim about the compiler's
internal source snapshot implementation.

## Experimental representations

The local AST fixture preserves node identity, parent/child topology, semantic
role, type identity, original-byte spans, revision and diagnostics. It compares:

- the existing nested typed JSON shape;
- a flat node array;
- a compact array with a shared string table.

Each decoder is checked against a canonical logical fixture. Injected parent,
span and revision mutations are required to remain observable. Cursor fixtures
compare the full typed `LexCursor`, a minimal logical representation retaining all
resume and authority fields, and an opaque-handle design-only simulator. The
opaque form is not an authenticated certificate and does not add host-held
production state.

Synthetic checked-AST and C23-emission fixtures are labelled in JSON and are
intended only to establish scaling and transport methodology until those stages
exist as supported Pep-written implementations.

## Reproduction

Fast, no-build self-test:

```powershell
python tests/performance02_lab.py --self-test
python -m unittest tests.test_performance02_lab tests.test_benchmark_runtime_transport -v
```

Genuine warm-session A11 stage profile (one trial):

```powershell
python tests/performance02_lab.py --a11 --mode direct --trials 1
```

The A11 command is bounded by the inherited build, startup, request and cleanup
deadlines. Use `--trials 3` or more for a spread; do not treat one local sample as
a stable performance claim.

## Slice 1 and Slice 2 disposition

The harness foundation is safe to extend because it is external and test-only.
The measured A11 route is the authority for available compiler-stage evidence.
The accepted A12 run is a separate disposable checkout and preserves the parser's
exact cursor chain and flattened-node contract.

The real fixed-width A11 campaign (one direct trial per row) measured the current
19,425-byte source as follows:

| width | calls | total ms | response bytes | outcome |
|---:|---:|---:|---:|:---|
| 32 | 1,216 | 5,671.7 | 4,114,973 | correct |
| 64 | 609 | 3,978.8 | 2,938,516 | correct |
| 128 | 305 | 3,165.9 | 2,349,319 | correct |
| 256 | 153 | 2,742.1 | 2,054,715 | correct |
| 512 | 77 | 2,506.5 | 1,907,379 | correct for A11; punctuation case hit `PEP_RUNTIME_STEP_LIMIT` |

The local representation fixture shows the direction of transport scaling, not a
wire-format recommendation. At eight nodes, existing typed JSON was 5,344 bytes,
a flat array 1,468 bytes and an interned compact array 368 bytes. At 256 nodes,
the corresponding sizes were 167,619, 45,695 and 9,868 bytes. All three round-trip
through independent decoders and injected parent/span/revision mutations are
rejected by the oracle. Full cursor JSON was 968 bytes; a minimal logical cursor
retaining all resume and authority fields was 318 bytes; an opaque handle was 92
bytes but is design-only and requires trusted lifecycle state.

The fixed/estimated/feedback scheduler is a bounded simulator, not production
batching. It uses only public observations and the unchanged 100,000-step and
1 MiB message limits. Fixed width 256 fails high-density simulated work;
conservative estimated and feedback schedules complete it. An intentionally
optimistic estimator records a bounded failure without committing the batch.
This supports adaptive scheduling as an experiment, but not a production batch
change until real Pep parser/checker workloads are measured.

Next work is session lifecycle and architecture comparison. No production
batching, cursor format, protocol, revision cache or host-state mechanism has
changed.

