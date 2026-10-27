# PEP-PERFORMANCE-02 compiler pipeline laboratory

Status: PEP-PERFORMANCE-02-R1 evidence-integrity and reliable-measurement receipt on the isolated `exp/pep-performance-02`
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

### R1 provenance ledger

The measured harness revision was `794c93b522911479dd373ea2dcceb87a7ee63408` on
`exp/pep-performance-02`; the final report-only receipt commit follows it. The
A11 workload was `examples/pep_lexer.pep`, 19,425 bytes,
`sha256:729e01acdbbb538ef6578220c69e9fb62881874fcc0ae592735051d089587c46`.
The direct profile executable was `_build/perf/pep-profile.exe`,
`sha256:e88c41b8fb3dbf84b34ce33cc897d90383a567ca03aac63042ca5b851c5713dc`,
built from `pep_ocaml.ml` source SHA
`8372fdcd9f5f60c58e3abafb9ee806148f7255023fb2a21ed417c6a90c7bbc06` with the
existing profile-build path. Clock sources were Python
`time.perf_counter_ns` and isolated OCaml `Unix.gettimeofday`; direct A11 used
one verified profile trial and PowerShell one host-only trial. The result oracle
was the existing test-only OCaml differential machinery; the AST oracle used 54
synthetic corruption outcomes. Limits remained 100,000 tool steps, 1 MiB tool
messages, 65,536 source bytes and the stated lifecycle campaign caps. These
measurements include host/process/JSONL costs where labelled; internal phase
attribution overlaps response wait, and typed construction, allocation behaviour
and exact CPU-vs-wall attribution remain limitations.

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

Each decoder is checked by an independent structural validator and then against a separately retained expected fixture. R1 corrupts the serialized bytes themselves: 18 mutations across all three representations (54 cases) cover parent/cycle/ID/order/child-index/role/span/revision/type/field/string-table/row-length/truncation/schema/value failures. Rejection is classified as decode error, structural invalidity, revision mismatch or reference-equivalence mismatch. A changed value is intentionally structurally valid but is rejected by the independent reference oracle. Cursor fixtures compare the full typed `LexCursor`, a minimal logical representation retaining all resume and authority fields, and an opaque-handle design-only simulator. The opaque form is not an authenticated certificate and does not add host-held production state.

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

Session lifecycle and architecture evidence:

```powershell
python tests/performance02_lab.py --lifecycle --lifecycle-count 8 --lifecycle-invokes 4 --lifecycle-cold-trials 2
python tests/performance02_lab.py --architecture
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
through independent decoders. The earlier R2 mutation controls only showed
that logical fixture differences were observable; the R1 serialized-corruption
corpus and independent validator now provide the rejection evidence. Full cursor JSON was 968 bytes; a minimal logical cursor
retaining all resume and authority fields was 318 bytes; an opaque handle was 92
bytes but is design-only and requires trusted lifecycle state.

The fixed/estimated/feedback scheduler is a bounded simulator, not production
batching. It uses only public observations and the unchanged 100,000-step and
1 MiB message limits. Fixed width 256 fails high-density simulated work;
conservative estimated and feedback schedules complete it. An intentionally
optimistic estimator records a bounded failure without committing the batch.
This supports adaptive scheduling as an experiment, but not a production batch
change until real Pep parser/checker workloads are measured.

## Slice 3 lifecycle and architecture evidence

The historical typed-result session measurement is preserved: two cold trials and one reused session containing four invocations had cold setup median 55.871 ms, cold invocation median 6.353 ms, process spawn 3.818 ms, ready 56.251 ms, setup 55.596 ms and warm invocation median 6.283 ms. Peak private memory was 7,639,040 bytes. These values remain directional because Windows process accounting is sampled.

R1 now verifies the live lifecycle rather than recording only informative booleans. A genuine direct session with count 2, one warm invoke and one cold trial matched source-derived initial, edit and recovery SHA-256 revisions; the stale write returned exact `PEP_STALE_REVISION`, a recovery query proved observable state unchanged, and a current-revision recovery edit/read succeeded. The verifier fails closed on failed edits, unchanged revisions, accepted stale writes, wrong stale codes, stale state mutation and failed recovery. Campaign limits are 64 generated items, 32 warm invokes, 8 cold trials and the unchanged 65,536-byte source cap.

The architecture comparison keeps evidence and design separate:

| model | round trips | response bytes | trust | status |
|---|---:|---:|:---|:---|
| separated A11 + A12 tools | 1,783 | 10,215,063 | low | measured components only |
| composed Pep invocation | 567 | 6,100,090 | low | supported direction; checker/emitter not implemented |
| hybrid retained host state | 567 | 1,525,022 estimated | high | design-only fixture ratio; no host state |

The composed row uses the accepted disposable A12 measurement and the measured
A11/A12 call counts; it is not a claim that a Pep-written checker or emitter
already exists. The hybrid row applies the local compact-fixture ratio only and
must not be read as a production transport forecast.

### R1 profile and output-integrity evidence

Direct profile requests are `verified` only when records are nonempty, identify a tool, contain finite nonnegative timing and count fields, report positive steps, and carry a fresh profile executable/source identity. A direct A11 run produced 1,216 profile records and 4,172,856 steps; the isolated profile executable was identified by SHA-256 and the OCaml source SHA. PowerShell remains explicitly `unavailable-host-only` with `internalProfile: null`; it is never represented as measured zero internal timing. Missing, truncated, negative, nonnumeric, zero-step, inconsistent-count, stale-identity and incompatible-workload controls fail closed.

Every A11 trial is compared to the existing test-only OCaml differential oracle for token kind/value, byte spans, line, column and diagnostics. The direct and PowerShell A11 smoke runs both returned 3,605 tokens with no error and `correctness.status: verified`. Token value, offset, missing-token and diagnostic-code mutations are rejected by the oracle.

## Bottleneck attribution and recommendations

The measured A11 sample attributes 5,610.7 ms to host response waiting out of
6,087.3 ms host elapsed. The internal elapsed profile was 489.7 ms: 237.5 ms
interpreter execution including typed construction, 177.1 ms result encoding,
56.1 ms revision/grant work, 10.5 ms request decode and 8.5 ms formatting. The
host ledger and internal ledger overlap while the host waits, so these values
are not additive CPU percentages. The dominant practical cost is repeated
transport and response serialization, with interpreter dispatch and typed
construction second in this sample. Typed construction is not separately
instrumented; that remains an uncertainty. The typed-result boundary check at
count 256 observed 1,027,410 setup-response bytes and 144,580 invocation-response
bytes, preserving the existing response boundary rather than changing it.

Ranked decisions:

1. Prefer one bounded composed Pep invocation across adjacent compiler stages
   where the language contract permits it. This removes measured continuation
   boundaries while retaining explicit revisions, diagnostics and typed values.
2. Keep continuation work bounded and introduce conservative feedback batching
   only after real A12/A13 workloads exist. The simulator shows fixed width 256
   failing high-density work, while conservative estimated and feedback plans
   complete; an optimistic estimate fails closed without committing the batch.
3. Investigate a flat/interned typed-result representation at a reviewed
   protocol boundary. Local fixtures reduced 167,619 typed bytes at 256 nodes
   to 45,695 flat bytes and 9,868 compact bytes, while independent decoders and
   topology/span/revision mutation oracles preserved meaning. Do not change the
   current wire schema in this mission.
4. Do not adopt opaque cursor handles or host-retained hybrid state now. They
   save bytes in the fixture but add authenticated lifecycle state, trust and
   recovery complexity and have not been measured in a real compiler stage.

No production batching, cursor format, protocol, revision cache, host-state
mechanism, interpreter budget, source cap, A12 file or A13 file changed.

### Architecture decision record

| candidate | measured gain/evidence | complexity and risk | compatibility / decision |
|---|---|---|---|
| composed bounded stage invocation | removes measured continuation boundaries; A12 accepted run is 567 calls versus 1,216 A11 lexer calls | medium; must preserve revision, diagnostics and typed-value boundaries | compatible direction for A12/A13; pursue at a reviewed stage boundary |
| conservative adaptive batches | fixed-width simulator fails dense work while estimated/feedback completes within unchanged limits | medium; estimator drift must fail before commit | compatible as test-only planning now; require real A12/A13 workload proof before landing |
| compact immutable node/result representation | local 256-node fixture falls from 167,619 typed bytes to 9,868 compact bytes | high; schema, tooling and debugging compatibility risk | experiment only; independent review and a versioned protocol decision required |
| opaque cursor or retained host state | 92-byte design-only cursor versus 968-byte full cursor | high trust/lifecycle/recovery complexity; no production measurement | reject for now; conflicts with transparent revision-authority boundary |

The simplest integration recommendation is therefore composed, explicitly bounded
Pep-written stages with conservative adaptive scheduling at internal boundaries,
while retaining explicit document/revision identity and independently checkable
results. Compact transport remains a separately reviewed future option; opaque
host state is not recommended.

## Verification receipt

R1 focused performance-lab suite: 23/23. Serialized AST self-test: 54/54
corruptions rejected across three representations with all four oracle classes.
Lifecycle negative controls: 7/7 rejected; a genuine direct lifecycle smoke
verified stale rejection and recovery. Direct A11 profile smoke: verified
profile status, 1,216 records, 4,172,856 steps and independent OCaml output
correctness. PowerShell A11 smoke: `unavailable-host-only`, `internalProfile:
null`, and independent output correctness verified. The current full-repository
receipt is 128/128, including A11 differential 7/7 and the accepted A12 disposable
checkout evidence 22/22 at SHA `69a47fe77187666bdd045b8dc8a9f633a7dd49d7`; these are
preserved prior evidence, not silently replaced by R1 harness tests. Width 128
and 256 matched the width-32 reference, while width-512 punctuation remained a
classified `PEP_RUNTIME_STEP_LIMIT`. The typed-result boundary evidence remains
1,027,410 setup-response bytes and 144,580 invocation response bytes. `python
-m py_compile` and `git diff --check` passed. No production compiler semantics,
protocol schema, budgets, source cap, A12 files or A13 files changed.

