# Bootstrap and first vertical slice

## Requirements

- MoonBit `moon` on PATH, or installed at `%USERPROFILE%\.moon\bin\moon.exe`.
- The matching bundled `internal\tcc.exe` shipped with that MoonBit toolchain.
- PowerShell 7 and Python 3 for the CLI and integration checks.

## Build the seed compiler

From the repository root:

```powershell
.\pep.ps1 describe --json
```

The wrapper runs `moon build --target native` and creates the MoonBit seed
executable under `_build/native/debug/build/cmd/main/main.exe`. The compiler
contains the lexer, parser, semantic validation, diagnostics, and C generator.

## Compile and run a Pep program

```powershell
.\pep.ps1 check examples/hello.pep
.\pep.ps1 build examples/hello.pep
.\pep.ps1 run examples/hello.pep
```

`build` asks the MoonBit seed for generated C, then invokes the bundled TinyCC
with `-std=c11` and links `runtime/pep_runtime.c`. On Windows the runtime uses Win32 `WriteFile` to preserve UTF-8 and NUL bytes. Generated C and executables
are kept under `_build/pep/`. `run` is the only command that executes the Pep
program.

## Tests

```powershell
& "$env:USERPROFILE\.moon\bin\moon.exe" test --target native
python -m unittest discover -s tests -v
```

The integration tests execute the native Pep program and check line endings,
escapes, deterministic C, diagnostics, and command exit codes.

## Self-hosting work remaining

The seed compiler is written in MoonBit and invokes the host C compiler. A
self-hosted Pep compiler still needs functions, variables, control flow,
complete type checking, a usable module/file model, and enough runtime support
to express the compiler itself. Packet 002 should add functions, variables, and
control flow while retaining this pipeline and its diagnostics.
