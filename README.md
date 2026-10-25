# Pep

Pep is a small, statically typed, AI-first language intended to become self-hosting. Its primary compiler seed is OCaml 5.5.2. Pep source remains ordinary plaintext `.pep` files.

## Build, inspect, check, and run

Requirements: PowerShell 7, opam, and the Pepin-specific OCaml 5.5.2 switch. The CLI uses the opam default root; set `PEPIN_OPAM_ROOT` when the switch is stored elsewhere.

```powershell
.\pep.ps1 describe --json
.\pep.ps1 inspect examples/hello.pep --json
.\pep.ps1 check examples/hello.pep --json
.\pep.ps1 run examples/hello.pep
python -m unittest discover -s tests -v
```

Pep supports `Int`, `Bool`, `Str`, and `Unit`, annotated or inferred bindings, `fn` functions with returns and lexical blocks, integer arithmetic, built-in calls, and typed or unconstrained holes. `inspect` returns a source-spanned AST, `check` returns a typed tree and hole information, and `query FILE --holes --json [--offset N]` selects holes by byte offset. `run` executes only complete, successfully checked programs.

The seed decision and original proof-of-concept limits are in [SEED_LANGUAGE.md](docs/SEED_LANGUAGE.md). The semantic-query design packet is in [NEXT_PACKET.md](docs/NEXT_PACKET.md). The original MoonBit compiler is preserved as `pep-moonbit.ps1` with its separate tests for reference.
