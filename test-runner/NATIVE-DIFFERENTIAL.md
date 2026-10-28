# Native differential testing — interpreter vs Clang vs GCC C23

`pep test` can run the same Pep program through three real backends and compare
what they actually do:

| backend | command the adapter runs |
| --- | --- |
| `interpreter` | `.\pep.ps1 run FILE` |
| `clang` | `.\pep.ps1 run-c23 FILE --compiler <clang>` |
| `gcc` | `.\pep.ps1 run-c23 FILE --compiler <gcc>` |

Nothing here re-implements Pep, the checker, the emitter or C. The adapter
drives the real CLI, strips build chatter, and decides a verdict from observed
bytes and exit codes.

## Usage

```powershell
.\pep.ps1 test --backend interpreter,clang,gcc        # three-way differential
.\pep.ps1 test --backend clang,gcc                   # native pair only
.\pep.ps1 test --backend interpreter,clang,gcc --filter native/
.\pep.ps1 test --backend clang --compiler-clang C:\tools\llvm\bin\clang.exe
.\pep.ps1 test --backend interpreter,clang,gcc --json --evidence-dir _build\diff
```

`--backend` defaults to `interpreter`, so an ordinary `.\pep.ps1 test` is
unchanged and needs no toolchain. Native fixtures are still *listed* by
`--list`; they are only *executed* when a native backend is selected, and the
runner prints a note when it leaves them out. Compilers default to PATH
(`clang`, `gcc`/`gcc.exe`) and can be overridden per backend.

Exit codes: `0` all executed tests passed or were declared unsupported, `1` any
failure/divergence/compile/runtime/timeout, `2` infrastructure (missing
compiler, unknown backend, malformed manifest, empty selection).

## What a fixture may declare

```json
{
  "id": "native/arith-return",
  "file": "fixtures/native_arith_return.pep",
  "kind": "native",
  "expect": { "exit": 0, "stdout": "42\n" }
}
```

`kind: "native"` selects the differential runner. `expect` supports four modes:

| mode | meaning |
| --- | --- |
| `exact` (default) | every selected backend must reproduce `expect.stdout` byte-for-byte and `expect.exit` |
| `diagnostic` | every backend must exit with `expect.exit` and report `expect.diagnosticCode`; formatting may differ per backend |
| `reject` | the program is invalid: the interpreter must reject it with `expect.diagnosticCode` and no native backend may execute it |
| `nativeUnsupported` | the C23 subset is known-unsupported: every native backend must report `Pep C23 unsupported:` containing that substring |

In `diagnostic`/`reject`/`nativeUnsupported` modes, `expect.stdout`/`exit`
describe the interpreter column, so the interpreter's behaviour is still
asserted rather than ignored.

## Why the fixtures look the way they do

Measured against the real CLI (clang 23.1.4, gcc 16.2.0, 2026-10-28):

* `run` executes **top-level statements only** — it never calls `fn main`.
* `run-c23` requires a top-level `fn main() -> Int`, prints the returned Int to
  stdout and exits 0.
* `run-c23` writes exactly two build lines to stderr before the program runs:
  `C23: <generated .c>` and `Executable: <exe>`.

So a plain `fn main` program gives the interpreter nothing to run. A genuine
three-way runtime comparison needs the **hybrid shape**: compute the same value
once in `main` (compiled) and once at top level (interpreted).

```pep
fn main() -> Int { return 40 + 2 }
say(int_text(40 + 2))
```

Both paths print `42`, so a byte comparison across interpreter, clang and gcc is
meaningful. Native fixtures follow this shape; `native/unsupported-*` fixtures
deliberately do not need it because they assert rejection, not output.

## Observed behaviour this suite pins

| program | interpreter | clang / gcc |
| --- | --- | --- |
| `fn main() -> Int` arithmetic, calls, `if`/`else` | prints the same value via top level | prints the returned Int, exit 0 |
| `1 / 0` | exit 1, `line:col: PEP_RUNTIME_DIVISION_BY_ZERO:` | exit 1, `PEP_RUNTIME_DIVISION_BY_ZERO` |
| `9223372036854775807 + 1` | exit 1, `line:col: PEP_RUNTIME_OVERFLOW:` | exit 1, `PEP_RUNTIME_OVERFLOW` |
| `fn main() -> Unit` / `Bool` | runs normally | `Pep C23 unsupported: ... main function must return Int` |
| records, variants, `for`-in, `var`/`while`, `say` | runs normally | `Pep C23 unsupported: ...` |
| invalid program | rejected with a `PEP_*` code | `Pep C23 unsupported: ... requires a valid Pep checker report` |

Compilers `clang` and `gcc` agreed on every case measured; the suite asserts
that agreement rather than assuming it.

## Honesty rules

* A missing compiler is `infra_error` (exit 2) — never a pass and never a skip.
* `Pep C23 unsupported:` (exit 2) is a distinct native class. If the fixture did
  not declare it, that is a **failure** (`fail`), because a backend regression
  must not look like a supported run.
* A declaration that no longer holds also fails: if a backend starts supporting a
  declared-unsupported fixture, or the unsupported reason changes, the fixture
  fails and the manifest must be updated deliberately.
* `Pep C23 error:` (toolchain) is `infra_error`; a compiler refusing the emitted
  C, or a bare exit 2 with no Pep prefix, is `compile_error`.
* clang and gcc disagreeing on stdout, exit or (in `diagnostic` mode) the
  `PEP_*` code is `divergence` — checked *before* the oracle comparison, because
  otherwise the one expected answer a compiler matches would turn the split into
  an ordinary failure and hide it. It is counted and reported apart from `pass`
  and fails the run. Agreement between the compilers is never a pass on its own:
  the declared expectation still rules.
* Only the two leading `C23:`/`Executable:` lines are stripped, so a program
  that itself prints `C23: ...` is compared verbatim.
* Declared-unsupported fixtures are counted as `unsupported`, never as `pass`.

* A `skip` on a native fixture is honoured: it is recorded with its reason and
  source SHA-256 and never executed, so nothing is compiled on its behalf.
* Incoherent declarations are `infra_error` *before* anything runs: an unknown
  `match` mode, `diagnostic`/`reject` without `diagnosticCode`, or a fixture
  declaring both `nativeUnsupported` and `match: reject`.
* A native fixture with no `expect` block is a strict expectation — empty
  stdout and exit 0 — never "anything goes".
* Any fixture that could not be evaluated makes the run exit `2`, distinct from
  a test that genuinely failed.

## Evidence

Each native fixture records, per backend, in the JSON result and under
`--evidence-dir` as `native-<backend>.json`: command, exit code, stdout, program
stderr (metadata removed), elapsed seconds, timeout flag, build metadata lines
and the resolved compiler path. The run document also records `backends`, and
`toolchain.native` carries each compiler's resolved path plus the first line of
its `--version`, so a "clang agreed with gcc" receipt names the compilers that
produced it. A compiler that cannot report itself is recorded as `unknown: ...`
rather than guessed, and never aborts the run.

## Working with Agent 2's native backend

The manifest pins the boundary measured on **this branch's base (`52a75d6`)**
with the campaign emitter. Agent 2's `codex/native-collections-loop` branch is a
later, more capable revision: at `872a997` it supports tested `for`-in list forms
(Int/Bool literal, mutable and parameter shapes) and mutable-state `while`.

Checked against that revision rather than assumed:

* both `native/unsupported-*` declarations stay **truthful** there — record field
  access still reports `Pep C23 expression lowering does not support this
  expression`, and a valid `Unit`/`Bool` main still reports `Pep C23 main
  function must return Int`, which is what these fixtures declare;
* what the later revision changes is the *documented limits* below (`for`-in and
  mutable `while`), which describe this base and not that branch — they are not
  manifest declarations, so nothing lies until someone edits a fixture.

Rules that keep this honest:

* Compare two real revisions before editing a declaration. A declaration a
  backend has outgrown fails loudly by design; the migration is a deliberate
  one-line manifest edit per fixture, made only after re-measuring both sides.
* Never copy another agent's claim into a manifest. Add a new `exact` or
  `diagnostic` fixture for a newly supported shape instead of widening an
  existing one, so each capability keeps its own evidence.

## Current limits

* The C23 subset is what the Pep-written emitter supports **at this branch's
  base (`52a75d6`)**: `fn main() -> Int` with integer arithmetic, function calls
  and `if`/`else`, plus the div-zero and overflow guards. Records, variants,
  lists, `for`-in, `var`/`while` and non-`Int` mains are unsupported *there* and
  asserted as such; Agent 2's later branch widens some of these, so re-measure
  before inheriting these limits.
* Diagnostic *text* is not compared across backends — only the `PEP_*` code and
  the exit code, because the interpreter and native paths format differently by
  design.
* No property generation, shrinking or cross-run caching yet; fixtures are
  explicit and each backend build is unconditional.
* Fixtures are LF-canonical (`test-runner/fixtures/.gitattributes`). A CRLF
  fixture that pins byte spans is refused as `infra_error` instead of reporting
  a misleading mismatch.
