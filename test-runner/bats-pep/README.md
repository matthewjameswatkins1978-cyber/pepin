# First Pep-written Terror Bats oracle

A real Terror Bats judgement written in ordinary Pep: the `exit_code`
falsification condition, evaluated by Pep's own checker and interpreter.

This is not a wrapper and not a reimplementation of the framework in another
language. It is the smallest honest kernel of "Terror Bats in Pep": given recorded
observations, decide whether the claim was falsified, with the same verdict
semantics as the Rust reference.

## Reference contract pinned, not guessed

Read from The-Terror-Bats `@ d5e6404` (`src/oracle.rs`):

```rust
Condition::ExitCode { step, equals: Option<i64>, not_equals: Option<i64> }
```

| Reference behaviour | Source |
| --- | --- |
| exactly one of `equals` / `not_equals`, else INVALID | `validate`: "exit_code requires exactly one of `equals` or `not_equals`" |
| bad step reference → Undetermined | `eval_condition` |
| step did not execute → Undetermined | `eval_condition` |
| step produced no exit code → Undetermined (a crash is never a falsification) | `eval_condition` |
| `fired = (code == equals)` / `fired = (code != not_equals)` | `eval_condition` |
| `fired ? Falsified : NotFalsified` | `OracleResult` |

Verdict labels in the reference and here: `Falsified` → **PROVEN**,
`NotFalsified` → **NOT OBSERVED** (never a certificate), `Undetermined` →
**INCONCLUSIVE**, malformed spec → **INVALID**.

## The Pep implementation (typed)

`oracle.pep` — ordinary functions over typed values, no host process spawning, no
imports, and no sentinel:

```pep
type Mode = EqualsMode(Int) | NotEqualsMode(Int) | BothModes(Int, Int) | NoMode(Str)
type ExitObservation = ObservedExit(Int) | AbsentExit(Str)
type EvidenceStep { phase: Str, index: Int, exit: ExitObservation }
type Verdict = Proven(Str) | NotObserved(Str) | Inconclusive(Str) | Invalid(Str)
```

- `judge(mode, observation)` — validation first (a malformed mode is `Invalid`,
  never evidence about the claim), then `AbsentExit` is `Inconclusive`, then the
  reference's fired/not-fired rule.
- `judge_step(mode, step)` — the same judgement over a recorded evidence record.
- `verdict_label(verdict)` / `verdict_reason(verdict)` — the label and the reason a
  verdict carries, so a result explains itself.

Missing evidence is now an explicit `AbsentExit(reason)` case instead of a sentinel
integer, and a malformed specification is a representable `BothModes`/`NoMode`
instead of two booleans that could contradict each other.

## Condition composition

`OracleExpr::All` / `Any` / `Not` are Kleene three-valued logic in the reference,
not boolean logic, and an empty conjunction is **not** vacuously true. The Pep
engine now reproduces that shape over its own typed verdicts:

```pep
type Found = NotFound() | FoundReason(Str)
fn compose_all(verdicts: List[Verdict]) -> Verdict
fn compose_any(verdicts: List[Verdict]) -> Verdict
fn compose_not(verdict: Verdict) -> Verdict
```

| Rule | Reference (`src/oracle.rs`) | Here |
| --- | --- | --- |
| `all` | NotFalsified wins, then Undetermined, then Falsified | `NotObserved` > `Inconclusive` > `Proven` |
| `any` | Falsified wins, then Undetermined, then NotFalsified | `Proven` > `Inconclusive` > `NotObserved` |
| `not` | swaps Falsified/NotFalsified, leaves Undetermined | swaps `Proven`/`NotObserved`, leaves `Inconclusive` |
| `all: []` / `any: []` | Undetermined, "empty combinator: nothing to judge" | `Inconclusive("empty combinator: nothing to judge")` |
| malformed child | `validate` runs on every node before `evaluate`, so nothing is evaluated | the child's `Invalid` propagates carrying its own reason |

Composition is written as assignment in priority order — least decisive first, most
decisive last — so the surviving verdict is the most decisive finding and no
`if`-nesting is needed. `Invalid` is assigned last because a malformed experiment
must never be composed into a judgement, the same principle as case 9.

Because each component is an ordinary function, composition composes: `compose_not`
of `compose_all` of any list of `judge(...)` results is just a call.

## Judgement trail

A verdict that only prints a label cannot be audited. The reference records one
`ConditionOutcome { condition, result, note }` per leaf and an `OracleEvaluation
{ result, conditions }` around them, so the Pep engine now does the same:

```pep
type ConditionOutcome { label: Str, verdict: Verdict }
type Evaluation { result: Verdict, trail: List[ConditionOutcome] }

fn outcome(label: Str, verdict: Verdict) -> ConditionOutcome
fn evaluate_all(trail: List[ConditionOutcome]) -> Evaluation
fn evaluate_any(trail: List[ConditionOutcome]) -> Evaluation
fn evaluate_not(negated: ConditionOutcome) -> Evaluation
fn explain(evaluation: Evaluation) -> Unit        // human-readable
fn say_trail(evaluation: Evaluation) -> Unit      // machine-readable
```

Two details are copied deliberately rather than invented:

- **A combinator does not record itself.** Only leaves appear in the trail. The one
  exception is a childless `all`/`any`, which records the synthetic outcome
  `("all: []", Undetermined, "empty combinator: nothing to judge")` because
  otherwise nothing in the trail would explain the verdict.
- **`not` records the leaf, not the negation.** The leaf keeps the verdict it
  actually reached and only the composed result inverts, because "what was seen"
  and "what was concluded" are different facts.

Leaf labels use the reference's own `describe(cond)` wording — `exit_code run:0
equals 1` — so a Pep trail and a Rust receipt trail are directly comparable. The
differential exploits exactly that.

`say_trail` emits one record per line (`RESULT <label>`, then repeated `LEAF
<condition> <label>`) because Pep has no `Str` concatenation, so a positional
format is the honest one.

## Recursive oracle expression

Composition over a flat list is not the reference's shape. `OracleExpr` is a
recursive tree, and A4 recursive tagged unions make that expressible directly:

```pep
type OracleExpr =
  LeafNode(ConditionOutcome) |
  AllNode(List[OracleExpr]) |
  AnyNode(List[OracleExpr]) |
  NotNode(OracleExpr)

fn evaluate_tree(expr: OracleExpr) -> Evaluation
```

Two facts were measured against the real framework before this was written, because
guessing either one yields a wrong oracle that still looks plausible:

1. **A combinator combines its direct child RESULTS, not the flattened leaves.**
   Kleene AND/OR are associative, so for pure nesting the difference is invisible —
   but it is decisive once `not` is nested. Measured: with exit 1,
   `all[not(equals 0), equals 1]` is **PROVEN** in the reference (the leaves are
   `NotFalsified` and `Falsified`; `not(NotFalsified)` is `Falsified`, and
   `Falsified AND Falsified` is `Falsified`). Flattening the leaves instead gives
   `NotFalsified AND Falsified` = NOT OBSERVED. The self-test case and the
   differential both pin that case precisely for this reason.
2. **The trail is depth-first, left to right**, leaves only, and `not` leaves the
   child's trail untouched while inverting only the result it returns.

So `evaluate_tree_all` accumulates two parallel things: each child's composed
`Verdict` for the Kleene step, and each child's trail concatenated in evaluation
order for the explanation. The two are deliberately not derived from each other.

## Multi-step evidence and step references

An `exit_code` condition names a step. Reading `eval_condition` closely shows the
reference resolves that name in three ordered steps, and that only two of them are
evidence problems:

| Order | Reference step | On failure |
| --- | --- | --- |
| 1 | `parse_step_ref(step)` | **validation** — the spec is INVALID |
| 2 | `find_step(steps, phase, index)` | Undetermined, `step ... did not execute` |
| 3 | `record.exit_code` | Undetermined, `step ... produced no exit code` |

Step 1 is the surprising one. It is tempting to model an unknown phase as the
defensive `bad step reference` → Undetermined branch inside `eval_condition`, but
`validate_condition` calls `parse_step_ref` first, so the spec never reaches
evaluation. Measured against the framework:

| Spec step | Verdict |
| --- | --- |
| `run:0` | PROVEN / NOT OBSERVED, depending on `equals` |
| `run:9` (not executed) | INCONCLUSIVE |
| `setup:0` (wrong phase, no such record) | INCONCLUSIVE |
| `bogus:0` (unknown phase) | **INVALID** |
| `run0` (no colon) | **INVALID** |
| `run:x` (non-numeric index) | **INVALID** |

So `judge_step_ref` validates the mode and the phase first and answers `Invalid` for
either, matching the reference's validate-before-evaluate ordering and the same
vacuity principle as self-test case 9.

```pep
type EvidenceStep { phase: Str, index: Int, exit: ExitObservation }

type StepResolution =
  ResolvedExit(Int) |
  StepNotExecuted(Str) |
  StepHasNoExitCode(Str)

fn judge_step_ref(mode: Mode, steps: List[EvidenceStep], phase: Str, index: Int) -> Verdict
```

`EvidenceStep` gained a `phase` because a step record genuinely has one, and because
without it `judge_step_ref` could not tell `run:0` from `setup:0`.

The two evidence causes are kept apart on purpose. `judge_step(mode, step)` over a
single step cannot distinguish "this step never executed" from "this step ran and
produced no exit code", and those are different facts about a run:

| Case | Verdict | Reason |
| --- | --- | --- |
| `run:9` against a record containing only `run:0` | INCONCLUSIVE | `step did not execute` |
| `run:0` present with `AbsentExit("process killed")` | INCONCLUSIVE | `process killed` |

`find_step` searches in record order and the first match wins, which is the
reference's `steps.iter().find(...)`. Matching requires both phase **and** index, so
a resolver that matched on index alone would wrongly resolve `setup:0`.

## Condition: `evidence_present`

The first leaf condition here that is not `exit_code`, and it is fully expressible
because the reference reads it from captures rather than from the filesystem:

```pep
type Capture = CaptureAbsent() | CapturePresent()
type Captures { git_diff: Capture, git_status: Capture, base_snapshot: Capture }

fn judge_evidence_present(kind: Str, captures: Captures) -> Verdict
```

`git_diff`, `git_status` and `base_snapshot` are present → PROVEN; absent → NOT
OBSERVED; any other kind → INCONCLUSIVE.

**Two measured findings, and the first one contradicts the step-reference rule.**

1. An unknown kind is **INCONCLUSIVE, not INVALID.** `evidence_present` has no rule
   in `validate_condition`, so `kind: bogus` is an evaluation problem. That is the
   exact opposite of a malformed step reference, which is a validation problem. The
   two conditions look similar and behave differently, which is why each condition is
   measured instead of generalised from the previous one.
2. The runner **always** captures git state. `git_diff`, `git_status` and
   `base_snapshot` are PROVEN even with `capture: []`, so the absence branch cannot be
   reached by an ordinary spec run. It is modelled anyway, from the source's
   `is_some()`, because absence is representable in the reference's type and a model
   that cannot express it would be a weaker model. The self-test covers it; the
   differential does not claim it.

Dispatch is on the kind name and therefore per-capture, not "is any capture present".
Self-test case 55 exists to catch that specific shortcut: with only `git_status`
present, asking for `git_diff` must answer NOT OBSERVED.

## Conditions: `file_exists` and `file_absent`

These judge a **recorded** view of the worktree rather than the live filesystem, for
the same reason the exit-code condition judges recorded steps: this engine evaluates
evidence, it does not perform the run. A driver supplies what it observed and Pep
decides.

```pep
type WorktreeView { present_paths: List[Str], rejected_paths: List[Str] }

fn judge_file_exists(path: Str, view: WorktreeView) -> Verdict
fn judge_file_absent(path: Str, view: WorktreeView) -> Verdict
```

Measured against the framework:

| Case | Verdict |
| --- | --- |
| `file_exists ".git"` | PROVEN |
| `file_exists "no-such-file.txt"` | NOT OBSERVED |
| `file_absent ".git"` | NOT OBSERVED |
| `file_absent "no-such-file.txt"` | PROVEN |
| `file_exists "../outside.txt"` | INCONCLUSIVE |
| `file_exists "C:/Windows/system.ini"` | INCONCLUSIVE |

`rejected_paths` exists because the reference distinguishes a path it refused
(`resolve_in_worktree` error → Undetermined) from a path it checked and did not find
(NotFalsified). Collapsing the two would let a broken experiment look like a clean
negative result, which is the same error the vacuity guard exists to prevent.

**Not attempted, deliberately:** `resolve_in_worktree` normalisation itself —
rejecting `..` escapes, absolutising, symlink policy. Pep has no string manipulation,
so a path either arrives worktree-relative or arrives in `rejected_paths` as a host
fact. That boundary is recorded rather than faked.

This is also the first condition to use `contains` over `List[Str]` (scalar list
membership), which exists and works.

## Evidence-driven trees: all four conditions composed

Until here the tree judged leaves that had already been judged. This section judges
**conditions** against run evidence, so one oracle can mix condition types — which is
what a real bat does, and the first time this engine composes more than one condition
type in a single judgement.

```pep
type Condition =
  ExitCodeCondition(Mode, Str, Int) |
  EvidencePresentCondition(Str) |
  FileExistsCondition(Str) |
  FileAbsentCondition(Str)

type RunEvidence {
  steps: List[EvidenceStep],
  captures: Captures,
  worktree: WorktreeView
}

type EvidenceExpr =
  ConditionLeaf(Str, Condition) |
  AllOf(List[EvidenceExpr]) |
  AnyOf(List[EvidenceExpr]) |
  NotOf(EvidenceExpr)

fn evaluate_evidence_tree(expr: EvidenceExpr, evidence: RunEvidence) -> Evaluation
```

Measured against the framework (exit 1, clean clone):

```yaml
oracle:
  all:
    - { type: exit_code, step: run:0, equals: 1 }
    - { type: evidence_present, kind: git_diff }
    - { type: file_exists, path: ".git" }
    - { type: file_absent, path: "no-such-file.txt" }
```

→ **PROVEN**, four leaves, in exactly that order, with labels `exit_code run:0 equals
1`, `evidence_present git_diff`, `file_exists .git`, `file_absent no-such-file.txt`.
The differential compares result *and* the full leaf trail for four such trees.

`EvidenceExpr` is a second tree type rather than a fifth case on `OracleExpr`. A leaf
here is a condition still to be judged, not a finished judgement; without generics on
this base one parameterised tree cannot be both, and keeping them apart keeps
`evaluate_tree`'s contract exactly as it was — it never has to answer a node it has no
evidence for.

Leaf labels are supplied by the caller because the reference's `describe(cond)`
renders arguments (`exit_code run:0 equals 1`) and Pep has no string concatenation.
The label is descriptive text; every verdict is still decided in Pep.

`condition_name(condition)` gives the bare kind name for callers that do not need the
arguments.

## Run it

```powershell
cd test-runner/bats-pep
.\..\..\pep.ps1 check oracle.pep --json          # status valid, 0 diagnostics
# selftest calls run at top level because the interpreter does not call fn main
$lib = Get-Content oracle.pep -Raw; $st = Get-Content selftest.pep -Raw
New-Item -ItemType Directory -Force -Path ..\..\_build | Out-Null
[IO.File]::WriteAllText("$PWD\..\..\_build\composed.pep", $lib + "`n" + $st, [Text.UTF8Encoding]::new($false))
.\..\..\pep.ps1 run ..\..\_build\composed.pep
```

Observed (67 cases; each prints its verdict label then its reason):

| # | Inputs | Verdict |
| --- | --- | --- |
| 1 | `EqualsMode(1)`, `ObservedExit(1)` | PROVEN |
| 2 | `EqualsMode(1)`, `ObservedExit(0)` | NOT OBSERVED |
| 3 | `NotEqualsMode(0)`, `ObservedExit(0)` | NOT OBSERVED |
| 4 | `NotEqualsMode(0)`, `ObservedExit(2)` | PROVEN |
| 5 | `EqualsMode(7)`, `ObservedExit(3)` | NOT OBSERVED |
| 6 | `BothModes(1, 0)`, `ObservedExit(1)` | INVALID |
| 7 | `NoMode(...)`, `ObservedExit(1)` | INVALID |
| 8 | `EqualsMode(1)`, `AbsentExit(...)` | INCONCLUSIVE |
| 9 | `BothModes(1, 0)`, `AbsentExit(...)` | INVALID (validation outranks missing evidence) |
| 10 | `judge_step` over `EvidenceStep{exit: ObservedExit(1)}` | PROVEN |
| 11 | `judge_step` over `EvidenceStep{exit: AbsentExit(...)}` | INCONCLUSIVE |
| 12 | `compose_all([Proven])` | PROVEN |
| 13 | `compose_all([Proven, Proven])` | PROVEN |
| 14 | `compose_all([Proven, NotObserved])` | NOT OBSERVED |
| 15 | `compose_all([Proven, Inconclusive])` | INCONCLUSIVE |
| 16 | `compose_all([Inconclusive, NotObserved])` | NOT OBSERVED |
| 17 | `compose_all([])` | INCONCLUSIVE (empty combinator) |
| 18 | `compose_all([Proven, Invalid(...)])` | INVALID (child's own reason survives) |
| 19 | `compose_any([NotObserved, Proven])` | PROVEN |
| 20 | `compose_any([NotObserved, NotObserved])` | NOT OBSERVED |
| 21 | `compose_any([NotObserved, Inconclusive])` | INCONCLUSIVE |
| 22 | `compose_any([Inconclusive, Proven])` | PROVEN |
| 23 | `compose_any([])` | INCONCLUSIVE (empty combinator) |
| 24 | `compose_any([Proven, Invalid(...)])` | INVALID |
| 25 | `compose_not(Proven)` | NOT OBSERVED |
| 26 | `compose_not(NotObserved)` | PROVEN |
| 27 | `compose_not(Inconclusive)` | INCONCLUSIVE |
| 28 | `compose_not(Invalid)` | INVALID |
| 29 | `compose_all` over two real `judge(...)` verdicts | NOT OBSERVED |
| 30 | `evaluate_all` over two Proven leaves | PROVEN |
| 31 | `evaluate_all` over Proven + NotObserved | NOT OBSERVED |
| 32 | `evaluate_any` over NotObserved + Proven | PROVEN |
| 33 | `evaluate_all([])` | INCONCLUSIVE |
| 34 | `evaluate_not(Proven leaf)` | NOT OBSERVED |
| 35 | `evaluate_all` over Proven + Invalid child | INVALID |
| 36 | `evaluate_tree(LeafNode(Proven leaf))` | PROVEN |
| 37 | `all[not(equals 0), equals 1]` on exit 1 | PROVEN (the flattening discriminator) |
| 38 | `not(all[equals 1, equals 1])` | NOT OBSERVED |
| 39 | `all[any[equals 0, equals 1], equals 1]` | PROVEN |
| 40 | `any[not(equals 1), equals 0]` | NOT OBSERVED |
| 41 | `evaluate_tree(AllNode([]))` | INCONCLUSIVE |
| 42 | `run:0` exit 1, `equals 1` | PROVEN |
| 43 | `run:0` exit 1, `equals 0` | NOT OBSERVED |
| 44 | `run:9` against `[run:0]` | INCONCLUSIVE (`step did not execute`) |
| 45 | phase `bogus` | INVALID (`bad step reference: unknown phase`) |
| 46 | `setup:0` against `[run:0]` | INCONCLUSIVE (phase guard) |
| 47 | `run:0` present with `AbsentExit(...)` | INCONCLUSIVE (`process killed`) |
| 48 | `[run:0 exit 1, run:1 exit 2]`, `run:1`, `equals 2` | PROVEN (index guard) |
| 49 | `BothModes` with an empty step list | INVALID (vacuity guard) |
| 50 | `git_diff`, all captures present | PROVEN |
| 51 | `git_diff`, nothing captured | NOT OBSERVED |
| 52 | `git_status`, all present | PROVEN |
| 53 | `base_snapshot`, nothing captured | NOT OBSERVED |
| 54 | kind `bogus` | INCONCLUSIVE (`unknown evidence kind`) |
| 55 | `git_diff` absent but others present | NOT OBSERVED (dispatch guard) |
| 56 | `file_exists ".git"` | PROVEN |
| 57 | `file_exists "no-such-file.txt"` | NOT OBSERVED |
| 58 | `file_absent ".git"` | NOT OBSERVED |
| 59 | `file_absent "no-such-file.txt"` | PROVEN |
| 60 | `file_exists "../outside.txt"` (rejected path) | INCONCLUSIVE |
| 61 | `file_absent` absolute path (rejected) | INCONCLUSIVE |
| 62 | `all` of exit + evidence + `file_exists` + `file_absent` | PROVEN |
| 63 | `all` of exit fires + `file_exists` misses | NOT OBSERVED |
| 64 | `any` of `file_exists` missing + present | PROVEN |
| 65 | `not` of `file_exists .git` | NOT OBSERVED |
| 66 | `all` with no children | INCONCLUSIVE |

Then `trail_size` of the case-62 tree is `4`.

Then `trail_size` of a two-leaf evaluation is `2`, `trail_size` of
`evaluate_all([])` is `1` (the synthetic empty-combinator outcome), `trail_size` of
the case-39 tree is `3`, and `explain` prints the composed verdict followed by
every leaf: label, verdict, reason.

Case 9 is the vacuity guard: a malformed experiment must never be reported as
merely inconclusive, and case 5/6 are the infrastructure guard: missing evidence
must never be reported as a falsification.

An earlier draft of this table expected NOT OBSERVED for `equals 0, exit 0`; that
expectation was wrong, because `equals` fires when the code equals the configured
value. The table was corrected, not the oracle — recorded here because a wrong
expectation is indistinguishable from a wrong implementation until it is checked.

## Grammar and checker rules measured here (for Agent 1, minimal repros)

Each of these cost real time, so each is recorded with the smallest case that shows
it:

1. **Nullary constructors ARE matchable — with `B()`.** An earlier revision of this
   file claimed they were not. That was wrong, and Agent 1 confirmed the actual
   grammar: `B()` is a nullary constructor pattern while bare `B` is a binding.
   Measured here: `type Found = NotFound() | FoundReason(Str)` with
   `match f { NotFound() => "none"` / `FoundReason(r) => r }` is accepted and
   behaves correctly, so `compose_*` uses `NotFound()` patterns. What *is* true is
   that a bare `B` arm is an irrefutable catch-all, so any arm after it is rejected
   with `PEP_UNREACHABLE_MATCH_ARM: Match arm follows an irrefutable pattern`.
2. **A nullary constructor must be declared with empty parentheses.** `type T = A(Int) | B`
   fails with `PEP_PARSE_EXPECTED: Expected '('`.
3. **Match arms are newline-separated, and arm bodies are expressions.** Two arms on
   one line parse as one; `P(why) => { return "X" }` fails with
   `PEP_PARSE_EXPRESSION: Expected an expression` where the `{` starts.

4. **`if` requires an `else`, even an empty one.** `if c { ... }` followed by a new
   line is rejected with `PEP_PARSE_ELSE: Expected else after if block`. `else { }`
   with an empty body is accepted, and that is what the composition loops use.
5. **There are no ordering comparisons.** `<` is not a token at all
   (`PEP_UNEXPECTED_CHARACTER: Unexpected character '<'`), and `>` / `>=` are absent
   from the operator table. Available: `<=`, `==`, `!=`, `&&`, `||`, `+`, `-`, `*`,
   `/`. A loop counter must therefore be driven by `==`, `!=` or `<=`.
6. **A match arm body cannot be an assignment.** `P(w) => acc = found` fails with
   `PEP_PARSE_PATTERN: Expected a constructor pattern, binding, or wildcard` — a
   different error from the `{ ... }` case in rule 3. Assign in an enclosing `if`
   block around a `match` that returns a value.7. **`var` may hold a union and be reassigned across its cases.** `var acc =
   NotFound()` then `acc = FoundReason(...)` type-checks, and `for x in xs` over a
   `List[Union]` binds each element at the union type.

## Language dependencies found (for Agent 1, reproducible)

1. **No `Str` concatenation.** `"a" + b` is `PEP_TYPE_MISMATCH: Expected Int but
   found Str`, so a verdict message cannot be composed inline; the self-test emits
   positional lines instead. This is the main blocker for human-readable verdicts.
2. **No generic option type.** There is no `Option[T]`, but a dedicated union per
   absence is the honest substitute and it works: `AbsentExit(reason)` for a
   missing exit code, and `NotFound()` / `FoundReason(r)` for a searched-for value.
   No sentinel is needed.
3. **The interpreter does not call `fn main`.** Top-level statements execute, so a
   library entry point cannot be exercised by the interpreter today; the self-test
   is therefore top-level calls rather than a `main`.
4. **No `Str` → bytes, so `text_contains` still cannot be implemented.** This is a
   measured wall, not a guess:

   | Attempt | Result |
   | --- | --- |
   | `byte_length("abc")` | `PEP_TYPE_MISMATCH: Expected SourceBytes but found Str` |
   | `byte_length(s)` for a `s: Str` parameter | `PEP_TYPE_MISMATCH: Expected SourceBytes but found Str` |
   | `length("abc")` | `PEP_LIST_EXPECTED: Builtin 'length' expects a List, found Str` |
   | `contains("abcdef", "cd")` | `PEP_LIST_EXPECTED: Builtin 'contains' expects a List, found Str` |
   | `byte_length(source_bytes())` | checks, but `PEP_RUNTIME_SOURCE_CONTEXT: source_bytes is available only for a host-authorised v2 semanticTarget` |

   `byte_at`, `byte_slice` and `utf8_slice` all take `SourceBytes`, and the only
   producer of `SourceBytes` is `source_bytes()`, which reads the program's **own**
   source under a host-authorised v2 semanticTarget. `contains` is list membership
   with scalar element equality, not substring search. `Str` supports `==` and `!=`
   and nothing else.

   **The precise missing primitive** is either
   - `str_bytes(s: Str) -> SourceBytes`, after which `byte_length` / `byte_at`
     suffice for a byte-window substring search; or
   - `str_contains(haystack: Str, needle: Str) -> Bool` directly.

   Until one exists, `text_contains`'s judgement is not attempted: it is neither
   approximated nor delegated to Python. Composition over the conditions that *are*
   expressible is what shipped instead.

## Same-input differential against the Rust runtime

`differential.py` judges the *same* inputs twice: once with a real framework Bat
whose attack step exits with the chosen code, and once with `oracle.pep` under
Pep's interpreter. Run with `--repo <clean clone>` (default
`D:\Projects\wt-bats-clean`).

| Case | Rust runtime | Pep oracle | Expected |
| --- | --- | --- | --- |
| `equals 1`, exit 1 | PROVEN | PROVEN | PROVEN |
| `equals 1`, exit 0 | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| `not_equals 0`, exit 0 | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| `not_equals 0`, exit 2 | PROVEN | PROVEN | PROVEN |
| `equals 7`, exit 3 | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| both modes set | INVALID | INVALID | INVALID |
| neither mode set | INVALID | INVALID | INVALID |
| supervised process killed before exit | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |
| `all: []` | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |
| `any: []` | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |
| `all` fired + not fired | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| `any` not fired + fired | PROVEN | PROVEN | PROVEN |
| `not` fired | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| `not` not fired | PROVEN | PROVEN | PROVEN |
| `all` with a malformed child | INVALID | INVALID | INVALID |
| `any` with an unparseable child | INVALID | INVALID | INVALID |
| `all` with an unexecuted step (`run:9`) | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |

Composition is one claim; the trail is a stronger one. For six more specs the
differential compares Rust's own `oracle.conditions` against the Pep `Evaluation`
trail — the same leaf labels and the same per-leaf verdicts, not just the same
composed result:

| Trail case | Leaves | Rust trail | Pep trail |
| --- | --- | --- | --- |
| `all` fired + not fired | 2 | `Falsified`, `NotFalsified` | PROVEN, NOT OBSERVED |
| `all` fired + fired | 2 | `Falsified`, `Falsified` | PROVEN, PROVEN |
| `any` not fired + fired | 2 | `NotFalsified`, `Falsified` | NOT OBSERVED, PROVEN |
| `not` not fired | 1 | `NotFalsified` | NOT OBSERVED |
| `all: []` | 1 | `all: []` Undetermined | INCONCLUSIVE (synthetic) |
| `all` fired + unexecuted step | 2 | `Falsified`, `Undetermined` | PROVEN, INCONCLUSIVE |
| `all[not(equals 0), equals 1]` | 2 | `NotFalsified`, `Falsified` | NOT OBSERVED, PROVEN |
| `not(all[equals 1, equals 1])` | 2 | `Falsified`, `Falsified` | PROVEN, PROVEN |
| `all[any[equals 0, equals 1], equals 1]` | 3 | `NotFalsified`, `Falsified`, `Falsified` | NOT OBSERVED, PROVEN, PROVEN |
| `any[not(equals 1), equals 0]` | 2 | `Falsified`, `NotFalsified` | PROVEN, NOT OBSERVED |

Those four nested rows are what distinguish "combines child results" from "combines
flattened leaves": in each one the flattened composition answers differently from
the reference, and the Pep engine matches the reference.

Step references are compared separately, as verdict-only cases, because an INVALID
spec is never evaluated and therefore has no trail:

| Step reference | Rust runtime | Pep oracle | Expected |
| --- | --- | --- | --- |
| `step: run:0` | PROVEN | PROVEN | PROVEN |
| `step: run:9` (not executed) | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |
| `step: setup:0` (wrong phase) | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |
| `step: bogus:0` (unknown phase) | INVALID | INVALID | INVALID |

`evidence_present` is compared as verdict-only cases too:

| Evidence kind | Rust runtime | Pep oracle | Expected |
| --- | --- | --- | --- |
| `git_diff` | PROVEN | PROVEN | PROVEN |
| `git_status` | PROVEN | PROVEN | PROVEN |
| `base_snapshot` | PROVEN | PROVEN | PROVEN |
| `bogus` (unknown kind) | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |

`file_exists` / `file_absent` are compared against a clean clone, so `.git` is present
and `no-such-file.txt` is not:

| Case | Rust runtime | Pep oracle | Expected |
| --- | --- | --- | --- |
| `file_exists ".git"` | PROVEN | PROVEN | PROVEN |
| `file_exists "no-such-file.txt"` | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| `file_absent ".git"` | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |
| `file_absent "no-such-file.txt"` | PROVEN | PROVEN | PROVEN |
| `file_exists "../outside.txt"` | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |

Mixed-condition trees are compared on result **and** full leaf trail, so a leaf that
is judged correctly but recorded in the wrong order still shows up:

| Tree | Rust runtime | Pep oracle | Leaves |
| --- | --- | --- | --- |
| `all` of exit + evidence + `file_exists` + `file_absent` | PROVEN | PROVEN | 4 |
| `all` of exit fires + `file_exists` misses | NOT OBSERVED | NOT OBSERVED | 2 |
| `any` of `file_exists` missing + present | PROVEN | PROVEN | 2 |
| `not` of `file_exists .git` | NOT OBSERVED | NOT OBSERVED | 1 |

`SUMMARY cases=44 mismatches=0`.

One measurement worth recording: `terrorbats spec check` **accepts** a spec whose
`exit_code` sets both modes; the reference rejects it at **run** time with verdict
`INVALID` and `status: Invalid` ("oracle not evaluated"). The differential first
compared the wrong phase and reported a false disagreement. Validating the
validation-phase assumption is part of the work.

The "step produced no exit code" path is now compared at runtime too: the Bat
starts a supervised `Start-Sleep` process and kills it before it exits, so the step
has no exit code. The reference answers Undetermined and the Pep oracle answers
INCONCLUSIVE for the same recorded inputs (executed, no exit code). A kill or crash
is never a falsification on either side.

## Not claimed

- No process/Git host adapters, no receipts, no `pep bats` CLI, no native C23
  integration. Those are explicitly out of scope for this first kernel.
- `text_contains` is **not** implemented, because Pep cannot yet read the bytes of
  a `Str`. The precise missing primitive is recorded above rather than worked
  around.
- The differential covers the *expressible* slice. Process/Git host adapters,
  receipt generation and a `pep bats` CLI remain out of scope for this mission.
