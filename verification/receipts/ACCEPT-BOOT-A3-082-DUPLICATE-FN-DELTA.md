# ACCEPT BOOT-A3-082 — A1's new duplicate-function refusal verified; my five identity channels persist unchanged

**Verdict: A1's `07f1da86` duplicate-top-level-name refusal is genuinely fail-closed and correctly scoped, and its
"seed-mirror" claim is verified against the seed rather than taken on trust. The five identity channels from A3-080 are
unaffected — A1's new commit did not touch the merge path.**

## Delta audited

`183b2fac` → `07f1da86`, one commit: *"refuse duplicate top-level fn names host-side (seed-mirror PEP_DUPLICATE_FUNCTION)"*.
`pep_sectional.py` blob `fa886d08` → `75902237`; `pep_chunk_contract.py` unchanged.

## The seed-mirror claim, checked against the seed

I did not take "mirrors the seed" on trust. New fixture `verification/fixtures/emit/dup_top_level_fn.pep` (two top-level
`fn main`), classified by the live seed:

```
{"status":"invalid","diagnostics":[{"code":"PEP_DUPLICATE_FUNCTION","severity":"error",
  "message":"Duplicate function 'main'",
  "span":{"start":{"offset":269,"line":8,"column":1},"endOffset":300}}]}
```

The seed refuses, at the **second** declaration. A1's host-side path returns
`(name, "duplicate-function", ["PEP_DUPLICATE_FUNCTION"])` — same code, and `build_c23` raises
`ValueError("Pep C23 sectional check failed in main: ['PEP_DUPLICATE_FUNCTION']")` before any emission. So the mirror claim
holds at the level that matters: same code, fail-closed, before emission.

`_duplicate_top_level_functions` edge cases, driven directly:

| input | result |
|---|---|
| two `main` | `['main']` |
| distinct names | `[]` |
| three `main` | `['main']` (deduped once) |
| second `main` with `parentId=5` (nested) | `[]` — correctly **not** flagged; only top level counts |
| empty | `[]` |

The nested case is the one that would have been easy to get wrong, and it is right.

## Two notes, neither blocking

1. **`"sigs": sigs` on the duplicate path carries `None`.** The early return runs before
   `if sigs is None: sigs = fetch_all_sigs(...)`, so when a caller omits `sigs` the returned dict has `"sigs": None`.
   `build_c23` raises on `failures` before reading `sigs`, so no current consumer trips — latent, not live. A caller that
   reads `checked["sigs"]` on a rejected program would get `None` where every other return shape gives a list.
2. **No source span on the host-side refusal.** The seed points at offset 269 / line 8; the host path reports only the
   name. Acceptable for a fail-closed refusal, but it means seed↔host diagnostic parity is not exact on this channel —
   relevant to A1's R2 span work, which just reported 348/348 name spans faithful through transport.

## A3-080's findings re-confirmed at the new revision

All five identity channels behave exactly as before — A1's commit did not touch `merge_reports`. The six fail-closed
channels and the valid control still pass. Nothing I reported is stale.

```
PEPIN_SECTIONAL_ROOT=<worktree at 07f1da86> python verification/probes/sectional_negatives_080.py
```

REF GH #16. Input SHA `07f1da86` (was `183b2fac` in A3-080). Author under audit: A1. Independent run: A3.