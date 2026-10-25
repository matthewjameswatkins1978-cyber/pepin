# Pep

Pep is a small, statically typed, AI-first programming language intended to become self-hosting. Its canonical v0.3 vision is [Founding Design v0.3](docs/FOUNDING_DESIGN_v0.3.md), and binding technical decisions are in [Technical Resolution 001](docs/TECHNICAL_RESOLUTION_001.md). These design documents include planned capabilities; they are not a claim that those features are implemented.

The primary compiler seed is OCaml 5.5.2. Pep source is ordinary plaintext `.pep` files. The current seed is a small interpreter with types `Int`, `Bool`, `Str`, and `Unit`, functions, lexical scopes, integer operations, conditionals, built-in calls, and typed or unconstrained holes. Its exact limits are in [the seed-language note](docs/SEED_LANGUAGE.md) and [the implementation-status index](docs/DESIGN.md).

## Build, inspect, check, and run

Requirements: PowerShell 7, opam, and the Pepin-specific OCaml 5.5.2 switch. By default the CLI uses the standard opam root; set `PEPIN_OPAM_ROOT` if the switch is installed in another root.

```powershell
.\pep.ps1 --help
.\pep.ps1 describe --json
.\pep.ps1 inspect examples/hello.pep --json
.\pep.ps1 check examples/hello.pep --json
.\pep.ps1 query examples/hello.pep --holes --json
.\pep.ps1 run examples/hello.pep
python -m unittest discover -s tests -v
```

`inspect` returns a source-spanned AST. `check` returns the checked tree and hole information. `query` selects holes and compatible in-scope bindings; `--offset` accepts an original UTF-8 byte offset. `run` executes only complete, successfully checked programs. `describe --json` reports implemented capabilities only.

## Design and history

- [Founding Design v0.3](docs/FOUNDING_DESIGN_v0.3.md): language vision.
- [Technical Resolution 001](docs/TECHNICAL_RESOLUTION_001.md): binding technical decisions and acceptance requirements.
- [Implementation status](docs/DESIGN.md): what is implemented versus planned.
- [Seed-language decision](docs/SEED_LANGUAGE.md): OCaml seed choice and current limits.
- [Next implementation packet](docs/NEXT_PACKET.md): revision-aware document analysis work.
- [Historical A0 MoonBit design](docs/HISTORICAL_DESIGN_A0.md): retained prototype record; not the primary compiler feature list.

The original MoonBit compiler remains available as `pep-moonbit.ps1` with its separate tests for historical/reference use. The current bootstrap instructions are in [BOOTSTRAP.md](docs/BOOTSTRAP.md).
