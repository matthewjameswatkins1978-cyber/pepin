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
- **No native column in the generated manifest (yet).** Generated fixtures are
  `kind: "run"`, which only ever executes the interpreter. Passing
  `--backend interpreter,clang,gcc` therefore **fails loudly** — the runner now
  refuses to label interpreter-only fixtures with compilers they never touched.
  A real native column needs hybrid fixtures (`fn main() -> Int` returning the
  same value the top-level statement prints) and is the next slice here.

  Measured by hand on this base so the gap is stated, not guessed:

  | helper shape | clang / gcc |
  | --- | --- |
  | single `if`/`else` returning a value (`int_abs`, `int_min`, `int_max`) | runs, matches the interpreter |
  | nested `if`/`else` returns (`int_sign`, `int_clamp`) | `Pep C23 unsupported: ... require direct local/supported scalar ...` |
  | `var` + `while` bodies (`int_mod`, `int_gcd`, `int_lcm`, `int_pow`, parity) | `Pep C23 unsupported: ... require direct local ...` |
  | the whole 11-helper module plus a caller | `PEP_RUNTIME_STEP_LIMIT` in the staged parser, before the emitter |

  That is why each case composes only its own closure: a whole-library
  composition does not even reach the emitter on this base.
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
