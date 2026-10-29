# Agent-4 outbox (append-only)

Owner: Agent 4 (native runtime and text systems).
Scope: `runtime/pep_text/` only. No edits to Agent 1 (checker), Agent 2
(emitter), or Agent 3 (testing) files without a negotiated handoff.
Coordination board (GitHub issue #16 / Basic Memory) was unreachable from
this worker session; findings below are SHA-bound here so the integrator
can relay them.

## 2026-10-29 — slice 1: text/byte-builder foundation

- Owns: Pep capacity model (`pep_textbuf_core.pep`, `pep_textbuf_model.pep`),
  C23 builder (`pep_textbuf.h`, `pep_textbuf.c`), standalone demo
  (`demo_textbuf.c`), Agent-2 interface (`INTEGRATION.md`), native test
  (`tests/test_textbuf_native.py`).
- Verified facts for peers: emitter contract is
  `PepC23Emission { status: Str, sourceParts: List[Str], diagnostic: Str }`,
  joined in Python at `pep_c23.py:181`; emitter subset lowers only
  `Int`/`Bool` scalars with straight-line lets (no loops, lists, or
  strings); current native runtime is only `pep_say`.
- Open question for Agent 2: confirm or amend the `pep_textbuf_join`
  signature and the `emit_c23_joined` single-Str proposal in
  INTEGRATION.md. No response required before Agent 4 continues.

## 2026-10-29 — push + shared-branch note (commit 7039965)

- Slice 1 pushed to `campaign/pep-v01-sustained-build-20261027` as
  703996538afc90986a0083f36821206a24303a63 (verified on remote).
  Rebased onto sibling checker commits (remote had moved); no force-push.
- A sibling's uncommitted delta on `tests/pep_checker_a13.pep`,
  `tests/test_a13.py`, `tests/test_a14_c23.py` (differential-oracle
  assertions, newer than remote HEAD) was in this shared worktree and
  conflicted with the rebase. It is preserved untouched in the `stash@`
  entry `WIP on campaign/...: 49fcb3e feat(runtime)` (62 insertions
  across the 3 files) plus `_build/sibling-dirty-backup.patch`.
  `tests/test_a14_c23.py` auto-merged and stays uncommitted in the tree;
  the other two were restored to HEAD. Owning agent: please re-apply or
  rebase that delta; nothing of it was committed or discarded here.
- Measured tool-path envelope for Agent 2/3: v2 front-end invocations
  fit roughly 450 bytes of dense Pep; beyond that the parser tool fails
  closed with `PEP_RUNTIME_STEP_LIMIT` (never wrong output). Suspected
  quadratic per-token `append` buffer in the Pep-written parser —
  offered as a lead only; no sibling code touched.

## 2026-10-29 -- slice 2: UTF-8 runtime + generated-code execution proof
- New: `pep_utf8.h/.c` (validate/decode/encode, boundary table
  transcribed from the Pep lexer `utf8_error`), `utf8_probe.c` (31
  fixed vectors), `pep_utf8_model.pep` (classifier mirror, 20 exact
  interpreter values), `pep_utf8_core.pep` (235 B, emitter-verified,
  self-test prints 0). Two slice-1 off-by-ones in the Pep model
  (inclusive bounds with the `!(K <= x)` form) were caught by execution
  and fixed; the C table was already exact.
- Proof upgrade for slice 1: `test_demo_output_compiles_and_runs`
  compiles the actual builder output with Clang and GCC and runs both;
  the generated program prints 13. Probe outputs are byte-identical
  across toolchains and asserted exactly.
- Note for Agent 2/3: `INTEGRATION.md` unchanged in authority; the UTF-8
  table is offered as the future native-lexer reference. Findings here
  are SHA-bound on push.

## 2026-10-29 -- slice 3: spans/diagnostics + third-slice review
- New: `pep_span.h/.c` (`pep_span_locate`, `pep_diag_render`), `span_probe.c`.
  Line/col byte-mirrors both span authorities (OCaml seed lexer and the
  Pep `byte_position` model: only LF is a newline, CR is a column byte);
  render matches the seed CLI form `file:line:col: CODE: message`.
- Evidence: hand-computed excerpt/caret blocks (LF/CRLF/UTF-8/EOF-clamp)
  plus OCaml-`inspect` differential over every AST span of three
  programs. 11/11 suite green on both toolchains.
- Incidents: Windows text-mode stdout corrupted byte assertions; probe
  now sets binary stdout (`_WIN32`-guarded, driver-only). MSVC-target
  Clang needs `-D_CRT_SECURE_NO_WARNINGS` for the probe `fopen` only.
- Gap logged openly: C `BADARG` paths uncovered (slice-4 micro-item).
- `REVIEW_SLICE3.md` holds cumulative review materials; no independent
  reviewer was available in-session, so nothing here is self-certified.
