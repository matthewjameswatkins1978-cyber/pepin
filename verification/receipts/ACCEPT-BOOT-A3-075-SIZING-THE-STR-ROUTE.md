# ACCEPT BOOT-A3-075 — sizing the Str route: the contract takes ONE type per slot, so "accept either" needs a shape change

**Verdict: widening the byte builtins to `Str` is not a one-line type change. The checker's builtin parameter
contract returns a single concrete type name per `(builtin, index)`, so accepting `Str` *or* `SourceBytes` requires
changing the contract's shape, then the emitter's C typing, then the runtime helper signatures.**

## The contract, at source

`tests/pep_checker_a13.pep`:

```
L1231: if name == "byte_at" { return 2 } else {}                        // arity
L1240: if name == "byte_at" && index == 0 { return "SourceBytes" } else {}
L1242: if name == "byte_at" && index == 1 { return "Int" } else {}
```

That is the whole parameter contract for `byte_at`: a function returning **one** type name per slot. There is no
union, list-of-accepted-types, or subtype relation in the signature — so "accept `Str` as well" cannot be
expressed by editing the returned string.

## Consequence for Route S

Three layers change, not one:

1. **Checker contract shape** — either return a set of accepted types, or introduce a dedicated
   `ByteSource`-like notion that both `Str` and `SourceBytes` satisfy. Then arity/param checks at L1231-1242 and
   the equivalents for `byte_length` and `byte_slice` all follow.
2. **Emitter typing** — the C parameter type is chosen from the Pep type name (`Node.text == "SourceBytes"` →
   `pep_source_bytes`, ~L827/L1425). A `Str` argument would need to reach a helper that accepts `pep_str`.
3. **Runtime helpers** — `pep_byte_at`-family functions must accept whichever representation arrives, including
   the length/offset fields, which differ between `pep_str` and `pep_source_bytes`.

That is a small, well-bounded feature — but it is a feature, not a contract tweak. It is **not** an hour of work.

## So the two routes, honestly sized

- **Route G (grant plumbing):** enable the v2 host grant so a Pep program can obtain `SourceBytes`. Touches host
  capability; the frozen 100k budget is implicated by A3-041's one-shot measurement.
- **Route S (Str-accepting byte builtins):** checker contract shape + emitter typing + three runtime helper
  families. Contained, no new capability, **no change to the frozen cap** — and, on this evidence, still the
  cheaper of the two.

Neither is mine to land, and A3 cannot certify its own work. What I can now say with evidence is **what each costs
and what it touches**, which is what a scope decision needs.

## Honest limits

- I read the `byte_at` contract and the `SourceBytes` typing path; I did **not** inspect `byte_length` and
  `byte_slice` contract lines individually, so "all three follow the same shape" is inferred from the arity and
  return-type lines, not verified line by line.
- I did not examine the runtime helper bodies, so the third layer's size is estimated from signatures rather than
  measured.

REF: GH #16.