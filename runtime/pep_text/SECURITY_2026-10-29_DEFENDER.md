# SECURITY INCIDENT NOTE — Windows Defender quarantine, 2026-10-29

Reading guide: "Provenance" and "Detection record" are verified facts
(hashes, transcripts, Defender history). "Assessment" is explicitly an
unconfirmed hypothesis. "Unresolved risks" and the reviewer asks are
open items. Nothing in this file clears the binaries or authorises
resuming builds or execution.

Status: INVESTIGATED READ-ONLY. No executables generated or run after
the alert. Nothing restored, no exclusions added, no settings changed.
This file is committed as the durable incident record; the security hold itself is NOT lifted by committing it.

## Alert (as received)

Windows Defender flagged as Severe / Trojan and quarantined:
- `D:\Projects\pepin\_build\textbuf\rt_empty_clang.exe`
- `D:\Projects\pepin\_build\textbuf\rt_cstr_empty.bin_rt_clang.exe.exe`

Both files are absent from disk (quarantine confirmed by absence).
Their generated `.c` sources remain; executable hashes are therefore
UNAVAILABLE and will not be reconstructed (that would mean rebuilding).

## Provenance (verified, not assumed)

1. Generator: `tests/test_textbuf_native.py`,
   `test_cstr_roundtrip_through_compilers`, committed at
   `c3400ca` (slice 9, `.exe.exe` naming) and renamed at `bea69f9`
   (slice 10, clean names). Both commits pushed; HEAD is `bea69f9`.
   Test-file blob: `263ce7ae810bbb2c617c647f77d9b40ff0ca3460`.
2. The flagged binaries are compiled from a GENERATED runner `.c`,
   produced by substituting the probe's escaped literal into this
   committed template (exact text from HEAD):
   `#include <stdio.h> / static const char s[] = %s;` + main that
   opens `argv[1]` `"wb"`, conditionally `fwrite`s `sizeof s - 1`
   bytes, closes, returns `fclose(...) != 0`.
3. The on-disk generated sources are byte-identical to the template
   output: SHA256
   `725A933BC6D79AFD016D0D6787BFD8B5CAC37F4C3870D638D7D9DD8D330323A2`
   for both `rt_empty_clang.c` and
   `rt_cstr_empty.bin_rt_clang.exe.c` (identical inputs → identical
   303-byte file; contents printed in full in the investigation log).
4. Compile commands (from the committed test, no shell wrappers):
   `clang -std=c23 -Wall -Wextra -Wpedantic -Werror
   -D_CRT_SECURE_NO_WARNINGS <runner.c> -o <runner.exe>`,
   where clang is `C:\Users\Matmus\scoop\apps\llvm\23.1.4\bin\clang.exe`
   (MSVC target). GCC equivalents used MinGW 16.2.0 with the same
   strict flags minus the MSVC-only define.
5. Both flagged binaries are CLANG builds of the EMPTY vector
   (`static const char s[] = "";` — opens the output file, writes
   zero bytes because of the `sizeof s > 1` guard, closes, exits 0).
   The `.exe.exe` name is a test bug from slice 9 (exe stem already
   ended in `.exe`, then `-o` appended another); cleaned to
   `rt_<tag>_<cc>.exe` in slice 10. The bug explains the name fully.
6. Full `_build` sweep: every other `.exe` under `_build\textbuf`
   maps to a known test output (demo/probe/span/json/num/neg/file/
   frag/utf8check binaries); no foreign executables found. Sibling
   `_build` trees (OCaml `pep.exe`, MoonBit, native, c23-feasibility)
   predate this lane and were not flagged per the alert.

## Assessment (hypothesis, NOT a conclusion)

The flagged programs are trivially small file-writers built minutes
before execution, unsigned, exhibiting dropper-like behavior
(create-file-then-exit, zero-byte variant included). That matches the
well-known profile of ML-heuristic false positives on compiler-test
harnesses — but a resemblance is not evidence, so this note does NOT
clear the binaries.

## Unresolved risks / what I cannot verify from here

- The quarantined binaries cannot be inspected (absent) and will not
  be rebuilt or restored by me.
- Toolchain compromise cannot be ruled out from inside: no
  clean-room reference hashes exist here for the scoop Clang install,
  MinGW GCC, or the MSVC UCRT import libraries they link against.
- Asymmetry is incomplete evidence: no GCC-built empty runner was
  ever executed (the clang build/run precedes it and failed first),
  so "only clang builds flagged" may reflect ordering, not cause.
- Sibling `_build` executables were not flagged per the alert, but
  that is the alert's scope, not an independent audit.

## Detection record (read-only Defender history query, 2026-10-29)

No settings changed, nothing executed or restored. Read-only
`Get-MpThreat` / `Get-MpThreatDetection` output:

- Name: `Trojan:Win64/LummaC.NFD!MTB` (ThreatID 2147937686,
  SeverityID 5/Severe). The `!MTB` suffix is, to the best of my
  knowledge, a behavioral/ML detection tag rather than a static hash
  signature — verify before acting on that reading.
- Both repo files remediated (quarantined, ThreatStatusID 3):
  `rt_cstr_empty.bin_rt_clang.exe.exe` (first seen 01:28:05,
  remediated 01:29:11 after repeated spawn attempts) and
  `rt_empty_clang.exe` (first seen 01:30:30, remediated 01:30:50).
  Times match this lane's session transcript to the minute
  (generated `.c` mtime 01:28:44 sits between first detection and
  remediation; the 01:28:59 pwsh entry matches a manual run
  attempt). Spawning processes were our own harness
  (`python.exe`, `pwsh.exe`).
- `DidThreatExecute: False` on both records: Defender reports the
  payloads never executed — consistent with the WinError 225
  launch blocks observed live.
- Machine-hygiene context (no action taken, reported for the
  supply-chain question only): Defender history also shows an older,
  unrelated `PUABundler:Win32/FusionCore` detection (July 2026)
  against a third-party keygen in the user's Downloads folder.
  Product name deliberately omitted here. It does not implicate
  the repo, but it means this machine has run grayware before,
  which raises the prior against casually dismissing any
  detection as a false positive.

### What this changes

- The heuristic-suffix reading mildly supports the false-positive
  hypothesis (ML detections on tiny unsigned file-writers are the
  classic FP shape), but LummaC is a real stealer family: if the
  verdict were correct, credential-bearing material on this box
  would be at risk. I do not clear the binaries either way.
- Concrete asks for the reviewer: (1) confirm or correct the
  `!MTB` reading; (2) decide whether to submit the two file hashes
  (sources only — binaries are gone) to Microsoft as suspected
  false positives; (3) decide on credential-rotation hygiene for
  this box proportional to your reading; (4) rule on the workspace
  Defender exclusion before any native lane resumes.

## Standing lane posture until review

- No native generation or execution in Agent-4 lane (test suite left
  red-barred by policy, not by code: 19/19 was green before the
  alert; nothing re-run since).
- Safe work may continue (sources, docs, Pep-side models, review
  notes). No exclusions, no restores, no Defender interaction.
- Suggested reviewer actions: confirm the two `.c` sources against
  the committed template (hashes above), decide whether to submit
  the quarantined files' identities to Microsoft as suspected false
  positives, and rule on a workspace Defender exclusion before any
  native lane resumes.
