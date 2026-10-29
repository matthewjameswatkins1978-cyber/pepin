# Negative and edge cases (V0 adversarial set 1)

All observations via `./pep.ps1 check <file> --json` /
`./pep.ps1 run <file>` from base `805062b` (OCaml interpreter only).
Each case is minimal and deterministic.

## N1 — unresolved hole in unused function: `incomplete`, run refuses

```pep
fn main() -> Int { return ?pending }
```

| oracle | result |
|---|---|
| SPEC (seed facts) | `check` → `incomplete`; `run` refuses even if hole is unused |
| OCAML | `TESTED` PASS — `check` status `incomplete`, no diagnostics; `run` → `incomplete: unresolved typed holes`, exit nonzero |

## N2 — `edit` parameter mode absent from seed grammar (DEC-002 gap)

```pep
fn bump(edit value: Int) -> Unit { value = value + 1 }
fn main() -> Int { return 0 }
```

| oracle | result |
|---|---|
| SPEC | DEC-002 `read/edit/take` is accepted design, but NOT in the shipped seed grammar (`describe` lists no access modes) |
| OCAML | `TESTED` — `check` status `invalid`, `PEP_PARSE_EXPECTED` at bytes 13–18 (the `edit` token). Recorded as an accepted-design/implementation gap, not a defect. |

## N3 — nested `contains` fails closed (scalar-only membership)

```pep
fn has() -> Bool { return contains([[1]], [1]) }
```

| oracle | result |
|---|---|
| SPEC | `contains` is scalar-only per `describe` (`equality: scalar-only`) |
| OCAML | `TESTED` PASS — `check` status `invalid`, `PEP_MEMBERSHIP_UNSUPPORTED` at bytes 35–40. Fail-closed as required; matches builder `test_nested-list-contains` expectation. |

## N4 — division by zero is a controlled diagnostic, not a trapdoor

```pep
say(int_text(1 / 0))
```

| oracle | result |
|---|---|
| SPEC (seed facts) | runtime arithmetic faults produce controlled diagnostics |
| OCAML | `TESTED` PASS — `1:14: PEP_RUNTIME_DIVISION_BY_ZERO: Division by zero`, exit 1, byte-exact span. `check` alone reports `valid` (fault is dynamic, not static) — correct layering. |

## E1 — `main` return value unobserved by `run` (recorded, not a finding)

```pep
fn main() -> Int { return 1 / 0 }
```

| oracle | result |
|---|---|
| observed | `TESTED` — `run` exits 0 silently (no `say` output; return discarded). Consistent with a `say`-observed CLI, but worth stating: a fault inside a discarded `main` return is silent at the CLI layer. No defect claimed; CLI contract question for Agent 1 if ever specified otherwise. |

## Not yet covered (next slices)

UTF-8/CRLF span adversarial set, stale/forged revision identity,
source-limit vs fuel-limit confusion, short-circuit error ordering —
each as its own minimal case with SPEC-first expectations.
