# FINDING BOOT-A3-110 — two seed revisions are in play, and they differ by exactly one builtin: `str_concat`

**Verdict: the workshop is running on two different seed commits. The campaign base, A1's ledger branch and A4's lane carry
one seed; A1's pipeline branch and A2's branch carry a newer one. They differ in exactly one place: the newer seed knows
`str_concat`, the older one rejects it as `PEP_UNKNOWN_FUNCTION`. `str_concat` appears in no documentation, and it will
enter the merged candidate through A1-S3's integration without any explicit decision.**

## The two seeds

| lane | revision | seed blob | size | `str_concat` |
|---|---|---|---|---|
| campaign base | `bddd354` | `c92f9cc4a3` | 143,092 | **absent** |
| A1 ledger | `8e9edab6` | `c92f9cc4a3` | 143,092 | **absent** |
| A4 spec | `946d9b6e` | `c92f9cc4a3` | 143,092 | **absent** |
| A1 pipeline | `9bf18699` | `f8f476198f` | 146,713 | **present** |
| A2 spike | `ad7f1c08` | `f8f476198f` | 146,713 | **present** |

Note A1's own two branches disagree: the oracle/ledger lane runs the old seed, the sectional/pipeline lane runs the new one.

## The divergence is exactly one builtin

I probed all eleven non-`SourceBytes` builtins through `pep.ps1 check` on both seeds:

```
                old seed (143,092)      new seed (146,713)
append          valid                   valid
byte_at         valid                   valid
byte_slice      valid                   valid
contains        valid                   valid
int_text        valid                   valid
length          valid                   valid
prepend         valid                   valid
reverse         valid                   valid
say             valid                   valid
str_concat      invalid PEP_UNKNOWN_FUNCTION   valid
utf8_slice      valid                   valid
```

Ten identical, one different. Measured at both `check` and `run`: the old seed rejects `str_concat` in both paths; the new
seed accepts and evaluates it (`say(str_concat("a","b"))` prints `ab`).

## Where it came from

`git log -S str_concat -- pep_ocaml.ml` → **`844c8b0`, 2026-11-03, "feat(host): str_concat builtin closes CD3
diagnostic-message parity (Slice 1)"**. It is present on `codex/a1-typed-bound-pipeline`, `codex/a2-divergence-spike`,
`codex/candidate7-20261105`, `codex/checker-emitter-integration` and several scratch branches, and **absent from
`campaign/pep-v01-sustained-build-20261027`**. It appears in **no file under `docs/`** on either the campaign branch or the
ledger branch.

So this is most likely a legitimate earlier slice that simply has not been merged to the campaign branch. I am **not**
calling it unauthorised. The finding is about consequences and record-keeping, not blame.

## Why it matters

1. **The integration merge will carry a seed change.** A1-S3 merges A1-pipeline + A2 + A4. Both implementation lanes carry
   the new seed, so the candidate automatically gains a builtin that the campaign base does not have. That is a
   language-surface change arriving through a merge rather than through a decision — the kind of thing the dispatch's "no
   automatic permission: semantic change" line exists to catch. It should be named in the S3 receipt, not discovered after.
2. **"Verified against the seed" is ambiguous.** A result measured on one seed can be false on the other. My own 9-case
   differential passes **9/9** on the new seed and **7/9** on the old one, where the two failures are `SEED ERROR exit=1
   PEP_UNKNOWN_FUNCTION` rather than emitter disagreements. Every verification receipt in this lane should name the seed
   blob.
3. **A1's lanes cannot check each other's work consistently.** The ledger lane (oracle, 23 shapes) and the pipeline lane
   (sectional, fragment work) run different seeds, so a program valid on one is not necessarily valid on the other.

## My own error, recorded

My first attempt at the table reported all five lanes as carrying the *old* seed, which would have meant no committed seed
anywhere had `str_concat` — contradicting A2's live worktree. The cause was my PowerShell loop reusing `$obj`/`$size` from
the previous iteration when `rev-parse` failed, because I had not fetched the new commit into that worktree. Every row
looked identical because every row was stale. Caught it by cross-checking one row against the worktree directly
(`HEAD:pep_ocaml.ml` = 146,713, clean, contains `str_concat`). Refetched, added explicit `$LASTEXITCODE` handling, and the
table above is the corrected result. That is the sixth instrument defect in this lane and the same pattern as the others: my
harness, not the code under audit.

## Recommendation, not a demand

- A1-S3's candidate receipt should state which seed blob the integrated tree carries, and record that it introduces
  `str_concat` relative to the campaign base.
- `SEED_LANGUAGE.md` (or equivalent) should list `str_concat`, or the builtin should be removed from the lanes. Right now
  the implementation and the documentation disagree on whether it is part of the language.
- Verification receipts in this lane should name the seed blob. I will do so from here on.

## Limits

- I probed eleven builtins through `check`; `source_bytes` needs a v2 host grant and could not be included.
- Two seed blobs is what the five named revisions show. Other branches not examined may carry further variants.
- I did not attempt to determine which seed the *next* candidate should use — that is A1's integration call with Lucy.

REF GH #16. Seed blobs `c92f9cc4a3` and `f8f476198f`. Investigation: A3.