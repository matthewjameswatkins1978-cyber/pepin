# BOOT-A3-001: A2 pre-fix vs re-pin independent reproduction (PEP-BOOT-20261106-01, Agent 3 slice 1/3)

**Date:** 2026-11-06 · **Dispatch:** PEP-BOOT-20261106-01 (mirror comment `6687014403`) + LUCY-20261106-003
**Seat:** Agent 3 (independent verify / hostile oracles). No builder code written; `verification/**` only.
**PIN: A3 | `codex/bootstrap-agent3-verification@4748cf6`** (clean, remote-verified at start of slice).

## Live remote check before acting (all match dispatch pins)

- A2 `origin/codex/a2-bounded-emission` = `123d8b3` — **re-pin NOT published, blocker still holds.**
- A1 `origin/codex/p1-checker-cost-fix` = `1aaead7`; no remote `codex/candidate7-20261105`.
- A3 `origin/codex/bootstrap-agent3-verification` = `4748cf6` (this branch, clean).
- Main checkout `D:/Projects/pepin` left untouched (campaign branch + Matthew's uncommitted A14 hunk preserved).
- Read-only note: `D:/Projects/wt-a2-bounded` (HEAD `123d8b3`) currently holds the 3-line repair as
  **local unstaged edits** (worker active there; observed mid-slice index churn `MM`→` M`).
  A2's staged text matches the dispatch recipe exactly (captured read-only, one hunk each for
  `A1_SHA`, contract fetch, `duplicate_fact` stamps). A2 branch itself untouched by me.

## What I did: disposable scratch, pre-fix vs patched, same probe

- Scratch `D:/Projects/wt-a3-bootdisp1` = `git worktree add --detach 123d8b3` (never pushed, no branch).
  Cold at start: no `pep_chunk_contract.py` anywhere, no `_build` (verified by listing).
- **Pre-fix run** (`python tests/probe_seam_chunked.py`, committed `123d8b3` text): seed built from
  stale pin `2ad750b`, `bundle-open OK`, `parse OK nodes=68 bytes=575`, `sig-id-state OK`
  (renumber, no collision) — then **`ModuleNotFoundError: No module named 'pep_chunk_contract'`
  at line 278**. Cold-start defect independently reproduced; nothing past the seam executes.
- **Patch in scratch only** (Threadmoth `preview → mutate`, 3 atomic commits, certificates on file):
  1. `A1_SHA` → `727f8af4d019e6e5e235ac26077a12b166b9c080`;
  2. `prepare()` fetch list += `("pep_chunk_contract.py", "pep_chunk_contract.py")`;
  3. `duplicate_fact` += `"document": sem["document"], "revision": sem["revision"]`.
  Deviation from A2's text: explanatory comments shortened; all three semantic lines byte-equivalent.
- **Patched run: `EXIT=0`**, full log in scratch (removed after this receipt; key lines below).

## Patched result (exact)

- `bundle_sha256 80c28ef521d8076674a3925891f47ca4be18a3005cc396465667a250ed4dfd65` —
  **identical** to my K-A3-8 dry run and A1's reported value (checker content pin-invariant).
- Seed marker `seed_source_pin.txt` = `727f8af…080`; build-input parity proven:
  `git rev-parse 727f8af:pep_ocaml.ml` = `git hash-object _build/a1_seed/pep_ocaml.ml` = `923769a…`.
- Chunks valid with A1-ledger node counts: decl 18, make_token 55, add_one 8, main 5.
- `strict-clang OK b'42'`, `strict-gcc OK b'42'`, reverse order both OK, `oracle-seed OK seed=b'42'`.
- Toolchains observed: **Clang 23.1.4** (`-std=c23`), **GCC 16.2.0** (`-std=c2x`),
  probe strict flags `-Wall -Wextra -Wpedantic -Werror -O2` (probe lines 414–418, 460–464, 608–610).
- **11 negatives, all refusing** (A1's "12" remains an overcount; use this list):
  `neg-no-call-fact`, `neg-ambiguous-call`, `neg-missing-target`, `neg-ambiguous-target`,
  `neg-arity-mismatch`, `neg-foreign-result`, `neg-stale-revision` (transport gate,
  `PEP_STALE_REVISION`), `neg-unit-index`, `neg-dup-external-name` (`status=invalid`,
  `codes=['PEP_DUPLICATE_FUNCTION']`, distinct-name control passes — the stamp fix is what
  exercises this instead of a `KeyError`), `neg-unit-order-clang`, `neg-unit-order-gcc`.

## False-green oracle for Candidate7 (recorded, not yet run)

- Guard location (static): probe `prepare()` rebuilds the seed exe whenever
  `seed_source_pin.txt != A1_SHA` — a marker/exe mismatch cannot silently pass.
- Acceptance pair this run binds: `bundle 80c28ef5…` **and** `marker == published A1 SHA`
  **and** `hash-object(build input) == rev-parse(<A1_SHA>:pep_ocaml.ml)`.
  A "green" with a stale marker, stale bundle, or rebuilt-from-other-source exe is RED.
- Prepared focused invocation (frozen Full-v2 deliberately NOT run — no candidate exists):
  1. `python verification\probes\verify_frozen_manifest.py <candidate>` → exit 0, 15 pins, drift 0;
  2. cold scratch: merge published A1 + published A2 SHAs only, run patched-shape probe,
     expect the exact values above (bundle/marker/42s/11 negatives);
  3. on published Candidate7: `verification\tools\run_acceptance_gates.ps1 -Mode Full
     -CombinedWorktree <candidate>` with OWN verification files, report all 15 frozen rows
     verbatim (66-node row stays RED), plus the separate strict staged-zero-uncovered gate —
     never relabel old 14/15 as green.

## Status

- Awaiting A2 push (`123d8b3` at last check) → then A1 Candidate7 → then my gate verdict.
  No GitHub #16 post: no new handoff, collision, or gate event — A2 is actively working the
  repair and my receipt lives here on my own branch.
- Next (slice 2/3 while waiting): minimal cross-function wrong-signature adversarial pinned to
  same-target revision, honest producer boundaries (normal-host attack vs hand-forged fact);
  verify A4's record-return vertical when A2 publishes.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-bootdisp1 123d8b3d9c528ce6cd476fa88839624036d89d80
cd D:/Projects/wt-a3-bootdisp1; python tests/probe_seam_chunked.py   # pre-fix: ModuleNotFoundError line 278
# apply the 3 scratch lines above (Threadmoth), re-run                    # patched: EXIT=0, 42/42, 11 negatives
```
