# Pep C23 runtime ABI-04 report

Mission: `PEP-C23-ABI-04`  
Branch: `exp/c23-feasibility`  
Scope: isolated C23 runtime and ABI experiments only. This is not an A14
emitter, a native Pep compiler, a language-semantics change, or an A15 step.

## RESULT

The ABI-04 corpus now has compiled, executed evidence for ownership recovery,
independent benchmark oracles, bounded measurement, and a separate-translation-
unit ABI/layout gauntlet. Strict C23 Clang and GCC builds produce equivalent
observable fixture semantics and errors. Per-toolchain artifact sizes and
layout values are recorded without being mistaken for a portable byte-level
ABI. The branch remains an experimental research candidate pending Lucy's
independent review.

## TOOLCHAINS

Evidence was collected on 2026-10-26 with Windows PowerShell 7.6.9.

| Compiler | Installation and version | Strict result |
|---|---|---|
| Clang | `C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe`; LLVM/Clang 23.1.4, target `x86_64-pc-windows-msvc` | C23 language/runtime/benchmark/fixture builds and executions pass |
| GCC | `C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe`; MinGW-Builds GCC 16.2.0, `x86_64-posix-seh-rev1` | C23 language/runtime/benchmark/fixture builds and executions pass |

Every native build uses:

```text
-std=c23 -Wall -Wextra -Wpedantic -Werror -O2
```

Discovery is explicit `PEP_C23_CLANG`/`PEP_C23_GCC` override, PATH, then the
environment-relative manifest. Missing compilers return exit 2 and
`UNAVAILABLE|name`; a found compiler that fails compilation is a different
nonzero result. The MinGW headers still lack the named `nullptr_t` typedef;
the corpus records that gap and uses `typeof_unqual(nullptr)` only in the
cross-compiler probe.

## OWNERSHIP

`pep_i64_list` stores the exact allocate/deallocate/context triple that owns
its items. Disposal with an alternate allocator returns `PEP_ERR_RANGE` and
does not free. Disposal with the stored allocator frees and resets the list.
List constructors reject occupied output objects, preventing accidental
overwrites of a live owner. String construction rejects null output pointers,
and failed UTF-8 validation leaves the output object unchanged.

The separately compiled fixture exercises a valid owner, a same-function but
different-context mismatch, and recovery with the original owner. Both
compilers report `owner_mismatch=range` and `owner_recovery=ok`. The contract
is intentionally strict: callers must retain the owner triple or use the
no-argument disposal wrapper; an arbitrary equivalent-looking allocator is
not sufficient.

## BENCHMARK ORACLES

`benchmark_runtime.py` computes each expected checksum independently in Python,
checks operation count and signed-64-bit range, validates the warmup and every
measured trial, and requires identical observed checksum sequences for Clang
and GCC. Wrong warmup, trial, operation-count, missing-field, malformed-output,
timeout and cross-compiler disagreement negative controls are tested and fail
closed. Trials are bounded to 2..20; build and process execution have separate
deadlines.

The Windows benchmark clock uses `QueryPerformanceCounter` with checked
conversion to nanoseconds. The non-Windows fallback is explicitly reported as
`timespec_get_utc`; it is not presented as a monotonic guarantee. Benchmark
operation totals use the checked runtime arithmetic helpers where signed
overflow is possible. The report records operation time separately from
process startup time and records arena reserved capacity, not peak RSS.

## ARTIFACTS

`abi_fixture.py` builds and runs three separately compiled translation units:

1. `c23_runtime.c` provides the isolated runtime;
2. `fixtures/abi_fixture_module.c` owns record, recursive union, list, UTF-8,
   checked-error and allocator cases;
3. `fixtures/abi_fixture_main.c` is an independent caller that validates
   layout invariants and prints the machine-readable receipt.

The current receipt has schema 1, `separate_translation_units=true`, semantic
and error equality true, and records object/executable byte sizes. On this
Windows run the Clang fixture executable was 155,648 bytes and GCC's was
64,429 bytes. Runtime and fixture object sizes are also retained in the JSON
receipt. These are useful implementation measurements, not generated-Pep
size claims or cross-compiler ABI requirements.

## ABI GAUNTLET

The fixture proves across independently compiled boundaries:

- fixed-width `int64_t` record fields and field offsets;
- a recursive tagged union with explicit tag dispatch and invalid-tag failure;
- function calls returning a status plus an out-parameter report;
- embedded NUL bytes in a length-delimited UTF-8 value;
- checked overflow and deterministic allocator-owner mismatch/recovery.

Both compilers reported `point_sum=42`, `tree_sum=42`, `list_sum=49`,
`utf8_len=3`, `overflow=overflow`, `invalid_tag=invalid_variant`,
`owner_mismatch=range`, and `owner_recovery=ok`. Both independently reported
`point_size=16`, `point_align=8`, `point_y_offset=8`, `tree_size=24`,
`tree_align=8`, and `tree_payload_offset=8` on this host. The acceptance rule
does not require those numeric values to remain universal: the emitter must
avoid depending on undocumented padding and the generated program must be
checked under each target compiler.

## A14 STARTING CONTRACT

The future emitter may consume only a reviewed checked-AST contract containing:

1. stable node/statement tags, source spans, and resolved binding/call IDs;
2. checked scalar and nominal record/union/list types, ordered fields and
   constructor IDs;
3. exhaustive checked match trees and explicit recursion edges;
4. validated UTF-8 byte spans and lengths, never C fragments;
5. explicit checked-error sites for overflow, division, allocation, invalid
   variant and depth failures;
6. an explicit supported-feature set and deterministic unsupported-feature
   diagnostic boundary;
7. ownership/lifetime annotations sufficient to decide borrowed versus owned
   string/list/recursive values without emitter inference.

The runtime model is fixed-width values, length-delimited strings, ordinary
structs, explicit tagged unions, arena-owned recursive graphs, fresh immutable
list results, allocator identity carried with owned storage, and enumerated
status/out-parameter failures. A14 must fail closed before emitting C23 when
the checked AST omits any required identity, type, ownership or support fact.

For identical checked input, output bytes must be canonical: stable helper,
declaration, field and case ordering; stable formatting; no timestamps,
absolute paths, host addresses or incidental compiler output. The runtime may
be statically embedded or linked from a version-pinned support object, but the
choice must be deterministic and include an ABI version constant. Generated
artifacts are accepted only after strict Clang and GCC compilation, execution,
and checked-interpreter comparison.

## A13 DEPENDENCIES

This corpus does not define the A13 checked AST. A13 must review and provide
the node topology, nominal identity, ownership annotations, error sites and
unsupported-feature set above. The current parser/flat AST observations are
not sufficient evidence for emitter consumption. The fixture is a contract
test candidate, not permission to change A12 or A13.

## SANITIZERS AND HAZARDS

Clang AddressSanitizer passes when LLVM's `lib\windows` runtime directory is
on `PATH`. GCC AddressSanitizer remains incomplete: this MinGW installation's
linker reports `cannot find -lasan`. That is a toolchain limitation, not a
suppressed test. Remaining hazards include target-specific allocator and
linker behavior, portable object layout/padding, recursion depth/stack limits,
and the absence of a generated-artifact differential test.

## TEST RECEIPT

- ABI-04 focused suite: 22/22 passed, including separate-TU fixture tests.
- Strict Clang and GCC language/runtime/benchmark builds: pass, exit 0.
- Strict Clang and GCC separate-TU fixture builds: pass, exit 0.
- Fixture semantic/error comparison: equal; layout checked per compiler.
- Clang ASan runtime proof: pass, exit 0, `SUMMARY|failures=0`.
- GCC ASan: incomplete, linker lacks `-lasan`.
- Interpreter/native comparison: six successes plus three comparable failures
  per compiler, with zero comparable counterexamples; native-only invalid
  states remain explicitly non-comparable.
- Full repository regression is required at the final consequential boundary
  and is reported in the final mission receipt.

## NEXT GATE

Lucy should independently review the pushed ABI-04 slice and the generated
fixture/benchmark receipts. The next acceptance gate is a checked-AST fixture
with canonical generated C23 bytes, strict dual-compiler execution, and
interpreter equivalence. No production emitter, merge, master change,
milestone update, or A15 self-hosting work is authorized by this report.
