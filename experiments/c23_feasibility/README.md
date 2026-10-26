# Pep C23 backend feasibility corpus

This directory is an isolated research corpus for `PEP-C23-RESEARCH-01`.
It is not production Pep runtime code, an emitter, an A14 implementation, or
evidence that Pep has a native backend.

## What is here

- `c23_runtime.h` / `c23_runtime.c`: small C23-mode runtime experiments for
  checked `int64_t`, UTF-8 strings with explicit lengths, records, recursive
  tagged unions, immutable list copies, recursion, loops, and deterministic
  status results.
- `c23_probe.c`: executable representation and runtime proof cases.
- `c23_language_probe.c`: strict C23 language-feature probe. It is deliberately
  separate from the runtime so a compiler can report feature support precisely.
- `build.ps1`: strict `-std=c23` build, discovery and probe driver. It never
  falls back to `c11` or `gnu23`.
- `toolchain_paths.json`: shared known-location manifest used by the driver and
  Python discovery tests.
- `shared_semantics.pep`: pinned Pep oracle fixture for native comparison.
- `compare_semantics.py`: deterministic machine-readable interpreter/native
  comparison.
- `test_feasibility.py`: automated discovery, interpreter-oracle, strict native,
  failure-propagation and sanitizer checks.
- `REPORT.md`: current evidence, rejected alternatives, and the proposed A14
  starting contract.

## Usage

```powershell
.\build.ps1 -Compiler all -Probe
python .\test_feasibility.py -v
python .\compare_semantics.py
```

`build.ps1` returns exit code 2 when a requested compiler is not installed.
That is an explicit environment result, not a successful native proof. An
invoked compiler failure is a separate nonzero result. Use `-Discover` to
report paths and versions without compiling, `PEP_C23_CLANG` or `PEP_C23_GCC`
for explicit paths, and `-Sanitize` for the Clang AddressSanitizer build. On
Windows, run the ASan executable with LLVM's `lib\clang\23\lib\windows`
directory on `PATH`.

The intended native commands are:

```text
clang -std=c23 -Wall -Wextra -Wpedantic -Werror
gcc   -std=c23 -Wall -Wextra -Wpedantic -Werror
```

Clang is the primary compiler and GCC is an independent cross-check, as bound
by Technical Resolution 002. A compiler discovered through a non-standard
path may be selected with `PEP_C23_CLANG` or `PEP_C23_GCC`.
