# ACCEPT BOOT-A3-097 — canonical `compiler_a.pep` is a valid Pep program on three independent seeds

**Verdict: `examples/dogfood/pep0/compiler_a.pep` (blob `ca732536`, 9,639 B,
sha256 `4F6CE394D825671D4C551A708466F565CA2668363E1AF256C1C21D34941EDB88`) checks **valid with zero diagnostics** on the
seed compiler, and parses to 21 top-level forms. Verified on three separate seed builds across three lanes.**

Small receipt, foundational fact. Every M-1/M-2/M-3 claim rests on compiler A's own source being a well-formed program in the
real Pep language. That was assumed everywhere and verified nowhere.

## Result

| seed worktree | `pep_ocaml.ml` (working tree) | `check compiler_a.pep` |
|---|---|---|
| `wt-a3-dbea` (A2 lane, `bea071a`) | 148,791 B | **valid**, no diagnostics |
| `wt-a3-a1led` (A1 ledger, `ee7d104d`) | 145,104 B | **valid**, no diagnostics |
| `wt-a3-d188` (A2 pin, `1885566`) | 148,791 B | **valid**, no diagnostics |

`inspect` reports `status = parsed` with **21 top-level forms** — matching the 21 functions counted independently in A3-087.

Three different seed builds, two different seed revisions, same verdict. So the source is not merely accepted by whichever
seed happened to build it first.

## Why it needed saying

BOOT-A3-083/084 measured how much of this source the *emitter* can lower (10 whole-chunk check-valid, 9/21 emit) and A3-087
counted its constructs. Neither asked the prior question: does the seed consider it a legal program at all? If it did not,
"self-hosting" would be an attempt to compile an invalid program, and the 9/21 figure would be measuring the wrong thing.
It is legal, so the remaining gap is genuinely about emission and input access.

## Note on the seed sizes, since they look inconsistent elsewhere

`git cat-file -s` reports 143,092 B for `pep_ocaml.ml` at `ee7d104d` while the working tree shows 145,104 B. That is CRLF
checkout expansion, not a different seed: the difference tracks the file's line count. The *git blob* is the identity that
matters and it differs between lanes (`231caf1` fork), which is why A3-095's driver cross-check used blob hashes rather than
sizes.

## Limits

- `check` validates; it does not execute. I did **not** run compiler A under the seed interpreter — that needs
  `SourceBytes` input access, which A3-073/074 established is unavailable (no working `--grant-file`, one-shot CLI over the
  100k budget). So this says nothing about compiler A's runtime behaviour.
- Validity on the seed does **not** imply acceptance by compiler A's own S0 subset — the opposite is documented: all 21
  functions are outside S0 (A4 `OWN_SOURCE.md`, verified in A3-092). This receipt is about the seed's view only.
- Source identity is `ca732536`; a new A4 revision must be re-checked.

## Reproduce

```
git cat-file blob ca732536 > /tmp/compiler_a.pep
pwsh -NoProfile -File <seed worktree>/pep.ps1 check /tmp/compiler_a.pep --json   # -> status valid
pwsh -NoProfile -File <seed worktree>/pep.ps1 inspect /tmp/compiler_a.pep --json # -> parsed, 21 forms
```

REF GH #16. Source authored by A4. Verification: A3.