# PEP-PERFORMANCE-02 compiler pipeline laboratory

Status: Slice 1 measurement foundations on the isolated `exp/pep-performance-02`
branch. This report is experimental evidence only. It does not change Pep
semantics, the JSONL schemas, execution budgets, source cap, revision authority,
or A12/A13/A14 implementation status.

## Scope and evidence boundary

`tests/performance02_lab.py` reuses the accepted R2 session client and lexer
runner for a genuine A11 end-to-end profile. It also contains local-only cursor,
AST, checker and C23-emitter fixtures. The latter are synthetic and are not
measurements of an A12 parser, A13 checker or A14 emitter. The known A12 candidate
`69a47fe77187666bdd045b8dc8a9f633a7dd49d7` remains provisional and is not imported
into this branch.

A disposable worktree pinned to that candidate was independently exercised with
the candidate's own differential test adapter. On the current 19,425-byte A11
source it produced 2,030 flattened nodes through 567 parser continuations,
4,183,287 request bytes and 6,100,090 response bytes. The largest request and
response were 67,408 and 69,118 bytes respectively. This is candidate evidence,
not accepted A12 behavior; the source cap and protocol remained unchanged.

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

## Slice 1 disposition

The harness foundation is safe to extend because it is external and test-only.
The measured A11 route is the authority for available compiler-stage evidence.
Compact transport, adaptive batching, session reuse and parser-specific fixtures
remain the next experimental slices; none is a production recommendation yet.

