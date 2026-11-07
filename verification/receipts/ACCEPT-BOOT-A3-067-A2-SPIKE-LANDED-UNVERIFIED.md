# BOOT-A3-067 — A2 has landed the three-site work on `codex/a2-divergence-spike` (unverified by A3)

**Status: landed by A2, NOT yet verified by A3. Reported here because it is the first movement on the floor in
this campaign, and because it carries a base problem that must be fixed before anyone treats it as done.**

## What exists now

Branch `origin/codex/a2-divergence-spike` @ `3ad2bff`, three commits:

```
3ad2bff test(c23): pin DIVERGENCE-2 input-dependent emission end to end (two unseen inputs, both compilers)
a5efd0d test(c23): pin the utf8_slice channel end to end (build-c23, strict compilers)
7335114 feat(emitter): by-name utf8_slice + int_text lowering with bump-pool runtime helpers
```

By-name site counts on that branch (the measurement from BOOT-A3-062, re-run there):

| builtin | sites | before |
|---|---|---|
| `utf8_slice` | **3** | 0 |
| `int_text` | **3** | 0 |
| `byte_slice` | 0 | 0 |
| `source_bytes` | 0 | 0 |

So A2 implemented exactly the three-site shape, for both builtins, with runtime helpers. **True change size is
`+61 lines` in `tests/pep_c23_emitter.pep`** — measured against its own base, not against `86ff953`.

## The base problem — do not merge this as-is

- `merge-base(86ff953, spike) = 231caf1` and **`86ff953` is not an ancestor of the spike**. The branch forked
  from A1's lane `231caf1`, before A1's later work at `86ff953`.
- The naive `git diff 86ff953..spike` looks like **2,964 deletions** — including `docs/outbox/AGENT2_OUTBOX.md`,
  `examples/dogfood/pepin-source-scan.pep`, `tests/probe_dogfood_scan_a1.py` and
  `tests/test_c23_twin_byte_identity.py`. Those are **not** deletions by A2; they are content the spike simply
  never had. Anyone reading the raw diff will misread this as destructive work.
- Consequence: the patch needs a rebase onto current work, and **my BOOT-A3-062 counts were measured at
  `86ff953`** while A2 presumably measured against `231caf1`. The acceptance must be re-run on the rebased tree,
  not inferred from either measurement.

## What is still unproven

- **DIVERGENCE-2 has not been run by A3.** A2 pinned its own end-to-end test; that is A2's evidence, and A2
  cannot be the verifier of its own slice.
- `source_bytes` remains at **0** sites, so the input channel question from BOOT-A3-066 is untouched by this
  patch. Whether A2's divergence test obtains input another way is exactly what the verification run must
  establish — if it does not, the test may be pinning something weaker than input-dependent C text.

## Next action (concrete)

1. Create a disposable worktree at `3ad2bff`.
2. Run `divergence_2_042.py`, then `emit_any_049.py` over `verification/fixtures/str/s5_slice_local.pep` and
   `verification/fixtures/emit/iso_int_text.pep`, then the five acceptance criteria from the amended proposal.
3. Report which criteria pass, and specifically whether the two unseen inputs produce **different C text** that
   compiles under strict Clang **and** GCC and runs to different outputs.

REF: GH #16.