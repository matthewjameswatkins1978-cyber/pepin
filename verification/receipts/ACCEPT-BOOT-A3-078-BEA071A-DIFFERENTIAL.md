# ACCEPT BOOT-A3-078 — A3-S1: `bea071a` emission is byte-identical to `1885566`, but `b758c91` silently narrows a fallibility refusal

**Verdict: A2's `prepend+reverse` rewrites are semantics-preserving — generated C is byte-identical across all four rewritten
lowerings. A2's arithmetic `may_fail = OR(operands)` rule is *mostly* right but makes a variable-divisor `/` look infallible,
which removes a guard that exists specifically to stop an unspecified-order diagnostic. One fixture I built to prove a hazard
turned out NOT to be one; I record that against myself.**

## 1. DIVERGENCE-2 still passes at both pins (dispatch-specified baseline)

Run exactly as the dispatch specifies, at the named starting pin and at A2's current tip:

| pin | result | generated-C sha (input A / B) | generator C size |
|---|---|---|---|
| `1885566` | **16/16 PASS** | `29eee68f4a58` / `e72d299afce6` | 11757 B |
| `bea071a` | **16/16 PASS** | `29eee68f4a58` / `e72d299afce6` | 11757 B |

Identical C, identical bytes, both strict-Clang and strict-GCC runs, different runtime outputs.
`./pep.ps1` seed was reused not rebuilt: `pep_ocaml.ml` is byte-identical across `1885566`, `3ad2bff` and `bea071a`
(`git diff --stat` empty), so the seed binary is the same object at every pin and the emitter file is the only variable.

## 2. The `prepend+reverse` rewrites are byte-identical — measured, not assumed

A performance rewrite that regenerates C is precisely where evaluation or emission order can drift, so I compared bytes.
`1885566..bea071a` touches four lowerings in `tests/pep_c23_emitter.pep`: `byte_length`, `byte_at`, `utf8_slice`, `int_text`,
plus the binary lowering (`a38a91e`). Three committed fixtures, each emitted at both pins:

| fixture | lowerings exercised | emitted C sha256 | identical |
|---|---|---|---|
| `d_a_byte_builtins.pep` | `byte_at`, `byte_length`, `utf8_slice` | `7D4AE57B7373…` (11799 B) | **yes** |
| `d_b_int_text.pep` | `int_text` | `B234213E10764…` (11248 B) | **yes** |
| `d_c_arith.pep` | binary `+ * <=` | `5215C9F63D60B…` (11993 B) | **yes** |

I traced the inversion by hand first (`prepend` builds the list backwards, then `reverse` restores source order) and then
confirmed it empirically, because a trace is not evidence.

**Fixture-design note, recorded because it cost two attempts:** a helper returning `Str` is refused cross-chunk —
`Pep C23 cross-chunk calls support Int, Bool, and locally declared record results`. The Str-returning lowering therefore
stays inline in `main`; Int-returning helpers are fine. That refusal is a known limit, not the thing under test, and it
must not be read as an emitter defect here.

## 3. `b758c91` narrows a refusal that `pep_div` still justifies

`b758c91` added: arithmetic `may_fail = OR(operands)`, with a static literal `/ 0` staying fallible.

The runtime it protects:

```
int64_t pep_div(int64_t a, int64_t b) {
  if (b == 0) { fputs("PEP_RUNTIME_DIVISION_BY_ZERO\n", stderr); exit(1); }
  if (a == INT64_MIN && b == -1) { fputs("PEP_RUNTIME_OVERFLOW\n", stderr); exit(1); }
  return a / b;
}
```

`pep_div` aborts on a zero divisor. So `/` with a **variable** divisor is not infallible, but the new rule returns
`OR(may_fail(left), may_fail(right))` = false for it. Measured consequence at `1885566` vs `bea071a`, same source, same
node count:

| fixture | shape | `1885566` | `bea071a` |
|---|---|---|---|
| `d_f_one_div.pep` | one fallible operand: `size / gap` | EMITS | EMITS |
| `d_g_literal_div.pep` | `size / size + size / 5` | REFUSES | EMITS |
| `d_d_var_div.pep` | `size / size + size / 1` | REFUSES | EMITS |
| `d_e_order_abort.pep` | `size / gap + (size + INT64_MAX)` | REFUSES | **EMITS** |

### The genuine hazard is `d_e` only — and I withdraw `d_d` as a hazard

I built `d_d` expecting to demonstrate the hole, then checked it properly and it does **not** demonstrate one:
`size / 1` has a literal divisor of 1, and `pep_div(a, 1)` cannot abort (`b != 0`; `b != -1`). So only **one** operand in
`d_d` can fail, there is no ordering choice, and emitting it is safe. Same for `d_g`, where `size / 5` is genuinely
infallible. Removing the `1885566` refusal on those two is a **correct widening**, not a regression.

`d_e` is different and is the real reproducer: **both** operands can abort, with **different** messages.
`size / gap` aborts `PEP_RUNTIME_DIVISION_BY_ZERO` (gap is 0); `size + 9223372036854775807` aborts `PEP_RUNTIME_OVERFLOW`
(any non-empty input makes size ≥ 1). Emitted at `bea071a` as:

```c
int64_t pep_local_11 = pep_add(pep_div(pep_local_4, pep_local_7), pep_add(pep_local_4, 9223372036854775807));
```

C leaves the evaluation order of those two arguments unspecified, so which abort message a user sees is unspecified.

**Observed, and honest about what it does not show:** run under both compilers on a 1-byte input, both printed
`PEP_RUNTIME_OVERFLOW`. I did **not** demonstrate clang/gcc divergence — the two chosen compilers happened to pick the same
order. The claim is not "compilers disagree"; it is that **the emitted program has an order-dependent diagnostic and the
guard that refused exactly that shape is now gone.**

## 4. Proposed minimal fix (predicted, NOT applied, NOT verified)

Scope `may_fail` for `/` to the real runtime condition: **`/` is infallible only when the divisor is an integer literal
whose value is neither `0` nor `-1`** (those are the only two values for which `pep_div` can abort). Everything else
stays fallible. `right.node.integerValue` is already used by A2's existing condition, so this is a same-line widening of
one predicate, not a new contract.

Predicted effect, stated in advance so it can be checked rather than believed:

| fixture | predicted | why |
|---|---|---|
| `d_e` | REFUSED (guard restored) | both operands fallible |
| `d_d` | emits (unchanged) | only `size/size` fallible → one operand |
| `d_g` | emits (unchanged) | `size/5` infallible → one operand |
| `d_a`/`d_b`/`d_c` | byte-identical C (unchanged) | no `/` in the emitted expression |

This sits with **A2** (emitter internals). I have not edited `tests/pep_c23_emitter.pep` and will not: I do not author what
I verify.

## Commands used (reproducible)

```
git worktree add --detach <dir> 1885566   # and bea071a; seed pep.exe copied (pep_ocaml.ml identical)
PEPIN_GATE_ROOT=<dir> python verification/probes/divergence_2_042.py
PEPIN_GATE_ROOT=<dir> PEPIN_APP_REL=<fixture> PEPIN_APP_REV=<sha> \
  PEPIN_C_OUT=<path.c> python verification/probes/emit_any_049.py
```

## Limits

- Emitted-C comparison is byte identity, which is the *stronger* demand; the dispatch allows alpha-equivalence. Byte
  identity passing is therefore sufficient, not merely necessary.
- Fixtures are small by construction; a lowering exercised only inside a large function is not covered here.
- Cross-chunk call resolution (`3acdd7d` is a **test pin**, not the fix) is untouched by this receipt; gating it waits on
  A2 actually landing the fix.

REF GH #16. Input SHAs `1885566`, `bea071a`. Author of the code under audit: A2. Independent run: A3.