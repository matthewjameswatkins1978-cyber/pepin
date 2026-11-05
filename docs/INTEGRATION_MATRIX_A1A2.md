# A1/A2 joint tree compatibility matrix (Campaign K K1)

Measured 2026-11-05 by A1 in `D:/Projects/wt-a1-fix`. Every SHA below was verified with
`git ls-remote` **and** `git cat-file -t` before this document was written. Nothing here is
inferred from prose; each row states the command that produced it.

This document is the integration contract between A1's checker lane and A2's C23 emitter lane.
It replaces per-campaign re-derivation of "which side owns which file at which SHA".

## 1. Pins (verified on `origin`)

| Role | Branch | SHA | Worktree | Verified |
|---|---|---|---|---|
| A1 | `codex/p1-checker-cost-fix` | `727f8af4d019e6e5e235ac26077a12b166b9c080` | `D:/Projects/wt-a1-fix` | `ls-remote` = local, `cat-file -t` = commit, worktree clean |
| A2 | `codex/a2-bounded-emission` | `123d8b3d9c528ce6cd476fa88839624036d89d80` | `D:/Projects/wt-a2-bounded` | `ls-remote` = commit; not re-pinned to A1 `727f8af` |
| Integration | `codex/checker-emitter-integration` | `46b6712df20eba5ec5dea5a95771017f4245602a` (**Candidate6**) | `D:/Projects/wt-integration` | frozen, A/B baseline, must not be rewritten |
| Contract | — | `docs/CHECKED_CHUNK_CONTRACT.md` @ `727f8af` | — | A1-owned, authoritative |

## 2. File dependency map (who owns what, and what breaks if it moves)

| Artefact | Owner | Consumed by | Pin discipline today |
|---|---|---|---|
| `tests/pep_checker_a13.pep` (checker source) | A1 | A2 probe bundle, A1 tests | fetched at A1_SHA |
| `pep_ocaml.ml` (seed compiler) | A1 | A2 probe seed build, `pep.ps1` | fetched at A1_SHA |
| `tests/chunk_helper.py` (fact marshaller) | A1 | A2 probe | fetched at A1_SHA |
| `pep_chunk_contract.py` (host document/revision index) | A1 | A2 probe (`__import__`), A1 tests | **NOT fetched — imported from the local tree** (see §4) |
| `examples/pep_lexer.pep`, `examples/pep_parser.pep` | A1 | A2 probe bundle | fetched at A1_SHA |
| `tests/pep_c23_emitter.pep` (emitter) | A2 | A2 tests, probe | in-tree |
| `tests/probe_seam_chunked.py`, `tests/probe_text_builder_span.py` | A2 | A2/A3 seam evidence | in-tree; pins A1_SHA as a constant |
| `stdlib/scan.pep`, `c_init.pep`, `c_text.pep`, `c_tokens.pep`, `text_builder.pep` | A2 | A2 tests | in-tree |
| `tests/test_c23_*.py`, `test_a14_c23.py`, `test_scan.py`, `test_lexer_diff.py` | A2 | A2 | in-tree |
| `tests/test_chunk_*.py`, `test_a13*.py`, `test_lexer_chunk_ledger.py`, `test_checked_chunk_contract.py`, `test_bounded_units.py`, `test_closure_inventory.py`, `test_staged_ingress.py` | A1 | A1 | in-tree |
| `pep_c23.py` (host bridge / `require`/`parse_target`/`typed`) | A1-owned, effectively shared | both probes | in-tree on both branches |

**Overlap is zero.** Since merge-base `b9e26dfa51ff4e60d4ec90d5e1e880e416c0dc5f`, A1 changed
23 files and A2 changed 35; `Compare-Object` of the two name lists returns no common file.

## 3. Candidate7 merge sequence (measured, not planned)

Dry run performed in a disposable detached worktree, no commit published:

```
git worktree add --detach <tmp> 46b6712        # Candidate6
git merge --no-commit --no-ff 727f8af          # -> clean, 5 files (A1 delta only)
git commit                                     # scratch only
git merge --no-commit --no-ff 123d8b3          # -> clean, 24 files (A2 delta only)
```

Result: **zero conflicts in both steps.** Candidate6 already contains A2 emitter `e0e49e5`, so
merging `123d8b3` adds only the delta after it (prototypes section, guard-chain Str, probe
re-pin, stdlib, tests). A1's delta is `2ad750b` + `727f8af` (batch-uniqueness gate + stamped
callee identity). The two deltas touch disjoint file sets.

Merge-bases (measured): `merge-base(46b6712, 727f8af) = 52cb397`;
`merge-base(46b6712, 123d8b3) = e0e49e5`; `merge-base(123d8b3, 727f8af) = b9e26df`.

## 4. The re-pin, exactly (this is the whole A2 K1 ask)

A2 `123d8b3` + A1 `727f8af` are **compatible**, but the probe as published cannot run or cannot
tell the truth at `727f8af`. Two facts, both measured:

**(a) Cold-clone dependency (independently reproduced, matches A3 H-V1).**
Fresh worktree of `123d8b3`, no `_build`: `python tests/probe_seam_chunked.py` →
`ModuleNotFoundError: No module named 'pep_chunk_contract'` at `tests/probe_seam_chunked.py:278`.
`prepare()` fetches five A1 files but not this one, and the file does not exist on A2's branch.

**(b) Schema delta (new at `727f8af`).** With the contract fetched, the probe reaches
`neg-dup-external-name` and dies at `helper.checked_fn_value(duplicate_fact)` with
`KeyError: 'document'`. The probe's single hand-built fact predates A1 G-A1-2, which put
`document`/`revision` on `CheckedFunction` and `ResolvedSignature`. `helper.fetch_all_sigs`
stamps real facts, so every honestly-produced fact in the probe is already fine.

Minimum patch (three lines, applied and tested by A1 in a scratch worktree — **A2's branch was
not modified**):

```python
A1_SHA = "727f8af4d019e6e5e235ac26077a12b166b9c080"
#   in prepare()'s fetch list:
                           ("pep_chunk_contract.py", "pep_chunk_contract.py"),
#   in the hand-built duplicate fact:
                      "document": sem["document"], "revision": sem["revision"],
```

## 5. Result of that re-pin (builder-run by A1, A2's code, disposable tree)

At `123d8b3`'s emitter + `727f8af`'s checker/seed/helper, `python tests/probe_seam_chunked.py`
→ **exit 0**:

- four chunks `status=valid` from the *new* checker bundle
  (`bundle_sha256 80c28ef5…`, pin marker `727f8af`, vs `19a56ef…` / `2ad750b` before);
- `emit-prototypes-{make_token,add_one,main}` = emitted, `prototypes_bytes=267`;
  `assembled_c_bytes=5875`, reverse-order `6142`;
- strict Clang **and** GCC run `42\n` in document order **and** in reverse unit order;
- seed oracle `42\n`;
- 9 unit negatives + `neg-stale-revision` (`PEP_STALE_REVISION` at the transport gate, emitter
  never reached) + `neg-dup-external-name` (`PEP_DUPLICATE_FUNCTION`, distinct-name control
  green) + both `neg-unit-order` compiler negatives → **all held**.

This is `PUBLISHED + TESTED` as a *builder* result about A2's code. It is **not** an independent
gate; A3 owns that.

## 6. Known baseline-red exceptions (SHA-stamped, do not re-derive)

1. `test_c23_nested_record_emission::test_recursive_ast_union_carries_record_and_child_list` —
   `PEP_RUNTIME_STEP_LIMIT`; verified current at `63b3ea8`, baseline-verified at `ea0bc9a`.
2. `tests/test_c23_collections` — 17 methods / 191 subtests, STEP_LIMIT class; last A/B
   baseline-identical at `ea0bc9a`; label **STALE-BASELINED**, re-run once before a merge
   decision (47 min).
3. `test_textbuf_native::test_arena_demo_builds_and_runs` — Windows CRLF (`b'42\r\n6\r\n'`),
   environmental, not a regression.

## 7. Conditions before Candidate7 is published

1. A2 lands the three-line re-pin on its own branch and pushes (A1 will not edit it).
2. A3 independently gates A1 `727f8af` (one-target adapted `fact_laundering.py`) and A2's
   re-pinned probe, and confirms the tree's checker pin equals the tree's checker.
3. A1 then creates Candidate7 in a **fresh** worktree from Candidate6 by two deliberate merges
   (§3), runs targeted integration tests, and asks A3 for one unmodified frozen Full-v2.
4. Candidate7 may honestly remain FAIL 14/15 (66-node row). No master/CURRENT/manifest change.

## 8. Residual risks carried explicitly

- `pep_chunk_contract.py` is currently *unpinned* in A2's probe. Benign today only because the
  file is byte-identical at `2ad750b` and `727f8af`; the probe would silently mix versions if
  the contract ever changes. Fixing it is A2's one-line fetch (already in the patch above).
- In the merged tree, A2's *unpatched* probe stays green while pinning `2ad750b` — i.e. it
  would describe an older checker than the tree ships (`bundle_sha256 19a56ef…` vs tree
  `80c28ef…`). A green there is not evidence about Candidate7's checker. Measured; do not
  mistake it for a pass.
- Same-revision forged callee facts remain admitted by design (`727f8af` caveat): stamps are
  consistency, not content authenticity. A1 K4 addresses content binding separately.
