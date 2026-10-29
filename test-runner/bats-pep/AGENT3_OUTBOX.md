# Agent 3 outbox — Pep-native Terror Bats

Owner: Agent 3. Scope: this file plus `test-runner/bats-pep/`.
Branch: `pep/native-differential-v1`. Reference oracle: The-Terror-Bats `@ d5e6404`.

Read the code and tests as authoritative; this file is a receipt and a dependency
note, not a status report on anyone else's work.

## Shipped this session

Starting point was `749edb2` — typed `Mode`, `ExitObservation`, `EvidenceStep`,
`Verdict`; 11 self-tests; 8/8 differential.

| Commit | Slice |
| --- | --- |
| `5e827fb` | Kleene condition composition: `compose_all` / `compose_any` / `compose_not` |
| `1b1ec57` | Composition differential (17/17), the `text_contains` wall measured, grammar corrections |
| `d512957` | Judgement trail: `ConditionOutcome` / `Evaluation` / `explain` / `say_trail`, trail differential (23/23), this outbox created |
| (this commit) | Recursive `OracleExpr` tree with `evaluate_tree`, nested differential (27/27) |

## Checks actually run

| Check | Result |
| --- | --- |
| `.\pep.ps1 check test-runner\bats-pep\oracle.pep --json` | `status valid`, 0 diagnostics |
| `.\pep.ps1 run _build\composed.pep` (oracle + selftest) | 93 lines, 41 verdict cases plus trail sizes and a full `explain` |
| `python test-runner\bats-pep\differential.py` | `SUMMARY cases=27 mismatches=0` |
| `git ls-files --eol test-runner/bats-pep/` | all five files `i/lf w/lf` |
| every file edit | Threadmoth `preview` → `mutate`, budget PASS, `unrelated_bytes_changed=false` |

## Capacity delivered

- **Composition** is Kleene three-valued, matching `OracleExpr::All/Any/Not`:
  `all` is AND with `NotObserved` dominating, `any` is OR with `Proven` dominating,
  `not` swaps only the two decided judgements, `all: []` / `any: []` are
  Undetermined, and one malformed child invalidates the whole composition.
- **Trails** record one outcome per leaf, never per combinator, except the synthetic
  `("all: []", Undetermined)` outcome, mirroring the reference. Leaf labels use the
  reference's own `describe(cond)` wording, which is what makes trail comparison
  possible at all.
- **Recursive trees** (`LeafNode` / `AllNode` / `AnyNode` / `NotNode`) evaluate by
  recursion. A combinator combines its direct child *results*, and the trail is
  depth-first left-to-right; both were measured against the framework rather than
  assumed. Flattening leaves would be wrong as soon as `not` is nested, and four
  differential cases exist specifically to catch that regression.

## Blocked upstream: `text_contains` (measured, not suspected)

Pep cannot read the bytes of a `Str`, so the byte-window search inside
`Condition::TextContains` is not expressible today. Measured diagnostics are in
`README.md` under "Language dependencies found". The precise missing primitive is
either `str_bytes(s: Str) -> SourceBytes` or `str_contains(haystack: Str, needle:
Str) -> Bool`. `Str` supports only `==` / `!=`; `contains` is list membership;
`source_bytes()` is the program's own source under a host-authorised v2
semanticTarget.

Nothing was approximated and no judgement was moved into Python to work around it.

## Language findings for Agent 1

Recorded with minimal repros in `README.md`. Two corrections and four additions in
this session:

- **Corrected**: nullary constructors *are* matchable as `B()`. The earlier claim
  that they were not was wrong; bare `B` is a binding and an irrefutable catch-all.
  Agent 1 confirmed this and it was reproduced here.
- **Corrected**: no generic `Option[T]` is needed — a dedicated union per absence
  (`AbsentExit`, `NotFound()`) works and avoids sentinels.
- `if` requires an `else`, even an empty `else { }`.
- There are no ordering comparisons: `<` is not a token, and `>` / `>=` are absent.
- A match arm body cannot be an assignment; assign in an enclosing `if`.
- `var` may hold a union and swap cases; mutually recursive functions over recursive
  unions work.

## Next action

Either (a) implement `text_contains` the moment `str_bytes`/`str_contains` exists,
validating against `contains_substring` including the empty-needle rule (an empty
needle returns true, so it always fires); or (b) continue the expressible engine.
(a) is preferred the moment the primitive lands.

## Artifact checksums (sha256)

These are the checksums of the files committed in the same commit as this outbox;
verify with `Get-FileHash -Algorithm SHA256`.

```
d06062f3e98f78a5d183ac34c72961e3c56effd87960ed647b41f588712208f5  oracle.pep
890088ca6f38b451fcd080d7cbaad1dc78c211e92a5c79494f0415d48851a19e  selftest.pep
1d5dca7fe84a20a6ea460d7bf7c1b328fe97fb073acf3a77a9cebc12057931cd  differential.py
000f372fcaa9b4c0dfc37b0aae808b01fd271229fd559b08fea2a4dc8f0696eb  README.md
```
