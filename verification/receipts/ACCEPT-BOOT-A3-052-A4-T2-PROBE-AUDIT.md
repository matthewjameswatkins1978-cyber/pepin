# ACCEPT BOOT-A3-052 — A4's T2 names probe: semantics confirmed, two concrete emit blockers

**Verdict: A4's expected values are exactly right; the probe cannot emit, for two reasons I can name
precisely, both fixable by design changes already measured.**

Audit of `examples/dogfood/t2_names_probe.pep` + `t2_valid/t2_nocall/t2_nodef` @ A4 `5e1fc9d`.

## 1. Semantics — A4's three claims CONFIRMED independently

| fixture | `pep.ps1 check` | my independent oracle | A4 claimed |
|---|---|---|---|
| `t2_valid.pep` | **valid** | **0** | 0 |
| `t2_nodef.pep` | **invalid** `PEP_PARSE_EXPRESSION` | **1** | 1 |
| `t2_nocall.pep` | **invalid** `PEP_PARSE_EXPECTED` | **2** | 2 |

The two "invalid" fixtures are deliberately malformed **inputs** to the probe, not programs; the probe's
scan logic is correct on all three, and my Python reimplementation agrees exactly. `find_fn` returning
`0 - 1` rather than a negative literal is also correct for this subset.

## 2. Capability — the probe cannot be emitted, and the first refusal is size

```
chunk ascii_letter 24 valid   emit OK
chunk find_fn      50 valid   FIRST REFUSAL: PEP_RUNTIME_STEP_LIMIT at 5358:8
chunk find_call    30 valid
chunk main         24 valid
```

**`find_fn` is 50 nodes** — over the boundary my earlier probes located. For calibration from measured
data: a `while` with **one** conditional emitted at **34 nodes** (66,577 steps), and two sequential
conditionals refused at **48**. `find_fn` has only one conditional in its loop body, but at **50 nodes**
the size alone exceeds the budget.

## 3. A second blocker waiting behind it: `main`'s all-nested returns

`main` is 24 nodes with `if { return 1 } else { if { return 2 } else { return 0 } }` — **every path
returns, none at top level**. That is exactly the contradiction I documented in BOOT-A3-051: nested
returns alone make the **emitter** refuse (*"Pep C23 functions require a return statement"*), and adding a
trailing return makes the **checker** refuse (`PEP_UNREACHABLE`).

So even after `find_fn` is shrunk, `main` will not emit as written. It needs the idiom that satisfies both
layers: **assign a result variable, then one reachable trailing return**.

## Concrete fixes for A4 (both already measured, no new emitter work implied)

1. **Shrink `find_fn`** from 50 nodes toward ≤ ~34. The condition
   `byte_at(source,o)==102 && byte_at(source,o+1)==110 && byte_at(source,o+2)==32` is most of the cost;
   moving it into a small loop-free helper (`fn is_fn_at(source, o) -> Bool`) keeps each function small —
   the decomposition that made BOOT-A3-051's lexer shape fully emit.
2. **Rewrite `main`** with `var r = 0` … `return r` so the trailing return is reachable, avoiding
   `PEP_UNREACHABLE` while satisfying "requires a return statement".

With both, this probe plausibly emits — and it would then be the first **negatively-tested** compiler-shaped
program in the repository (it has invalid-input cases, which is what my auditor's A4 criterion wants).

## What I did not do

- Did not modify A4's files: this is an audit, and A4 owns the design.
- Did not run the probe: it cannot be emitted, so there is no binary to run. **A4's expected values are
  verified as semantics by oracle, not as a native result** — the distinction I have kept throughout.

## Honest limits

- Emission feasibility only; nothing compiled or run.
- One seed build (`a7d3ee1`) on A1's tree (`86ff953`); one machine.
- The "shrink to ≤ ~34" figure is interpolated from two measured points (34 emits, 48 refuses) plus the
  loop-free boundary (32 emits, 35 refuses); it is a target, not a guarantee.

## Reproduce

```powershell
$env:PEPIN_GATE_ROOT='<t>'; $env:PEPIN_APP_REL='examples/dogfood/t2_names_probe.pep'; $env:PEPIN_APP_REV='5e1fc9d'
python verification/probes/emit_any_049.py     # find_fn 50 nodes -> emission STEP_LIMIT
```

## Scope

A3 changed only `verification/**`. A4's files read, not modified. Cap unchanged; no `CURRENT`, manifest,
frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-052).