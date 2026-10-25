# Bootstrap and current interpreter seed

## Requirements

- PowerShell 7;
- opam; and
- the Pepin-specific OCaml 5.5.2 switch.

The CLI uses the standard opam root unless `PEPIN_OPAM_ROOT` is set to the root containing that switch. The switch is named `pepin-5.5.2`.

## Build and run the OCaml seed
From the repository root:

```powershell
.\pep.ps1 --help
.\pep.ps1 describe --json
.\pep.ps1 check examples/hello.pep --json
.\pep.ps1 run examples/hello.pep
'{"schemaVersion":3,"op":"open","name":"hello","source":"say(\"hello\")\n"}' | .\pep.ps1 session --jsonl
```

`pep.ps1` compiles `pep_ocaml.ml` with `ocamlopt` when the source changes, placing generated files under the ignored `_build/ocaml/` directory. The OCaml seed parses Pep source, checks it into a typed representation, reports holes and diagnostics, and interprets complete checked programs. `run` does not invoke a native Pep code generator.

`session --jsonl` keeps revisioned source snapshots only in the current process. Its request and response contract is schema v3 in [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md); the existing file-oriented commands remain schema v2. Each changed revision is fully parsed and checked, so this feature is not incremental compilation.

Run the OCaml CLI regression suite with:

```powershell
python -m unittest discover -s tests -v
```

The tests in `tests/test_cli.py` exercise the primary OCaml CLI, including session revision and edit behavior. The separate `tests/test_moonbit_cli.py` suite belongs to the historical MoonBit compiler and has its own MoonBit/TinyCC requirements; do not treat it as evidence about the OCaml CLI.
## Bootstrap direction

The primary seed decision is [OCaml 5.5.2](SEED_LANGUAGE.md). Pep remains interpreter-first while its syntax, type system, typed holes, semantic queries, and JSON interface become dependable. The intended native path is a C11 generator written in Pep and compiled by a host C compiler. That generator and a self-hosted compiler do not exist in the current seed.

The former MoonBit `say("text")`-to-C11 implementation is preserved as historical/reference work in `pep-moonbit.ps1`, `HISTORICAL_DESIGN_A0.md`, and the separate MoonBit tests. It is not the current primary bootstrap path. See [Founding Design v0.3](FOUNDING_DESIGN_v0.3.md), [Technical Resolution 001](TECHNICAL_RESOLUTION_001.md), and [implementation status](DESIGN.md) for the canonical direction and feature boundary.
