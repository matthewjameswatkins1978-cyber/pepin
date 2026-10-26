# Pep C23 runtime ABI hardening and benchmark report

Mission: `PEP-C23-ABI-03`  
Accepted research base: `6a41f0e8d62e8fb3d82bb5d6bc13a338bc4762ec`  
Branch: `exp/c23-feasibility`  
Benchmark/comparison slice: `3d027ed4f7174ca898b4c46f1b7109a7eae81022`

## Result

The isolated corpus has compiled and executed strict C23 runtime proofs on
Windows with both the Technical Resolution 002 compiler choices. The runtime
ownership and allocation seam is adversarially exercised, native results are
compared with the current Pep interpreter for comparable cases, and a
repeatable benchmark report is produced. This remains feasibility research:
there is no production A14 emitter, no native Pep compiler claim, and no Pep
language-semantics change.

## Toolchains and portability

Evidence was collected on 2026-10-26 using Windows PowerShell 7.6.9. Both
compilers are user-scoped Scoop installations; no system configuration or
administrator privilege is required.

| Compiler | Executable and actual version | Result |
|---|---|---|
| Clang | `C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe`, LLVM/Clang 23.1.4, target `x86_64-pc-windows-msvc` | strict C23 probe, runtime proof and benchmark pass |
| GCC | `C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe`, MinGW-Builds GCC 16.2.0, `x86_64-posix-seh-rev1` | strict C23 probe, runtime proof and benchmark pass |

The build contract is:

```text
<compiler> -std=c23 -Wall -Wextra -Wpedantic -Werror -O2
```

Discovery order is explicit `PEP_C23_CLANG`/`PEP_C23_GCC` override, PATH, then
the environment-relative `toolchain_paths.json` manifest. A missing compiler
returns `UNAVAILABLE|name` with exit code 2. An invoked compiler failure is a
different nonzero result and is never reported as an unavailable skip.

The language probe confirms C23 mode under both compilers. Clang accepts the
standard named `nullptr_t` typedef from `<stddef.h>`; the current MinGW header
does not, although GCC accepts `nullptr` and `typeof_unqual`. The dedicated
probe records this portability difference rather than hiding it. The shared
corpus uses `typeof_unqual(nullptr)` for the cross-compiler proof.

## Runtime correctness evidence

The runtime proof covers checked signed `int64_t` arithmetic, division by zero
and minimum-integer division, valid UTF-8 with embedded zero bytes, immutable
records, recursive tagged unions, immutable list copies, recursion, loops,
invalid tags, depth-limit and depth-counter overflow, alignment, size
overflow, deterministic allocator failure/recovery and disposal accounting.

All checked operations validate before performing C arithmetic. Allocation
sizes are checked for multiplication/addition overflow and against
`PEP_MAX_ALLOCATION_SIZE`; failed arena growth does not publish a partial
block. Lists carry their allocator, append copies rather than aliases, and
disposal uses the owning allocator. Strings carry `(data, len)` and never
depend on NUL termination. Invalid tags and failure statuses propagate through
explicit `pep_status` values and out parameters.

One real ASan defect was found and fixed: a `SIZE_MAX` arena request reached
the system allocator before the portable allocation guard existed. Clang ASan
is now clean when its LLVM runtime directory is on `PATH`. The installed MinGW
GCC sanitizer build is incomplete: linking `-fsanitize=address` fails because
this installation has no `-lasan`; this is recorded as an unavailable sanitizer
capability, not suppressed.

## Native/interpreter comparison

`compare_semantics.py` emits deterministic JSON for each compiler. It contains
six successful observable rows: expression/record/list values, factorial and
loop summation. It also contains three comparable controlled failures:

| Semantic case | Native status | Pep interpreter diagnostic |
|---|---|---|
| signed integer overflow | `overflow` | `PEP_RUNTIME_OVERFLOW` |
| division by zero | `division_by_zero` | `PEP_RUNTIME_DIVISION_BY_ZERO` |
| recursive call depth | `depth` | `PEP_RUNTIME_CALL_DEPTH` |

Both Clang and GCC have zero comparable counterexamples. Invalid variant tags,
malformed UTF-8 bytes and injected allocator failure are included as explicit
`not_representable` native-only rows because the current Pep surface cannot
express those invalid runtime states or allocator injections. They are not
counted as interpreter equivalence.

## Benchmark evidence

`benchmark_runtime.py --trials 3` performs one warmup and three measured
processes for each of seven cases at three sizes (21 rows per compiler). It
records compiler version, strict flags, compile elapsed time, C23 operation
wall time, separate process wall time, operation count, checksums and arena
reserved capacity. The current report has zero checksum mismatches across both
compilers and all 42 rows.

Representative largest-size medians from the pushed JSON report:

| Case | Size | Clang native ns | GCC native ns | Clang process ns | GCC process ns |
|---|---:|---:|---:|---:|---:|
| arithmetic | 2048 | 4,427,900 | 4,011,300 | 14,280,900 | 13,001,500 |
| record | 64 | 996,400 | 981,900 | 11,015,300 | 9,711,900 |
| union | 64 | 112,600 | 108,500 | 10,061,600 | 10,355,300 |
| arena | 256 | 220,600 | 224,800 | 9,763,100 | 10,328,300 |
| list | 256 | 52,800 | 56,700 | 9,963,400 | 10,218,000 |
| recursive | 64 | 77,300 | 57,400 | 10,104,300 | 10,901,800 |
| UTF-8 | 4096 | 492,100 | 1,501,700 | 10,332,300 | 12,572,400 |

Process startup dominates the small cases. `arena_reserved_bytes` is not RSS,
and no peak RSS claim is made. The benchmark is evidence for representation
trade-offs, not a generated-Pep performance claim.

## Provisional A14 contract

The future emitter should accept only an approved checked AST containing:

1. stable node/statement tags and source spans;
2. resolved binding and call IDs, types and recursion edges;
3. nominal record IDs, ordered fields and checked field types;
4. nominal union and constructor IDs, payload types and exhaustive match trees;
5. homogeneous list element types, including explicit empty-list typing;
6. validated UTF-8 bytes and lengths, never C fragments;
7. explicit checked-error sites for overflow, division and allocation failure;
8. a supported-feature set so unsupported nodes fail before emission.

The runtime ABI candidate is fixed-width values, length-delimited UTF-8,
ordinary structs, explicit union tags, arena-owned immutable recursive graphs,
fresh owned list results, and enumerated status/out-parameter failures. The
emitter must not infer types, lower unsupported nodes silently, use global
mutable state, rely on host allocation behaviour, or emit compiler extensions.

For identical checked input, emitted C23 bytes must be canonical: stable
declaration/helper/field ordering, stable formatting, no timestamps or absolute
paths. Acceptance must compile those bytes with strict Clang and GCC and
compare both executables with the checked interpreter, including deterministic
failures.

## Remaining blockers and next gate

- Decide whether A14 avoids named `nullptr_t` or requires a MinGW header
  baseline that supplies it.
- Define reproducible Windows ASan DLL deployment; GCC sanitizer coverage is
  currently unavailable with this MinGW distribution.
- A13 must supply a reviewed checked-AST topology and ownership contract;
  this corpus does not authorize parser/checker changes.
- Peak RSS, generated C code size and a production emitter remain unmeasured.
- Cross-compiler layout of future emitted records/unions still requires
  generated-artifact tests rather than this standalone runtime corpus.

The next gate is Lucy's independent review of this pushed branch and approval
of the provisional runtime/emitter contract. No merge, master change, packet
pointer update or A15/self-hosting work is requested.

## Evidence receipt

- C23 targeted suite: **19/19 passed**.
- Strict Clang language/runtime/benchmark builds and executions: pass, exit 0.
- Strict GCC language/runtime/benchmark builds and executions: pass, exit 0.
- Clang ASan runtime proof: pass, exit 0, `SUMMARY|failures=0`.
- GCC ASan: incomplete; linker reports missing `-lasan`.
- Native/interpreter comparison: six successes plus three comparable failures
  per compiler, zero comparable counterexamples.
- Benchmark: 42 rows, one warmup plus three trials, zero checksum mismatches.
- Full repository regression: **104/104 passed**, `python -m unittest discover -s tests -v`.
