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
- `build.ps1`: strict `-std=c23` build and probe driver. It never falls back to
  `c11` or `gnu23`.
- `test_feasibility.py`: automated interpreter-oracle checks and native proof
  checks when a supported compiler is installed.
- `REPORT.md`: current evidence, rejected alternatives, and the proposed A14
  starting contract.

## Usage

```powershell
.\build.ps1 -Compiler all -Probe
python .\test_feasibility.py -v
```

`build.ps1` returns exit code 2 when a requested compiler is not installed.
That is an explicit environment result, not a successful native proof. The
Python test suite skips native execution in that case and still runs the
interpreter comparison and corpus-policy checks.

The intended native commands are:

```text
clang -std=c23 -Wall -Wextra -Wpedantic -Werror
gcc   -std=c23 -Wall -Wextra -Wpedantic -Werror
```

Clang is the primary compiler and GCC is an independent cross-check, as bound
by Technical Resolution 002. A compiler discovered through a non-standard
path may be selected with `PEP_C23_CLANG` or `PEP_C23_GCC`.
