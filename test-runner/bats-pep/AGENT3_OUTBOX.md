# Agent 3 outbox — Pep-native Terror Bats

Owner: Agent 3. Scope: this file plus `test-runner/bats-pep/`.
Branch: `pep/native-differential-v1`. Reference oracle: The-Terror-Bats `@ d5e6404`.

Read the code and tests as authoritative; this file is a receipt and a dependency
note, not a status report on anyone else's work.

## Shipped this session

| Commit | Slice |
| --- | --- |
| `5e827fb` | Kleene condition composition (`compose_all` / `compose_any` / `compose_not`) |
| `1b1ec57` | Composition differential against the real framework, 17/17; `text_contains` wall recorded with measurements; grammar corrections |
| (this commit) | Judgement trail (`ConditionOutcome` / `Evaluation` / `explain` / `say_trail`) and trail differential, 23/23 |

Starting point was `749edb2` (typed `Mode`, `ExitObservation`, `EvidenceStep`,
`Verdict`; 11 self-tests; 8/8 differential).

## Checks actually run

| Check | Result |
| --- | --- |
| `.\pep.ps1 check test-runner\bats-pep\oracle.pep --json` | `status valid`, 0 diagnostics |
| `.\pep.ps1 run _build\composed.pep` (oracle + selftest) | 80 lines, 35 verdict cases plus trail sizes and one full `explain` |
| `python test-runner\bats-pep\differential.py` | `SUMMARY cases=23 mismatches=0` |
| `git ls-files --eol test-runner/bats-pep/` | all four files `i/lf w/lf` |
| all file edits | Threadmoth `preview` → `mutate`, budget PASS, `unrelated_bytes_changed=false` |

## Capacity delivered

- Composition is Kleene three-valued, matching `OracleExpr::All/Any/Not`: `all` is
  AND with `NotObserved` dominating, `any` is OR with `Proven` dominating, `not`
  swaps only the two decided judgements, `all: []` / `any: []` are Undetermined, and
  one malformed child invalidates the whole composition.
- Trails record one outcome per leaf and never per combinator, except the synthetic
  `("all: []", Undetermined)` outcome, which mirrors the reference.
- Leaf labels use the reference's own `describe(cond)` wording, which is what makes
  the trail differential possible: for six specs the Pep trail is compared against
  Rust's `oracle.conditions` leaf by leaf, not just by composed verdict.

## Blocked upstream: `text_contains` (measured, not suspected)

Pep cannot read the bytes of a `Str`, so the byte-window search inside
`Condition::TextContains` is not expressible today. Measured diagnostics are in
`README.md` under "Language dependencies found". The precise missing primitive is
either `str_bytes(s: Str) -> SourceBytes` or `str_contains(haystack: Str, needle:
Str) -> Bool`. `Str` supports only `==` / `!=`; `contains` is list membership;
`source_bytes()` is the program's own source under a host-authorised v2
semanticTarget.

Nothing was approximated and no judgement was moved into Python to work around it.

## Next action

Either (a) implement `text_contains` immediately once `str_bytes`/`str_contains`
lands, validating against `contains_substring` including the empty-needle rule
(which returns true, so an empty needle always fires); or (b) continue the
expressible engine with a typed evidence-record surface that more than one step can
be judged from. (a) is preferred the moment the primitive exists.

## Artifact checksums (sha256)

```
337153993e7c693d906382101a2b68586b82a6258c17b7bfffa2b3148d8b5b1f  oracle.pep
184b4480043647c4cb4ee07b690596baf44029b1de61c42e8bbefde641a4e197  selftest.pep
6ce0b1581d67594abca43addb9670cedd9e8c42a1277bf7b4cf4bc9922b50300  differential.py
7a0e493dccc439f99c4e8149064f8738d1019c1643dd2505c782f2ebfcd909df  README.md
```

These are the checksums of the files as committed in the same commit as this
outbox; verify with `Get-FileHash -Algorithm SHA256`.
