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

## Cases

- `cases/VALUE_COPY_DEC001.md` — V1-linked positive probes: list/record
  copy independence on the interpreter (P1–P3, all `TESTED` passing).
- `cases/NEGATIVE_AND_EDGE.md` — holes refuse execution, `edit` absent
  from seed grammar, nested `contains` fail-closed, controlled
  division-by-zero, unobserved `main` return value.

## Reproduction

Probes run from the pinned base (`805062b`) worktree with e.g.:

```powershell
./pep.ps1 check $env:TEMP/a3_probe.pep --json
./pep.ps1 run $env:TEMP/a3_probe.pep
```

No fixture is committed as generated input under `_build/`; `.pep`
sources here are hand-written, deterministic, UTF-8, LF.
