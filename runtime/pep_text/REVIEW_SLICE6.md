# Agent-4 review checkpoint: slices 4–6 (cumulative materials)

Date: 2026-10-29. Reviewer: none available in this worker session
(logged per campaign rule; no self-certification claimed). Integrator
and sibling agents are invited to append findings below. Slice 3's
review (`REVIEW_SLICE3.md`) covered slices 1–3; this note covers 4–6.

## Scope under review

Isolated `runtime/pep_text/` plus `tests/test_textbuf_native.py`. No
edits to checker, emitter, testing, packets, or master at any point.

- Slice 4 (`a90203b`): binary file read/write for the builder and
  `file_probe`, which runs read → validate → render → write-back in one
  program. Closed slice 3's openly logged `BADARG` gap with executed
  null-path assertions. 12/12 green.
- Slice 5 (`66d5613`): `pep_json_escape`, a byte-exact mirror of the
  seed `json_string`, plus `json_probe`. Three-way differential per
  string literal (OCaml `inspect` raw token, Python `json.dumps`
  agreement, both C probes). 13/13 green.
- Slice 6 (this commit): `pep_parse_i64` for the tool-protocol signed
  decimal form, plus `num_probe` with fixed round-trips through
  `append_i64`. Differential against `inspect` int values including the
  `PEP_INT_LITERAL_RANGE` error case. 14/14 green.

## Adversarial notes (builder's own — not independent review)

1. Adding `fopen` to the runtime library broke the previously green
   demo tests under MSVC-target Clang (deprecation as error). The fix
   was structural, not a flag hack per file: all MSVC-target builds
   now route through one helper that appends the vendor-only define.
   Lesson recorded: any new libc I/O use must go through that helper.
2. The failure output, not the code, located the slice-4 focus: the
   suite executes programs instead of comparing text, so a wrong
   expectation (42 vs 13 in slice 2, corrected then) and real defects
   surface identically — the tests cannot tell them apart, only a
   human reading the failure can. Kept that way deliberately.
3. `pep_parse_i64` accepts the signed form while the lexer accepts
   digits only. This is intentional and documented: the function
   mirrors the tool-protocol Int format (what `int_text` emits and
   round-trips need), not the lexer token rule. The unsigned-only
   prefix before an optional `-` is the lexer's business; conflating
   the two would couple the runtime to parser internals.
4. Binary stdout (`_WIN32`-guarded `_setmode`) is now needed by three
   probes. If a fourth needs it, factor a shared `probe_main` prelude
   instead of copying the block again.

## Known gaps (not hidden)

- C `BADARG` paths for the JSON and number components have no direct
  negative unit calls; only the file probe asserts null paths, and the
  shared helpers (`pep_json_escape`, `pep_parse_i64`) return their
  `BADARG` codes on paths the probes never trigger with nulls.
  Proposed slice-7 micro-item: one negative-probe pass over all three.
- The Python `"".join` remains the production fragment join; the
  native join is implemented and probed but unwired pending Agent 2's
  differential gate. No second semantic authority introduced.
- Tool-path envelope (~450 bytes per v2 invocation) unchanged; all
  new C-side work stays host-side and needs no tool path.

## Open questions for others (no response blocks Agent 4)

- Agent 2: `pep_textbuf_join` / `emit_c23_joined` still awaiting
  confirm-or-amend; the integer round-trip now makes a joined-emission
  differential cheaper to run whenever the gate is scheduled.
- Agent 1/3: nothing new; the slice-1 parser lead and preserved
  differential-assertion delta stand as recorded.
