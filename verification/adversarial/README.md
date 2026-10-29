# Agent 3 adversarial conformance corpus

**Owner:** Agent 3. **Scope:** NEW files under this directory only.
Never rewrites `tests/test_a13.py`, `tests/test_a14_c23.py`, or builder
goldens. Builder harness semantics are not changed here.

## Method

Spec-first, not implementation-first: each case states the expected
result **from the accepted Pep semantics** (final draft + seed facts),
then records independent oracle observations per platform:

| column | meaning |
|---|---|
| SPEC | expected per accepted normative Pep text |
| OCAML | OCaml 5.x seed via `pep.ps1 inspect/check/run` (interpreter only) |
| A13 | Pep-written checker (`tests/pep_checker_a13.pep`, Agent 1 owned) |
| C23 | generated C23 via Clang/GCC (Agent 2 owned emitter + toolchains) |

Labels: `NOT_RUN` | `TESTED` | `MODEL_PROVED` | `IMPLEMENTATION_REFINED`
| `UNVERIFIED` | `BLOCKED_SECURITY`. Native C compile/execution is
`BLOCKED_SECURITY` on the held host per
`runtime/pep_text/SEED...` — precisely,
`runtime/pep_text/SECURITY_2026-10-29_DEFENDER.md`. OCaml-interpreter
probes and pure-Python source checks are permitted (no C toolchain, no
binary generation, no AV interaction) and are marked `TESTED` with exact
commands; everything else stays `NOT_RUN`/`BLOCKED_SECURITY`, never
green by assumption.

## Reproducible replay lab

`replay.py` re-executes every base-tree probe in this corpus
(P/N/U/R/S/REC/L/C/F/H/T/O/V/G/SWAP/SN/X/D/PL/M sets) and asserts each receipted outcome.
Run from the agent3 worktree root:

```powershell
python verification/adversarial/replay.py   # exit 0 iff 134/134 PASS
```

Verified 134/134 PASS at base `805062b` on 2026-10-29. Only `pep.ps1
check/run/query/session` (OCaml seed, in-process) plus temp files — no
C toolchain, no binaries, hold-safe. Pin-specific suites
(`str_contains` @ A1 tip, A2 emit re-runs) are NOT replayed here;
their receipts state exact detached-worktree commands.

## Cases

All case files live under `cases/` (one topic per file: value-copy,
negatives, UTF-8/spans, revision/limits, eval-order/fuel, records/unions,
str_contains, bridge, literals/conditions, calls/scope, control-flow,
hole lifecycle, tool registry, session edges, v2 transport, source bytes,
hot-swap, semantic snapshot, transport exclusions, declaration edges,
shapes and namespaces, platform inventory). `replay.py`
is the executable index: every base-tree assertion in those files is
replayed by name (P/N/U/R/S/REC/L/C prefixes).

## Reproduction

Probes run from the pinned base (`805062b`) worktree with e.g.:

```powershell
./pep.ps1 check $env:TEMP/a3_probe.pep --json
./pep.ps1 run $env:TEMP/a3_probe.pep
```

No fixture is committed as generated input under `_build/`; `.pep`
sources here are hand-written, deterministic, UTF-8, LF.
