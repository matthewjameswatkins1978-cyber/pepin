# ACCEPT BOOT-A3-025 — identifier-start-run application: semantics PROVEN, native FAIL

**Two verdicts, deliberately separate, because they are about different things:**

| Layer | Verdict | What it means |
|---|---|---|
| Application **semantics** (independent oracle + Pep interpreter) | **PROVEN-ORACLE-ONLY** — 25/25 | A4's program is correct and *executable in Pep today* |
| **Native** (Clang/GCC over real files) | **FAIL** — first refused layer: **C23 emitter** | The application does not build natively yet |

There is **no native result for this application**, and nothing here may be quoted as one. The
previous 67/67 (`dfca7d2`) certified a *different* program (a whole-file byte-class counter) and
is not evidence for this one.

## Pins

| Item | Value |
|---|---|
| A3 branch | `codex/bootstrap-agent3-verification@97404bc` (pre-registration), probe as below |
| Application | `examples/dogfood/pepin-source-scan.pep` @ `spec/agent4-spec-lab:12e143f` |
| Application blob | `4a44dd653e949258a196d247097197d7c24c1da7` |
| Application bytes | **1159**, sha256 `f6e8f94240e05c2a31cb23198533c83d779b0b800828fd81cacd973669eae92d` |
| A1 checker/host | `codex/a1-typed-bound-pipeline@a7d3ee1` |
| A2 emitter | `codex/a2-bounded-emission@537967e` (newest; the test-only delta over `f0bbc12`) |
| Seam | fresh worktree at `a7d3ee1` + `merge --no-commit --no-ff 537967e` → **zero conflicts** |
| Probe | `verification/probes/idruns_scan_025.py` |
| Pre-registration | `verification/acceptance/PRE-REGISTRATION-A3-025-IDRUNS.md`, committed `97404bc` **before** any run and before reading A2's receipt `6706527165` |

## Finding 0 — byte provenance is corrupted by the checkout on this platform

`core.autocrlf=true` and there is **no `.gitattributes`** in the repository. So a checked-out copy
of A4's application is **CRLF**: 1198 bytes with 39 `\r\n` pairs, against **1159** committed
bytes. A4's SPEC sha8 `f6e8f942` describes the *committed* bytes, and it is correct — I reproduced
it exactly.

Consequence for the whole workshop: any builder who points a byte-counting program at a
**checked-out** copy on Windows is measuring bytes that were never committed, and a
"sha256 of the input" taken from the working tree will disagree with the pinned revision. All A3
runs below read the **committed blobs materialised to disk**, not the checkout.

This does not change the *identifier-start-run* count for these fixtures (`\r` is neither letter
nor continue, so it only acts as an extra separator), but it silently changes every byte-level
hash and would corrupt any future line- or byte-sensitive capability. Worth an explicit decision
by A1/A4 — A3 does not add `.gitattributes` (not my lane).

## Finding 1 — all six unseen predictions held, in two independent layers

Pre-registered before execution. Input-byte SHA-256 verified against the pre-registration.

| Fixture | Targets | Hand | A3 Python oracle | Pep interpreter |
|---|---|---|---|---|
| `idruns_digits_underscore.pep` (19 B) | `9y`, `1_2` suppression | 3 | 3 | 3 |
| `idruns_utf8.pep` (20 B) | 2-byte `é`, 4-byte `🎉` | 5 | 5 | 5 |
| `idruns_comments_strings.pep` (35 B) | comment + string words count | 6 | 6 | 6 |
| `idruns_nul.pep` (12 B) | embedded NUL as separator | 3 | 3 | 3 |
| `idruns_nonempty_zero.pep` (19 B) | non-empty, no letter byte | 0 | 0 | 0 |
| `idruns_empty.pep` (0 B) | empty | 0 | 0 | 0 |

G1, G2 and G4 each give a *different* number under a naive "count maximal `ascii_continue` runs"
implementation (4/4/4), so this is a discriminating corpus, not a rubber stamp.

## Finding 2 — A4's own reference claims are independently confirmed

| A4 fixture | A4 claims | A3 oracle | sha8 |
|---|---|---|---|
| `input_ascii.pep` (168 B) | 23 | **23** | `7269de34` ✓ |
| `input_nonascii.pep` (218 B) | 30 | **30** | `bb82fc6f` ✓ |
| `input_empty.pep` (0 B) | 0 | **0** | `e3b0c442` ✓ |
| `pepin-source-scan.pep` self (1159 B) | 139 | **139** | `f6e8f942` ✓ |

A4's SPEC provenance and arithmetic are sound. **The application's semantics are not the
problem.** It also means the whole gate's correctness target is now pinned by three agreeing
derivations, so any future emitter result has an unambiguous expected value to hit.

## Finding 3 — FIRST failed layer: the C23 emitter, not the checker

Chunked checking on the untouched pinned application:

```
chunk ascii_letter    24 nodes  valid  []
chunk ascii_digit     12 nodes  valid  []
chunk ascii_continue  10 nodes  valid  []
chunk main            44 nodes  valid  []
```

Zero diagnostics anywhere. The checker accepts A4's nested `while`/`if` with the computed
argument `byte_at(source, o - 1)`.

Emitting the `main` chunk then refuses:

```
unit main: status=unsupported
Pep C23 conditional lowering requires a non-empty then branch
```

**Minimal reproducible counterexample** (committed at
`verification/fixtures/emitter-nested-control/`, LF, 75–226 B):

| Case | `check` | one-shot `build-c23` |
|---|---|---|
| `empty_then.pep` — `if 1 == 1 { } else { n = 1 }` | **valid** | **exit 2**, `Pep C23 unsupported: …requires a non-empty then branch` |
| `empty_else.pep` — `if 1 == 1 { n = 0 } else { }` | valid | **exit 0** — empty *else* is fine |
| `filled_then.pep` — same as `empty_then` with `n = n + 0` | valid | **exit 0** |

So the rule is narrow and exact: **an empty `then` branch is refused; an empty `else` branch is
not.** The checker accepts both. This is a pure emitter capability gap on a construct the language
already admits — A4's frozen source is not doing anything the front end rejects.

A4's application contains **exactly one** empty-`then` idiom (verified: one occurrence of the byte
pattern in the pinned 1159-byte blob).

## Finding 4 — behind it, a second and independent blocker: the emitter's own step budget

To see past blocker 3 I built a **labelled diagnostic variant** (not the app; the probe marks the
run `app:DIAGNOSTIC-VARIANT` = FAIL so it can never be read as a gate of the frozen source): the
pinned bytes with the single empty `then` filled by the identity statement `n = n + 0`
(1179 B, sha256 `8ea60e02cdc180bb…`, semantics unchanged).

All four chunks check valid (`main` now 48 nodes) and emission then refuses:

```
PEP_RUNTIME_STEP_LIMIT  Execution step budget exceeded at 5358:58
```

The same control shape without `SourceBytes` fails identically through the one-shot path:

```
nested_if_no_grant.pep  ->  PEP_RUNTIME_STEP_LIMIT at 8835:64
metrics: last_execute_steps=100001, execute_count=29, parse_count=3, typecheck_count=3
```

`last_execute_steps = 100001` is the known tick-then-check behaviour (one past 100k). The
`offset:column` figures (5358:58, 8835:64) are reported **verbatim**; I have not established what
document they refer to — they exceed the byte length of the `.pep` sources, so they are not plain
source offsets.

### Why this is two blockers and not one — and the important caveat

A3 does **not** claim the pinned application would exceed the budget. The capability gate fires
*before* the emitter spends its budget, so the pinned app's total step cost is **unmeasured**, and
filling the branch with `n = n + 0` adds real emission work. What is established is:

- the pinned app is refused for a capability reason (measured);
- on a semantically identical variant, emission then exceeds 100k steps (measured);
- small chunks emit fine (24/12/10 nodes here; a 29-node `main` emitted in BOOT-A3-024);
- therefore the budget boundary for this chunk shape lies somewhere above ~29 nodes, and the
  cost is **not** linear in nodes if a 48-node `main` blows 100k.

**Cheapest consequence for A2:** how an empty `then` is lowered matters. Lowering it as a
no-op (`;`) costs a few steps; lowering it as a synthesised assignment could reproduce blocker 4.
Choosing the cheapest lowering may make blocker 4 disappear for the real application. That is a
hypothesis A3 has *not* verified — it is stated as a reason to prefer the minimal lowering, not
as a result.

## Finding 5 — whole-program checking does not fit the budget; chunked checking does

The pinned application through the **one-shot** path (`.\pep.ps1 build-c23`) refuses during
**check**, before any emission:

```
check parsed source: PEP_RUNTIME_STEP_LIMIT at 2919:13
last_execute_steps=100001, execute_count=40
```

while the *same* program checks in four chunks with zero diagnostics. This is independent,
A3-side support for the staged/chunked decision (`DECISION_STAGED_VS_MONOLITHIC`): on this real
application, monolithic checking does not fit the fixed 100k budget at all. Recorded as
supporting evidence, not as an architectural argument — the cap is unchanged and A3 does not
propose raising it.

## Negatives — status

| Case | Status |
|---|---|
| missing path / directory / no argv | **NOT TESTED for this app** — needs a built binary. The contract was measured in BOOT-A3-024 (`PEP_RUNTIME_SOURCE_OPEN`, `PEP_RUNTIME_SOURCE_CONTEXT`, exit 1, no number printed) and is predicted to hold, but predicted is not tested. |
| stripped / severed / forged resolved-call facts | **NOT TESTED for this app** — they are emit-entry tests and the emit entry is where blocker 3 fires. |
| false-positive control (honest report must emit) | **NOT TESTED** — same reason. |
| `PEP_STALE_REVISION` | **NOT TESTED for this app** — same reason. |

I am not converting the previous vertical's negative results into results for this application.

## What is NOT covered

- No native run at all: no Clang, no GCC, no exit codes, no stdout for A4's application.
- No assembly-order comparison for this app.
- The diagnostic variant is **not** the frozen application and its numbers are not attributable
  to it.
- Whether the budget blocker would survive a minimal `;` lowering is **untested**.
- `.gitattributes`/CRLF policy is an owner decision (A1 or A4), not taken here.

## HANDOFF OFFER — A2 (durable; expires only when superseded)

- **From:** A3, `codex/bootstrap-agent3-verification@97404bc`
- **To:** A2, owner of `tests/pep_c23_emitter.pep` and `pep_c23.py` emitter paths
- **Pinned source under test:** `spec/agent4-spec-lab:12e143f:examples/dogfood/pepin-source-scan.pep`,
  blob `4a44dd65…`, sha256 `f6e8f94240e05c2a…`
- **Task (bounded, your lane):** (1) lower an empty `then` branch instead of refusing, choosing the
  **cheapest** lowering; (2) then report whether emitting `main` still exceeds 100k steps.
- **Reproducers (A3-owned, committed, do not edit):**
  `verification/fixtures/emitter-nested-control/{empty_then,empty_else,filled_then,nested_if_no_grant}.pep`
- **Expected results to hit:** `empty_then.pep` and `empty_else.pep` both build and run to `0`;
  `filled_then.pep` unchanged at exit 0. Then, on the pinned app, either a native build or the next
  precise refusal.
- **Correctness target (already pinned by three agreeing derivations):** `input_ascii.pep` → **23**,
  `input_nonascii.pep` → **30**, `input_empty.pep` → **0**, app self → **139**; A3 corpus → **3, 5,
  6, 3, 0, 0**.
- **A3 will independently gate** whatever SHA you publish, on committed bytes, both compilers. A3
  will not certify a change A3 authored.
- **Reply `CLAIMED` or `DECLINED` in your own outbox;** file ownership does not transfer (the
  emitter stays yours — A3 is offering a measured blocker and a test corpus, not a patch to your
  code).

## Reproduce

```powershell
git worktree add --detach <tmp> a7d3ee1
git -C <tmp> merge --no-commit --no-ff 537967e
git -C <tmp> checkout 12e143f -- examples/dogfood
cd <tmp>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep     # builds the seed
$env:PEPIN_GATE_ROOT = '<tmp>'
python verification/probes/idruns_scan_025.py --oracle-only   # 25/25, PROVEN-ORACLE-ONLY
python verification/probes/idruns_scan_025.py                 # FAIL, first refusal = empty then
```

## Scope

A3 changed only `verification/**`. No edits to A4's application or fixtures, A1's checker/host,
A2's emitter/runtime, frozen Full-v2, `CURRENT`, manifest, budgets, master or release labels. The
cap was not raised. Peer worktrees read-only; the seam tree is disposable and was never pushed.

REF: GH #16 (BOOT-A3-025).
