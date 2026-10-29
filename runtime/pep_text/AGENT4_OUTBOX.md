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

## 2026-10-29 -- slice 4: file pipeline + null-path coverage
- New: `pep_textbuf_read_file` / `pep_textbuf_write_file` (binary,
  chunked, sticky-error contract) and `file_probe.c`, which runs the
  whole pipeline in one program: null-path codes (`n 2 1 1 3`),
  read, UTF-8 validate, per-offset diag render, write-back.
- The slice-3 `BADARG` gap is closed: null paths are executed and
  asserted exactly. New hand vectors: UTF-8+CRLF mix with round-trip
  byte identity, `0xFF` invalid input (`v err 0`), missing file
  (`r io`, exit 1). 12/12 suite green on both toolchains.
- Incidents: the library itself now uses `fopen`, so the MSVC
  deprecation define moved from probe-only to every MSVC-target build
  via the shared `_build_c` helper (vendor diagnostic only; code stays
  strict portable C23). `file_probe` needed the same binary-stdout
  treatment as `span_probe`. No Pep files this slice: host file I/O is
  not expressible in Pep by design (OCaml host owns effects).

## 2026-10-29 -- slice 5: JSON string escaping
- New: `pep_json.h/.c` (`pep_json_escape`), a byte-exact mirror of the OCaml seed `json_string`, plus `json_probe.c`. Short escapes, `\b`, `\f`, lowercase `\u00xx`, raw passthrough for DEL/UTF-8/invalid bytes — no validation, exactly like the authority.
- Evidence: differential loop per string literal — OCaml `inspect` raw token, Python `json.dumps` agreement assert, both C probes reproduce the token byte-for-byte. Covers `\" \\ \n \t \r \0`, raw controls (0x01 raw tab 0x08 0x0C 0x7F), empty string, quote/backslash-only, unicode, emoji, embedded NUL (length-delimited, no `strlen`), and raw invalid bytes. 13/13 suite green on both toolchains.
- No Pep files: Str has no byte access or concatenation in the language, so this primitive is inexpressible in Pep; the OCaml differential is the execution evidence. Escaping changes rendering only, never semantics — offered as the future native machine-interface primitive.

## 2026-10-29 -- slice 6: integer parsing + second review
- New: `pep_num.h/.c` (`pep_parse_i64`) for the tool-protocol signed
  decimal form (optional `-`, maximal digit run, MIN-safe unsigned
  accumulation, NODIGITS/OVERFLOW/BADARG), plus `num_probe.c` with
  argv vectors and fixed round-trips through `append_i64`.
- Evidence: differential against OCaml `inspect` int values (0, 007,
  42, MAX) with consumed-length equality, plus the overflow literal
  rejected with `PEP_INT_LITERAL_RANGE`; exact probe output on both
  toolchains incl. partial runs (`12x` → 12/end 2) and all nine
  round-trips. 14/14 suite green.
- Signed form is deliberate (tool-protocol authority, round-trip
  needs), not lexer-token conflation; documented in the header.
- Gap logged openly: JSON/number `BADARG` paths lack direct negative
  calls (slice-7 micro-item). `REVIEW_SLICE6.md` holds the slices 4–6
  cumulative review; no independent reviewer available in-session.

## 2026-10-29 -- slice 7: negative probe + utf8check tool
- New: `neg_probe.c` pins every null path (`n 3 3 3 3 3 3 3`) and the
  sticky-error contract (`s 2 2 2` after a forced overflow), closing
  the slice-6 gap with executed assertions instead of documentation.
- New: `utf8check.c`, the first real native application on the
  runtime: `utf8check FILE...` prints `FILE: ok`,
  `FILE:OFFSET: invalid UTF-8` (first bad byte), or `FILE: cannot
  read`, exit 0 only when all files are valid. 16/16 suite green on
  both toolchains, outputs byte-identical.
- No Pep files, same standing rule: host I/O and byte-level C work
  stay in minimal runtime primitives; the compiler keeps semantics.

## 2026-10-29 -- slice 8: JSON value writer
- New: `pep_jsonval.h/.c` — explicit-shape streaming writer (objects,
  arrays, comma/colon, str/int/bool/null, `"key":`), compact
  seed-style with no spaces, O(1) per call, no DOM, no parsing.
- New: `jsonval_probe.c` emitting a compiler-report-shaped document
  (nesting, empty object/array, escapes, unicode, INT64_MIN); exact
  bytes asserted on both toolchains plus Python `json.loads` value
  assertions. 17/17 suite green.
- No Pep files, same rule. No review this slice (next at slice 9).

## 2026-10-29 -- slice 9: C literals + third review
- New: `pep_cstr.h/.c` (`pep_cstr_escape`) rendering any bytes as a
  safe C23 literal: unconditional `\?` (no trigraphs on any flags),
  fixed 3-digit octal for NUL and non-printables (no digit-merge),
  short escapes otherwise, printable ASCII raw.
- New: `cstr_probe.c`; the test round-trips vectors through Clang and
  GCC themselves (literal -> compiled program -> byte comparison):
  hello, tricky (quotes/backslash/NUL+digit/DEL/0xFF/`??(`),
  empty, and all 256 byte values. 18/18 suite green.
- Incident: Defender persistently blocks the empty-vector runner
  (WinError 225, not a race — bounded retry failed). Execution scoped
  to non-empty vectors; probe still pins `""`. Workspace exclusion is
  a human decision, not taken here; suite is green either way.
- `REVIEW_SLICE9.md` holds the slices 7–9 cumulative review; no
  independent reviewer available in-session.

## 2026-10-29 -- slice 10: native join over real emitter output
- New: `frag_probe.c` joining argv fragments with `pep_textbuf_join`.
  The test emits real C from `pep_textbuf_core.pep` through the
  production Python path, splits it at odd boundaries (empty,
  single-char, mid-line), and proves the native join byte-identical
  to `"".join` — then compiles the natively joined source with both
  compilers and runs its self-test (`0`). 19/19 suite green.
- This is the complete pre-integration evidence for the Agent-2
  `emit_c23_joined` proposal, assembled without touching Agent 2's
  code or changing authority. No review this slice (next at slice 12).

## Hold-time re-reads (no execution)
- All four `.pep` models re-derived by hand against their recorded
  expected outputs (14 capacity + 20 UTF-8 values); every boundary
  matches, headers accurate. Test-file audit done earlier stands.
  Nothing left unexamined in the lane except generated `_build`
  artifacts, which stay untouched.

## 2026-10-29 -- test-file audit under hold (no execution)
- Read `tests/test_textbuf_native.py` end to end and re-derived every
  hand-computed expectation independently (span line/col/excerpts,
  file-pipeline blocks, JSON/number/cstr vectors). All match; no
  assertion bugs. The earlier `!(K <= x)`-class risk does not recur:
  no boundary literals left to misread that the differentials do
  not already pin.
- Resolved open puzzle from slice 7: `utf8_probe.c` needs no MSVC
  define because it never calls `fopen` (vectors are static arrays).
  Every TU that does call `fopen` already routes through `_build_c`.
- Three uniformity cleanups queued for post-hold (no behavior
  change): module docstring still describes only slice 1; MSVC-flag
  logic is inline-duplicated in the cstr/join tests instead of
  reusing `_build_c`; the utf8-probe and demo-gen builds predate
  the helper and bypass it. None affect correctness; all green.

## 2026-10-29 -- static audit under security hold (no execution)
- Read all seven runtime components end to end (builder, UTF-8,
  spans, JSON str/values, numbers, C literals). No correctness
  defects in any executed path; boundary tables match their
  authorities exactly as the differentials already prove.
- Four doc-level findings, sources untouched (fixes need test runs,
  which are paused): (1) `next_capacity` comment claims a `false`
  return it never produces; (2) `pep_utf8_validate(nullptr, 0)`
  returns OK against the header's BADARG promise — recommend code
  follows header; (3) `pep_parse_i64` header says `*end` is
  untouched on OVERFLOW but the code zeroes it first (behavior is
  good, doc is wrong); (4) BADARG numeric values differ per
  component (1/2/3) — namespaced and workable, but callers should
  be told codes are component-local.
- No changes made: audit only, zero bytes modified, nothing built
  or run. Residual `_build/spanprobe` scripts kept as evidence.
