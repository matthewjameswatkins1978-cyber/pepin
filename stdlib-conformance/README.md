# Standard-library conformance

An independent contract for the standard library, run through the existing
`pep test` infrastructure. It exists so library work has a fast, honest
regression signal that does **not** duplicate the library, re-implement its
internals, or introduce a second test runner.

## Usage

```powershell
# against a pinned revision of the library — no checkout, no copy
git fetch origin codex/native-collections-loop
python stdlib-conformance/conformance.py --library-rev 872a997

# against the working tree once the library is merged
python stdlib-conformance/conformance.py

# machine-readable, with the runner's JSON document
python stdlib-conformance/conformance.py --library-rev 872a997 --json

# native column, where the emitter supports those shapes
python stdlib-conformance/conformance.py --backend interpreter,clang,gcc

# the integer module owned by this lane
python stdlib-conformance/conformance.py --library stdlib/intmath.pep `
  --cases stdlib-conformance/cases-intmath.json
```

Exit codes are the runner's: `0` all cases pass, `1` a case failed, `2`
infrastructure (unusable case table, unreadable library, empty selection).

## How it works

Pep has no imports yet, so a case is **composed, never duplicated**:

1. the real library source is read from a git object (`--library-rev`) or the
   working tree (`--library`);
2. each case is appended as a one-line caller;
3. the composed `.pep` files and a generated manifest are written under
   `_build/stdlib-conformance/<rev>/` — ignored by git, never committed;
4. `test-runner/pep_test.py` runs that manifest, and its JSON/counts/evidence
   are what you see. There is no second classification implementation.

The generated manifest records the library's provenance (`source`, `sha256`,
case count), so a conformance result names exactly what it tested.

## The case table

`stdlib-conformance/cases.json` is the contract:

```json
{ "id": "list_int_sum/empty", "expr": "list_int_sum([])", "result": "Int", "expect": "0" }
```

| Field | Meaning |
| --- | --- |
| `id` | Unique case name; `--filter` matches substrings of it. |
| `expr` | A call into the library's public API. |
| `result` | `Int` or `Bool` — how the result is observed. |
| `expect` | Expected observable text (`"0"`, `"true"`, ...). |

Nothing in a case refers to how a helper is implemented, so a
behaviour-preserving refactor passes and a regression fails. Empty-collection
identities are canonical (`sum([]) == 0`, `product([]) == 1`, `all([]) == true`,
`any([]) == false`, `none([]) == true`), so a failure there is a real defect
rather than a preference.

Bool results are observed by branching, because this base has `int_text` but no
`bool_text` (measured: `PEP_UNKNOWN_FUNCTION`):

```pep
say(if list_bool_none([false, false]) { "true" } else { "false" })
```

That workaround is deliberate. Adding a `bool_text`-style helper to a fixture
would invent part of the library's public surface, so the gap is reported
instead — see "Missing primitives" below.

## What this does not do

- **No imports.** Composition is string concatenation of the real source, so a
  case sees the whole library. When Pep gains modules, this harness should be
  the thing that changes, not the case table.
- **Native coverage is declared, not assumed.** See "Native column" below: the
  case table states, per helper, what the compilers do, and a declaration that
  stops being true fails the run.
- **No ownership of the library.** `stdlib/collections.pep`, the C23 emitter and
  their regression files belong to Agent 2. This harness only reads library
  revisions and asserts public behaviour.

## Modules covered

| Module | Owner | Contract | Status |
| --- | --- | --- | --- |
| `stdlib/collections.pep` | Agent 2 | `cases.json` (25 cases) | measured against `872a997`; runs in-tree once the library merges |
| `stdlib/intmath.pep` | Agent 3 | `cases-intmath.json` (40 cases) | in this branch; 40/40 pass on the interpreter |

Each case composes only the library functions it actually reaches (transitive
closure of calls), so a case pays for its own dependency graph instead of the
whole module. `--no-prune` composes everything, which is useful for measuring
whole-module parse cost — and on this base that is exactly where the staged
parser hits `PEP_RUNTIME_STEP_LIMIT`.

`stdlib/intmath.pep` provides `int_abs`, `int_sign`, `int_min`, `int_max`,
`int_clamp`, `int_mod`, `int_gcd`, `int_lcm`, `int_is_even`, `int_is_odd` and
`int_pow`, each with its domain documented in the module header. It is written
only with operators this base accepts, so it needs no language change.

## Native column

```powershell
python stdlib-conformance/conformance.py --library stdlib/intmath.pep `
  --cases stdlib-conformance/cases-intmath.json --native
```

`--native` generates **hybrid** fixtures — the value is computed once in
`fn main() -> Int` (compiled) and once in a top-level `say` (interpreted) — so
interpreter, clang and gcc must all print the same text. Only Int-result cases
can do this, because native `main` must return `Int`.

Every native expectation is declared in the case table's `native` block, which
was measured with real clang 23.1.4 and gcc 16.2.0:

| helpers | measured native result |
| --- | --- |
| `int_abs`, `int_min`, `int_max` | run and match the interpreter on both compilers |
| `int_sign`, `int_mod`, `int_pow` | `Pep C23 unsupported: ... require direct local lets followed by one return` |
| `int_clamp` | `Pep C23 unsupported: ... require supported scalar parameters and results` |
| `int_gcd`, `int_lcm` | **excluded**: their closure is 2–3 functions plus `main`, which hits `PEP_RUNTIME_STEP_LIMIT` in the staged parser before the emitter |
| `int_is_even`, `int_is_odd` | **excluded**: Bool results, and native `main` must return `Int`, so there is no comparable observable. Probed through an `Int` wrapper, `int_is_even` reports `requires a valid Pep checker report`; `int_is_odd` adds a second function and meets the composition ceiling |

A declared-unsupported entry still carries the interpreter's `exit` and
`stdout`, so `unsupported` never means "unchecked": both compilers must reject
**and** the interpreter must have produced the expected value. Otherwise a
program that computes the wrong result while both compilers refuse it would
report `unsupported` and prove nothing.

Current result: **9 pass, 15 declared-unsupported, 1 infra_error**. The
infra_error is real and recorded rather than hidden: `int_clamp(-5, 0, 10)`
exceeds the parser budget where the sibling `int_clamp` arguments reach the
emitter and are cleanly rejected. Argument shape, not only source shape, moves
that cost — the run exits 2 because it cannot vouch for that case.

`int_abs` carries a narrowed domain: negating the minimum `Int` is not
representable and raises `PEP_RUNTIME_OVERFLOW` by design. Parity does **not**
have that gap — `int_is_even` takes the remainder by truncating division
(`x - 2 * (x / 2)`), never negating the value, and is total over every `Int`
including both boundaries. Boundary cases for `INT64_MIN` and `INT64_MAX` are in
the contract and pass.

Two consequences worth knowing before writing more library code:

1. **The composition ceiling is the binding constraint.** Two library functions
   plus `main` already exceed the staged parser's 100,000-step budget, so most
   multi-function library code cannot be natively tested at all on this base —
   independent of whether the emitter would accept each helper.
2. **Declarations go stale loudly.** If a helper starts compiling natively, the
   declared-unsupported fixture fails; if it stops, the supported fixture fails.
   Update the `native` block from a fresh measurement, never by guess.

## Missing primitives found

Reported, not patched — inventing language surface is a compiler decision:

1. **No `bool_text`.** `int_text` exists; `bool_text` raises
   `PEP_UNKNOWN_FUNCTION`. Any library function returning `Bool` can only be
   observed through branching, which makes every Bool case two lines instead of
   one and blocks a symmetric text-conversion story for the standard library.
2. **No `<`, `>`, `>=` operators.** Each raises `PEP_UNEXPECTED_CHARACTER`, so
   only `==`, `!=` and `<=` compare. `stdlib/intmath.pep` spells `a > b` as
   `!(a <= b)`, which works but reads badly and forces every author to
   rediscover the idiom.
3. **No `%` operator.** `PEP_UNEXPECTED_CHARACTER` again. Remainder has to be
   reimplemented by subtraction, which `int_mod` does for a non-negative domain;
   negative remainders are simply not expressible without a language decision.
2. **No imports/modules.** Library helpers cannot reference each other across
   files, so a conformance case must concatenate the whole library. This is the
   main reason the harness composes sources.
4. **No list/collection display or `length` on `List` in this base's library
   contract.** `length`, `contains` and friends are C23-emitter features on
   Agent 2's branch; on this base only `contains` is available to library code.

## Current measured result

Against `codex/native-collections-loop` @ `872a997`, composed with this branch's
compiler and run through the interpreter:

```
pass=25 fail=0 ... infra_error=0     library: 872a997:stdlib/collections.pep
```

The base checker accepts that library source (`status: valid`), and the
interpreter reproduces every contract case, so the contract is meaningful now
even though the library itself lands with Agent 2.
