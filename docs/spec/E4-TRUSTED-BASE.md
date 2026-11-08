# E4 — Smallest Honest Trusted Base for Bootstrap Compiler A

**Programme:** PEP-A4-RESEARCH-E-20261104, Phase II slice 1 (Campaign F F3).
Source-read at seed `57fe424` unless noted. Labels: ESTABLISHED / INFERRED /
UNKNOWN. No implementation, no new proof platform, no recommendations that
create work for A1/A2.

## 1. Trust-boundary map (ESTABLISHED by source-read)

| # | Layer | Trusted for | Verified how (today) | Honest gap |
|---|---|---|---|---|
| T1 | OCaml stage-0 (`pep_ocaml.ml`, 1930 lines) | Lexing, parsing, checking, interpreting, session host, JSON | `pep.ps1` sha256 hash-guarded rebuild; opam switch `pepin-5.5.2` | Switch contents unpinned (no lockfile read); interpreter is the single largest trusted semantic block |
| T2 | Session transport | Moving sources/facts between host and staged code | Schema v3, 65536 open cap, typed caps (depth 16, 10k nodes, 1 MiB), step/depth budgets | `trustedLocal:true, sandboxed:false` — host compromise = total compromise (stated, not mitigated) |
| T3 | Staged bundle (`pep_c23.py` `emit()`) | The 4-source compiler bundle opens `valid` before tool registration | `require(opened,"outcome","ok")` + `"status","valid"` gate | Bundle = 4 files concatenated — no per-file identity; a swapped file passes if the bundle still checks |
| T4 | C toolchain (`clang`, PATH/scoop/`--compiler`) | Translating emitted C to behavior | `-std=c23 -Wall -Wextra -Wpedantic -Werror -O2` (strict, warnings-as-errors) | No vendor/version/hash pin; `run-c23` returns exe code directly — Pep trap failures (`PEP_RUNTIME_*`) live in stderr text, not exit codes |
| T5 | OS / filesystem | Source bytes in, artifacts out | sha256[:12] in default exe name (traceability) | Traceability, not verification; no receipt binds compiler version to artifact |
| T6 | Staged emitter prelude | Checked arithmetic, call-depth guard | C helpers mirror seed limits (overflow/div0/depth-512) | Prelude is emitted text, not a reviewed artifact — drift between prelude and seed limits would be silent |

Irreducibly native: T1-interpreter, T4-codegen, T5-bytes, UTF-8 tables,
integer arithmetic. Suspiciously hidden semantics: NONE FOUND in T3/T4 path —
the staged emitter does its own lowering (E2-B3) and Clang only compiles;
but T6 prelude and T3 bundling are the two places staged logic could hide
host-trusted behavior. (INFERRED: no second semantic engine observed.)

## 2. One boundary proved/falsified with existing source

**Claim tested:** "the C toolchain is a legitimate external tool, not hidden
semantic compilation." **PROVED (legitimate):** `pep_c23.py` lines 186–260 —
the staged emitter produces full C text, Clang receives `-std=c23 ... -O2`
with no Pep-aware plugins, and refusal happens pre-emission in Pep
(`pep_c23_unsupported`). Clang cannot accept a program the emitter refused.
**QUALIFIED 2026-11-04 (independent review + A3 cold-start receipt
ACCEPT-H-V1 @ `1de76b62`):** "can only miscompile" UNDERSTATES the trusted
surface — the runtime, linker, ABI, execution environment, and the C
standard library the prelude assumes are all trusted alongside the compiler
proper, and none appear in any receipt. Further, a verifier-side version
string (e.g. A3's "Clang 23.1.4") attests the VERIFIER's run, not the
producer's artifact: A3's cold start exposed a missing module dependency
(`pep_chunk_contract.py` absent from A2's tree) AND a rebuilt-from-pinned-seed
executable whose identity no marker authenticated. A version line in the
producer's own receipt is therefore necessary but NOT sufficient — input,
tool, and output identities must be bound together (see revised §4).

## 3. Three runnable negative test obligations (for a future lane, not A4)

- **N-T4-1:** run `run-c23` twice with two different Clang versions/paths on
  one fixed source; receipts MUST differ in recorded compiler identity
  (currently they cannot — obligation fails today, which is the point).
- **N-T3-1:** swap one bundled staged source for a same-status variant and
  confirm the `outcome:ok + status:valid` bundle gate still passes (documents
  the per-file-identity gap; expected pass = gap confirmed, not a bug).
- **N-T4-2:** feed a `PEP_RUNTIME_OVERFLOW` program through `run-c23` and
  assert the harness distinguishes trap-stderr from harness-failure by TEXT,
  not by exit code alone (locks the stderr-as-oracle contract).

## 4. Narrow recommendation (REVISED 2026-11-04 — the "no added assurance"
conclusion is withdrawn)

The G-A4-7 verdict is revised: verifier-side recording does NOT cover the
producer gap (cold-start evidence). The revised trial: bind
{input sha256, tool path+version+sha256, output sha256} in the PRODUCER's
own receipt (one line per identity, no new infrastructure), and measure for
one campaign whether any receipt EVER diverges across reruns. Cost: one
receipt line per build; benefit: the cold-start class (missing dep,
unauthenticated rebuild) becomes receipt-visible instead of
investigation-visible. If after one campaign no divergence is ever recorded,
downgrade to verifier-only recording with the evidence cited. Do NOT attempt
hermetic-toolchain pinning (unchanged: cost exceeds the risk).

## 5. Status labels

MAP (not a build plan): 6-layer table, 1 boundary adjudicated (qualified —
runtime/linker/ABI/env trusted too), 3 obligations specified for a future
lane. Correction pass 2026-11-04 applied (verifier≠producer provenance;
cold-start evidence; revised trial with measure-and-downgrade rule).
