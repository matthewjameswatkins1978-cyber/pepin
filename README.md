# Pep

Pep is a small, statically typed, AI-first programming language intended to become self-hosting. Its canonical v0.3 vision is [Founding Design v0.3](docs/FOUNDING_DESIGN_v0.3.md), and binding technical decisions are in [Technical Resolution 001](docs/TECHNICAL_RESOLUTION_001.md) as amended by [Technical Resolution 002](docs/TECHNICAL_RESOLUTION_002.md). These design documents include planned capabilities; they are not a claim that those features are implemented.

The primary compiler seed is OCaml 5.5.2. Pep follows a **modern-by-default, evidence-driven upgrade policy**; its planned native backend is a **Pep-written C23 generator** (ISO/IEC 9899:2024), using **Clang as the primary native compiler and GCC for independent checks**, not yet implemented. Pep source is ordinary plaintext `.pep` files. The current interpreter supports `Int`, `Bool`, `Str`, and `Unit`; immutable nominal records and recursive tagged unions; `List[T]` with homogeneous literals, contextual empty lists and typed element holes; functions, lexical scopes, fixed-type mutable `var` bindings, integer operations, conditional blocks and expressions, `for-in`, `while`, scalar equality and short-circuit Boolean operators; built-in `length`, immutable `append`, scalar-only `contains`, `say` and `int_text`; and typed or unconstrained holes. Examples cover [records](examples/point_sum.pep), [recursive unions](examples/recursive_expr.pep), [typed match holes](examples/match_holes.pep), and [A6 collections and control flow](examples/a6_collections_control.pep). Exact limits are in [the seed-language note](docs/SEED_LANGUAGE.md) and [implementation-status index](docs/DESIGN.md).

## For implementation agents

**[Read the current Pepin implementation packet](docs/packets/CURRENT.md)**. This stable GitHub link points to the next authorised milestone. The [complete packet roadmap](docs/packets/README.md) includes individually prepared A6–A15 contracts; later self-hosting packets are **provisional plans, not shipped features or permission to implement them automatically**. The [A5 acceptance record](docs/packets/archive/A5-ACCEPTANCE-RECORD.md) and [A6 acceptance record](docs/packets/archive/A6-ACCEPTANCE-RECORD.md) are preserved.

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
.\pep.ps1 run examples/a6_collections_control.pep
.\pep.ps1 query examples/match_holes.pep --holes --json
python -m unittest discover -s tests -v
```

`inspect` returns a source-spanned AST. `check` returns the checked tree and hole information. `query` selects holes and compatible in-scope bindings; `--offset` accepts an original UTF-8 byte offset. `run` executes only complete, successfully checked programs. `describe --json` reports implemented capabilities only.

The in-process semantic session reads and writes JSON Lines over standard input/output and keeps documents and tool registrations only until the process exits. Schema-v3 supports revision-bound queries, byte edits, and named-hole fills. Tool protocol v1 provides checker-derived registration, test-vector validation, explicit activation, scalar typed invocation, listing, and hot replacement. Protocol v2 adds bounded typed List/record transport and the host-authorised `semantic_snapshot() -> ProgramInfo` interface, while preserving v1. The trusted-local interpreter blocks say and enforces call-depth and step budgets; it is not a sandbox. The A8 [unused-function analyzer](examples/unused_functions.pep) is a Pep-written example tool that computes reachability from host-authorised checker facts; it reports functions unreachable under declared roots and is not a built-in CLI command. See [the hole example](examples/fill_double_hole.pep), [SESSION_PROTOCOL.md](docs/SESSION_PROTOCOL.md), and [TOOL_PROTOCOL_V2.md](docs/TOOL_PROTOCOL_V2.md) for message shapes and limits. Existing file-oriented JSON commands remain schema v2.
## Design and history
- [Founding Design v0.3](docs/FOUNDING_DESIGN_v0.3.md): language vision.
- [Technical Resolution 001](docs/TECHNICAL_RESOLUTION_001.md): founding technical decisions and acceptance requirements.
- [Technical Resolution 002](docs/TECHNICAL_RESOLUTION_002.md): modern-by-default rule and current C23 native target.
- [Implementation status](docs/DESIGN.md): what is implemented versus planned.
- [AI-first execution and resource-boundary research (26 October 2026)](docs/RESEARCH_AI_FIRST_EXECUTION_2026-10-26.md): provisional analysis of concurrency, leases, real-time memory, GPU lifetimes and semantic library contracts; not implementation authority.
- [Session protocol v3](docs/SESSION_PROTOCOL.md): ephemeral revision-aware JSONL interface and its limits.
- [Seed-language decision](docs/SEED_LANGUAGE.md): OCaml seed choice and current limits.
- [Current implementation packet](docs/packets/CURRENT.md): stable agent entry; [all packets](docs/packets/README.md): A6–A15 roadmap.
- [Historical A5 acceptance](docs/packets/archive/A5-ACCEPTANCE-RECORD.md): verified first local Pep tool extension.
- [Historical A0 MoonBit design](docs/HISTORICAL_DESIGN_A0.md): retained prototype record; not the primary compiler feature list.

The original MoonBit compiler remains available as `pep-moonbit.ps1` with its separate tests for historical/reference use. The current bootstrap instructions are in [BOOTSTRAP.md](docs/BOOTSTRAP.md).
