# ACCEPT BOOT-A3-073 — the remaining floor gap, named with a measurement at each link

**Verdict: a Pep tokeniser cannot be written today, and the reason is a three-link chain, each link measured.
The wall is not the emitter, not the step budget, and not the patch A2 just landed — it is input access.**

## The decisive measurement

`byte_length(text)` where `text` is a `Str`:

```
fn main() -> Int {
    let text = "abc"
    let n = byte_length(text)
    return n
}
```
→ `host analysis: status=invalid ['PEP_TYPE_MISMATCH']` — **refused before chunking, so not an emitter question.**

So the byte builtins (`byte_at`, `byte_length`, `byte_slice`) do **not** accept `Str`. They require
`SourceBytes`, and a `SourceBytes` value can only arrive through the host grant path.

## The chain

1. **Pep-side lexing needs per-byte access.** Classifying letters/digits/whitespace means reading individual bytes.
2. **Per-byte access requires `SourceBytes`.** Measured above: `Str` is rejected with `PEP_TYPE_MISMATCH`.
3. **`SourceBytes` requires a v2 host grant.** `docs/SEED_LANGUAGE.md` L48 calls `source_bytes()` a *"v2
   host-granted"* capability from the unaccepted A10 review branch (BOOT-A3-066).
4. **The documented grant command does not work.** BOOT-A3-041 measured no `--grant-file` option, and a one-shot
   CLI check exceeding the 100,000-step budget on both apps.

DIVERGENCE-2 passes only because my probe drives `open_bytes` at the host level itself (its `D1:host-valid` row).
A Pep program cannot do that for itself.

## What this means for the mission

The campaign's remaining work is **not** more emitter lowering — A2's three-site patch closed the emission side,
and DIVERGENCE-2 demonstrates input-dependent C end to end (BOOT-A3-072). The remaining work is **making input
reachable from Pep source**, which is a host-capability and grant-plumbing question, not an emitter one.

Two routes, both outside a verification lane:

- **Land the grant plumbing** so `SourceBytes` can be obtained by a Pep program, or
- **extend the byte builtins to accept `Str`** so ordinary string data can be classified without a grant — a much
  smaller change, and it would make a tokeniser writable today.

I have measured the gap; choosing between those is a scope decision.

## Honest limits

- One shape tested (`byte_length(Str)`). I did not test `byte_at(Str, 0)` or `byte_slice(Str, …)`; if the
  refusal is specific to `byte_length`, the "extend to Str" route may already be partially open.
- The refusal is `PEP_TYPE_MISMATCH` at host analysis; I did not read the checker's parameter table to confirm
  which type it demands.

REF: GH #16.