# K-A3-3: A2 `123d8b3` prototypes verified — and A1 `727f8af` compatibility is one dict literal away

**Date:** 2026-11-05 · **Mission:** LUCY-20261105-001 / Campaign K, A3 cards K3 + K7 · **Evidence label:** `TESTED`
**PIN: A3 | `codex/bootstrap-agent3-verification` | tested A2 `123d8b3` in a fresh clone; A1 pins `2ad750b` (A2's declared pin) and `727f8af`**
**First next action:** report the two field additions to A2 (Signal block below) so its K1 re-pin lands; then K5.

## Part 1 — A2's cold-clone repair is NOT in `123d8b3` (K7)

Fresh `git clone --single-branch` of `codex/a2-bounded-emission` → HEAD `123d8b3`, clean, **no `_build`**, root `*.py` = `pep_c23.py` only.

```
tests/probe_seam_chunked.py:278
  index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
ModuleNotFoundError: No module named 'pep_chunk_contract'
```

`prepare()` at `123d8b3` still extracts the same five files (`examples/pep_lexer.pep`, `examples/pep_parser.pep`, `tests/pep_checker_a13.pep`, `tests/chunk_helper.py`, `pep_ocaml.ml`) and never `pep_chunk_contract.py`. This is the **second** independent confirmation (first at `58fc9bf` in H-V1) — the defect persists at the newer SHA. A2's card K2 has not been done.

**Labelled workaround used for the rest of this receipt:** extracted `2ad750b:pep_chunk_contract.py` (33757 B, sha256 `1a53a70fd3bdfec0…`) into the clone root. Labelled, not clean reproducibility.

## Part 2 — prototypes claim verified at A2's own pin (K3, first half)

Probe run unmodified against A1 `2ad750b` (A2's declared `A1_SHA`), under the labelled workaround: **exit 0**.

| evidence | observed |
|---|---|
| prototypes per chunk | `emit-prototypes-make_token/add_one/main` all `emitted`, `prototypes_bytes=267` |
| normal-order assembly | `assembled_c_bytes=5875`, strict Clang **42**, GCC **42** |
| **reverse-order assembly** | `reverse_bytes=6142`, strict Clang **42**, GCC **42** |
| seed oracle | `42` |
| 11 negatives | all as specified, incl. `neg-stale-revision` → `PEP_STALE_REVISION` at transport |
| **control that makes prototypes load-bearing** | `neg-unit-order-clang`/`-gcc` still `exit=1 undeclared_callee=True` — the *no-prototypes* reverse path still fails |

That last row is the discriminating control: reverse order only works **because** of the prototypes block, so the claim is not an artefact of something else changing.

## Part 3 — compatibility with A1 `727f8af`: one crash, one-line fix, then fully green

A2's probe declares `A1_SHA = 2ad750b`. Re-pointed at `727f8af` in my disposable clone and run unmodified:

- **Everything passed** up to the last negative: all chunk checks, all emissions, normal + reverse assembly, Clang + GCC `42`, seed `42`, `neg-stale-revision`, and 10 of 11 negatives.
- **Then it crashed**: `KeyError: 'document'` in `checked_fn_value`, raised from A2's own hand-built `duplicate_fact` dict, which supplies `name/arity/rtype/rshape/ptypes/semid/synid/node/start/end` but not the two new stamp fields.

So the A2↔A1 incompatibility is **not semantic**: it is one dict literal in one negative test. Verified fix (2 added fields, nothing else):

```python
duplicate_fact = {..., "node": "0", "start": "0", "end": "0",
                  "document": sem["document"], "revision": sem["revision"]}
```

With that applied, the same probe at A1 `727f8af` finishes **exit 0**, and `neg-dup-external-name` still reports `invalid codes=['PEP_DUPLICATE_FUNCTION']` — i.e. the negative still exercises the duplicate rule rather than being satisfied by a missing-stamp rejection. That distinction matters: a stamp-only failure would have looked like a pass while testing nothing.

## What this de-risks for Candidate7

- A2's prototypes/reverse-order/native-42 claim is **independently verified**, at its own pin and again at A1 `727f8af` after the two-field fix.
- The blocker between "two ready SHAs" and "one gated candidate" is therefore **not** an interface redesign: it is (a) A2 re-pinning `A1_SHA` to `727f8af` and adding two fields, (b) A2 fixing `prepare()` for cold clones (`pep_chunk_contract.py`), and (c) A1 composing. Nothing in this slice gives me grounds to say the two branches cannot be combined legitimately — the overlay is coherent.

## Reproduce

```powershell
git clone --branch codex/a2-bounded-emission --single-branch <repo> D:\Projects\wt-a3-k3-cold
python -X utf8 tests\probe_seam_chunked.py            # ModuleNotFoundError at line 278
git show 2ad750b:pep_chunk_contract.py > pep_chunk_contract.py   # LABELLED workaround
python -X utf8 tests\probe_seam_chunked.py            # exit 0 (A1 2ad750b pin)
# re-pin experiment: copy probe, set A1_SHA=727f8af, add the two fields to duplicate_fact
python -X utf8 tests\probe_seam_chunked_repin727.py   # exit 0 after the fix
```

Toolchain: Clang 23.1.4, GCC 16.2.0, OCaml 5.5.2 (`PEPIN_OPAM_ROOT=D:\opam-roots\pepin\`). Clone is disposable and outside the repo; no peer file edited in any peer worktree.

## Limits / NOT VERIFIED

- The `727f8af` re-pin result is **my** edited copy of A2's probe, not A2's own file; A2 should confirm on their branch. I did not push to A2's branch.
- A2's cold-clone failure is reported, not fixed — that is A2-owned (`tests/probe_seam_chunked.py`).
- Reverse-order verification covers one fixture with two external callees; it does not prove arbitrary unit permutations are safe.

## Signal v0.1 handoff to A2 (consequential)

```text
PIN: A3 | codex/bootstrap-agent3-verification | e77c788 (+this commit) | pushed+remote-verified | clean
RESULT: your 123d8b3 prototypes claim VERIFIED (reverse-order 42 on Clang+GCC, seed 42, 11 negatives, no-prototype control still fails). Re-pin to A1 727f8af needs exactly 2 fields on duplicate_fact; cold clone still dies at line 278. TESTED.
REPRO: clone codex/a2-bounded-emission; git show 2ad750b:pep_chunk_contract.py > pep_chunk_contract.py; python tests\probe_seam_chunked.py
FALSIFIER: if prepare() already extracts pep_chunk_contract.py on a later SHA, Part 1 is stale — check before fixing.
NEEDS: A2 — add "document"/"revision" to duplicate_fact, set A1_SHA=727f8af, extract pep_chunk_contract.py in prepare(); then publish the re-pin SHA.
```
