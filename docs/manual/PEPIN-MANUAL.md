# The Pepin Manual

*A practical introduction to Pep, its programming model, and the intended Pepin environment*

**Editorial edition:** 28 October 2026  
**Design basis:** `PEP-LANG-FINAL-DRAFT-2026-10-27`, approved language-design direction  
**Language:** Pep (`.pep`) · **Project/environment:** Pepin · **Intended compiler:** Lucy  
**Status:** **Draft-based manual, not a declaration of implemented Pepin 1.0.**

> **Read this first.** Pepin is being built. This manual teaches the *approved language direction*. A small subset already works in the OCaml seed compiler, while other examples show agreed designs whose exact grammar or implementation is unfinished. Every example is labelled accordingly. To discover what your installed compiler supports, ask the compiler, not an AI or this document: `./pep.ps1 describe --json` on Windows PowerShell, or check the version-specific compiler documentation.

## Contents

1. [What Pep is](#1-what-pep-is)
2. [Getting started with today's compiler](#2-getting-started-with-todays-compiler)
3. [The shape of a Pep program](#3-the-shape-of-a-pep-program)
4. [Values, variables, and types](#4-values-variables-and-types)
5. [Functions and control flow](#5-functions-and-control-flow)
6. [Records, unions, and matching](#6-records-unions-and-matching)
7. [Collections and independent values](#7-collections-and-independent-values)
8. [Generics and behaviour values](#8-generics-and-behaviour-values)
9. [Read, edit, and take](#9-read-edit-and-take)
10. [Expected errors and external effects](#10-expected-errors-and-external-effects)
11. [Modules, imports, and packages](#11-modules-imports-and-packages)
12. [Memory and danger](#12-memory-and-danger)
13. [Async work and task scopes](#13-async-work-and-task-scopes)
14. [Testing](#14-testing)
15. [Working with Lucy's semantic information](#15-working-with-lucys-semantic-information)
16. [Writing dependable Pep](#16-writing-dependable-pep)
17. [What is finished, and what is next](#17-what-is-finished-and-what-is-next)
18. [Sources and further reading](#18-sources-and-further-reading)

---

## 1. What Pep is

**Pep** is a small, statically typed programming language designed for AI agents to write and for people to read, inspect, and govern. **Pepin** is the broader compiler and development environment. **Lucy** is the intended name of its compiler; that name is a design intention, not a guarantee that today's executable uses it.

Three ideas shape the language:

- **The compiler should do work the programmer does not need to do.** If Lucy can infer a local type, track ownership, or choose a sound allocation strategy, the source should not require a ceremony to restate it.
- **The compiler is the authority.** An agent can suggest code, edits, tests, or safety claims. Only compiler-owned analysis and independently recorded evidence can justify a checked fact. AI is not required at runtime.
- **Safety first, without a swollen language.** Everyday programming uses readable typed functions, values, and a substantial standard library. Low-level access, effects, capabilities, and concurrency have explicit contracts.

Pep's aspiration is not to make every feature a keyword. Its standard library, written in Pep where practical, should carry most everyday power. The same compiler model should support command-line builds, editor queries, test tools, and verified source edits.

### Two kinds of examples

Throughout this manual:

- **SEED EXAMPLE** shows syntax or a feature documented as implemented in the accepted OCaml seed. It is not an assertion that this particular snippet was rerun while writing the manual.
- **DESIGN EXAMPLE** shows the approved *direction* or one of the draft's proposed spellings. It is not guaranteed to parse today, and some punctuation or library names still require final specification.

We do not blur those two categories. A design example can be worth learning without masquerading as an executable program.

## 2. Getting started with today's compiler

Pep source files use the `.pep` extension. The source of a program is ordinary, versioned text. The current seed compiler was developed in **OCaml 5.5.2** and is invoked in the repository on Windows through PowerShell 7 and a project-specific opam switch. This is the *development* workflow, not a published cross-platform installation promise.

From a configured clone of the Pepin repository:

```powershell
.\pep.ps1 --help
.\pep.ps1 describe --json
.\pep.ps1 inspect examples/hello.pep --json
.\pep.ps1 check examples/hello.pep --json
.\pep.ps1 run examples/hello.pep
```

The repository's `examples/hello.pep` contains:

```pep
say("Hello, Pep!")
```

**SEED EXAMPLE.** `say` is the seed's built-in operation for outputting a `Str`. Other documented seed commands include `query FILE --holes --json`, `session --jsonl`, and, on the development campaign, limited `build-c23`/`run-c23` operations. Native C23 support is a **restricted experimental subset**, not a general alternative compiler for the whole final language.

**Testing status:** A separate development branch, `pep/test-runner-v8-slice1`, has delivered a first-party **manifest-driven** `pep test` CLI, but that does **not** establish the draft's compiler-recognised `test "name" { ... }` language feature or the `std.test` API. Use the command only where that development branch has been integrated or explicitly installed. See [Testing](#14-testing).

### What the commands tell you

- `describe --json`: implemented capabilities reported by the actual tool.
- `inspect FILE --json`: parsed, source-spanned syntax.
- `check FILE --json`: type and validity checking, including incomplete typed holes.
- `query FILE --holes --json`: scope-aware hole information and proposed fills.
- `run FILE`: execute *only* successfully checked, complete programs.
- `session --jsonl`: versioned in-process document and semantic operations for tools.

Treat machine output as versioned evidence. A program that checks on a branch does not necessarily check on accepted `master`.

## 3. The shape of a Pep program

Pep's accepted surface direction is deliberately conventional: `fn` for functions, braces for blocks, `let` for immutable bindings, `var` for mutable bindings, `type` for data declarations, `if`/`match` for decisions, and `for`/`while` for loops.

```pep
fn double(value: Int) -> Int {
    return value + value
}

let answer = double(21)
say(int_text(answer))
```

**SEED EXAMPLE (illustrative composition).** Typed functions, `let`, integer arithmetic, `int_text`, and `say` are documented seed capabilities. Here, `answer` has an inferred type of `Int`. The source is meant to read from top to bottom.

Pep's intended rules prefer **newlines rather than mandatory semicolons**; an explicit semicolon may separate statements. The full grammar for multiline continuations and the exact difference between expression and statement blocks is still to be frozen with tests. Comments may use `#`; the historical `//` style remains a compatibility consideration. Neither comments nor an AI's descriptions are executable facts.

## 4. Values, variables, and types

The current seed has four core scalar types: `Int`, `Bool`, `Str`, and `Unit`. The approved complete language adds `Float`, `Float32`, `Byte`, `Bytes`, `Array`, `Map`, and general `Option`/`Result` families among others.

### Immutable and mutable bindings

```pep
let first: Int = 10
let second = 20
var total = first + second
total = total + 1
say(int_text(total))
```

**SEED EXAMPLE.** A `let` binding is immutable; `var` enables reassignment under the binding's type. Mutability is explicit rather than inferred from how often a name is used.

### Type inference is contextual, not speculative

Pep uses bidirectional typing. A local expression can suggest its own type; a function parameter, argument, or return position may supply the expected type. When there isn't enough information, the compiler should report the ambiguity rather than invent a type.

Named functions declare parameter and result types. Generic type parameters may often be inferred at a call site **once generic functions are implemented**. There are no implicit numeric conversions. If code needs an integer converted to a float, that conversion must be explicit and typed; the final conversion API and literal suffixes still need specification.

### Numbers

`Int` is a **checked signed 64-bit integer** in the approved contract. Overflow and division by zero are not allowed to silently turn into unintended C23 behaviour. `Float` and `Float32` are the intended IEEE 754 64-bit and 32-bit floating types. Their literal spellings, conversions, NaN comparison policy, and precise conformance cases require a final grammar and runtime contract.

### Text and bytes

`Str` means valid Unicode text stored using UTF-8. `Byte` and `Bytes` represent raw binary data, which must not silently be interpreted as valid text. Unicode operations must distinguish byte units, Unicode scalar values, and user-visible grapheme clusters. A `Str` is **not** an arbitrary array of byte-indexable characters.

## 5. Functions and control flow

### Functions and returns

```pep
fn factorial(n: Int) -> Int {
    if n <= 1 {
        return 1
    } else {
        return n * factorial(n - 1)
    }
}

say(int_text(factorial(5)))
```

**SEED EXAMPLE (illustrative composition).** Named typed functions, recursion, integer arithmetic and conditionals are part of the seed. The approved design also supports mutually referenced and forward-called functions.

### If expressions and if statements

A **value-producing** `if` requires an `else` yielding a compatible type. A statement-only `if` does not need an `else`.

```pep
let label = if score <= 10 { "small" } else { "large" }
```

**SEED EXAMPLE (illustrative expression).** The draft additionally accepts `else if`; the final exact parsing of statement/expression interactions remains an explicit grammar item.

### Loops

```pep
var sum = 0
for value in [2, 4, 6] {
    sum = sum + value
}
say(int_text(sum))
```

**SEED EXAMPLE (illustrative composition).** The seed supports `for-in`, `while`, and mutable bindings. `break` and `continue` are part of the final draft direction, but should not be assumed supported by every compiler branch.

Pep does not promise that every loop terminates. The interpreter and tool host enforce separate runtime budgets; absence of side effects is not a proof of termination.

## 6. Records, unions, and matching

A **record** collects named fields; a **tagged union** represents one of several named alternatives. The compiler can inspect these types, resolve field access and, for closed unions, check match exhaustiveness.

```pep
type Point {
    x: Int
    y: Int
}

fn sum_point(point: Point) -> Int {
    return point.x + point.y
}

let p = Point { x: 10, y: 20 }
say(int_text(sum_point(p)))
```

**SEED EXAMPLE (using documented record syntax).** Pep uses named record constructors and statically checked field access.

A union in the accepted surface direction looks like this:

```pep
type Answer = Yes() | No()
```

**DESIGN EXAMPLE for final surface spelling.** The seed supports monomorphic tagged unions and exhaustive `match`, but specific syntax should be checked against actual versioned fixtures. Match arms may destructure nested constructor patterns, bind values, or use wildcard patterns. A missing required alternative is an error, not a silent fallback.

**Why this matters:** When the set of cases changes, the compiler can identify code that no longer handles every possibility. Agents shouldn't have to remember to search the whole repository by hand to find such omissions.

## 7. Collections and independent values

**One of Pep's strongest accepted guarantees is independent ordinary value semantics.** If `b` is an ordinary logical copy of `a`, subsequently changing `b` must not change `a`. The compiler may use shared immutable backing storage, copy-on-write, stacks, regions, or managed heaps internally so long as the observable result is correct.

### The seed's lists

```pep
let numbers: List[Int] = [3, 5, 8]
let longer = append(numbers, 13)
say(int_text(length(numbers)))
say(int_text(length(longer)))
```

**SEED EXAMPLE.** The seed supports `List[T]` for supported element forms, homogeneous literals, `length`, immutable `append`, and scalar-only `contains`. This seed's append returns a new list, leaving the earlier list alone.

### The complete data model

The accepted target includes:

- `List[T]`: ordered growable logical values.
- `Array[T,N]`: fixed-size typed value collections.
- `Map[K,V]`: typed maps with **observable insertion order**, using appropriate equality and hashing abilities.
- `Option[T]`: value or absence.
- `Result[T,E]`: success or expected typed failure.

All ordinary indexing must be safe. An optional-get operation should report absence explicitly. Map deletion/reinsertion ordering, exact APIs, and several element/ABI details are open conformance questions, not safe places to guess.

Resource handles are different: a socket, file, GPU buffer, or manually owned allocation can have **identity** and may be **noncopyable**. Independent values do not imply that two handles own different external resources.

## 8. Generics and behaviour values

Pep's final design includes parametric generics without C++-style templates or language-changing macros.

```pep
pub fn identity[T](value: T) -> T {
    return value
}
```

**DESIGN EXAMPLE, taken from the final draft.** `T` describes a type parameter. Type arguments may be inferred if unique; otherwise the compiler must request more information. An unconstrained `T` is **not** automatically addable, orderable or comparable.

A small set of compiler-understood abilities is intended, including `Equal`, `Ordered`, and `Hashable`. `Ordered` must actually define a total order; it should not automatically be assigned to floating-point values with NaN unless a separate total-order policy is specified. Hashing must agree with equality.

For richer user-defined behaviours, the approved model passes **ordinary records containing typed functions** as values, rather than hiding global typeclass instances. Two formatting policies for the same type can coexist, and a caller sees which one it uses. First-class function values and anonymous closures are part of the design; exact closure-capture spelling still needs a tested grammar.

## 9. Read, edit, and take

Pep's function contracts distinguish three forms of access:

| Mode | Meaning | What the compiler must protect |
| --- | --- | --- |
| **read** (default) | Observe a value without caller-visible mutation or transfer | No illegal writes through the access |
| **edit** | Temporarily grant exclusive access to the caller-owned value | No overlapping incompatible edits; owner resumes afterward |
| **take** | Transfer ownership out of the caller's binding | No use after transfer; correct responsibility for resources |

The final draft illustrates the proposed shape:

```pep
fn bump(edit value: Int) -> Unit {
    value = value + 1
}
```

**DESIGN EXAMPLE from the final draft.** Exact call-site syntax must be checked against the final access grammar. Do not assume `edit` is a mutable global reference or that a `take` leaves a usable copy behind. On ordinary immutable values, the compiler may optimize storage aggressively while preserving the promised behaviour.

Pep's aim is to infer safe lifetimes and alias relationships **without exposing Rust-like lifetime notation to everyday source**. When the compiler cannot prove a risky alias or escape safe, it should refuse it or require an explicitly designed safe operation, not guess.

## 10. Expected errors and external effects

### Errors are values

Routine absence is represented by `Option[T]`. Expected failure uses `Result[T,E]`, where `E` identifies an error type. The complete language uses exhaustive matching for recovery; postfix `?` is the proposed shorthand for propagating a compatible error from the current function.

```pep
fn load(path: Str) -> Result[Str, fs.Error]
    uses fs.read
{
    return fs.read_text(path)
}
```

**DESIGN EXAMPLE from the final draft.** The target API names are illustrative, and the effect syntax is not yet fully frozen. A function cannot silently drop an unexamined `Result`; discarding it deliberately needs an explicit acknowledgement whose spelling remains to be specified.

**Do not confuse expected errors with every possible failure.** Checked arithmetic traps, programming defects, task cancellation, and resource violations have their own contracts. Pep does not introduce a general exception mechanism in the initial design.

### Effects are not permissions

An effect describes what code *may need to do*. A host capability grants what it is *authorised to do* in an actual execution. A signature saying `uses fs.read` does **not** open the filesystem. The compiler should check transitive effects through calls, generics, and function values; a host must separately enforce grants.

For restricted real-time code, proving the absence of filesystem access is insufficient. No allocation, no garbage collection, no blocking, and deadline constraints need separate proofs or measurements. “Pure” does not mean “terminates” or “runs in constant time.”

## 11. Modules, imports, and packages

The target rule is straightforward: **one source file is one module**. The project's relative path establishes module identity. Public API declarations use `pub`; other declarations are private by default.

```pep
import math
import fs

pub fn identity[T](value: T) -> T {
    return value
}
```

**DESIGN EXAMPLE.** Qualified imports and optional `as` aliases are intended. Wildcard imports are not. Import cycles are invalid. Importing a module must not secretly perform effectful global initialisation.

A selected executable entry file may execute top-level statements. Importable modules are subject to stricter purity rules for declarations and allowed initialisers; that boundary still needs exact grammar and conformance tests.

Packages and dependency locks must be reproducible. An `import` is not permission for the compiler to fetch a dependency from the network without explicit host authorisation. Lucy should expose checked public signatures so an agent can understand an imported API without rereading its entire implementation.

## 12. Memory and danger

Pep's normal mode asks the compiler to choose safe storage: registers, stack, regions, immutable sharing, copy-on-write, or managed heap. A precise tracing collector is the **proposed fallback strategy**, not an independently proven shipped runtime. The implementation decision can evolve without changing Pep's observable value and ownership semantics.

The language also intends **safe manual allocation** through typed, noncopyable owned handles. A typed deallocation operation consumes ownership. A second free or a use after a `take` should fail the static contract, rather than becoming a silent dangling pointer.

`danger` is the deliberately narrow escape route for foreign or raw-memory operations. It does **not** switch off all checking: the compiler still enforces whatever can be established about alignment, layout, access, effects, and lifetimes. Remaining unsafe assumptions must be identified as **trusted obligations**, not treated as a model's proof.

The exact raw-pointer syntax, allocator functions, cleanup order, FFI rules, and GC-pinning protocol remain design work. Do not copy speculative snippets from this chapter into a safety-critical application.

### Real-time and external hardware

Audio, GPU, DMA and other external resources have special timing and lifetime needs. Memory cannot be released merely because a task was cancelled while hardware is still using it. A verified real-time boundary must exclude blocking, allocation, and GC/reclamation activity *transitively*. None of those guarantees follow automatically from ordinary `danger` or `uses` annotations.

## 13. Async work and task scopes

The accepted direction is **structured concurrency**. An asynchronous function may suspend at `await`; `spawn` creates child work owned by an enclosing scope. The scope must supervise its children before it exits. Failures and cancellation must not silently leave uncontrolled tasks or free still-active resources.

The draft mentions `async fn`, `await`, `spawn`, and a provisional `task.scope` formulation. **No full program is presented here**, because exact scope syntax, task results, cancellation propagation, and capture/transfer grammar remain unresolved. That is a deliberate documentation boundary.

The mental model is stable even before its spelling is: **work belongs to a scope; values cross task boundaries safely; mutable shared identity requires an explicit coordinated mechanism.** A temporary `edit` borrow must not silently survive an `await` or move to another task.

## 14. Testing

Pepin wants tests to be a normal part of the language environment rather than a second collection of scripts that silently disagree with the compiler.

The *final draft* proposes:

```pep
test "simple arithmetic" {
    test.equal(2 + 2, 4)
}
```

**DESIGN EXAMPLE.** `test` declarations and the `std.test` assertion vocabulary still need exact compiler grammar, signatures, and isolation contracts. They must not be advertised as part of the accepted seed merely because a separate runner now exists.

### A real milestone: manifest-driven `pep test`

As of 28 October 2026, the separate `pep/test-runner-v8-slice1` branch at commit `52a75d6` has an implemented, agent-verified **first-party external-fixture runner**. Its documented surface includes JSON output, discovery/listing, filtering, evidence artifacts, and explicit failure categories. The final agent receipt reports 17 passing Python adversarial tests and 12 passing Pep fixtures plus one deliberate skip, but that evidence remains **builder-reported**, not independently rerun for this manual. It remains separate from the compiler-recognised `test` syntax goal.

### What a good test report means

A test report should identify the **source revision, compiler revision, backend/toolchain, test conditions, input or random seed, observed outcome, assertion verdict, limits, and saved evidence**. A crash, timeout, missing compiler, denied capability, or missing evidence must not quietly count as a pass.

Tests can demonstrate bugs and regressions; they cannot prove that every other program is correct. The separate Terror Bats framework uses **PROVEN** for a falsification demonstrated under a specified trial, not for overall program correctness.

## 15. Working with Lucy's semantic information

This is where Pepin most clearly differs from a conventional language. A capable agent should be able to ask Lucy for a **small, precise, versioned answer**:

- Which declarations are visible at this cursor location?
- What type is expected at this typed hole?
- Which functions call this function?
- What is an exported module's effect/error contract?
- Is this fact checked, inferred, observed in a test, proposed, or unresolved?
- Can this source edit be applied to exactly this revision without changing unrelated bytes?

The accepted seed already provides typed holes, source-spanned parsed and checked trees, immutable in-process revisions, queries, and a constrained hole-filling operation. The full goal adds more granular, shared semantic queries, safe staged checkpoints, and selectively reusable compiler-derived knowledge across builds **without creating a second checker or competing truth store**.

### Typed holes

```pep
fn double(value: Int) -> Int {
    return ?missing
}
```

**SEED EXAMPLE (typed-hole shape).** The program is incomplete; it is not executable. A semantic query can return the expected type `Int`, visible bindings, and compatible fill candidates. Nothing should be executed until a complete checked revision exists. A named hole `?name` is distinct from the draft's postfix `?` for `Result` propagation; their lexical interaction still needs final grammar tests.

### Notes and comments

The original final draft accepted a three-layer source idea: code, optional Semantic Notes, and ordinary comments. A separate proposal suggested `#@ intent`, `#@ verify`, and `#@ prefer`. **The subsequent 28 October product priority explicitly superseded annotation-centred Semantic Notes as core architecture and removed them as a Pepin 1.0 requirement without further acceptance.** Ordinary comments remain useful. Checked code and compiler-derived facts take priority over an agent's annotations.

A comment may explain *why* code exists. It cannot grant file access, make a theorem proved, waive a bounds check, or change how a program means things.

## 16. Writing dependable Pep

For a human or an AI agent, a productive habit is:

1. Start with the smallest readable program expressing the desired behaviour.
2. Use ordinary values and `let` by default; introduce `var` when mutation is genuinely useful.
3. Give functions explicit parameter and result types; let safe local inference reduce repetition.
4. Use records and unions to make possible states visible. Match every relevant case.
5. Treat `Result` and external effects as part of the API, not incidental exceptions.
6. Reserve `edit`, `take`, resource handles, and `danger` for the responsibilities they actually express.
7. Ask Lucy for *checked* semantic facts rather than infer them from old chat logs.
8. Test real supported backends and record negative cases, not just happy paths.

This is guidance for how to use the design; it is not an extra grammar or a list of guaranteed compiler optimisations.

## 17. What is finished, and what is next

### Grounded baseline at this document's date

| Capability | Evidence-aware status |
| --- | --- |
| OCaml seed, `Int`/`Bool`/`Str`/`Unit`, functions, records, unions, lists, `let`/`var`, loops, `match`, typed holes, source spans, session queries | Documented accepted seed capabilities, subject to exact version and supported subset |
| Pep-written checker/parser stages and restricted C23 native output | Active experimental campaign, partial; full native parity not implied |
| Manifest-driven `pep test` with machine-readable receipts | Separate development branch at `52a75d6`; agent-reported working; **not** full `test` syntax |
| General generics, closures, modules, arbitrary `Array`/`Map`, `Result`/effect enforcement, full memory model, structured concurrency | Accepted final design direction, not established as shipped |
| Fully Pep-written Lucy / self-hosted build / Pepin 1.0 | Not yet established as accepted release |

**Product priorities as of 28 October:** build the foundational **Pep-written standard library**, then expand the compiler's reliable semantic knowledge and stage checkpoints as *one semantic authority*. The playful rabbit tutorial, large tool-port campaign, and exploratory multiparadigm systems are deliberately deferred. No accepted core language feature is silently removed by that prioritisation.

## 18. Sources and further reading

This manual is a teaching presentation of the following primary sources. In cases of conflict, the later explicit accepted project decision takes precedence; executable support always requires code and versioned tests.

- [Pep final language draft, 27 October](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/design/final-language-draft-20261027/docs/final-draft/PEP-LANG-FINAL-DRAFT-2026-10-27.md) — approved design direction, not frozen grammar.
- [Final-draft acceptance matrix](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/design/final-language-draft-20261027/docs/final-draft/ACCEPTANCE-MATRIX.md) — intended verification gates.
- [Surface syntax decision DEC-009](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7Caf91b899-62b4-4c8f-8a1e-429bda9d4fa3) — syntax choice and open grammar questions.
- [28 October priority clarification](https://app.basicmemory.com/notes?id=cloud%7C703e9fd6-6c96-7c2a-6f0d-4a73c11281ba%7Cfcb7313a-e158-4d76-988a-2e54978bc067%7C563c337a-eb00-4cb4-aa42-95a2ba584a73) — compiler knowledge and Pep-written stdlib supersede annotation-centred work as priority.
- [Current seed implementation status](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/DESIGN.md) and [seed-language boundary](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/SEED_LANGUAGE.md).
- [Full-language gap ledger](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/FULL-LANGUAGE-LEDGER.md) and [Road 2 to Pepin 1.0](https://github.com/matthewjameswatkins1978-cyber/pepin/blob/campaign/pep-v01-sustained-build-20261027/docs/roadmaps/ROAD-2-PEPIN-1.0.md).
- [Pep Test development branch, exact final SHA](https://github.com/matthewjameswatkins1978-cyber/pepin/tree/52a75d668b6b3158c603accb757674f26114c75d/test-runner).

*This edition is a human-facing manual, not a newly approved grammar. Where a feature or spelling has no completed contract, it says so rather than invent one.*