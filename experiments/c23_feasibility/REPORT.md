# Pep C23 backend feasibility report

Mission: `PEP-C23-RESEARCH-01`
Baseline: reviewed A11 SHA `3fb83b7fb9eeb82674f12b021b1f21f2d677c795`
Branch: `exp/c23-feasibility`

## Result in one sentence

The proposed representation is technically implementable as a small portable
C23-mode runtime, but this Windows checkout has no installed Clang or GCC, so
native compilation, Windows ABI validation, cross-compiler agreement, code-size
measurement, and runtime benchmarking remain open acceptance work.

This branch contains experiments only. It does not implement A14, a Pep-written
emitter, a native backend, or a language-semantics change.

## Toolchain reality

The local checks were made on 2026-10-26 from PowerShell 7.6.9. Neither compiler
was callable from PATH. The following bounded installation locations were also
absent:

| Candidate | Result |
|---|---|
| `clang` | unavailable |
| `gcc` | unavailable |
| `clang-cl` / MSVC `cl` | unavailable |
| MSYS2 `C:\msys64\clang64\bin\clang.exe` | absent |
| MSYS2 `C:\msys64\clang64\bin\gcc.exe` | absent |
| LLVM `C:\Program Files\LLVM\bin\clang.exe` | absent |
| Visual Studio LLVM path | absent |
| TinyCC / Zig | unavailable |
| Docker Linux engine | daemon unavailable |
| WSL Ubuntu | installed but stopped |

Consequently there is no truthful local `clang --version`, `gcc --version`,
`-std=c23` feature result, executable, or native output to report. The build
driver records this explicitly as `UNAVAILABLE|clang`, `UNAVAILABLE|gcc` and
returns exit code 2. It never substitutes `c11` or `gnu23`.

The next toolchain gate must use the actual installed MSYS2 CLANG64 or another
verified Windows-compatible C23 toolchain, with Clang primary and GCC as the
independent cross-check, exactly as required by Technical Resolution 002.

## Corpus and representation findings

The isolated source in this directory covers the following candidate ABI:

| Pep value/operation | Experiment | Current disposition |
|---|---|---|
| `Int` | fixed-width `int64_t` plus checked add/sub/mul/div/neg | recommended |
| `Bool` | standard `bool` | recommended |
| `Unit` | explicit one-byte value object | recommended; avoid zero-size extensions |
| `Str` | `{ const unsigned char *data; size_t len; }` with strict UTF-8 validation | recommended |
| immutable record | ordinary C struct passed/read through `const` APIs | recommended for emitted value records |
| recursive union | tag plus union payload, arena-owned immutable graph | recommended starting model |
| homogeneous list | owned element array with explicit length; append copies input | recommended baseline |
| calls/recursion | ordinary C calls with checked recursive depth | recommended with depth/error policy |
| pattern matching | `switch` over a closed tag enum, invalid tags rejected | recommended |
| loops/control flow | ordinary `for`/`while` with checked arithmetic | recommended |
| failure propagation | explicit `pep_status` and out parameters | recommended; deterministic |

The C23 language probe intentionally tests C23 `constexpr`, `static_assert`,
`nullptr`, `typeof_unqual`, and standard alignment. It is separate from the
runtime probe so a compiler can report feature support independently. It has not
been compiled on this host.

## Runtime hazards addressed

- Signed overflow is checked before every arithmetic operation; the minimum
  integer divided by `-1` and negated minimum integer are explicit overflow
  cases.
- Division by zero is a status, never a C operation.
- UTF-8 is validated from byte ranges and rejects overlong encodings,
  surrogates, out-of-range code points, and truncated sequences.
- Strings carry a byte length, so embedded zero bytes do not truncate values.
- Recursive values use arena blocks with stable addresses and one explicit
  disposal point; no recursive destructor or ownership cycle is required for
  the immutable expression experiment.
- List append allocates a fresh array and leaves the input array unchanged.
- Allocation-size multiplication and arena capacity growth are checked before
  allocation.
- Every runtime failure is an enumerated status rather than `errno`, an
  assertion, an uninitialised output, or compiler-specific exception behaviour.
- The runtime uses fixed-width integer types and standard-library facilities;
  it does not use Windows APIs, compiler intrinsics, tagged pointers, NaN
  boxing, or unportable `long` width assumptions.

These are source-level design proofs until the same files pass strict Clang and
GCC builds and executable tests.

## Rejected approaches

1. **NUL-terminated `char *` strings:** rejected because Pep strings and source
   bytes may contain embedded zero bytes and require exact byte lengths.
2. **C `long` for Pep `Int`:** rejected because its width is ABI-dependent on
   Windows and other hosts; `int64_t` is the semantic contract.
3. **Raw untagged C unions:** rejected because they make an invalid constructor
   state indistinguishable from a valid value and make pattern-match failure
   nondeterministic.
4. **Tagged pointers or NaN boxing:** rejected for the first backend because
   they add alignment, provenance, representation, and sanitiser hazards
   without a demonstrated need in Pep's current checked value set.
5. **Tracing GC or reference counting:** deferred. Immutable records, lists and
   recursive values can use explicit arena ownership in the first ABI; GC would
   add a second runtime policy before Pep has a measured lifetime requirement.
6. **`assert`, `abort`, or ambient `errno`:** rejected as the semantic error
   channel because they do not provide deterministic Pep diagnostics or
   composable failure propagation.

## Interpreter comparison

The current OCaml interpreter is the semantic oracle. The repository's pinned
examples produced these exact outputs during this mission:

| Pep source | Output |
|---|---|
| `examples/hello.pep` | `Hello, Pep!` |
| `examples/point_sum.pep` | `42` |
| `examples/recursive_expr.pep` | `42` |
| `examples/a6_collections_control.pep` | `42`, `0`, `1`, `17`, `22`, `10`, `0`, `1`, `42` |

The C probe mirrors the same observable cases where the current language has
them: `20 + 22`, a recursive `Add(Number(20), Number(22))`, record field sum,
list sum/append preservation, recursion, loop sum, and controlled arithmetic
errors. No native comparison is claimed because no C compiler was available.

## A14 starting contract

The future Pep-written emitter should receive an approved checked AST containing,
at minimum:

1. stable node tags and source spans for expressions/statements;
2. resolved binding and call IDs, parameter/result types, and recursion edges;
3. nominal record IDs with ordered fields and their checked types;
4. nominal union IDs with ordered constructor IDs, payload types, and an
   exhaustiveness-checked match tree;
5. homogeneous list element types and explicit empty-list typing;
6. string values as validated UTF-8 bytes plus length, not C source fragments;
7. explicit control-flow and error sites, including checked arithmetic and
   division hazards;
8. a declared supported-feature set so unsupported nodes produce a structured
   diagnostic before any C text is emitted.

The emitter/runtime boundary should expose a small status-returning ABI based on
`int64_t`, `bool`, an explicit Unit value, length-delimited UTF-8 strings,
by-value records, tagged unions with a documented ownership policy, and
homogeneous list operations. The first ownership policy should be arena-backed
immutable recursive values plus fresh owned list results; the emitter must not
silently rely on C global state or host-specific allocation behaviour.

Generated C must be canonical for identical checked input: stable declaration
and field order, stable helper names, stable formatting, no timestamps, no
absolute paths, and no compiler-specific extensions. Acceptance must compile
the same generated bytes with strict `-std=c23` Clang and GCC and compare both
executables with the checked interpreter, including deterministic error cases.

## Next acceptance gate

Install or expose a verified Windows-compatible C23 toolchain and rerun:

```powershell
.\experiments\c23_feasibility\build.ps1 -Compiler all -Probe
python -m unittest discover -s tests -v
```

The gate passes only when both language and runtime probes compile with their
reported compilers under `-std=c23 -Wall -Wextra -Wpedantic -Werror`, the runtime
probe exits with `SUMMARY|failures=0` under both compilers, the feature probe
reports the required C23 facilities, and the output is compared against the
interpreter oracle. Only after that evidence should A14 review decide whether
the ABI is sufficient for an emitter implementation.
