# ACCEPT BOOT-A3-024 — independent dogfood gate on the source-scan vertical

**Verdict: PROVEN** — 67/67 checks pass, exit 0, two consecutive runs byte-identical.

This is an **independent A3 gate**, not a builder result. It answers only one question: does
the pinned source-scan vertical, run cold over a corpus A3 chose *before* measuring, produce
the values A3 predicted, under both strict compilers, against an independent reference, with
the malformed-fact cases still refusing?

**Scope warning, read first.** What is proven is a **byte-class count**
(`[A-Za-z0-9_]` bytes over a whole file), not a lexer and not tokenisation. A4's
`examples/dogfood/` application **does not exist yet** at `spec/agent4-spec-lab@712e549`, so
this gate covers the four-function vertical the packet handed over as builder-tested — nothing
of A4's application has been seen or judged.

## Pins (all verified by `git cat-file -t` before use)

| Role | Ref | Resolved |
|---|---|---|
| A3 own branch | `codex/bootstrap-agent3-verification` | `a9f4314` (pre-registration) |
| A1 checker/host (under test) | `codex/a1-typed-bound-pipeline` | `a7d3ee13b7a118132a13a4141ec485ec5382a8ad` |
| A2 emitter (under test) | `codex/a2-bounded-emission` | `f0bbc12` |
| Merge base of the two | — | `83351bb` |
| Merged working tree | `git write-tree` | `720b30483837eb741eb67c4c4f90562e655d7de5` |
| Checker source | `tests/pep_checker_a13.pep` | blob `2d714a0e9870` |
| Emitter source (merged) | `tests/pep_c23_emitter.pep` | sha256 `0bf0e1d4d016461e…` |
| Host bridge | `pep_c23.py` | blob `b2b71ab5507d` (A1's copy — A2 does not touch it) |
| Seed used for the interpreter derivation | `_build/a1_seed/pep.exe` | sha256 `705ce468ac91ce4c…` |
| Probe | `verification/probes/dogfood_scan_024.py` | sha256 `dd36a7784ef8b888…` |
| Pre-registration | `verification/acceptance/PRE-REGISTRATION-A3-024-DOGFOOD-SCAN.md` | committed `a9f4314`, **before** any run |

### The seam had to be rebuilt cold, deliberately

`git diff --name-status a7d3ee1 f0bbc12` shows A2's branch **deletes** A1's chunk tooling
(`pep_chunk_contract.py`, `tests/chunk_helper.py`, `pep_chunk_units.py`). A2's branch is not a
superset of A1's, so "four functions at A1 a7d3ee1" is a *merged* seam, not a branch anyone can
check out. Reconstruction: fresh worktree at `a7d3ee1`, then
`git merge --no-commit --no-ff f0bbc12` → **clean, zero conflicts**, 5 files
(`docs/outbox/AGENT2_OUTBOX.md`, `tests/pep_c23_emitter.pep`, `tests/probe_function_closure.py`,
`tests/probe_grant_host_merged.py`, `tests/probe_grant_lexer_chunked.py`). That matches A1's
published integration matrix ("overlap is zero"; `pep_c23.py` is A1-owned).

**Harness control first.** A2's own `tests/probe_grant_lexer_chunked.py`, unmodified, on the
merged tree: exit 0, four chunks `valid`, `17` from both compilers and the seed, three
negatives held. So the seam was green *before* my probe existed; the numbers below are my
corpus, not a re-print of A2's.

## Pre-registered corpus and outcome

Fixtures A3-authored under `verification/fixtures/dogfood-scan/`, exact bytes hashed. Predictions
were hand-tallied from the hex dumps in the pre-registration commit; nothing was filled in after
a run.

| File | Bytes | SHA-256 (16) | Kind | Hand | Ref | Seed | Clang d/p | GCC d/p |
|---|---|---|---|---|---|---|---|---|
| `scan_ascii.pep` | 49 | `1cac438e0867f773` | ordinary ASCII Pep source | **24** | 24 | 24 | 24/24 | 24/24 |
| `scan_nonascii.pep` | 58 | `325aa1b93655aae2` | non-ASCII UTF-8 in a string (`é`=`c3 a9`, `→`=`e2 86 92`) | **26** | 26 | 26 | 26/26 | 26/26 |
| `scan_empty.pep` | 0 | `e3b0c44298fc1c14` | empty file | **0** | 0 | 0 | 0/0 | 0/0 |
| `scan_nul.pep` | 31 | `b2ab07189603d6f6` | embedded NUL (`00`) at offset 18 | **16** | 16 | 16 | 16/16 | 16/16 |
| `scan_hello.pep` | 19 | `89667a79729f0f17` | byte-identical copy of `examples/hello.pep` @ a7d3ee1 | **11** | 11 | 11 | 11/11 | 11/11 |
| `scan_punct.pep` | 18 | `cff9abb88eb9488a` | non-empty, zero identifier bytes | **0** | 0 | 0 | 0/0 | 0/0 |

`d` = document order (callees then callers), `p` = prototypes-first order. **All 24 hand
predictions held: 24 values across 6 files, 3 derivations, 2 compilers, 2 assembly orders.**

Empty (F3) and non-empty-zero (F6) are separate rows on purpose: together they rule out the
obvious failure where a scanner answers `0` for *anything* it cannot scan. F1/F2/F5 are the
three genuinely different real files the first gate asks for.

## Real repository files (reference-derived, disclosed as such)

These were **not** pre-registered by hand; their expected value is the independent Python
classifier. Labelled so nobody mistakes them for predictions.

| File | SHA-256 (16) | Reference | Clang d/p | GCC d/p |
|---|---|---|---|---|
| `examples/hello.pep` | `07dd5c75126e46bc` | 11 | 11/11 | 11/11 |
| `examples/point_sum.pep` | `1ff3f3818f19bfa5` | 91 | 91/91 | 91/91 |
| `examples/pep_lexer.pep` | `729e01acdbbb538e` | **10626** | 10626/10626 | 10626/10626 |

`examples/pep_lexer.pep` is a genuine multi-KB repository source; all four builds agree with the
reference on it.

## Negatives — malformed, incomplete and unbound input

| Case | Expected | Measured |
|---|---|---|
| main chunk report, resolved call facts stripped | refuse at emit | `Pep C23 cross-chunk call has no resolved call fact` |
| call fact `calleeId` severed to 999999 | refuse at emit | `Pep C23 cross-chunk call target is missing from the checked functions` |
| checked-callee arity forged to 2 | refuse at emit | `Pep C23 cross-chunk call argument count disagrees with the checked arity` |
| honest report re-invoked on a second **valid** target | refuse | `PEP_STALE_REVISION` |
| argv path that does not exist | no number printed | exit 1, stdout empty, stderr `PEP_RUNTIME_SOURCE_OPEN` |
| argv path is a directory | no number printed | exit 1, stdout empty, stderr `PEP_RUNTIME_SOURCE_OPEN` |
| no argv path | no number printed | exit 1, stdout empty, stderr `PEP_RUNTIME_SOURCE_CONTEXT` |
| one binary, six files | six distinct answers | `24, 26, 0, 16, 11, 0` |

The metamorphic row is what makes the corpus rows mean anything: a build that printed a
constant, or ignored argv, fails there while individual rows might still look plausible.

## Measured usable scale — my own speculation was falsified

I expected the 100k step budget to cap the native path at a few KB. **Measured: wrong.** An
all-identifier file of **1 048 576 bytes** (1 MiB) scans completely and correctly, no refusal;
the ladder (1 KiB → 1 MiB) never refused.

Mechanism, read from the artefact rather than assumed: the emitted translation unit contains
**no step or budget instrument** — the only `limit` in `_build/dogfood_scan_024_docorder.c` is a
local variable inside a `text_contains` helper. So the 100k step limit is a *session/interpreter*
guard, not a property of the emitted native binary. Consequence for the workshop: native
scanning is not step-capped, but the equivalent program cannot even be expressed under
`pep.ps1 run` because `run` refuses ungranted `source_bytes()`. The interpreter derivation here
therefore supplies bytes **by value**, and that authority boundary is labelled, not hidden.

## Errors of mine, found during this slice and recorded rather than quietly fixed

1. **Mis-transcribed comprehension** from A2's probe added a stray `)` → `SyntaxError` at
   line 231. Fixed by copying the original lines from the source instead of retyping them.
2. **Corpus resolved under the tree under test** → `FileNotFoundError` for
   `…/wt-a3-dogfood-024/verification/fixtures/...`. Fixed by anchoring the corpus to the probe's
   own repository (`PROBE_ROOT`) and leaving `ROOT` for the tree under test.
3. **My interpreter derivation could not express the empty file**: `let bytes = []` →
   `PEP_EMPTY_LIST_NEEDS_TYPE: An empty list needs an expected List element type`. This was a
   *derivation* failure, not an app failure. Fixed by passing the list through a typed
   parameter (`fn count_from(bytes: List[Int]) -> Int`), which supplies the expected element
   type. Both the failure and the fix are in the run history; the expected value never changed.
4. **My first stale-revision test refused for the wrong reason**: it used `bytes: [65]`, which is
   not valid Pep source, so the session answered `PEP_SEMANTIC_ROOT_UNAVAILABLE` ("Entry
   functions cannot be resolved for invalid target source") *before* reaching the stamp gate. My
   check demanded `PEP_STALE_REVISION` and correctly failed. Fixed by using valid Pep source as
   the second target; the refusal then landed on `PEP_STALE_REVISION`. Worth recording as layer
   information: target validity is checked before report binding.

No failing check was deleted, weakened or re-worded to pass. The only expectation that changed
was the *oracle shape* in 3, which is my own harness.

## Unsupported / not covered — stated plainly

- **No A4 application exists to test.** `examples/dogfood/` is absent at `712e549`. Everything
  here is about the pre-existing four-function vertical.
- **One `main()` shape only.** A different entry (e.g. returning a record, or taking a second
  argument) is untested by this gate.
- **Not a lexer.** No token kinds, no comments/strings handling, no identifier-start runs. The
  number is a byte-class count and must not be reported as tokenisation.
- **A2's branch does not stand alone.** `f0bbc12` alone has no `tests/chunk_helper.py` and no
  chunk contract, so it cannot reproduce this; the gate is about the merged seam.
- **Six fixtures, three derivation paths.** This is not a fuzz campaign and does not establish
  that *no* input diverges.
- **No sanitizer run, no multi-file/incremental behaviour, no CLI beyond argv + grant.**
- Candidate7 was **not** touched or re-judged; nothing here changes its status.

## Reproduce

```powershell
git worktree add --detach <tmp> a7d3ee13b7a118132a13a4141ec485ec5382a8ad
git -C <tmp> merge --no-commit --no-ff f0bbc12
cd <tmp>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep     # builds _build/ocaml/pep.exe
$env:PEPIN_GATE_ROOT = '<tmp>'
python verification/probes/dogfood_scan_024.py            # from the A3 worktree
```

Expected: `67 checks, 67 passed` / `dogfood source-scan gate: PROVEN`, exit 0, in ~4 s.
Two consecutive runs produce byte-identical `--json` output
(`6b56a2c0ff16db3e68865479d9d2e667fb97df7d5bf5f6e0da23267c7d0062bc`).

## What this does and does not authorise

It supports one claim: the pinned vertical reads a real file through the host grant, classifies
its bytes with the compiler's own `ascii_*` functions, and does so identically under the seed
interpreter, an independent Python reference, and strict Clang and GCC — with malformed,
incomplete and unbound facts still refused at the emit entry.

It does **not** accept Candidate7, does not promote A8, does not change `CURRENT`, the manifest,
budgets, permissions or `master`, and says nothing about A4's unmade application.

REF: GH #16 (BOOT-A3-024 receipt). Scope: `verification/**` only. Peer worktrees read-only;
the merged tree existed only as a disposable scratch worktree and was never pushed.
