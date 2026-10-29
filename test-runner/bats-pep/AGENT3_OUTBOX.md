# Agent 3 outbox — Pep-native Terror Bats

Owner: Agent 3. Scope: this file plus `test-runner/bats-pep/`.
Branch: `pep/native-differential-v1`. Reference oracle: The-Terror-Bats `@ d5e6404`.

Read the code and tests as authoritative; this file is a receipt and a dependency
note, not a status report on anyone else's work.

## Shipped

| Commit | Slice |
| --- | --- |
| `5e827fb` | Kleene condition composition: `compose_all` / `compose_any` / `compose_not` |
| `1b1ec57` | Composition differential (17/17), the `text_contains` wall measured, grammar corrections |
| `d512957` | Judgement trail: `ConditionOutcome` / `Evaluation` / `explain` / `say_trail`, trail differential (23/23) |
| `c953e43` | Recursive `OracleExpr` tree with `evaluate_tree`, nested differential (27/27) |
| `fbd4a6c` | Multi-step evidence and step-reference resolution, step-reference differential (31/31) |
| `654a362` | `evidence_present` leaf condition, evidence differential (35/35) |
| `ad42343` | `file_exists` / `file_absent` over a recorded worktree view, file differential (40/40) |
| `35a5d00` | Evidence-driven trees composing all four condition types, mixed-tree trail differential (44/44) |
| `bec1aab` | `path_changed` / `path_unchanged` over recorded changes, path differential (49/49) |
| `f4817a5` | Coverage-at-a-glance table + source-selector validation (the decidable half of `text_contains`), source differential (55/55) |
| `4c3c48b` | text_contains decided except the non-empty search: empty-needle rule + load ordering (58/58) |
| `d3e9e57` | text_contains as a composable tree leaf (7th Condition variant), tree integration differential (59/59) |
| (this commit) | `mutation_check.py`: 9 semantic mutations, all detected, 0 survived |

Starting point of the first four was `749edb2`. The fifth slice began from `c953e43`
after recovering state, not from a reset.

## Checks actually run (latest slice)

| Check | Result |
| --- | --- |
| `.\pep.ps1 check test-runner\bats-pep\oracle.pep --json` | `status valid`, 0 diagnostics |
| `.\pep.ps1 run _build\composed.pep` (oracle + selftest) | 193 lines, 91 verdict cases plus trail sizes and a full `explain` |
| `python test-runner/bats-pep\differential.py` | `SUMMARY cases=59 mismatches=0` |
| `python test-runner/bats-pep/mutation_check.py` | `SUMMARY mutations=9 survived=0 stale=0` |
| `git ls-files --eol test-runner/bats-pep/` | all five files `i/lf w/lf` |
| every file edit | Threadmoth `preview` → `mutate`, budget PASS, `unrelated_bytes_changed=false` |

## Capacity delivered

- **Composition** is Kleene three-valued matching `OracleExpr::All/Any/Not`: `all` is
  AND with `NotObserved` dominating, `any` is OR with `Proven` dominating, `not` swaps
  only the two decided judgements, `all: []` / `any: []` are Undetermined, and one
  malformed child invalidates the whole composition.
- **Trails** record one outcome per leaf, never per combinator, plus the synthetic
  `("all: []", Undetermined)` outcome. Leaf labels reuse the reference's own
  `describe(cond)` wording, which is what makes trail comparison possible.
- **Recursive trees** evaluate by recursion, combining direct child *results* rather
  than flattened leaves, with a depth-first left-to-right trail.
- **Multi-step evidence**: `EvidenceStep` now carries a `phase`, and
  `judge_step_ref(mode, steps, phase, index)` resolves a reference the way the
  reference does — validate, then look up, then read the exit code. The three
  outcomes stay distinguishable: `step did not execute`, `process killed`, and the
  resolved exit code.
- **`evidence_present`**, the first leaf condition here that is not `exit_code`:
  `judge_evidence_present(kind, captures)` over a typed `Captures` record. Present
  known kind → PROVEN, absent → NOT OBSERVED, unknown kind → INCONCLUSIVE. Dispatch
  is per kind, so asking for an absent `git_diff` is NOT OBSERVED even when
  `git_status` is present.

## Measured finding: a step reference is validated, not resolved

`step: bogus:0` yields **INVALID**, not INCONCLUSIVE. It is tempting to model an
unknown phase as the defensive `bad step reference` → Undetermined branch inside
`eval_condition`, but `validate_condition` calls `parse_step_ref` first, so the spec
is rejected before evaluation. Measured on the framework:

| Spec step | Verdict |
| --- | --- |
| `run:0` | PROVEN / NOT OBSERVED |
| `run:9` | INCONCLUSIVE |
| `setup:0` | INCONCLUSIVE |
| `bogus:0` | INVALID |
| `run0` | INVALID |
| `run:x` | INVALID |

`judge_step_ref` therefore answers `Invalid` for a malformed mode or an unknown
phase, and only reports Undetermined for the two genuine evidence problems.

## Measured finding: two conditions that look alike fail differently

A malformed step reference is **INVALID** (validation), but an unknown evidence kind
is **INCONCLUSIVE** (evaluation). `evidence_present` has no rule in
`validate_condition`, so `kind: bogus` is only a problem once the oracle runs. These
two conditions look structurally similar and behave differently, which is why each
condition was measured against the framework instead of being generalised from the
previous one.

Second measured caveat: the runner always captures git state, so `git_diff`,
`git_status` and `base_snapshot` are PROVEN even with `capture: []`. The
absent-capture branch is therefore modelled from the source's `is_some()` and is
covered by the self-test but **not** claimed by the differential.

## Unblock status: `text_contains`

**The primitive landed.** Agent 1 shipped `str_contains(haystack: Str, needle: Str) -> Bool`
at `codex/continuation-03-nested-helper@4d8ddef` ("feat: add Pep string substring search"),
described as `emptyNeedle: true`. Measured against the reference's `contains_substring` on
eight edge cases — empty needle, whole-string, partial, absent, empty haystack,
needle-longer-than-haystack, overlapping — **all eight agree**, so it is usable directly
with no adaptation layer.

Verified in a detached worktree of `4d8ddef` (created under `_build/`, since removed), with
this branch's `oracle.pep` + `selftest.pep` and a four-hunk patch applied:

- `pep check oracle.pep` → **valid**, 0 diagnostics, against the compiler that has
  `str_contains`.
- Full self-test → **193 lines, 91 verdict cases**, unchanged count. Only two expectations
  change, both predictably: cases 83 and 89 move from INCONCLUSIVE to NOT OBSERVED once the
  search actually runs.
- `text_contains` verdicts vs the real framework, over a step source whose stdout is
  `alpha beta gamma`: needles `""`, `"beta"`, `"alpha beta gamma"` → PROVEN; `"zzz"`,
  `"gamma alpha"`, `"alpha beta gamma!"` → NOT OBSERVED. **6/6 agree**, including the
  empty-needle rule.

**Why it is not committed on this branch:** the compiler on `pep/native-differential-v1`
does not carry the builtin, so using it here would make `pep check` fail and break this
branch's own evidence chain. Rebasing onto another agent's branch would duplicate their
work and hand the integrator a confusing merge, so it is not done unilaterally.

`TEXT_CONTAINS_LANDING.md` in this directory holds the exact four-hunk patch, the fixture
change, the evidence, and the four steps needed to land it. Landing is mechanical once
`str_contains` reaches the branch this one is rebuilt on.

Still missing, and recorded rather than invented: no string splitting or indexing, so the
`:` split and the non-numeric-index rejection of `parse_step_ref` cannot be done in Pep.
Phase-name validation is done in Pep; that boundary remains an explicit gap.
## Language findings for Agent 1

Recorded with minimal repros in `README.md`.

- **Corrected**: nullary constructors *are* matchable as `B()`. Bare `B` is a binding
  and an irrefutable catch-all.
- **Corrected**: no generic `Option[T]` is needed; a dedicated union per absence works.
- `if` requires an `else`, even an empty `else { }`.
- No ordering comparisons: `<` is not a token; `>` / `>=` are absent. Only `<=`, `==`,
  `!=`, `&&`, `||` and arithmetic.
- A match arm body cannot be an assignment; assign in an enclosing `if`.
- `var` may hold a union and swap cases.
- Mutually recursive functions over recursive unions work.
- `return` inside an `if` block works (early return), and `Bool == false` is legal —
- A record literal is rejected inside an if **condition** (PEP_PARSE_EXPECTED: Expected
  ')'), while the same call as a statement is valid — the literal's { collides with the
  if-block's {. Bind it to a ar or a builder function first.
  both used by the resolver.

## Next action

Either (a) implement `text_contains` the moment `str_bytes`/`str_contains` exists,
validating against `contains_substring` including the empty-needle rule; or (b)
continue the expressible engine. (a) is preferred the moment the primitive lands.

## Artifact checksums (sha256)

Committed in the same commit as this outbox; verify with
`Get-FileHash -Algorithm SHA256`.

```
2556ce5ec9e288f9ede032ea8dd28d24599383d41c67eebf92198215a031f724  oracle.pep
70f12a9f11391a2caafc5c4b238c30a6e8124e25f52bc7106e945c2beecd6908  selftest.pep
2e779df6e878b940bfe38d3b1aa663529f595b29fde925e0afff5ebc59033fc8  differential.py
35c03aaa6483b4906d425f51bd7884443cb478a0e6c298a9d3f5ad8cbcff9d79  README.md
```
