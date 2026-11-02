# Pepin
### A small programming language with a compiler that knows what it knows.

**Pepin** is an experimental, statically typed programming language and development environment built for humans and AI agents working on the *same* source code, with the *same* compiler and the *same* rules.

The language is **Pep** (`.pep` files). The long-term compiler and toolchain is **Lucy**. The idea is simple: keep source code readable and the language core compact, while making the compiler exceptionally good at explaining programs, checking changes and exposing reliable knowledge to other tools.

> **Project status: pre-1.0, actively under development.** The accepted `master` baseline is the working OCaml seed through milestone **A8**. Later compiler, native-backend and language work exists on development/review branches but is **not** part of the accepted master release. [See what actually works](docs/DESIGN.md) · [Road to 1.0](docs/ROADMAP_TO_1_0.md)

## Why build Pepin?

Today, an AI coding agent often has to reconstruct a program's meaning from text, search output and error messages. But a compiler already knows which names resolve, what types are expected, what is missing and which facts it has checked.

Pepin makes that knowledge available instead of asking an agent to guess.

- **Readable first.** Familiar functions, types, records, matching and control flow. No prompt syntax or second, AI-only programming language.
- **Compiler-guided development.** Inspect checked program structure, query types and in-scope values, and work with *typed holes* in unfinished code.
- **Precise, revision-bound changes.** Information and supported edits are tied to exact source revisions, so stale proposals can be rejected.
- **Programs that extend the environment.** Write ordinary Pep functions, register them as typed development tools and validate them before activation.
- **One source of truth.** Compiler facts, test observations, agent suggestions and human acceptance are different things. They should never be confused.
- **Small language, serious ambitions.** Grow a powerful standard library in Pep itself, and work toward a self-hosting compiler and a genuinely useful general-purpose 1.0.

**AI-first does not mean AI-dependent.** Pep's parser, checker and runtime are deterministic software. No model subscription or LLM is required to compile or run Pep.

## A glimpse of Pep

This program is supported by the current OCaml seed:

```pep
fn double(n: Int) -> Int {
    return n * 2
}

say(int_text(double(21)))
```

Now replace the return expression with a **named typed hole**:

```pep
fn double(n: Int) -> Int {
    return ?calculation
}

say(int_text(double(21)))
```

Pep can still analyse the incomplete program. The compiler knows the hole needs an `Int`, that `n` is an `Int` in scope, and where the missing expression lives. Release-style execution refuses unresolved holes. The actual repository example is [fill_double_hole.pep](examples/fill_double_hole.pep).

This is the central Pepin idea in miniature: **the compiler supplies facts; the programmer or agent supplies intent and implementation.**

## What we've built

The accepted A8 baseline is more than a parser demonstration:

| Area | Implemented on accepted `master` |
| --- | --- |
| **Language** | Typed functions, lexical scoping, inference for supported locals, `Int`/`Bool`/`Str`/`Unit`, records, recursive tagged unions, exhaustive matching, lists and essential control flow |
| **Compiler intelligence** | Source-spanned syntax and checked trees, typed holes, diagnostics, visible bindings and deterministic semantic queries |
| **Development interface** | `describe`, `inspect`, `check`, `query`, `run`, plus a JSON Lines semantic session with revision identity and guarded hole filling |
| **Living tools** | Checker-derived tool registration, test-vector validation, explicit activation, typed invocation and controlled replacement in a trusted local host |
| **Pep developing Pep** | A real [unused-function analyser written in Pep](examples/unused_functions.pep), consuming host-authorised, checker-derived call-graph facts |

The A8 acceptance record reports **55/55 primary OCaml tests** and **11/11 historical MoonBit tests** at its recorded revision. Those are historical, revision-bound results, **not** a claim that the latest experimental branches or all 1.0 features pass.

The first-generation tooling is already unusual. It is also intentionally limited: the extension host is **not a security sandbox**, source edits are not yet a general structural refactoring system, and the accepted compiler does not yet provide general generics, modules, maps, native Pep compilation or self-hosting. [Full feature boundary](docs/DESIGN.md).

## Try the current seed

The documented development setup uses **PowerShell 7**, **opam** and a project-specific **OCaml 5.5.2** switch (`pepin-5.5.2`). This is a source-development workflow, **not** a polished cross-platform installer. See [bootstrap requirements and troubleshooting](docs/BOOTSTRAP.md).

From the repository root, after configuring the OCaml switch:

```powershell
.\pep.ps1 --help
.\pep.ps1 describe --json
.\pep.ps1 check examples/hello.pep --json
.\pep.ps1 run examples/hello.pep
.\pep.ps1 query examples/fill_double_hole.pep --holes --json
```

For further examples, try [records](examples/point_sum.pep), [recursive unions](examples/recursive_expr.pep), [typed matching](examples/match_holes.pep) and [collections/control flow](examples/a6_collections_control.pep).

To run the repository's Python-driven regression suites:

```powershell
python -m unittest discover -s tests -v
```

The CLI can report its actual supported capabilities using `describe --json`. Trust that and a verified build over aspirational documentation.

## The road to 1.0

**Two roads, one destination.** The first gets us to *Pepin in Pepin*: a Pep-written compiler capable of rebuilding itself. The second completes the language and environment people can rely on. **Self-hosting is not, by itself, 1.0.**

1. **Prove the foundation.** Working typed OCaml seed; source revisions, holes, semantic queries and Pep-written development tools. **Accepted through A8.**
2. **Make Pep capable of building Pep.** Grow the smallest necessary Pep-written compiler foundations, lexer, parser and checker; prove a genuine C23 native path; reproduce compiler self-builds. **Experimental/development work, not accepted on master.**
3. **Finish the everyday language.** Complete the accepted typing, values, generics, modules, errors, effects, safe memory/access rules, concurrency and native parity. Build useful standard-library layers **in Pep whenever practical**.
4. **Make Lucy a dependable development partner.** A single compiler-derived semantic model, stage checkpoints, evidence-aware queries, safe edits, tests and versioned tooling, with no second hidden semantic engine.
5. **Earn the 1.0 release.** Independent negative/adversarial testing, real Pep applications, reproducible builds, documented platforms, language and library specifications, security review and explicit release acceptance.

No calendar date or version badge is being promised ahead of evidence. The [detailed 1.0 milestones and acceptance gates](docs/ROADMAP_TO_1_0.md) distinguish accepted, experimental and proposed work.

## Documentation

| Start here | Purpose |
| --- | --- |
| [Documentation guide](docs/README.md) | Find the right document and understand which sources are authoritative |
| [Road to 1.0](docs/ROADMAP_TO_1_0.md) | Product milestones, priorities and release criteria |
| [Implementation status](docs/DESIGN.md) | Accepted compiler capabilities and known limits |
| [Bootstrap and first commands](docs/BOOTSTRAP.md) | Reproduce today's development workflow |
| [Founding design](docs/FOUNDING_DESIGN_v0.3.md) | The original vision, with later decisions taking precedence |
| [Current implementation packet](docs/packets/CURRENT.md) | Authorised work and acceptance status for implementation agents |

Additional language manuals, detailed design decisions and compiler experiments are linked from the [documentation guide](docs/README.md). The earlier MoonBit compiler remains in this repository as a historical reference, not the primary Pep toolchain.

---

**Pepin's bet:** the most useful thing we can give intelligent programmers is not a language that guesses better. It's a language whose tools make guessing less necessary.
