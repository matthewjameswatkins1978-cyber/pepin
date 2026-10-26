# PEP-PERFORMANCE-01 runtime and transport laboratory

Status: experimental evidence on the reviewed A11 base. This report does not change the packet state, protocol schema, runtime budgets, or A12 files.

## Reproduction

Checkout: `exp/session-performance-lab`, base `3fb83b7fb9eeb82674f12b021b1f21f2d677c795`.

Build and smoke check:

```powershell
pwsh -NoProfile -File .\pep.ps1 describe --json
python -m py_compile tests/benchmark_runtime_transport.py
python -m unittest tests.test_a11 -v
```

The lab harness is test-only and emits one JSON object per measurement:

```powershell
python tests/benchmark_runtime_transport.py --modes direct,powershell --trials 3 --chunk-widths 16,32,64,128,256,512
```

It measures request encoding, pipe write/flush, response read, Python JSON parsing, bytes, process memory samples and process creation. `PEP_PROFILE=1` is opt-in. The harness drains diagnostic stderr continuously so profiling cannot block on a full pipe. Generated inputs and the high-resolution profile executable are under ignored `_build/`.

## Current baseline

The live A11 lexer source is 19,425 CRLF bytes and returns 3,605 normalized tokens. The old A11 receipt's 18,696-byte source and 1,169-call result are historical and are not used here. The current width-32 route makes 1,216 session requests, sends 1,555,051 request bytes and receives 4,114,973 response bytes.

For one direct run, the A11 request group took 5,628 ms, of which 5,492 ms was waiting for session responses and 77 ms was Python JSON parsing. A repeated profiled run took 5,695 ms. This is warm-session execution; process creation was sampled separately at about 7 ms for the direct executable.

The PowerShell wrapper returned the same A8 and A11 results. In one A8 run, process creation was 283 ms and the first `open` response took 37 ms; in the A11 run the measured first-process startup varied, so wrapper startup must be reported as a distribution rather than a fixed constant. The wrapper's sampled working set/private bytes were about 96/34 MB, compared with about 15/11 MB for the direct executable. These are process samples, not allocator or OS peak proofs.

## Chunk-width experiment

The harness makes isolated in-memory variants of the A11 lexer source. Only the internal `while` bound and reset value change; the protocol and budgets remain unchanged. Every successful variant was compared with the width-32 normalized result.

| width | A11 calls | A11 median total | A11 median read | response bytes | correctness |
|---:|---:|---:|---:|---:|:---:|
| 16 | 2,430 | 9,346 ms | 9,082 ms | 6,468,408 | pass |
| 32 | 1,216 | 6,075 ms | 5,893 ms | 4,114,973 | pass |
| 64 | 609 | 4,058 ms | 3,971 ms | 2,938,516 | pass |
| 128 | 305 | 3,121 ms | 3,075 ms | 2,349,319 | pass |
| 256 | 153 | 2,739 ms | 2,692 ms | 2,054,715 | pass |
| 512 | 77 | 2,526 ms | 2,486 ms | 1,907,379 | pass for A11 |

The width-512 punctuation-dense case (`b'+,' * 2048`) exceeded the existing 100,000-step tool budget. Width 256 therefore looks like a safer candidate than “always use the largest batch”; width 128–256 is the recommended experiment range. This is a source-locality/batching result, not permission to raise a budget.

## Attribution

The opt-in profile records per-invocation phase boundaries, step count, returned value-node count and encoded result length. The production executable uses `Sys.time`; because that clock is too coarse for many short calls, the harness also builds an isolated profile executable replacing those calls with `Unix.gettimeofday`. Consequently the profile totals below are high-resolution elapsed phase measurements, not certified CPU-cycle measurements.

Across the 1,216 A11 calls, the isolated profile summed approximately:

| phase | elapsed time |
|---|---:|
| argument decode | 8 ms |
| semantic target/grant lookup | 50 ms |
| interpreter execution, including typed-value construction | 203 ms |
| result encoding | 166 ms |
| response-string formatting | 8 ms |
| interpreter steps | 4,172,856 |

The corresponding direct host read/round-trip total was about 5.56 s in that run. The evidence therefore points to repeated session/JSONL request handling, pipe communication and repeated cursor/result transport as the dominant cost, rather than Pep evaluation itself. The profile does not isolate OCaml JSON parsing from other per-call work, and it does not measure write-side host scheduling separately from the response read.

## Typed-result and large-response evidence

The nested result workload constructs `List[Item]`, where each item contains three `Leaf` records. Direct measurements were:

| items | source bytes | validation setup response | setup time | invoke response | invoke time |
|---:|---:|---:|---:|---:|---:|
| 8 | 1,299 | 33,798 | 52 ms | 4,664 | 5.7 ms |
| 32 | 4,963 | 127,910 | 170 ms | 18,072 | 22.6 ms |
| 128 | 20,047 | 511,314 | 655.7 ms | 72,132 | 92.2 ms |
| 256 | 40,527 | 1,027,410 | 1,316 ms | 144,580 | 181.8 ms |

The 256-item validation response crosses the 1 MiB transport boundary while the final invoke response remains below it. That is a concrete reproducer for the distinction between large typed validation data and large final results. PowerShell produced identical values; its setup timing was about 477 ms at eight items and 1,661 ms at 256 items in the sampled runs, with higher process memory.

## Engineering decision

Ranked recommendations:

1. **Safely batch resumable work.** For future lexer/parser components, test a bounded 128–256 unit batch and retain the existing per-invocation step limit. Adapt batch size to work density or return a normal bounded-runtime error; do not increase budgets to make width 512 pass.
2. **Keep parser token consumption inside one Pep invocation.** PARSER's current one-invocation lexer-to-parser boundary directly addresses the measured fixed-call cost. Return bounded flattened data or metadata when the full AST would exceed the message cap; keep metadata-only behaviour opt-in and preserve the default contract.
3. **Reduce redundant cursor and token serialization at a reviewed boundary.** This is the highest-value architecture candidate, but changing v2 transport or typed encoding needs independent protocol review. The measurements do not justify a wire-schema change in this branch.
4. **Treat compact immutable token/AST representations and source-revision locality as follow-up architecture work.** They may reduce bytes and repeated traversal, but this lab has not isolated their gains.
5. **Do not prioritise interpreter dispatch rewrites yet.** The measured execution phase is a small fraction of warm A11 elapsed time. Typed construction and encoding deserve a separate microbenchmark only after round-trip count is reduced.

Safe to land as lab support: the opt-in instrumentation, external harness, generated workload variants and this report. Requiring independent review: production batch-bound changes, protocol/typed-encoding changes, persistent revision reuse, and any budget or transport-cap change.

## R1 reliability hardening

The harness now applies bounded deadlines to process startup, JSONL writes/flushes, response reads, input close and cleanup. Blocking pipe operations run in daemon workers; a deadline expires into SessionTimeout with a phase name, terminates the child, and joins cleanup threads for a bounded interval. Missing, malformed and non-object JSONL responses are SessionProtocolError; a Pep PEP_RUNTIME_STEP_LIMIT response is PepStepBudgetRejected, keeping expected language-level rejection separate from operating-system timeout.

The generated profile executable is rebuilt when any identity changes. _build/perf/pep-profile.json records source SHA-256, generated profile-source SHA-256, opam root, opam switch and ocamlopt version. PEPIN_OPAM_ROOT and PEPIN_OPAM_SWITCH are configurable; no developer-specific root is required by the harness.

Profiling clocks are now called only when PEP_PROFILE=1. A fresh executable produced one profile record for the nested count-8 invocation; the normal executable produced zero profile records. Existing step limits, typed results, protocol output and authority checks are unchanged.

Windows memory calls now declare pointer-width-safe argtypes/restype values and always close successful process handles. Unavailable memory returns null/None; a genuine available zero sample remains zero. Reported values remain sampled working-set/private bytes, never allocator peaks.

R1 gate evidence after the hardening: harness self-tests 8/8; full repository regression 101/101 (including A11 differential 7/7); direct A8 569 ms and PowerShell A8 596 ms in the sampled runs; width 128 A11 3,240 ms, width 256 2,860 ms, and width 512 a classified PEP_RUNTIME_STEP_LIMIT; the 256-item typed boundary remained a 1,027,410-byte setup response and 144,580-byte invocation response.

## Remaining uncertainty

The memory numbers are sampled working-set/private-byte high-water values, not allocator traces. Profile phase totals use a generated executable and wall-clock timestamps. Typed construction is included in execution, not separately attributed. The current harness measures a Windows PowerShell process-creation sample but has no compiler-ready “session ready” handshake, so startup and first-response costs cannot be perfectly separated. No claim is made that a 128 or 256 batch is optimal for A12/A13; it is the measured candidate range on these A11 workloads.
