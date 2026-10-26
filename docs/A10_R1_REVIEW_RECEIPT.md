# A10-R1 review receipt

**Status:** repair candidate for Lucy's review; not A10 acceptance. This receipt does not advance `CURRENT.md` or the packet manifest.

## Raw-byte contract

Pep `Str` remains valid UTF-8 text. `SourceBytes` is a compiler-known opaque value used for retained source snapshots. `source_bytes() -> SourceBytes` is available only in a v2 host-authorised invocation with an exact `semanticTarget`; it does not look up documents or access files. `byte_length` and unsigned `byte_at` inspect it. `byte_slice` copies any checked half-open byte range and may split a UTF-8 sequence. `utf8_slice` is the explicit conversion to `Str`: it checks range, UTF-8 boundaries, and encoding, and reports `PEP_RUNTIME_BYTE_RANGE`, `PEP_RUNTIME_BYTE_BOUNDARY`, or `PEP_RUNTIME_INVALID_UTF8`.

Raw bytes cannot be coerced to `Str`, compared as scalar values, passed as tool arguments, returned as tool results, or nested in a transportable record/list. Local Pep records and lists may hold the opaque value. Existing Str result validation remains in place. Protocol v1 and v2 schemas are unchanged.

## Revision evidence

`tests/test_a10.py` now invokes the Pep-written lexer against an original document, edits that document, and invokes the retained old and current revisions. It checks each revision's SHA-256 identity, exact original token lexemes and half-open byte spans, and keeps the immutable tool-source revision separate from the inspected target revision. Stale mutation, unknown document, unknown revision, and missing host grant are rejected; a subsequent invocation proves the earlier revision remains available.

## Runtime evidence

Measurements were taken on the Windows development host after compiler build. Each invocation ran in an already-open JSONL session after tool registration, validation, and activation. For each data point, three fresh sessions were used and only the `tool_invoke` round trip was timed. Inputs were ASCII `name ` repeated N times (5N source bytes, N identifiers plus EOF). The scalar-result mode calls the same Pep lexer, constructs the same token records using `prepend` and `reverse`, and returns only `length(tokens)`. The typed-result mode returns the full `LexReport` and token list. The elapsed interval includes interpreter execution, response construction/JSONL output, and pipe read; setup and process startup are excluded.

| Tokens | Source bytes | Scalar-result median | Typed-result median | Typed response bytes | Outcome |
|---:|---:|---:|---:|---:|---|
| 17 | 80 | 0.254 ms | 0.816 ms | 6,886 | success |
| 65 | 320 | 0.730 ms | 2.116 ms | 24,205 | success |
| 129 | 640 | 1.152 ms | 4.194 ms | 47,309 | success |
| 193 | 960 | 1.915 ms | 5.670 ms | 70,413 | success |
| 241 | 1,200 | 2.349 ms | 8.050 ms | 87,864 | success |
| 257 | 1,280 | step limit | step limit | 243-byte error response | `PEP_RUNTIME_STEP_LIMIT` |
| 321 | 1,600 | step limit | step limit | 243-byte error response | `PEP_RUNTIME_STEP_LIMIT` |

Three samples per cell; medians shown. The scalar result provides a practical estimate for Pep UTF-8 validation, scanning, token construction, list operations, and interpreter execution without transporting the token tree. The gap to the typed result includes typed-tree encoding and larger JSONL transport; it is not a pure serializer benchmark. Validation, scanning, and token/list costs were not individually instrumented, so this evidence does not assign exact per-phase costs.

Nine process-start samples after build measured the compiled OCaml executable's `describe --json` at 17.259 ms median (16.043–18.540 ms). The PowerShell launcher plus the same command measured 524.819 ms median (509.041–835.717 ms). These are process-start measurements, not warm-session request latency. Peak memory and separate UTF-8 validator timings were not measured.

## Demonstrated boundary and A11 implications

The repeated-identifier workload completed at 241 tokens / 1,200 bytes and exhausted the unchanged 100,000-step tool budget at 257 tokens / 1,280 bytes. This is the currently demonstrated practical envelope for this workload, not a universal maximum: token shapes and error paths consume different numbers of interpreter steps. `open_bytes`'s 65,536-byte cap is an input transport ceiling, not a promise that the Pep interpreter can scan that many bytes.

The observed work follows the intended bounded construction: O(1) `prepend`, one O(n) `reverse`, and typed-result costs proportional to the emitted tree. No measured evidence justified changing that strategy or increasing runtime budgets. Larger-file support belongs at a separately reviewed A11 gate: measure a complete lexer against the OCaml oracle, choose an execution strategy that fits realistic files under explicit resource accounting, and retain deterministic step-limit failure. A10 does not claim a complete lexer, arbitrary-size source processing, or a native/self-hosted compiler.
