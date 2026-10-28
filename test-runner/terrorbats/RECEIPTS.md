# Terror Bats receipts — parser composition ceiling (#20)

Every row below is a real Terror Bats execution (`terrorbats run`, framework
built from `The-Terror-Bats` source, `doctor` 6/6 core checks) against a clean
clone of this branch. Receipts are content-addressed and replayable:

```powershell
terrorbats inspect <receipt-id>
terrorbats evidence show <evidence-id>
terrorbats replay <receipt-id>
```

Target repository: `https://github.com/matthewjameswatkins1978-cyber/pepin.git`
Fresh `git clone --branch pep/native-differential-v1` per session; `--repo` must
be clean, and each run gets its own disposable worktree from the framework.

## Results

| Experiment | Fixture | Verdict | Observed |
| --- | --- | --- | --- |
| `00-control-wrong-expectation-detected` | doctored manifest (expects 99, program prints 7) | **PROVEN** | exit 1, `FAIL control/deliberately-wrong stdout mismatch: got '7\n', expected '99\n'` |
| `01-parser-composition-ceiling` | `composed_int_gcd.pep` | **PROVEN** | `PEP_RUNTIME_STEP_LIMIT` at `873:13`, parse_count 3, typecheck_count 3, cache_hits 0 |
| `01-parser-composition-ceiling` | `composed_int_is_even.pep` | **PROVEN** | `PEP_RUNTIME_STEP_LIMIT` at `824:20`, parse_count 3, typecheck_count 3, cache_hits 0 |
| `01-parser-composition-ceiling` | `composed_int_clamp_negative.pep` | **PROVEN** | `PEP_RUNTIME_STEP_LIMIT` (argument-shape edge reproduces) |
| `01-parser-composition-ceiling` | `composed_forwarding_wrapper.pep` | **NOT OBSERVED** | **reaches the emitter**: `Pep C23 unsupported: Pep C23 one-parameter calls require one argument and a call-free target expression` |
| `02-session-continuation-invariants` | six hostile session probes | **NOT OBSERVED** | every probe `HOLD`: `PEP_SESSION_UNKNOWN_OPERATION`, `PEP_SESSION_MALFORMED_JSON`, `PEP_SESSION_FIELD_REQUIRED`, `PEP_TOOL_NOT_ACTIVE`, stable content revisions, liveness intact |
| `03-session-stateful-handshake` | supervised session, one piped request | **NOT OBSERVED** | `observe` returned `{"outcome":"ok","operation":"open","document":"doc-1","revision":"sha256:09d129…","status":"valid",…}` |

## Receipts

| Experiment | Receipt id | Target commit | Step exit | stderr evidence |
| --- | --- | --- | --- | --- |
| control | `receipt:sha256:51476b380d5b2766ea528d6115949e57b2153291cb3fe19c10eacb111cc13da0` | `79322e62d1a4` | 1 | empty (stdout carried the FAIL line) |
| int_gcd | `receipt:sha256:cf599f0c4c8153cdebfc752fb2197703f2d6f485da014787bf1bd1ce45de4401` | `243813775ce9` | 2 | `evidence:sha256:79b6cbe3a32e2b7106bb7ad5af0da55c46cb0d0efbc8bb75d7f133e8fbf7ca8e` |
| int_is_even | `receipt:sha256:04692cfcf314161ba5ab9ad0d4bd74109447b896faf961bdbf3209d7c5a783e0` | `243813775ce9` | 2 | `evidence:sha256:fe5be4c0e9ccc760de4c0beb9b0264ee8d258d4ea9d764e6d2853ce17bf9a7a6` |
| int_clamp(-5,0,10) | `receipt:sha256:a656ba69e0a0ef628b737b09f420f5ba2d983298154f44ef51865d82127cd572` | `243813775ce9` | 2 | `evidence:sha256:da4abce8fd79c48f50f8d2169559568f778d4af3d50401c027672d227a2d8866` |
| forwarding wrapper | `receipt:sha256:9ca557c2100af9b877d1fc4366317868a3ab54f8a92e9cdb10f8326e4a43e90f` | `243813775ce9` | 2 | `evidence:sha256:edb3bd4e0a6a18d89ef5543334b2a782c02df0e562dc1b93edd2e69c15386569` |
| continuation invariants | `receipt:sha256:6bfb2023e67ecb41e3ddcae190f1d3a43ea07619f4f598521d12326536c8801d` | `0d01279a622b` | 0 | driver stdout (ATTACK/HOLD/SUMMARY lines) |
| stateful handshake | `receipt:sha256:3553920a3727271ace1826361b81bccd493c542c57b72e54dca93a152b82a873` | `0d01279a622b` | — | `observe` stream on step 3 |

## Exact commands

```powershell
$tb  = "<The-Terror-Bats>\target\release\terrorbats.exe"
$bat = "test-runner\terrorbats\bats\01-parser-composition-ceiling.yaml"

& $tb run --repo <clean-clone> $bat `
    --param "fixture=test-runner/terrorbats/fixtures/composed_int_gcd.pep" --json

& $tb run --repo <clean-clone> `
    test-runner\terrorbats\bats\00-control-wrong-expectation-detected.yaml --json
```

Verdict exit codes observed: `PROVEN` = 1, `NOT OBSERVED` = 0,
infrastructure failure = 3.

## What these receipts do and do not establish

- They establish that **three of the four** #20 composition shapes abort inside
  the staged parser on the 100k budget on this revision, with metrics matching
  Agent 2's independent measurement (parse 3/3, typecheck 3/3, 0 cache hits).
- They establish that the **minimal** two-level forwarding wrapper does **not**
  hit the budget: it reaches the emitter and is rejected as unsupported for a
  different, honest reason (one-parameter calls need a call-free target
  expression). The claim that forwarding wrappers hit the ceiling therefore holds
  only for the larger compositions Agent 2 measured, not for a minimal one — a
  distinction worth keeping, because a Bat aimed at the wrong failure mode would
  have reported a vacuous pass.
- They do **not** prove anything about a repaired parser, because no continuation
  repair exists on this branch yet. Re-running the same Bats unchanged against a
  repaired revision is the intended comparison; a move from `PROVEN` to
  `NOT OBSERVED` on the three blocked fixtures, with the same command and the
  same oracle, is the evidence that the repair works.
- `NOT OBSERVED` is not a correctness certificate (framework semantics). It means
  this attack did not falsify the claim.

## Continuation and revision probes

`02` drives the real session through `drivers/session_continuation_attack.py`;
`03` supervises a real session with the framework's stateful process adapter
(`start` / `write_stdin` / `wait_ready` / `observe` / `kill`).

| Probe | Invariant | Observed |
| --- | --- | --- |
| unknown operation | structured refusal, session alive | `PEP_SESSION_UNKNOWN_OPERATION` |
| malformed JSON line | structured refusal, session alive | `PEP_SESSION_MALFORMED_JSON` |
| missing required field | named error code | `PEP_SESSION_FIELD_REQUIRED` |
| unregistered tool invocation | registry refusal | `PEP_TOOL_NOT_ACTIVE` |
| revision identity | same bytes → same revision; different bytes → different | `sha256:09d129…` reproduced; `sha256:92ffce…` for different bytes |
| liveness after refusals | still answers correctly | `outcome: ok` |

Carry-forward for any continuation repair: `document` is a per-open session
**handle** and changes between opens; `revision` is the content identity. Key
staleness on `revision`. My first driver asserted both and produced a false
`VIOLATED` — recorded because a wrong oracle looks exactly like a real bug until
it is checked.

These probes say the session's continuation-adjacent invariants hold on this
revision. They do **not** yet attack the cursor protocol itself
(`parser_start`/`parser_step`), which needs tool registration against the
compiler bundle; that is the next slice, and it is where a chunked-parser repair
could most plausibly go wrong: `parser_step` answers `done: true` together with
`status: "invalid"` for a stale cursor (`PEP_PARSER_CURSOR_REVISION`), so an
orchestrator that treats `done` as success would silently accept an empty AST.

## Deliberately failing control

`00-control-wrong-expectation-detected` is the required control. Its claim is
false by construction — the runner does *not* pass a wrong expectation — so a
working oracle must falsify it. It returns `PROVEN`, i.e. the harness detects
incorrect behaviour. If it ever returns `NOT OBSERVED`, every other green result
here is suspect.

## Incident kept in the record

The first ceiling run returned `NOT OBSERVED` for the wrong reason: the Bat used
`-o`, which under `pwsh -File` binds as an ambiguous PowerShell common parameter,
so the step died before Pep ran. The framework reported the failure honestly
(exit 1, empty stdout, non-empty stderr) and the receipt let me retrieve the
exact message. Fixed to `--output`; recorded in the README.
