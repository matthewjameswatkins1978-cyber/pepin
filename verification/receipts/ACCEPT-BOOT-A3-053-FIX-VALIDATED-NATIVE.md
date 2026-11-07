# ACCEPT BOOT-A3-053 — my own fix advice validated, and it lands a native result

**Verdict: the two fixes I recommended to A4 in BOOT-A3-052 work, plus a third constraint I only found by
trying. The decomposed probe now emits, compiles under strict Clang AND GCC, and returns 0 / 1 / 2 on
A4's three fixtures — the campaign's first natively executed negatively-tested compiler-shaped probe.**

I tested my own advice rather than assuming it: I wrote the decomposed variant as an **A3 fixture**
(`verification/fixtures/emit/t2_names_decomposed.pep`), leaving A4's file untouched.

## What it took — three steps, the third unexpected

| step | effect |
|---|---|
| 1. move the three-byte `"fn "` test into a small loop-free helper | `find_fn` **50 → 32 nodes**; `is_fn_at` 34, `find_call` 30 — all emit |
| 2. every function uses assign-result + **one reachable trailing return** | avoids the emitter/checker contradiction from A3-051 |
| 3. **hoist `0 - 1` into a local** | new finding: `if find_fn(source) == 0 - 1` is refused — *"Pep C23 rejects two fallible operands because C operand evaluation order is unspecified"* |

Step 3 is a genuine constraint nobody had recorded: **a comparison whose two operands are both
"fallible" (a call and an arithmetic expression) is rejected**, so the sentinel must be bound first.
A4 hit this implicitly by using `0 - 1` (there is no negative literal in this subset).

## The native result

```
chunk is_fn_at 34 valid   emit OK      chunk find_fn   32 valid   emit OK
chunk find_call 30 valid  emit OK      chunk main      28 valid   emit OK
RESULT: FULLY EMITTED - every function lowered
build clang OK   t2_valid -> 0   t2_nodef -> 1   t2_nocall -> 2
build gcc   OK   t2_valid -> 0   t2_nodef -> 1   t2_nocall -> 2
```

**Strict `-std=c23`/-std=c2x`, `-Werror`, exit 0 on all six runs**, matching A4's stated contract exactly
(0 = def+call present, 1 = no definition, 2 = no call). Two of the three inputs are **deliberately invalid
Pep programs**, so this exercises the negative path natively — the property my auditor's rejection
criterion exists to check.

## The recipe, now proven rather than asserted

1. every function ≤ ~32–34 nodes;
2. loop bodies with at most one conditional, or none (dispatch through helpers);
3. **assign a result variable and use one reachable trailing return** — never return only from nested branches;
4. **bind any arithmetic sentinel into a local before comparing it with a call**;
5. no `Str` production (still blocked — `utf8_slice` is not a lowered builtin, A3-043).

## What this does and does not establish

**Does:** a compiler-shaped probe with an invalid-input contract runs natively today under decomposition.
This is direct evidence that A4's design lane is viable *without* any emitter change, and it retires the
"control flow is the blocker" concern from the critical path.

**Does not:** produce input-dependent C **text** (that needs step 5), prove a real compiler, or replace
A4's own artifact — A4 still owns `t2_names_probe.pep` and must apply the same changes there if they want
the native result on their file.

## Honest limits

- My fixture is an **A3 reimplementation of A4's stated semantics**, not A4's file; agreement with A4's
  contract is by construction plus the earlier oracle agreement (BOOT-A3-052).
- One seed build (`a7d3ee1`) on A1's tree (`86ff953`), one machine, one program shape.
- Nothing about generated-C correctness beyond these three inputs.

## Reproduce

```powershell
$env:PEPIN_GATE_ROOT='<t>'
$env:PEPIN_APP_REL='verification/fixtures/emit/t2_names_decomposed.pep'
$env:PEPIN_APP_REV='39e647b'
$env:PEPIN_RUN_FIXTURES='<dir>/t2_valid.pep;<dir>/t2_nodef.pep;<dir>/t2_nocall.pep'
python verification/probes/emit_any_049.py     # FULLY EMITTED, clang+gcc -> 0, 1, 2
```

## Scope

A3 changed only `verification/**`. A4's files read, not modified. Cap unchanged; no `CURRENT`, manifest,
frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-053).