# H-V1: cold-start reproducibility — one real dependency gap, then a green chain

**Date:** 2026-11-04 · **Mission:** LUCY-20261104-015 / Campaign H, Workstream V1 · **Evidence label:** `TESTED`
**PIN:** A3 `codex/bootstrap-agent3-verification@ec2762b` (+this commit) · clean · tested A2 `58fc9bf` against A1 `2ad750b`
**First next action:** A2 adds the missing extraction line (five-line #16 handoff below); A3 then re-runs the same cold clone unmodified.

## Method: a genuine cold start, not a warm worktree

`git clone --branch codex/a2-bounded-emission --single-branch` → `D:\Projects\wt-a3-h1-cold`.
HEAD `58fc9bf8918d13df52cd1b5efec80beccfe0e822`, working tree clean, **no `_build/`**, root `*.py` = `pep_c23.py` only.
Toolchain: Clang `23.1.4` (x86_64-pc-windows-msvc), GCC `16.2.0` (MinGW-Builds x86_64-posix-seh-rev1), OCaml `5.5.2` / opam switch `pepin-5.5.2`, Python `3.15.1`, `PEPIN_OPAM_ROOT=D:\opam-roots\pepin\`.

## Result 1 — cold start FAILS on a declared-file gap (not on compiler semantics)

```
tests/probe_seam_chunked.py:278
  index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
ModuleNotFoundError: No module named 'pep_chunk_contract'
```

Everything before it succeeded from a cold tree: `prepare()` fetched the A1 pin, extracted 5 files, and **rebuilt the seed** from pinned `pep_ocaml.ml`; `bundle-open OK`; `parse OK nodes=68 bytes=575`; `sig-id-state raw_semids=[9000, 9001, 9002] collision=False renumber=removed`.

**Exact dependency, owner and identity of the missing input:**

| item | value |
|---|---|
| module | `pep_chunk_contract.py` |
| repo path | **repository ROOT** (not `tests/`) |
| exists at | A1 `2ad750b:pep_chunk_contract.py` — blob `0751391f3a13a5637c5cafa2bdc2753d8a1b3356`, 34472 B, sha256 `8247664777893d211fac0eacf343c5a99e320aeccc061825ceac4cc316085dfe` |
| absent at | A2 `58fc9bf` (whole tree), campaign main `57fe424` |
| imported | `__import__("pep_chunk_contract")` at probe line 278 |
| `prepare()` extraction list | `examples/pep_lexer.pep`, `examples/pep_parser.pep`, `tests/pep_checker_a13.pep`, `tests/chunk_helper.py`, `pep_ocaml.ml` — **five files, none of them this one** |
| transitive imports of the missing module | `copy`, `json`, `re` only — no further hidden inputs |
| owner of the fix | **A2** (`tests/probe_seam_chunked.py` `prepare()`); A3 did not modify it |

**LABELLED MANUAL WORKAROUND:** A3 extracted that one file from the A1 pin into the clone root. This is a workaround, not clean reproducibility, and the failure above stands as the finding.

## Result 2 — with the workaround, the whole chain reproduces (exit 0)

| stage | observed |
|---|---|
| bundle sha256 | `a79b1c2cacfb5133148792ddf18eda4c7351948eb8829f7c4d6b52ed81ecf15a` |
| chunk checks | declaration 18 / make_token 55 / add_one 8 / main 5 nodes, all `valid` |
| emissions | header + 3 function units + epilogue all `emitted` |
| assembled C | `seam_chunked.c` **5875 B**, sha256 `1b7fe170d80ffc89…` |
| Clang strict (`-std=c23 -Wall -Wextra -Wpedantic -Werror -O2`) | `42` |
| GCC strict (same flags) | `42` |
| seed oracle | `42` (entry-point difference: seed runs top-level statements, C runs `main`) |
| **11 negatives** | no-call-fact, ambiguous-call, missing-target, ambiguous-target, arity-mismatch, foreign-result, stale-revision (`PEP_STALE_REVISION` at transport), unit-index, dup-external-name (`PEP_DUPLICATE_FUNCTION`), unit-order-clang, unit-order-gcc — all as specified |

Pinned-input hashes observed: `a1_lexer.pep` 18931 B `8352a6a2…`, `a1_parser.pep` 94274 B `29a2b00d…`, `a1_checker.pep` 188095 B `3080d38c…`, `a1_chunk_helper.py` 13815 B `ef4f8bf8…`, `pep_ocaml.ml` 146163 B `137dcb37…`.

## Result 3 — provenance perturbations, layer-attributed

| # | perturbation | layer | observation |
|---|---|---|---|
| P2a | seed `pep.exe` **substituted** by a stub (`exit 7`) while `seed_source_pin.txt` still said `2ad750b` | **process/session transport** | guard did **not** notice; failure surfaced as `BrokenPipeError` at the first `open`. Fail-closed, never a silent pass — but the marker is *consistency, not binary authenticity* |
| P2b | stub in place + **wrong** marker | guard | `prepare()` detected the mismatch, deleted the exe, rebuilt from the pinned source, rewrote the marker → chain green again (exit 0), new exe 4882972 B |
| P2c | seed source from older A1 `9ad7d95` vs pinned `2ad750b` | none | **`pep_ocaml.ml` is byte-identical (146163 B, same sha256)** — no discrimination is possible; A1's checker work lives entirely in the Pep-written `tests/pep_checker_a13.pep`, so seed rebuilds across that range are content-free |
| P3 | malformed/foreign `document` + `revision` in `semanticTarget` (new probe `p3_document_matrix.py`) | **host transport** | 9-cell matrix, all malformed cells refuse: `PEP_DOCUMENT_NOT_FOUND` (empty, foreign-same-length), `PEP_SESSION_FIELD_TYPE` (`null` doc; `0` / `-1` / `2^62` revision), `PEP_REVISION_NOT_FOUND` (foreign well-formed `sha256:0…`, truncated). Control cell invokes normally |
| P3b | `open` request carrying extra `document`/`foreign-document` field | none | silently ignored, `status=valid` — the host assigns its own `doc-1` + content-hash revision. An observation, not an assertion |

## Side finding for V2 (measured, not inferred)

Opening A1's checker **file alone** as a document is refused by the checker: `PEP_UNKNOWN_TYPE: Unknown type 'FlatAstNode'`. The checker source is only openable inside the lexer+parser+checker bundle. Any attempt to run a single compiler function "as the original source" hits this first — recorded here so V2 does not rediscover it as a false blocker.

## Five-line handoff to A2 (#16)

1. `tests/probe_seam_chunked.py` `prepare()` does not extract `pep_chunk_contract.py`, which line 278 imports.
2. The file lives at the **repository root** of the A1 pin (`2ad750b:pep_chunk_contract.py`, 34472 B, sha256 `8247664777893d21…`), not under `tests/`.
3. A fresh clone of `codex/a2-bounded-emission@58fc9bf` therefore dies with `ModuleNotFoundError` before any chunk is checked.
4. Suggested one-line fix: add `("pep_chunk_contract.py", "pep_chunk_contract.py")` to the `prepare()` extraction list (BUILD root lands on `sys.path` via `ROOT`).
5. Everything else reproduced cold: 42 on Clang+GCC, 11 negatives, 5875 B C — no other hidden inputs found.

## Admitted unknowns / limits

- Workaround copy was placed in the clone root; that clone is disposable and outside the repo.
- P2a cannot distinguish "stub" from "genuinely different compiler build" — both are label-blind. That is the point of the finding, not a measurement gap.
- No A1/A2/spec/frozen-gate/budget/master/CURRENT/manifest change by A3; only `verification/**` on the A3 branch.

## Reproduce

```powershell
git clone --branch codex/a2-bounded-emission --single-branch https://github.com/matthewjameswatkins1978-cyber/pepin.git D:\Projects\wt-a3-h1-cold
$env:PEPIN_OPAM_ROOT='D:\opam-roots\pepin\'
python -X utf8 tests\probe_seam_chunked.py            # -> ModuleNotFoundError at line 278
git show 2ad750b:pep_chunk_contract.py > pep_chunk_contract.py   # LABELLED workaround
python -X utf8 tests\probe_seam_chunked.py            # -> exit 0, 42 on both compilers, 11 negatives
python -X utf8 <a3-branch>\verification\probes\p3_document_matrix.py D:\Projects\wt-a3-h1-cold
```
