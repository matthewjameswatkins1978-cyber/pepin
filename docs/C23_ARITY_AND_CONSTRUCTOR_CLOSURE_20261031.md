# Native C23 parameter arity and lexer constructor closure — 31 October 2026

Agent 2 (A2-NATIVE), mission `LUCY-20261031-008` gates A2-1 to A2-3.
Branch `codex/a2-list-record-fields`; slices `a602659` (arity) and `deef0ed`
(List[Str] parameters). Prior slice on this branch: `052d894` (List record
fields). Toolchain for every native result: Clang 23.1.4 and MinGW GCC 16.2.0,
`-std=c23 -Wall -Wextra -Wpedantic -Werror -O2`, stdout compared with Pep's own
interpreter.

## A2-1 — the arity failure, reproduced and attributed

| probe | parent `052d894` | now |
| --- | --- | --- |
| `fn f(a,b,c,d: Int) -> Int { return a+b+c+d }` called with 4 args | refused: `Pep C23 calls require a known target and at most three arguments` | emits, runs |
| same signature with 8 parameters | refused: `Pep C23 functions require supported parameters and scalar or record results` | emits, runs |
| `fn f(a,b,c: Int) -> Int { return a+b+c }` with 3 args | refused: `Pep C23 three-parameter calls require three arguments and a call-free result` | emits, runs |
| real `make_token` (8 parameters, `List[Str]` parameter into a `List[Str]` field) | refused | still **checker-budget**, see A2-3 |

Stage attribution, measured rather than inferred from message text:

- **Emitter only.** Four or more parameters and four or more arguments were both
  rejected by the emitter while the checker accepted the same source. The
  three-parameter path additionally demanded a *call-free* result, so a function
  that summed its own parameters was refused even at arity three.
- **Not a runtime C ABI problem.** Once emitted, the generated C compiles under
  strict flags on both compilers and matches the interpreter exactly.
- **The real constructors are blocked upstream of the emitter.** `LexToken` +
  `make_token` + a small `main` stops at `check parsed source` with
  `PEP_RUNTIME_STEP_LIMIT` before any C is produced. That is the checker-cost
  dependency the first current agent owns; it is not an emitter gap and no cap
  was raised.

## A2-2 — what was implemented

All in `tests/pep_c23_emitter.pep`, the Pep-written emitter.

1. `pep_c23_ordered_children` / `pep_c23_parameters` collect parameters and
   arguments in declared `childIndex` order, so arity is no longer baked into
   fixed slots.
2. Name lowering resolves **any** parameter by `childIndex`. The previous form
   only resolved slots 0, 1 and 2 — the fourth parameter was invisible, so even a
   correct signature would have produced invalid C.
3. Prototype and definition parameter lists and the `(void)pep_arg_N` unused
   casts are emitted by loop over the ordered parameter list.
4. `pep_c23_many_argument_call` is one ordered path for more than three
   parameters: exactly one argument per declared parameter, each lowered against
   its declared parameter type (so lists, records and unions keep their existing
   argument rules), and **at most one runtime-fallible argument** because C leaves
   argument evaluation order unspecified. Routing is deliberately minimal: four or
   more parameters or arguments always use it (detected through the already
   computed `extraParameter`/`extraArgument` lookups, so no extra traversal), and a
   three-parameter call uses it **only when the fixed-slot path would refuse it**.
   Programs that already emitted therefore keep the cheaper path and their exact
   behaviour — see the step-cost section below for why that mattered.
5. `pep_c23_function_expression` validates every declared parameter type and the
   result type by loop, and the for-in parameter-shadowing guard covers all
   parameters rather than the first three.
6. `List[Str]` gained a parameter/return representation (`pep_list_str` already
   existed for list values), a literal argument lowering with static `pep_str`
   elements, parameter forwarding, and a `length()` case.
7. A list record field now accepts a **matching list parameter** in addition to a
   literal. Forwarding copies the descriptor only, so the caller keeps ownership of
   the element storage; a non-matching parameter type is refused.
8. `pep_c23_field_value_may_fail` was renamed `pep_c23_infallible_value` and is
   now shared by record construction and the many-argument path — the first place
   where string and list literals are routinely arguments. Its scope is unchanged:
   one- and two-argument programs execute exactly the previous predicate.

## Step cost: a regression I caught and closed

Recording this because a focused suite did not catch it, and because the first two
fixes I tried both made it worse.

My first routing sent **every** three-or-more-parameter call through the general
ordered path. That path re-walks the parameter and argument lists per call site, and
it pushed four int-collection programs over the emitter's unchanged 100k step budget.
They pass at the parent and failed reproducibly in an isolated sequential run:

| test | parent `26be4be` | first routing | minimal routing |
| --- | --- | --- | --- |
| `..._count_outside`, `..._int_all_between`, `..._int_any_between`, `..._int_product_between` | 0 failures | **8 failures** | **0 failures** |
| `..._int_last_outside`, `..._sum_between` | 14 failures | 4 failures | **2 failures** |

Two further rounds of measurement were needed, each isolating one variable:

| revision | routing | ordered-parameter collection | failures on the four-test group |
| --- | --- | --- | --- |
| parent `26be4be` | fixed slots only | n/a | 6 |
| `a602659` | three or more | count + indexed lookup per parameter | **24** |
| `3ff56de` | four or more, plus a three-parameter fallback | count + indexed lookup | 14 |
| current | four or more only | single pass | **4** |

Two conclusions, both from measurement rather than reasoning:

- Routing three-parameter calls through the general path made things **worse**, not
  better, for these programs. It was removed; one- to three-argument calls keep the
  fixed-slot paths exactly.
- The real cost was `pep_c23_ordered_children`, which collected parameters with a
  count query plus one indexed lookup per element — several full AST scans per
  function, twice per function (prototype and definition). It now collects in a
  single pass and falls back to indexed lookups only if arrival order is not
  ascending by `childIndex`. That alone moved the group from 14 failures to **4**,
  better than the parent's 6.

Note on method: my first two whole-suite collection runs (parent 213 failures,
branch 229) were taken while other heavy suites ran concurrently on the same
machine, and they disagree with isolated sequential measurement in both directions.
I therefore treat only the isolated, sequential comparisons above as evidence, and
I make no claim about the collections module's total failure count.

## A2-3 — native evidence

`tests/test_c23_arity.py` — 11 tests, all pass:

| case | clang | gcc | interpreter |
| --- | --- | --- | --- |
| scalar arity 3, 4, 5, 6, 7, 8 (`sum(1..n)`) | ok | ok | ok |
| all four parameters bind, fourth returned | ok | ok | ok |
| mixed `Int`/`Bool`/5 parameters with a conditional body | ok | ok | ok |
| record parameters at arity 3 and 4 | ok | ok | ok |
| one fallible argument among four | ok | ok | ok |
| unchanged one- and two-parameter calls | ok | ok | ok |

`tests/test_c23_list_record_fields.py` — now 18 tests, 17 pass, 1 documented skip;
new this slice:

| case | result |
| --- | --- |
| `make_tok(kind, parts: List[Str], count) -> Tok` forwarding `parts` into a `List[Str]` field, called with a literal | clang ok, gcc ok, interpreter ok |
| `List[Str]` literal argument + parameter forwarding through two frames | clang ok, gcc ok, interpreter ok |
| `List[List[Int]]` field | still refused: `record fields require Int, Bool, or a preceding record declaration` |

Fail-closed boundaries preserved and tested: two fallible arguments
(`rejects multiple fallible call arguments`), arity mismatch (the checker rejects
it first), unsupported `Str` result, and non-matching list parameter types.

### Measured boundary, stated plainly

The acceptance gate asks for 8/11/16-arity fixtures. What the evidence supports:

- **8 parameters: verified natively** end-to-end through checker, emitter, C
  compilation and execution on both compilers.
- **11 and 16 parameters: cannot be verified end-to-end at this revision.** A
  program with 9 or more parameters already exceeds the Pep-written checker's
  fixed 100k-step per-invocation budget at `check parsed source`, before the
  emitter runs. This is pinned as
  `test_high_arity_is_bounded_by_the_checker_not_the_emitter`, which asserts the
  program is never refused *for an arity reason* — it either emits or stops with
  `PEP_RUNTIME_STEP_LIMIT`.
- The real `make_token` (8 parameters) and `make_cursor` (16 parameters) remain
  unreachable for the same checker reason, not for arity.

The emitter's arity handling is therefore complete and unit-tested past the
point the checker can currently reach; no budget was raised and no cap changed.

### Lexer closure recount

Real declarations in `examples/pep_lexer.pep`, emitted with dependency closure:

| declaration / constructor | parent `052d894` | now | blocking stage |
| --- | --- | --- | --- |
| `SourcePosition`, `Utf8Check`, `LexToken`, `LexCursor` | emit | emit | — |
| `LexProgress` closure | checker budget | checker budget | checker |
| `make_token` (8 parameters) | emitter-refused (arity) | **checker budget** | checker |
| `make_cursor` (16 parameters) | emitter-refused (arity) | **checker budget** | checker |
| `make_progress` (11 parameters) | emitter-refused (arity) | **checker budget** | checker |
| `lexer_step` | checker envelope | checker envelope | checker |

Every constructor moved one stage forward: from an emitter arity refusal to a
checker step-budget stop. That is real progress towards the native lexer even
though no constructor is natively executable yet.

## What remains, by stage

1. **Checker step budget (first order, other agent's lane).** 9+ parameters, the
   `LexProgress` closure, and all three real constructors stop at
   `check parsed source`. Handed to the first current agent with exact
   reproducers (see the outbox receipt).
2. **Native recursion (pre-existing, any arity).** Recursive calls inside an
   if-expression branch are refused, and `test_recursive_native_calls_enforce_pep_depth`
   is one of the three remaining `test_a14_c23` failures inherited from the
   parent. Not an arity problem.
3. **One- to three-argument calls and two literal arguments.** Calls with one to
   three arguments keep the fixed-slot path and its pre-existing restrictions: two
   literal arguments are still refused by the conservative evaluation-order guard,
   and a three-parameter call whose result is not call-free, parameter-based or
   conditional is still refused (`three-parameter calls require three arguments and a
   call-free result`). Both are pinned by tests. Left untouched deliberately: those
   paths run for almost every program, and every attempt to move them measured worse
   on unrelated collection programs.
4. **List[Str] local bindings** are unsupported (`immutable collection bindings
   require ...`), so a `List[Str]` value cannot yet be built and mutated locally.
5. **Bounded emitter input (A2-4)** — not started; the >1 MiB one-shot checked-AST
   handoff is still open and needs an agreed revision-bound interface with the
   checker owner.

## Reproducing

```
python -m unittest tests.test_c23_arity -v
python -m unittest tests.test_c23_list_record_fields -v
python -m unittest tests.test_c23_nested_record_emission tests.test_c23_str_contains tests.test_c23_cli
```

No `master`, `CURRENT.md`, manifest, milestone or release state changed. The first
current agent's checkout, its uncommitted `tests/test_a14_c23.py` edit, its Pep Lab
and Workshop files, and its checker/host paths were not touched. Defender settings
and the excluded Clang vector are untouched.
