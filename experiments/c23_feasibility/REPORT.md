# Pep C23 backend feasibility report

Mission: `PEP-C23-PROOF-02` (continuation of `PEP-C23-RESEARCH-01`)
Reviewed base: `e1df2a2a8b17026848889ecbec8fd932ee7b19eb`
Branch: `exp/c23-feasibility`

## Result

The isolated C23 corpus now has genuine Windows compilation and execution
evidence with Clang and GCC. Both strict builds and both runtime executables
pass. The checked-AST-to-C23 contract remains a proposal for A14; this work
does not implement an emitter, native Pep compiler, A14, or a language change.

## Toolchains and environment

Evidence was collected on 2026-10-26 from Windows PowerShell 7.6.9 in the
repository checkout. Both compilers were installed user-scoped with Scoop;
system configuration and administrator privileges were not used.

| Compiler | Actual executable | Version / target | C23 preprocessor evidence |
|---|---|---|---|
| Clang | `C:\Users\Matmus\scoop\apps\llvm\current\bin\clang.exe` | LLVM/Clang 23.1.4, `x86_64-pc-windows-msvc`, POSIX thread model | `__STDC_VERSION__ 202311L`, `__clang__ 1` |
| GCC | `C:\Users\Matmus\scoop\apps\mingw\current\bin\gcc.exe` | MinGW-Builds GCC 16.2.0, `x86_64-posix-seh-rev1` | `__STDC_VERSION__ 202311L`, `__GNUC__ 16` |

The reproducible strict command is:

```text
<compiler> -std=c23 -Wall -Wextra -Wpedantic -Werror -O2 -I experiments/c23_feasibility c23_runtime.c <probe> -o <output>
```

The driver records the resolved path, version and command. Discovery order is
explicit override (`PEP_C23_CLANG` / `PEP_C23_GCC`), PATH, then the shared
`toolchain_paths.json` known-location manifest. `-Discover` reports availability
without compiling. A missing compiler is `UNAVAILABLE|name` with exit code 2;
an invoked compiler failure is a nonzero failure other than 2.

The C23 language probe compiled and ran under both compilers. It exercises
`constexpr`, `static_assert`, `nullptr`, `typeof_unqual` and standard alignment.
Clang accepts the standard named `nullptr_t` typedef from `<stddef.h>`. The
MinGW GCC headers do not: a direct strict compile rejects `nullptr_t`, although
GCC accepts `nullptr` and `typeof_unqual`. The shared probe therefore uses
`typeof_unqual(nullptr)` so the language feature proof remains cross-compiler,
and this header portability limitation is recorded rather than hidden.

## Native proof results

Both compilers built the language probe and runtime probe with exit code 0.
Both runtime executables returned exit code 0 and printed
`SUMMARY|failures=0`.

The runtime proof covers:

- checked signed 64-bit add, subtract, multiply, divide and negation;
- division by zero and minimum-integer division by `-1`;
- valid UTF-8, embedded NUL bytes and rejection of overlong UTF-8;
- `bool`, explicit Unit and immutable record field access;
- arena-backed recursive tagged unions, recursive evaluation, depth and invalid-tag rejection;
- immutable list copying, append preservation, range checking and overflow-safe allocation sizing;
- recursive factorial overflow and iterative control-flow summation;
- arena alignment against `_Alignof(max_align_t)`.

The deterministic native/interpreter comparator is `compare_semantics.py`. Its
JSON result is true for both compilers, with these six observable rows per
compiler:

```json
{"expression":42,"record":42,"list_original":42,"list_extended":49,"factorial":120,"sum_to":5050}
```

This is an equality comparison of pinned observable values, not a claim that
the current interpreter and C runtime share an implementation or ABI.

Clang AddressSanitizer compilation also succeeds. On Windows the resulting
executable requires LLVM's `clang_rt.asan_dynamic-x86_64.dll` directory on
`PATH`; with that runtime directory supplied, the complete runtime proof exits
0 with no sanitizer report. The missing-DLL first attempt is a deployment
requirement, not a suppressed diagnostic.

## Runtime and portability decisions

| Pep value / operation | Experimental representation | Disposition |
|---|---|---|
| `Int` | `int64_t` with checked operations | Recommended |
| `Bool` | Standard `bool` | Recommended |
| `Unit` | Explicit one-byte object | Recommended; no zero-size extension |
| `Str` | `{ const unsigned char *data; size_t len; }`, strict UTF-8 | Recommended |
| Immutable records | Ordinary C structs, ordered fields | Recommended |
| Recursive unions | Explicit tag plus union payload, arena-owned immutable graph | Recommended starting model |
| Homogeneous lists | Owned element array plus length; append copies | Safe baseline, not a final performance choice |
| Calls and recursion | Ordinary C calls plus checked depth/error propagation | Recommended with explicit limits |
| Pattern matching | `switch` over closed tag enum; invalid tags return status | Recommended |
| Control flow | Ordinary `for` / `while` with checked arithmetic | Recommended |
| Failure | Enumerated `pep_status` and out parameters | Recommended deterministic ABI |

The runtime checks signed overflow before C arithmetic, rejects division hazards,
checks size multiplication and arena growth before allocation, preserves exact
string lengths including embedded zeros, and disposes arena/list ownership at
explicit boundaries. It does not use `long`, Windows APIs, compiler intrinsics,
tagged pointers, NaN boxing, `assert`, `abort`, ambient `errno`, or compiler
extensions.

Rejected or deferred alternatives are NUL-terminated strings, ABI-dependent
`long`, untagged unions, tagged pointers/NaN boxing, and a tracing GC or
reference-counting runtime before Pep has a measured lifetime requirement.

## A14 starting contract

The future Pep-written emitter should consume an approved checked AST containing,
at minimum:

1. stable node and statement tags with source spans;
2. resolved binding IDs, call IDs, parameter/result types and recursion edges;
3. nominal record IDs, ordered fields and checked field types;
4. nominal union IDs, ordered constructor IDs, payload types and the checked,
   exhaustive match tree;
5. homogeneous list element types and explicit empty-list typing;
6. validated UTF-8 string bytes plus length, never C source fragments;
7. explicit control-flow and checked-error sites for overflow and division;
8. a supported-feature set so an unsupported node produces a structured
   diagnostic before C text is emitted.

The runtime boundary should expose the representations above and a documented
ownership model: arena-backed immutable recursive values, fresh owned list
results, and status/out-parameter failure propagation. The checked tree, not
the emitter, owns semantic validation. The emitter must not infer types,
silently lower unsupported features, rely on global mutable state, or depend on
host-specific allocation behaviour.

Identical checked input must produce canonical C23 bytes: stable declaration,
field and helper ordering; stable formatting; no timestamps, absolute paths or
compiler-specific extensions. Acceptance should compile identical generated
bytes with strict Clang and GCC and compare both executables to the checked
interpreter, including deterministic failures.

## Remaining blockers and next gate

- The GCC MinGW distribution's `<stddef.h>` named `nullptr_t` gap needs an A14
  policy decision: avoid the typedef in generated C, or require a toolchain
  header baseline that supplies it. The current corpus avoids the gap without
  weakening `-std=c23`.
- The ASan Windows executable needs an explicit runtime-DLL deployment rule.
- This corpus does not yet measure generated-code size, allocation throughput,
  deep-recursion limits, or a complete checked-AST emitter. Those are A14 work,
  not evidence to invent here.
- Native equivalence currently covers pinned scalar observables; it does not
  prove arbitrary Pep programs or compiler-independent layout of future emitted
  records/unions.

The next acceptance gate is Lucy's independent review of the pushed branch and
the exact evidence below. A14 may begin only after the runtime contract,
unsupported-feature diagnostics and toolchain/header policy are reviewed; no
milestone pointer or master branch change is implied.

## Evidence receipt

- Strict targeted feasibility tests: 15/15 passed.
- Clang language probe: compiled and executed, exit 0.
- Clang runtime proof: compiled and executed, exit 0, `failures=0`.
- GCC language probe: compiled and executed, exit 0.
- GCC runtime proof: compiled and executed, exit 0, `failures=0`.
- Clang ASan runtime proof: compiled and executed with LLVM runtime DLL path,
  exit 0, `failures=0`.
- Native/interpreter JSON comparison: Clang and GCC both `equal=true`.
- Full repository regression suite: required at the final consequential
  boundary; its result must be recorded in the final mission receipt.
