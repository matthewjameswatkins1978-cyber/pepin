# Pep

Pep is a small, statically typed, AI-first programming language intended to become self-hosting. Its canonical v0.3 vision is [Founding Design v0.3](docs/FOUNDING_DESIGN_v0.3.md), and binding technical decisions are in [Technical Resolution 001](docs/TECHNICAL_RESOLUTION_001.md) as amended by [Technical Resolution 002](docs/TECHNICAL_RESOLUTION_002.md). These design documents include planned capabilities; they are not a claim that those features are implemented.

The primary compiler seed is OCaml 5.5.2. Pep follows a **modern-by-default, evidence-driven upgrade policy**; its planned native backend is a **Pep-written C23 generator** (ISO/IEC 9899:2024), using **Clang as the primary native compiler and GCC for independent checks**, not yet implemented. Pep source is ordinary plaintext `.pep` files. The current interpreter supports built-in types `Int`, `Bool`, `Str`, and `Unit`; immutable nominal records; recursive tagged unions; constructor pattern matching; functions, lexical scopes, integer operations, conditionals, built-in calls, and typed or unconstrained holes. Examples cover [records](examples/point_sum.pep), [recursive unions](examples/recursive_expr.pep), and [typed match holes](examples/match_holes.pep). Exact limits are in [the seed-language note](docs/SEED_LANGUAGE.md) and [implementation-status index](docs/DESIGN.md).

## Build, inspect, check, and run
Requirements: PowerShell 7, opam, and the Pepin-specific OCaml 5.5.2 switch. By default the CLI uses the standard opam root; set `PEPIN_OPAM_ROOT` if the switch is installed in another root.

```powershell
.\pep.ps1 --help
.\pep.ps1 describe --json
.\pep.ps1 inspect examples/hello.pep --json
.\pep.ps1 check examples/hello.pep --json
.\pep.ps1 query examples/fill_double_hole.pep --holes --json
.\pep.ps1 run examples/hello.pep
.\pep.ps1 run examples/point_sum.pep
.\pep.ps1 run examples/recursive_expr.pep
.\pep.ps1 query examples/match_holes.pep --holes --json
python -m unittest discover -s tests -v
```

`inspect` returns a source-spanned AST. `check` returns the checked tree and hole information. `query` selects holes and compatible in-scope bindings; `--offset` accepts an original UTF-8 byte offset. `run` executes only complete, successfully checked programs. `describe --json` reports implemented capabilities only.

The in-process semantic session reads and writes JSON Lines over standard input/output and keeps documents and tool registrations only until the process exits. Schema-v3 supports revision-bound queries, byte edits, and named-hole fills. Tool protocol v1 adds checker-derived registration, test-vector validation, explicit activation, scalar typed invocation, listing, and hot replacement. The trusted-local interpreter blocks say and enforces call-depth and step budgets; it is not a sandbox. See [the hole example](examples/fill_double_hole.pep) and [SESSION_PROTOCOL.md](docs/SESSION_PROTOCOL.md) for message shapes and limits. Existing file-oriented JSON commands remain schema v2.
## Design and history
- [Founding Design v0.3](docs/FOUNDING_DESIGN_v0.3.md): language vision.
- [Technical Resolution 001](docs/TECHNICAL_RESOLUTION_001.md): founding technical decisions and acceptance requirements.
- [Technical Resolution 002](docs/TECHNICAL_RESOLUTION_002.md): modern-by-default rule and current C23 native target.
- [Implementation status](docs/DESIGN.md): what is implemented versus planned.
- [Session protocol v3](docs/SESSION_PROTOCOL.md): ephemeral revision-aware JSONL interface and its limits.
- [Seed-language decision](docs/SEED_LANGUAGE.md): OCaml seed choice and current limits.
- [A5 implementation packet](docs/NEXT_PACKET.md): acceptance scope and implementation status for the first local Pep tool extension.
- [Historical A0 MoonBit design](docs/HISTORICAL_DESIGN_A0.md): retained prototype record; not the primary compiler feature list.

The original MoonBit compiler remains available as `pep-moonbit.ps1` with its separate tests for historical/reference use. The current bootstrap instructions are in [BOOTSTRAP.md](docs/BOOTSTRAP.md).
