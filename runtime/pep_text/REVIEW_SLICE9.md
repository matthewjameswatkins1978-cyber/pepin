# Agent-4 review checkpoint: slices 7–9 (cumulative materials)

Date: 2026-10-29. Reviewer: none available in this worker session
(logged per campaign rule; no self-certification claimed). Integrator
and sibling agents are invited to append findings below. `REVIEW_SLICE3`
covered slices 1–3, `REVIEW_SLICE6` slices 4–6; this note covers 7–9.

## Scope under review

Isolated `runtime/pep_text/` plus `tests/test_textbuf_native.py`. No
edits to checker, emitter, testing, packets, or master at any point.

- Slice 7 (`7e89bd9`): negative probe (every null path, sticky-error
  contract) and `utf8check`, the first real native application.
  16/16 green.
- Slice 8 (`5eb49a6`): JSON value writer plus probe; seed-style report
  asserted byte-exact and parsed. 17/17 green.
- Slice 9 (this commit): C string-literal emission with compiler-oracle
  round-trips (the emitted literal is compiled by Clang and GCC and the
  resulting programs' output is compared byte-for-byte with the input).
  18/18 green.

## Adversarial notes (builder's own — not independent review)

1. Windows Defender persistently blocks the empty-vector round-trip
   runner (WinError 225) while letting the other three vectors run.
   Diagnosis: not a transient race (bounded retry with backoff still
   failed) and not content alone (hello/tricky/all256 execute); the
   zero-byte-write binary is what gets verdicts, possibly abetted by
   the earlier `rt_*.bin_rt_*.exe.exe` double-extension naming, which
   has since been cleaned to `rt_<tag>_<cc>.exe`. Response: execution
   scoped to non-empty vectors; the probe still pins the `""` literal
   exactly; a workspace Defender exclusion is a human-owned decision,
   recorded in the outbox, not taken here and not a mission blocker.
2. Octal-merge trap, caught at design time: NUL followed by an ASCII
   digit must not use `\0` (it would merge: `"\01"` is 0x01, not
   NUL+`1`). All non-printables use fixed 3-digit octal for this
   reason; the tricky vector pins NUL+`1` explicitly.
3. Trigraph trap, decided conservatively: `?` is always emitted as
   `\?`, so no `??(` sequence can ever form, even under `-trigraphs`.
   Slightly ugly, provably safe on any flags.
4. The round-trip oracle is the C compiler itself, not an assertion
   the builder wrote: bytes go probe -> literal -> compiler ->
   program output -> byte comparison, with Python only ferrying
   bytes. A wrong escape table cannot pass.

## Known gaps (not hidden)

- Empty-literal execution omitted for the AV reason above; everything
  else about `""` (probe literal, `sizeof` guard reviewed) is covered.
- Tool-path envelope (~450 bytes per v2 invocation) unchanged; all
  slice 7–9 work is host-side and needs no tool path.
- The Python `"".join` remains the production fragment join; the
  native join plus the new literal emitter wait on Agent 2's
  differential gate. No second semantic authority introduced.

## Open questions for others (no response blocks Agent 4)

- Agent 2: `pep_textbuf_join` / `emit_c23_joined` still await
  confirm-or-amend; `pep_cstr_escape` is now available for any future
  string-lowering work that needs C literals.
- Workspace: Defender exclusion for `_build` (or living with the
  scoped empty-vector gap) is Matthew's call; the suite is green
  either way.
