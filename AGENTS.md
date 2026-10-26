# Pep project instructions

Pep is a small, statically typed, AI-first language intended to become self-hosting. The primary seed compiler is `pep_ocaml.ml`, implemented in OCaml 5.5.2. The primary PowerShell 7 CLI is `pep.ps1` and uses the Pepin-specific switch under the default opam root (override with `PEPIN_OPAM_ROOT`).

## Current language boundary

- Pep sources are plaintext `.pep` files.
- Current types are `Int`, `Bool`, `Str`, and `Unit`; syntax includes bindings, `fn` functions, returns, lexical blocks, integer arithmetic, calls, and typed or unconstrained `?` holes. Check implementation and tests before stating exact supported behavior.
- Read `docs/FOUNDING_DESIGN_v0.3.md` and `docs/TECHNICAL_RESOLUTION_001.md` for intended design and binding decisions. Read `docs/SEED_LANGUAGE.md` for current seed facts and `docs/NEXT_PACKET.md` before expanding syntax or document analysis.
- Keep parsing, source-spanned AST construction, type checking, checked-tree execution, and diagnostics as distinct stages.
- A hole is incomplete source with an expected type and visible bindings. The schema-v3 session can preview/apply a scope-qualified named-hole fill at an exact current revision; it checks one expression and the whole candidate through the existing compiler. Diagnostics and fill actions are deterministic JSON. Never claim incremental reuse until it is implemented and measured.
- The MoonBit compiler remains intact as historical/reference work. Its entry point is `pep-moonbit.ps1`; its tests are `tests/test_moonbit_cli.py`. Do not mix its legacy feature inventory into the primary Pep CLI.

## Verification

- Use `.\pep.ps1 inspect FILE --json`, `.\pep.ps1 check FILE --json`, and `.\pep.ps1 run FILE`. Only `run` executes Pep code.
- Use `python -m unittest discover -s tests -v` for the CLI suite.
- Build products and generated test inputs belong under ignored `_build/`.
- Keep `.pep` sources and machine-readable outputs deterministic; report supported behavior and unimplemented pieces exactly.
