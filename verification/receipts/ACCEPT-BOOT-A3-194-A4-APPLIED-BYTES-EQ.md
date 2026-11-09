# ACCEPT BOOT-A3-194 — A4's bytes_eq adoption clears names_equal; match_tail's empty-then is still there

**A4's `1f98045d` applies the A3-191 `bytes_eq` helper. Verified through the product path: `names_equal` no longer fails, no
"two fallible operands" refusal remains, and the build stops at `scan_value`'s step limit — the one blocker without a fix.**

Seed blob `f8f476198f`. A4 `1f98045d`, `compiler_a.pep` blob `506e8af2`, 1,546 lines, **35 functions**.

## The verification

```
$ python pep_c23.py build-c23 …/compiler_a.pep --sectional …
Pep C23 unsupported: Pep C23 sectional check failed in scan_value: ['PEP_RUNTIME_STEP_LIMIT']

fails in names_equal: False
fails in match_tail:   False
two-fallible refusals: False
```

**Blocker 2 is closed.** The `bytes_eq` helper is in and it does what A3-191 measured.

## But the file still carries match_tail's empty-then

`if qe == q {` with an empty then-branch is **still present**. It is not visible right now because the sectional check stops at
`scan_value` first — `scan_value` is checked before `match_tail` in the current order.

**So when A4 fixes `scan_value`, the next stop will almost certainly be `match_tail`'s empty-then.** A3-193's one-line inversion is
already verified; applying it now costs nothing and avoids a second round trip.

That is worth saying explicitly because the refusal being invisible is not the same as the construct being absent, and "it stopped
somewhere else" is exactly how a pending blocker gets missed.

## State

| # | function | state |
|---|---|---|
| 2 | `names_equal` | **closed by A4** in `1f98045d`, verified here |
| 3 | `match_tail` | empty-then **still present**; fix verified (A3-193), not applied |
| 1 | `scan_value` | the current stop; needs the loop restructure (A3-190) |
| 4 | `match_varlet_body` (347 nodes), `is_unsupported_prog` (687) | behind `scan_value` |

## Limits

- One commit, one build; I did not run the runbook because the build does not complete.
- I verified the absence of the *textual* empty-then pattern; I did not re-derive that no other construct blocks `match_tail` once
  `scan_value` clears.
- `bytes_eq` is present and `names_equal` passes; I did not inspect their version line by line against my proposed shape.

REF GH #16. Confirms `6729534712` (A3-191). Flags forward risk from `6729580473` (A3-193).