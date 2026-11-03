# Mutation check on A1's new test module at `0c5f12b` — the suite is not vacuous, but it does not pin the guards or duplicate-field behaviour

**Date:** 2026-11-03 · **Lane:** Agent 3 independent verification (PEP-A3-SUSTAINED-013 slice 2: "tests may share the builder's mistaken assumptions" — so the tests themselves are challenged) · **Evidence label:** `TESTED`
**Target:** `codex/p1-checker-cost-fix` @ **`0c5f12b`**, file `tests/test_chunk_type_decls.py` (4 tests, 8.3 s), producer `fn chunk_type_declarations` in `tests/pep_checker_a13.pep`
**Method:** eight hand-built mutants of the producer, applied one at a time in a **disposable detached worktree** (`D:\Projects\wt-a3-mut-0c5f12b`, never pushed, no branch, reverted after each mutant — final `git status` clean), each followed by `python -m unittest tests.test_chunk_type_decls`. Edits via Threadmoth (`--expect-count 1`, `--newline-policy exact`). Surviving mutants were then discriminated **behaviourally** (facts dumped on duplicate-bearing sources, clean vs mutated) so "untested" is never confused with "equivalent".

## Result

| mutant | what it removes | suite | behaviour difference | reading |
|---|---|---|---|---|
| **M1** `return []` | the whole function's output | **KILLED** | total | suite is **not vacuous** |
| **M2** `done` guard | `if !parsed.done { return [] }` | **SURVIVED** | yes (my probe T3: empty vs facts) | **guard untested by this module** |
| **M3** `status` guard | `if parsed.status != "complete" …` | **SURVIVED** | yes (probe T4) | **guard untested** |
| **M4** `tree_is_valid` | structural validation | **SURVIVED** | yes (probe T5) | **guard untested** |
| **M5** authority guard | document/revision equality with `semantic_snapshot()` | **SURVIVED** | yes in principle; the host refuses crossed pairs first (probe T1) | **defence-in-depth untested** |
| **M6** name dedupe | `if !contains(seenTypeNames, …)` | SURVIVED | **none** on `type Dup`twice — `resolve_all_records` already returns one record per name | **equivalent mutant** (redundant guard), not a gap |
| **M7** `duplicateType` exclusion | `!resolved.duplicateType && …` | SURVIVED | **none** on a duplicate-type source | **not distinguished here** (stated, not claimed) |
| **M8** duplicate-**field** exclusion | `if !facts.duplicate` | **SURVIVED** | **yes** — `type Fields { a: Int  a: Bool }` yields `['a']` clean vs `['a','a']` mutated | **genuine test gap** |

Behavioural evidence for the two survivors that matter:

```
clean                duplicate_type:   [{'type': 'Dup',    'start': '0', 'fields': ['a']}]
                     duplicate_field:  [{'type': 'Fields', 'start': '0', 'fields': ['a']}]
M8 duplicate fields  duplicate_field:  [{'type': 'Fields', 'start': '0', 'fields': ['a', 'a']}]   ← differs
```

## What this means (stated against the builder's interest, and fairly)

- **Not a code defect.** The producer's guards were independently shown to fire (my probe
  `a1_type_facts_attacks.py` T1–T5, 9/9 held), and the suite kills a totally broken producer. Nothing
  here suggests the compiler is wrong today.
- **A genuine regression-risk gap.** Four guards and one output rule (`M8`) can be deleted from the
  producer with `tests/test_chunk_type_decls.py` still green. Nothing in A1's own module would notice a
  future refactor that drops `done`, `status`, `tree_is_valid`, the authority comparison, or duplicate-field
  filtering — the only current protection is my out-of-tree probe and the host check for T1.
- **Concrete, cheap close:** add four tests that feed a doctored `ParserProgress` (`done=false`,
  `status="partial"`, self-parent tree) and an identical-revision/foreign-revision pair, plus one
  duplicate-field source asserting a single field. Those are exactly the mutants above, so the tests
  can be validated by re-running these mutants.
- **Two survivors are honest non-findings:** M6 is redundant code (the resolver already dedupes), and M7
  is indistinguishable on the duplicate-type input I could construct. I am not claiming a gap for either.

## Honest scope

- One file, one pin, eight mutants; the suite was run as-is (4 tests, `OK` at baseline).
- Mutation edits touched only the disposable worktree; the repository copy of `tests/pep_checker_a13.pep`
  is untouched (`git status` clean at the end, verified).
- No frozen gate was executed; this is not acceptance evidence.
- I did not mutate the *harness* or the emitter; only the producer under test.

## Reproduce

```powershell
git worktree add --detach <scratch> 0c5f12b
# for each mutant: edit one line in tests/pep_checker_a13.pep (Threadmoth), then
python -m unittest tests.test_chunk_type_decls
# discriminate a survivor:
python verification\_build\tm\facts_dump.py <scratch>     # clean vs mutated fact dumps
git -C <scratch> checkout -- tests/pep_checker_a13.pep
```
