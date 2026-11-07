# ACCEPT BOOT-A3-074 — the `Str` rejection is general to all three byte builtins

**Verdict: the "extend byte builtins to accept `Str`" route is not partially open. All three refuse `Str` with
`PEP_TYPE_MISMATCH` before chunking. Input access therefore requires `SourceBytes`, and `SourceBytes` requires the
host grant.**

## Measurements (spike tree `3ad2bff`, so A2's patch is in place)

| fixture | shape | host analysis |
|---|---|---|
| `probe_str_bytes.pep` | `byte_length(text)` where `text: Str` | `invalid ['PEP_TYPE_MISMATCH']` |
| `probe_byte_at_str.pep` | `byte_at(text, 0)` where `text: Str` | `invalid ['PEP_TYPE_MISMATCH']` |
| `probe_byte_slice_str.pep` | `byte_slice(text, 0, 1)` where `text: Str` | `invalid ['PEP_TYPE_MISMATCH']` |

All three refuse **at host analysis**, so none of this is an emitter question, and A2's patch cannot affect it.

## The completed chain

1. Pep-side lexing needs per-byte access.
2. Every byte builtin demands `SourceBytes`; `Str` is rejected by all three.
3. `SourceBytes` is a v2 **host-granted** capability (SEED_LANGUAGE L48, unaccepted A10 branch).
4. The documented grant command is non-functional (A3-041: no `--grant-file`, over the 100k budget).

DIVERGENCE-2 passes only because my probe supplies input through `open_bytes` at the host level
(`D1:host-valid`). **A Pep program cannot obtain its own input.**

## What this closes and what it leaves

**Closed:** the hypothesis that a tokeniser could be built cheaply by widening `byte_length` alone. It cannot —
the rejection is uniform across `byte_at`, `byte_length` and `byte_slice`.

**Left, and it is a scope decision rather than a verification finding:**
- **Route G — grant plumbing.** Make the v2 host grant work so a Pep program can obtain `SourceBytes`. Larger;
  touches host capability, and the frozen 100k budget is implicated (A3-041's one-shot check exceeded it).
- **Route S — widen the byte builtins to `Str`.** Three builtins, checker-visible type change plus emitter
  support, but no grant, no new capability, and no budget change. **This is the smaller route**, and on the
  evidence so far it is the only one that puts a Pep tokeniser within reach without touching the frozen cap or
  inventing a capability.

Both are code changes in files I do not own, and A3 cannot verify its own work. Naming which route to take is
Matthew's call; I have measured both and can accept either.

## Honest limits

- Three shapes, one tree, one seed build.
- I did not read the checker's parameter table, so I cannot say whether widening to `Str` is a one-line contract
  change or requires value-conversion machinery inside the builtins. That is the first thing whoever takes
  Route S should check — it decides whether Route S is an hour or a day.

REF: GH #16.