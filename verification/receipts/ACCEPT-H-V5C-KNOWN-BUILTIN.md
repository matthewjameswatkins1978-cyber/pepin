# H-V5c: A4's `known_builtin` vertical — oracle solid, native blocked by BUDGET, Str `==` is fine

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-015 / Campaign H, Workstream V5c · **Evidence label:** `TESTED`
**PIN:** A3 `codex/bootstrap-agent3-verification@1de76b6` (+this commit) · clean · tested A2 `58fc9bf` tree, A1 `2ad750b` seed
**Source:** A4 `docs/spec/H2-NEXT-VERTICAL.md` @ `spec/agent4-spec-lab@cdaf093` (read-only), whose handoff item 3 asks A3 to adopt this as a native anchor.
**First next action:** A4 should revise H2's "first blocker" — it is the step budget, not Str `==`; A2 needs no Str-equality fix.

## Verbatim function

`known_builtin(name: Str) -> Bool` from `tests/pep_checker_a13.pep:148-150` @ A1 `2ad750b` — 13-way `||` chain over Str equality. Extracted slice sha256 `f5ad0c57fe91e3c320a1b32ddef3a94ae7ad1afe7455259485757ed6980900e5`, **byte-equal to the checkout: True**.

## Result 1 — the seed oracle is exact (17 vectors)

`1 1 1 1 1 1 1 1 1 1 1 1 1 0 0 0 0` for the 13 builtin names then `nope`, `""`, `Say`, `str_conca`, `length ` (trailing space). Bits `111111111111100000` — matches expectation exactly. The real function's semantics are pinned.

## Result 2 — native REFUSED, and not for A4's stated reason

```
check parsed source -> outcome=error  PEP_RUNTIME_STEP_LIMIT
```

**Stage: checker.** A4's H2 predicts "Str `==` lowering (most likely) or Str-param passing" as the first blocker. Neither is the blocker: the budget refuses before lowering is reached.

## Result 3 — Str `==` lowering itself is CORRECT (4/4 parity)

Isolated below the budget (`fn is_named(name: Str) -> Bool { return name == "say" }`):

| literal | seed | Clang 23.1.4 | GCC 16.2.0 |
|---|---|---|---|
| `"say"` (equal) | 1 | **1** | **1** |
| `"nope"` | 0 | **0** | **0** |
| `"sa"` (prefix) | 0 | **0** | **0** |
| `""` | 0 | **0** | **0** |

The emitted C is a correct length-then-byte comparison (`pep_str_equal`), with both sides as `(pep_str){ .data = (const unsigned char *)"say", .length = 3 }`. **A4's flagged riskiest assumption is not a risk at this revision** — recorded as a positive result, since a silent-refusal claim there would have wasted A2's time.

## Probe bug I caught before publishing (stated for the record)

My first run of this probe compared the **process exit code** and reported `=0` for the equal case on both compilers — which reads exactly like "Str equality always returns false", i.e. a serious defect. Inspecting the generated C showed the truth: the epilogue is

```c
int main(void) { (void)printf("%lld\n", (long long)(pep_fn_main())); return 0; }
```

so the value is **stdout** and the exit code is always 0. Reading the artefact instead of trusting the number turned a false bug into a correct PASS. Both probes were corrected; the same mistake would silently mis-report every value-returning native program, so it is written into both files as a comment.

## Consequence for the H2 vertical

- The vertical is **not currently runnable**, so it cannot serve as the "smallest real useful app" anchor until the budget allows ~13 disjunctions in one function — which the H-V4 ladder shows is well beyond the present ceiling (one extra trivial declaration already refuses a Str-helper program).
- A4's own instruction ("the refusal names the true next block") is satisfied, but the named block is the **checker step budget**, which is A1's Q1 lane, not an A2 emitter capability.
- Do **not** adopt `known_builtin` as a native anchor at `58fc9bf`; keep the seed oracle result (it is exact and useful) and revisit after A1's budget work.

## Limits

- One function, 17 vectors, two compilers; no claim about the rest of H1's census (A4 owns that).
- Native refusal attributed by the pipeline's own stage message; per-phase step counts are not exposed to A3.
- No A1/A2/A4/spec/frozen-gate/budget/master/CURRENT change by A3; `verification/**` only.

## Reproduce

```powershell
python -X utf8 verification\probes\known_builtin_real.py  D:\Projects\wt-a3-h1-cold
python -X utf8 verification\probes\str_equality_real.py   D:\Projects\wt-a3-h1-cold
```
