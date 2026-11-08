# ACCEPT BOOT-A3-111 — differential is now seed-aware and names the seed blob; A2 `db8e9c56` clean

**Verdict: the seed-vs-emitted differential now reports per-seed applicability instead of counting an older seed's missing
builtin as a disagreement, and it prints the `pep_ocaml.ml` blob in every verdict — the practice BOOT-A3-110 committed to.
A case the seed genuinely cannot evaluate reads `N/A`; a real runtime error still reads `FAIL`. A2's `db8e9c56` is
non-regressive.**

Seed blobs in play this run: `f8f476198f` (146,713) and `c92f9cc4a3` (143,092).

## The improvement

Before, running on the older seed produced `SEED vs EMITTED: DISAGREE` with 2 failures, which reads like an emitter problem
and is not one. Now:

```
=== newer seed (f8f476198f) ===
9 cases: 9 applicable, 0 not applicable on this seed, 0 disagreeing
SEED vs EMITTED: AGREE on all  [seed f8f476198f]

=== older seed (c92f9cc4a3) ===
N/A  builtin composition   seed lacks builtin 'str_concat' (not an emitter finding)
9 cases: 7 applicable, 2 not applicable on this seed, 0 disagreeing
SEED vs EMITTED: AGREE on 7/9 (rest need a newer seed)  [seed c92f9cc4a3]
```

Two things changed and the second matters more:

1. **The seed blob is named in the output**, so a receipt quoting this result cannot be ambiguous about which seed produced
   it. That is the practice A3-110 committed to, now enforced by the tool rather than by my memory.
2. **`N/A` is narrow.** It applies only when the seed exits non-zero, the error is `PEP_UNKNOWN_FUNCTION`, *and* the missing
   name is one of thirteen known builtins. Everything else remains a failure.

## The guard, checked rather than assumed

An over-generous "not applicable" would be a way for this probe to quietly stop testing things — the failure mode I have been
criticising all mission. So I checked that a real error is not excused:

```
seed top-level division by zero -> exit=1  "2:14: PEP_RUNTIME_DIVISION_BY_ZERO: Division by zero"
builtin name found in error : '' (none)
error is PEP_UNKNOWN_FUNCTION: False
would classify as N/A       : False
```

A runtime abort carries no builtin name and is not `UNKNOWN_FUNCTION`, so `missing` is empty and the case fails. Only a
genuine "this seed predates that builtin" is ever excused.

A useful side effect: this confirms the seed **does** surface top-level runtime errors (exit 1 with a code and span), so the
seed side of the differential is really evaluating rather than silently doing nothing — the concern that produced A3-104.

## A2 `db8e9c56` regression check

`ad7f1c08` → `db8e9c56` is "carried-binding assignment-target resolution (A2-S2)", 26 lines in the emitter. Still no
`emit_c23_statement_fragment` entry or registered fragment tool, so fields 1/3/4 remain unverifiable — this is the third
consecutive commit of internal fragment preparation. What could be checked:

| check | result |
|---|---|
| `d_a_byte_builtins` emitted C | `7D4AE57B7373…` — identical to `1885566` |
| `d_b_int_text` | `B234213E1076…` — identical |
| `d_c_arith` | `5215C9F63D60…` — identical |
| seed blob at this pin | `f8f476198f` |

Assignment-target resolution touches name binding, which is high-risk area, and it produced no emitted-C drift — exactly the
right result for preparatory work behind an entry that does not exist yet.

## Limits

- The `N/A` list is thirteen builtins hard-coded in the probe. If a seed adds a fourteenth that a case needs, that case will
  report `FAIL SEED ERROR` until the list is extended — deliberately the safe direction.
- I verified the guard's classification by feeding it a real error string, not by adding a permanently-failing case to the
  suite. A permanently-failing case would make the suite red forever, which is worse.
- Applicability is per *case*, not per expression: a case needing two builtins is only excused when the seed names one.
- Both runs use the A2-lane emitter as the `gate` root; only the seed differs.

## Reproduce

```
# newer seed
PEPIN_SEED_ROOT=D:/Projects/wt-a3-dbea PEPIN_GATE_ROOT=D:/Projects/wt-a3-dbea \
  python verification/probes/seed_differential_106.py
# older seed
PEPIN_SEED_ROOT=D:/Projects/pepin     PEPIN_GATE_ROOT=D:/Projects/wt-a3-dbea \
  python verification/probes/seed_differential_106.py
```

REF GH #16. Emitter A2 `db8e9c56`; seeds `f8f476198f` and `c92f9cc4a3`; differential A3.