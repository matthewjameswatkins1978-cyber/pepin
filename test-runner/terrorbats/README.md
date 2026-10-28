# Terror Bats experiments — independent challenge for parser blocker #20

Real [Terror Bats](https://github.com/matthewjameswatkins1978-cyber/The-Terror-Bats)
experiments that try to break Agent 2's parser continuation repair rather than
confirm it. Each Bat is a falsification attempt: it states a claim, runs a
bounded attack against a disposable worktree of a clean repository, and applies a
deterministic oracle.

Nothing here re-implements a compiler, a parser or a test runner. Every attack
drives the real `pep.ps1` / `pep_c23.py` / conformance tooling already in the
repository, so a Bat can never disagree with the thing it is testing.

## Verdicts (framework semantics, not ours)

| Verdict | Means |
| --- | --- |
| `PROVEN` | the attack **falsified** the claim — the bad thing really happened |
| `NOT OBSERVED` | the attack did not falsify the claim — **not** a correctness certificate |
| `INCONCLUSIVE` | the oracle could not decide from the evidence |

Read them that way: a `PROVEN` result on a "this should work" claim is a bug
report, and `NOT OBSERVED` on a "this should be broken" claim is the expected
after-fix state.

## Running

```powershell
# the framework: build once from the real source
cargo build --release   # in The-Terror-Bats

$tb = "<The-Terror-Bats>\target\release\terrorbats.exe"

# --repo must be clean, so point it at a clean clone of the branch under test
git clone --branch pep/native-differential-v1 <remote> D:\Projects\wt-bats-clean

& $tb run --repo D:\Projects\wt-bats-clean `
    test-runner\terrorbats\bats\01-parser-composition-ceiling.yaml --json
```

`--param fixture=<path>` selects which composition to attack, so one Bat covers
the whole reproduction set:

```powershell
foreach ($f in 'composed_int_gcd', 'composed_int_is_even',
              'composed_int_clamp_negative', 'composed_forwarding_wrapper') {
  & $tb run --repo D:\Projects\wt-bats-clean `
      test-runner\terrorbats\bats\01-parser-composition-ceiling.yaml `
      --param "fixture=test-runner/terrorbats/fixtures/$f.pep" --json
}
```

## The experiments

| Bat | Claim attacked | Red baseline (this revision) |
| --- | --- | --- |
| `00-control-wrong-expectation-detected` | "the conformance runner passes a deliberately wrong expectation" | `PROVEN` — required control: the harness *does* detect it |
| `01-parser-composition-ceiling` | "a valid multi-function program reaches the C23 checker instead of aborting on the step budget" | `PROVEN` for gcd, is_even and clamp-negative; `NOT OBSERVED` for the minimal forwarding wrapper (it reaches the emitter) |
| `02-session-continuation-invariants` | "the JSONL session breaks continuation/revision invariants under hostile traffic" | `NOT OBSERVED` — all six probes hold on this revision |
| `03-session-stateful-handshake` | "a supervised session answers a piped request with an error instead of a successful open" | `NOT OBSERVED` — it answers normally |

`02` and `03` use the session protocol directly. `02` drives it through
`drivers/session_continuation_attack.py`, which speaks JSONL to the real CLI and
prints one `ATTACK … | HOLD|VIOLATED` line per probe plus a `SUMMARY`, so a
verdict is always traceable to a named attack. `03` uses the framework's stateful
**process** adapter (`start` / `write_stdin` / `wait_ready` / `observe` / `kill`)
to supervise a real session with generation-relative readiness.

Session invariants currently confirmed to hold:

| Probe | Observed refusal |
| --- | --- |
| unknown operation | `PEP_SESSION_UNKNOWN_OPERATION` |
| malformed JSON line | `PEP_SESSION_MALFORMED_JSON` |
| missing required field | `PEP_SESSION_FIELD_REQUIRED` |
| unregistered tool invocation | `PEP_TOOL_NOT_ACTIVE` |
| revision identity | same bytes → same `sha256:` revision; different bytes → different revision |
| liveness after refusals | session still answers correctly |

One nuance worth carrying into any continuation repair: `document` is a per-open
session **handle** and legitimately changes between opens, while `revision` is the
content identity. A repair must key staleness on `revision`. My first version of
the driver asserted both and produced a false `VIOLATED` — retained here because
a wrong oracle is indistinguishable from a real bug until it is checked.

`00-*` is the deliberately failing control. Its claim is false by construction,
so a working oracle must falsify it. If it ever returns `NOT OBSERVED`, the
harness has stopped detecting incorrect behaviour and no other green result here
is trustworthy.

## Reproduction set (from #20)

- `composed_int_gcd.pep` — `int_mod` + `int_gcd` + `main` (2-function closure)
- `composed_int_is_even.pep` — parity helper + `main`
- `composed_int_clamp_negative.pep` — the argument-shape edge: the same helper
  reaches the emitter for other arguments and aborts on this one
- `composed_forwarding_wrapper.pep` — two-level forwarding wrapper, the shape
  measured independently by Agent 2

## Findings the experiments already produced

- **`-o` is unusable through `pwsh -File`.** `pwsh -NoProfile -File pep.ps1
  build-c23 FILE -o OUT` fails with *"Parameter name 'o' is ambiguous. Possible
  matches: -OutVariable -OutBuffer"* and exits 1 before Pep runs. `--output`
  works. The CLI help lists `-o, --output`, so the short form is a trap for any
  harness (or agent) that invokes the script non-interactively. The first ceiling
  Bat run returned `NOT OBSERVED` purely because of this, which is exactly the
  kind of misleading-green failure these Bats exist to expose — `NOT OBSERVED`
  meant "the attack never reached the target", not "the blocker is gone".
- **The blocker reproduces with parse_count 3, typecheck_count 3, cache_hits 0**
  and `PEP_RUNTIME_STEP_LIMIT` at the staged parser, matching Agent 2's
  independent measurement of the same composition.

## Rules these Bats obey

- **Never** raise the 100,000-step per-invocation limit; a Bat that would need
  that is testing the wrong thing.
- Every receipt names the repository revision, the exact command, the captured
  streams and the verdict, so a run can be replayed.
- `unsupported` and `NOT OBSERVED` are never reported as passing evidence for
  native behaviour; the differential runner's own counts are quoted when relevant.
- Disposable worktrees only; the framework creates and removes them itself.
