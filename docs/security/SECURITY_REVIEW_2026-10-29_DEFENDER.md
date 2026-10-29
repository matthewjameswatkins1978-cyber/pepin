# SECURITY REVIEW — independent triage of the 2026-10-29 Defender detection

Ticket: [issue #22](https://github.com/matthewjameswatkins1978-cyber/pepin/issues/22) (`[SECURITY REVIEW] Triage Defender C23 detection and restore native verification safely`).
Subject incident record: `runtime/pep_text/SECURITY_2026-10-29_DEFENDER.md` @ `805062b`.

Reading guide, borrowed from the incident record because it is the right
distinction:

- **Observed** — read from live machine state, event logs or file bytes during
  this review. Commands are listed in §13 and can be re-run.
- **User-reported** — asserted by Matthew or by the incident record, *not*
  independently verified here.
- **Inference** — reasoning from the above. Never a clearance.

Nothing in this file clears the quarantined binaries, lifts the native-execution
hold, or authorises anything. The hold stays until Matthew decides otherwise.
This is an independent read-only review lane; it did not touch the compiler,
host security configuration, another agent's worktree, or the quarantined files.

## 1. Verdict (graded)

**Probable false positive** — the two quarantined binaries are most likely
benign compiler-test artefacts of a tiny generated C runner, and there is **no
evidence of compromise** of the Clang/GCC toolchain in the paths that were
checked.

- Confidence **moderate-to-high (~80%)** for "no compromise demonstrated and
  most likely a heuristic/ML false positive".
- Confidence is *not* 95%+ for two reasons, both honest limits rather than
  doubts I talked myself out of: the binaries themselves are gone and will not
  be rebuilt (§10), and Defender recorded `Detection Type: Concrete`, which on a
  plain reading is *not* a generic heuristic hit (§7). I could not reconcile
  that field's semantics from available documentation.
- Residual possibility of credible compromise evidence in the pinned toolchain
  can only be retired by the clean-environment smoke test in §11, not by
  argument.
- **Raised by later evidence:** a completed three-hour full scan under current
  definitions with every exclusion removed found nothing in the build tree
  (§15). That moves confidence to the upper end of the band, ~85%, without
  relaxing any limit in §10.

Recommendation in one line: **treat as probable FP, remove the newly added
`D:\Projects` exclusion, and require one bounded native smoke test on a clean
host before the native lane resumes** (§12). All three are Matthew's calls.

Two state changes flagged during this review — the `D:\Projects` exclusion and
the 05:55–08:05Z real-time-protection window — were confirmed by Matthew as his
own deliberate mitigation attempts against the suspected false positive (§4,
§5). They are recorded as evidence about method, not as evidence of compromise.

## 2. Defender health and protection settings (observed)

Host: Windows 11 Pro Insider Preview 10.0.26220, 64-bit, booted
2026-10-26T15:38Z. Reviewer session `2026-10-29T19:11Z`–`19:20Z`, **not
elevated**, read-only.

| Setting | Value |
|---|---|
| Antivirus / Antispyware enabled | True / True |
| Real-time, On-access, IOAV, Behaviour Monitor, NIS | all True |
| Tamper Protection | True |
| Platform / Engine | 4.18.26100.4 / 1.1.26100.4 |
| Security intelligence | 1.463.24.0, age 0, not out of date |
| MAPS (cloud) reporting | 2 (Advanced) |
| Submit samples consent | 1 (send safe samples automatically) |
| PUA protection | 1 (on) |
| Cloud block level / extended timeout | 0 / 0 (defaults) |
| Controlled folder access | 0 (off) |
| ASR rules | none configured |

Defender is healthy and fully enabled; the 18:39:29Z health report agrees
(`1150`: "up and running in a healthy state"). No protection was disabled by
this review.

## 3. Detection record (observed)

`Get-MpThreat` / `Get-MpThreatDetection` plus Defender operational events
`1116`/`1117`, retained log spanning **2026-08-06 → 2026-10-29T19:12Z**:

- Threat: `Trojan:Win64/LummaC.NFD!MTB`, ThreatID `2147937686`,
  SeverityID 5 (Severe), CategoryID 8 (Trojan).
- 8 detection events (`1116`), 5 quarantine actions (`1117`), all
  `ActionSuccess: True`, `ThreatStatusID: 3` (quarantined), `Error Code:
  0x00000000`.
- Two distinct paths only:
  - `_build\textbuf\rt_cstr_empty.bin_rt_clang.exe.exe` — first seen
    2026-10-29T01:28:05Z, quarantined 01:28:41Z; further detections 01:28:44Z,
    01:28:59Z, 01:29:11Z, each followed by a quarantine action.
  - `_build\textbuf\rt_empty_clang.exe` — first seen 01:30:24Z, quarantined
    01:30:50Z; further detections 01:30:30Z, 01:30:42Z, 01:30:50Z.
- Recorded at detection: `Detection Source: Real-Time Protection`,
  `Detection Origin: Local machine`, `Detection Type: Concrete`,
  security intelligence `1.463.12.0`, engine `1.1.26100.4`.
- `DidThreatExecute: False`; `CurrentThreatExecutionStatusID: 1` on every row.
- Spawning processes: `python.exe` (pythoncore-3.15-64) and `pwsh.exe` — the
  test harness, matching the incident record.
- **No detection of any kind after 01:30:50Z** (~18 h) and no third detection
  path. The complete local detection history since 2026-08-06 contains one
  other threat: `PUABundler:Win32/FusionCore` (June/July 2026, a third-party
  keygen file in `Downloads`, product deliberately unnamed here) and, on
  2026-09-12, five ML-suffixed (`!ml`) detections of a small agent-produced
  executable under `Documents\Codex\...` (§9).

## 4. Exclusion state — the material finding (observed via log)

`Get-MpPreference` returns `N/A: Must be an administrator to view exclusions`
and the registry key `HKLM\SOFTWARE\Microsoft\Windows Defender\Exclusions\Paths`
returns `Access is denied`, so the live list could not be read. The Defender
operational log records every exclusion change as event `5007`, which is
sufficient ground truth for this window. Only **four** path-exclusion events
exist in the retained log (2026-08-06 onward):

| When (UTC) | Change |
|---|---|
| 2026-10-07T06:12:41Z | added `C:\Users\...\RustroverProjects\untitled` |
| 2026-10-07T06:12:41Z | added `C:\Users\...\AppData\Local\JetBrains\RustRover2026.2` |
| **2026-10-29T18:29:45Z** | **added `D:\Projects`** |
| 2026-10-29T19:12:01Z | removed `C:\Users\*\Documents\Celemony\Separations` |

Two consequences:

1. **No workspace exclusion existed at detection time.** `D:\Projects` was not
   excluded on 2026-10-29 at 01:28Z, and no Pepin-specific path exclusion
   appears anywhere in the log. This is consistent with Real-Time Protection
   seeing and quarantining the freshly written binary. It also means the
   user-reported statement that Defender scans were run "before and after
   removing the Pepin folder exclusions" is **not corroborated** by telemetry:
   no removal of any `D:\Projects` exclusion is recorded, only the 18:29:45Z
   addition.
2. **`D:\Projects` is excluded right now**, added 2026-10-29T18:29:45Z with no
   removal event since. That post-dates the incident by ~17 h and is not
   recorded in the incident file, the issue, or any commit this review could
   find. It makes the entire native build tree, including
   `_build\textbuf\` and every future native artefact, invisible to Defender.

That second point is the most consequential state change in the whole incident,
and it cuts against every other reassurance: with the build tree excluded, no
future native run on this host can be verified by Defender, and "no new
detections since" is not evidence of anything for that path. An exclusion is
worse than the false positive it was presumably added to suppress.

The caller is not recorded by Defender (`5007` names the registry value, not
the process), and adding an exclusion requires elevation. Attribution is
resolved: the owner. Matthew confirmed during this review that he added the
`D:\Projects` exclusion himself, as a deliberate attempt to stop a suspected
false positive from blocking the native lane. That replaces an unexplained
elevation event with a recorded owner decision, and it withdraws the earlier
possibility of an automated agent change: no evidence supported that reading,
and the timeline correlation with `codex/bootstrap-agent2-b0` (18:36:58Z) must
not be read as attribution. The security consequence rests on the paragraph
above rather than on who did it — an excluded build tree cannot be verified,
and the reason to remove the exclusion is that it removes evidence.

## 5. Protection-setting changes today (observed)

Two attempts to disable Real-time Protection occurred **after** the incident,
both reverted by Tamper Protection:

- 05:55:32Z `5001` RTP disabled; 08:05:21Z `5013` tamper reverted
  `DisableRealtimeMonitoring 1 -> 0`; 08:05:27Z `5000` RTP re-enabled.
  Real-time protection was therefore **off for ~2 h 10 min** early today.
- 17:02:47Z `5001` RTP disabled; 17:02:50Z `5000` re-enabled and `5013` reverted.

Attribution is resolved: the owner. Matthew confirmed he disabled Real-time
Protection himself for the 05:55–08:05Z window, again to let the suspected
false positive pass over. It did not work, and could not have: disabling
protection leaves the detection record unchanged and removes the only
instrument able to distinguish a false positive from a real one. The
17:02:47Z three-second toggle is consistent with the same action but is not
separately confirmed here. Tamper Protection demonstrably worked and restored
RTP at 08:05:27Z. The incident itself, at 01:28Z, happened with RTP on and no
exclusion.

## 6. Scans (observed)

- 2026-10-27T12:23:31Z–12:29:03Z — quick scan completed (pre-incident).
- 2026-10-29T01:46:24Z — user quick scan started **and stopped before completion
  at 01:48:11Z** (`1002`, `Stop Reason: Unknown`). So the post-incident scan
  that was actually initiated over the affected tree did **not** finish.
- 2026-10-29T11:39:25Z–11:45:06Z — SYSTEM quick scan completed (after the 11:39:26Z
  `1013` retention event purged history older than 2026-10-14).
- 2026-10-29T19:05:48Z–19:11:19Z — quick scan completed.
- **No full scan has ever completed on this machine** (`FullScanAge`
  4294967295; `1151` reports `Last full scan start time: 1601-01-01`).

Both completed quick scans post-date 18:29:45Z and neither covers `D:\Projects`,
which is excluded. "Scanned with no detections" therefore says very little about
the workspace.

## 7. Discriminating evidence (observed) — the strongest fact in this review

Between **01:36:39Z and 01:37:15Z**, six to eight minutes *after* the last
quarantine and ~17 h *before* any exclusion existed, the same test harness
compiled and executed many more binaries into the same `_build\textbuf`
directory from the same template, including same-shape Clang runners:

| Artifact | Size | SHA256 | Outcome |
|---|---|---|---|
| `rt_hello_clang.exe` (literal `"hello"`) | 131,072 | `A29BF68E…E7317275` | built, ran, `.bin` written, **not flagged** |
| `rt_tricky_clang.exe` (14-byte escaped literal) | 131,072 | `886A905E…CF3B6698A` | ran, **not flagged** |
| `rt_all256_clang.exe` (all 256 bytes) | 131,584 | `5040454C…327BD62FF` | ran, **not flagged** |
| `cstr_clang.exe` (combined probe; wrote `cstr_empty.bin`, 0 bytes, 01:36:42Z) | 141,312 | — | ran, **not flagged** |

Same compiler, same flags, same template, same directory, same signature version
(1.463.12.0), RTP enabled, no exclusion — and Defender flagged none of them,
including a run that wrote a **zero-byte** file. The detector discriminated the
two empty-literal runners from their near-identical neighbours.

Still present on disk and untouched by this review (same generated template,
same builder):

- `rt_cstr_hello.bin_rt_clang.exe.exe` — 131,072 B, SHA256
  `47F70CB1BC32E9DCEB349163DBC17CB0707C58B1AECDA98E04D03C11946D7A07`
- `rt_cstr_tricky.bin_rt_clang.exe.exe` — 131,072 B, SHA256
  `2B372CA5DA0DE7824FE048FDA446E2B0CB9082742F06BDB0E9CB437780343A8A`
- GCC equivalents — `E2D9B36E…8B39F1E2` (hello, 55,307 B) and
  `6E4CEC3B…907AB996` (tricky, 55,308 B)

Targeted on-demand probe performed by this review (because the originals are now
inside the excluded tree): the `hello` clang runner was copied to
`%TEMP%\pepin-sec\`, hash-verified identical, and scanned with
`MpCmdRun.exe -Scan -ScanType 3 -File` under **current** signatures
`1.463.24.0`. Result: `Scanning ... found no threats`, exit code 0. The copy was
then deleted; the original remains at the path and hash above.

Source-side provenance re-verified against the checkout at `805062b`:

- Both flagged generated sources are byte-identical to each other and match the
  committed runner template at `tests/test_textbuf_native.py:595-602`
  (`... static const char s[] = %s; ... fopen(argv[1], "wb") ...`), SHA256
  `725A933BC6D79AFD016D0D6787BFD8B5CAC37F4C3870D638D7D9DD8D330323A2` — the same
  hash the incident record published. The `"hello"` variant differs only in the
  substituted literal (`50D0BB57…48655CE0AF`).

**Note on `!MTB`** (the incident record asks for confirmation): Microsoft does
not document this suffix. Microsoft's own malware-encyclopedia entries use
`!MTB` on *behavioural* detections (`Trojan:Win64/ShellcodeRunner!MTB`,
`Trojan:Python/Metasploit!MTB`), and community reading is "behaviour / ML-derived"
rather than a static hash signature. Microsoft's published suffix table covers
`!bit`, `!dha`, `!rfn`, `!plock` and similar, and omits `!MTB`. **Confirmed: do
not read `!MTB` as a false-positive marker, and do not read it as a hash
signature either.** It is an internal vendor tag whose semantics are not public.

Open point I could not settle: event `1116` says `Detection Type: Concrete`.
Documented usage of that field separates specific/concrete hits from
`Heuristic`/`Generic`. If `Concrete` really means "not a generic heuristic", a
pure ML false positive is a slightly less comfortable explanation than it looks.
I found no authoritative mapping for this field and will not invent one.

## 8. Toolchain provenance (observed)

Verified hash chain, all read-only:

| Component | Installed | Cached installer SHA256 | Equals official upstream asset digest |
|---|---|---|---|
| LLVM/Clang 23.1.4 (`scoop\apps\llvm\23.1.4`, installed 2026-10-26T20:08Z) | `clang.exe` SHA256 `CFC98FFD…94A189A9A`, target `x86_64-pc-windows-msvc`, build `+alloc:rpmalloc` | `LLVM-23.1.4-win64.msi` 639,641,329 B `15e49aca3540991a6f28a0e57babab67da82155c4f73f79dd5e8666a851f9127` | **Yes** — GitHub API asset `digest` for `llvm/llvm-project` release `llvmorg-23.1.4` |
| MinGW-w64 GCC 16.2.0-rt_v14-rev1 (`scoop\apps\mingw\16.2.0-rt_v14-rev1`, installed 2026-10-26T20:10Z) | `gcc.exe` SHA256 `277CB1B8…0CF00EB0`, `ld.exe` `3B56FF30…A6CC6628` | `x86_64-16.2.0-release-posix-seh-ucrt-rt_v14-rev1.7z` 107,890,935 B `26788998d615856a915e1eeacb0854fce87bc608fa9a0c16f96bcbfdcf3415c0` | **Yes** — GitHub API asset `digest` for `niXman/mingw-builds-binaries` release `16.2.0-rt_v14-rev1` |

Supporting checks:

- Both were installed from the **official Scoop `main` bucket** at git commit
  `5be7f8c702856c72800a0a4945b88fe6ea2bd52f` (remote
  `ScoopInstaller/Main.git`), working tree clean — no local manifest edits, so
  the pinned hash is the bucket's own reviewed value.
- The cached installers hash-match both the bucket manifest and the digest
  GitHub reports for the release asset. The artifact unpacked on this host is
  therefore the artifact upstream published.
- **No file** in either install tree (599 LLVM files, 13,881 MinGW files) has a
  modification time later than 2026-10-27, i.e. no post-install tampering is
  visible.
- Linked MSVC/UCRT import libraries came from an installed Microsoft toolchain
  (VS 2022 BuildTools 17.14.37710.0, Windows SDK 10.0.22621.0). Those installers
  are Microsoft-signed and were not hashed file-by-file in this pass.

What this **cannot** establish, stated plainly:

- **None of the toolchain binaries is Authenticode-signed.** `clang.exe`,
  `lld-link.exe`, `gcc.exe`, `ld.exe` and the LLVM MSI all report `NotSigned`.
  There is no publisher signature to check; identity rests entirely on the hash
  chain to GitHub release metadata.
- A GitHub asset digest proves the bytes are the ones upstream published. It does
  not prove upstream was not compromised, and it is not a reproducible-build
  attestation.
- The Windows SDK / MSVC library files were not independently verified here.
- There is no clean-room reference build on this machine to compare generated
  binaries against, so "the compiler emitted exactly what it should have" is
  untested for the two quarantined artefacts.

## 9. Competing hypotheses (graded)

**H1 — ML/heuristic false positive on a tiny unsigned file-writer (probable,
~80%).** For: the source is a committed, reviewed 303-byte template that only
opens a path and writes a literal; the detection name carries a behavioural/ML
tag; the same-family suffix appears on Microsoft's own behaviour detections;
public prior art for Defender false-positiving locally compiled small
executables is extensive and specific to this exact toolchain class (LWJGL
issue #1005 attributing detections to a switch to `clang-cl`; winlibs/MinGW
builds flagged as generic/heuristic; long-standing reports of MinGW-built
.dll/.exe being flagged); the paired non-detections in §7 show the detector is
selective, not sweeping; and this host has a *previous* documented instance of
small agent-produced executables being hit by `!ml` detections
(`Documents\Codex\...\gary.exe`, 2026-09-12, `Behavior:Win32/Execution.A!ml` +
`Trojan:Win32/Bearfoos.A!ml`) — same shape of event, same machine, before this
incident. Against: `Detection Type: Concrete` (§7), the binaries are
uninspectable, and Lumma is a real stealer family.

**H2 — Compromised compiler / dependency / build host (not supported).** For: in
principle an injected payload would appear in compiler output and Defender would
be reporting truthfully. Against: it would have to be content-keyed to fire on
the empty-literal build only and stay silent on four same-template builds from
the same compiler executed minutes later (§7); the toolchain hash-chains to
official upstream assets with no post-install modification (§8); the generated
sources are byte-identical to committed source (§7). Nothing supports H2, and
the selective behaviour actively disfavours it. It cannot be closed by argument
— only by the clean-host comparison in §11.

**H3 — Independent compromise of the machine unrelated to the build (cannot be
assessed here).** The `.exe.exe` double extension is a classic masquerade
pattern, and in this case it is fully explained by a test-naming bug fixed in
`bea69f9`. Both were owner actions (§4, §5): pragmatic attempts to keep the
native lane moving past a suspected false positive. That intent is reasonable —
the detection has the classic shape of an ML false positive on a tiny unsigned
build artefact — but the method cannot work, for a reason worth fixing in
habits rather than repeating: disabling or excluding removes evidence instead
of producing a verdict. The 05:55–08:05Z window still stands as a genuine
unmonitored interval on this host, and the exclusion still blinds Defender to
the build tree. Neither is evidence that the flagged binaries were malicious.

**Grade: probable false positive, no credible compromise evidence, with three
documented unresolved items** (§10). If H1 is wrong, the failure mode is
credential theft on a developer box, so the cost of being wrong is not trivial
and the smoke test in §11 is worth its small cost.

## 10. Remaining uncertainty — what is not established

1. The two quarantined binaries are absent and will not be rebuilt or restored
   by this review. Their behaviour is inferred from source, and innocuous source
   is not proof of a benign binary.
2. `Detection Type: Concrete` semantics are unresolved (§7).
3. The live exclusion list could not be read (no elevation). §4's conclusion
   rests on the Defender config-change log, which is authoritative for changes
   but does not show whether any exclusion predates 2026-08-06.
4. Attribution of the 18:29:45Z exclusion and the 05:55–08:05Z RTP window is
   resolved: both are owner actions, confirmed by Matthew (§4, §5). Defender
   still does not record the caller, so this rests on his account rather than
   on telemetry.
5. Whether the detection still reproduces today for the *empty-literal* binary
   is untested, deliberately: testing it means rebuilding a quarantined binary
   on the affected host, which this lane is forbidden to do.
6. This review inspected one host from a non-elevated account. It says nothing
   about other machines, and nothing was learned from GitHub alone.
7. Whether the post-alert native runs at 01:36–01:37Z were authorised is outside
   this lane. They are recorded here because they are the decisive evidence in
   §7 and because the incident record's "no executables generated or run after
   the alert" line is inconsistent with the timestamps of those artefacts (they
   are 6 minutes after the last quarantine, and the record was committed at
   04:03Z). Factual correction only; no accusation intended or supported.

## 11. Exact conditions for a safe native C23 smoke test (proposal — needs approval)

Not authorised by this document. The existing clean-Ubuntu Lean 4 authorisation
is **Lean-only** and does not cover this. This is a *proposal for Matthew to
approve or amend*, not a plan that may start.

Scope, deliberately minimal — this is a conformance smoke test, **not** a rebuild
of either flagged runner:

- **Environment.** A different, controlled machine: VM or separate host, clean
  image, Defender (or the host OS equivalent) fully enabled, **no exclusions**,
  and none of the Pepin working tree present. Not this host.
- **Source.** Pin an exact commit SHA and a small new source that is *not* the
  empty-literal runner — e.g. a program that writes a known N-byte payload to a
  path given on argv and prints a checksum of what it wrote. Record the source
  SHA256 in the receipt.
- **Toolchain.** Fetch on the clean host and verify before use: LLVM MSI
  `15e49aca3540991a6f28a0e57babab67da82155c4f73f79dd5e8666a851f9127`, MinGW 7z
  `26788998d615856a915e1eeacb0854fce87bc608fa9a0c16f96bcbfdcf3415c0`. Record
  `--version` output and any signature status. Do **GCC first** — there is no
  flagged precedent for the MinGW build — then Clang.
- **Compile flags.** Exactly the committed flags: `-std=c23 -Wall -Wextra
  -Wpedantic -Werror`, plus `-D_CRT_SECURE_NO_WARNINGS` for the MSVC target.
  Expect exit 0 with no warnings.
- **Expected behaviour.** Program exits with the expected status; the written
  file is byte-compared by an independent reader (Python), not by the program
  itself; stdout checksum matches the independently computed one.
- **Pre/post evidence.** Before and after: `Get-MpComputerStatus` (or platform
  equivalent) and the detection history, plus the signature/engine version in
  force during the run. Both compilers, both artefacts, hashes recorded.
- **Re-alert stop condition.** Any new `1116`/`1117`, any Severe detection, or
  any file blocked at write or launch during the run: **stop immediately**. Do
  not retry, do not add an exclusion, do not disable protection, do not restore
  anything. Capture the event record and the SHA256 of the freshly built
  artefact (that artefact is lawfully obtainable, because it was just built in a
  controlled run on the clean host), then escalate.
- **Interpretation.** Re-alert on the clean host with a hash-pinned compiler and
  a *different* source ⇒ persistent false-positive signature (or, if the same
  binary shape is involved, a real signature) ⇒ submit as suspected false
  positive (§12) and keep the native lane held. No re-alert with identical
  pinned toolchain ⇒ the detection was specific to the 01:28 artefacts/host ⇒
  host-scoped escalation instead of a global hold.

## 12. Recommendation to Matthew (decisions he owns)

1. **Decide on the `D:\Projects` exclusion — recommend removing it.** It was
   added 2026-10-29T18:29:45Z without a recorded decision, it is not the FP
   mitigation it looks like, and while it stands every native run and every "no
   new detections" claim about this repository is unverifiable. I did not touch
   it. It needs elevation, so it is his action either way.
2. **Treat the incident as a probable false positive and keep the native lane
   formally held until §11 is approved and run.** Do not clear the binaries.
3. **Do not repeat the 05:55–08:05Z RTP-off window or the workspace**
   **exclusion.** Both were owner actions rather than intruders, so the concern
   is not attribution — it is that each one removes evidence and leaves the
   native lane unverifiable. Tamper Protection reverted the 17:02:47Z attempt;
   the earlier window left ~2 h 10 min unprotected and the exclusion is still
   in place.
4. **Optional false-positive submission — his action, his consent.** The two
   quarantined samples still exist in the Defender quarantine store, so the
   samples are available to submit *without* restoring or rebuilding them, via
   Windows Security. I will not upload anything. Ready-made facts for the
   submission form: threat `Trojan:Win64/LummaC.NFD!MTB`, ThreatID
   `2147937686`, severity Severe, two quarantined paths, and the generated-source
   SHA256 `725A933B…330323A2`. Note `SubmitSamplesConsent = 1`, so Defender may
   already have shared safe-sample metadata automatically.
5. **Communicate to the integrator** that: the hold is not lifted; the exclusion
   state changed at 18:29:45Z and native binaries were built and executed at
   01:36–01:37Z after the alert; therefore "nothing has run since the alert"
   should not be relied on in status reporting. Source-only and non-native work
   can continue.

## 13. Commands actually run (all read-only unless noted)

Non-elevated, `2026-10-29T19:11Z`–`19:20Z`. Outputs are summarised above;
nothing was changed in the repository or in Defender configuration.

- `Get-MpComputerStatus` (selected fields), `Get-MpPreference` (non-exclusion
  fields; exclusion fields return "requires administrator"), `Get-MpThreat`,
  `Get-MpThreatDetection` (full property dump).
- `Get-WinEvent -LogName 'Microsoft-Windows-Windows Defender/Operational'` —
  full-log extent, all `5007` events mentioning `Exclusions`, all
  `5000/5001/5004/5007/5010/5012/5013` since 2026-10-28, all events
  2026-10-29T00:00–03:30Z, and all `1116/1015` in the retained log.
- `reg query "HKLM\SOFTWARE\Microsoft\Windows Defender\Exclusions\Paths"` →
  `Access is denied` (recorded as a limit, not worked around).
- `Get-FileHash -Algorithm SHA256` on the surviving `_build\textbuf` artefacts,
  the generated `.c` sources, the cached installers and the compiler binaries;
  `Get-AuthenticodeSignature` on those same files; `Get-ChildItem -Recurse`
  mtime sweep over both toolchain trees; `git` state of the three Scoop buckets.
- `gh api repos/llvm/llvm-project/releases/tags/llvmorg-23.1.4` and
  `gh api repos/niXman/mingw-builds-binaries/releases/tags/16.2.0-rt_v14-rev1`
  — asset `digest` fields only, compared against the cached installers.
- `clang --version`, `gcc --version`, `vswhere` — capability/provenance only.
  **No compilation and no native execution was performed by this review.**
- One deliberate on-demand scan, §7: `Copy-Item` of the `hello` clang runner to
  `%TEMP%\pepin-sec\` (hash-verified identical), `MpCmdRun.exe -Scan -ScanType 3
  -File <copy>` → "found no threats", exit 0; the copy was then deleted. No
  restoration, no exclusion, no protection change, no rebuild.
- Scoped `Select-String` over the interactive PowerShell history for
  Defender-related commands (no matches).

Deliberately **not** done: no AV exclusion or setting change, no protection
disable, no quarantine restore, no rebuild of either flagged binary, no native
C23 build or execution, no sample upload, no credential or secret collection,
no change to shared security status, no merge.

## 14. Redactions and publication note

This repository is public. Host name, account identifiers beyond the username
already published in the incident record, and the name of the unrelated
third-party product implicated in the June/July detection are omitted here, on
the same principle the incident record applied.

## 15. Full-scan outcome — 2026-10-29T19:28–22:31Z (added after the review)

Executed on the owner instruction, following the recommendation in §11 and with
every path exclusion removed first (verified from the Defender config log:
`RustRover2026.2`, `RustroverProjects\untitled` and `D:\Projects` all removed
19:27:27Z–19:27:35Z, ~40 s before the scan started).

**The scan.** One on-demand full scan, `MpCmdRun -Scan -ScanType 2`, PID 30596,
scan ID `{53D18399-634F-4099-A538-DD05EEDD76D1}`: started 2026-10-29T19:28:16Z,
finished 2026-10-29T22:31:31Z, `Scan Time: 3:03:15`. `FullScanAge` is now 0 —
the first full scan this host has ever completed. RTP and tamper protection
enabled throughout; signatures 1.463.28.0 at start, 1.463.30.0 at completion.

**Result for this repository: clean.** No detection of any file under
`D:\Projects`, and specifically none of the 44 artefacts in `_build\textbuf`
or the surviving same-template runners. Verified against the pre-scan hash
inventory captured at 20:55Z: **435 of 435 native binaries under `_build`
present and hash-identical, 0 missing, 0 changed**; textbuf is 44 of 44.
Toolchain installers re-verified afterwards and still hash-match the upstream
asset digests (§8).

**Two detections did occur**, 2–4 s before the scan completed, both outside this
repository and both quarantined at 22:31:53Z with `DidThreatExecute: False`:

| Threat | Severity | Path |
| --- | --- | --- |
| `Trojan:Win32/Suschil!rfn` (2147927547) | Severe | `...\scoop\cache\harfbuzz#14.5.1#ae19982.zip` |
| `HackTool:Win32/Keygen` (2147593794) | High | `E:\...\<third-party pack>\keygen.exe` and the same file inside `keygen.rar` |

**What this settles.** Under active protection, current definitions and no
exclusions, the same compiler, template and directory now produce
same-shaped artefacts that are not flagged, and a full-disk walk found nothing
in the build tree. That is the strongest available support for the §1
probable-false-positive grade, and it is the evidence the native lane was
missing. Nothing in §10 is relaxed: the two quarantined binaries remain
destroyed and unrebuilt, and the empty-literal variant in particular remains
untested. I did not change that.

**On the harfbuzz detection** (a text-shaping library, not copy-protection
grayware): `!rfn` is an internal Microsoft category, and `Suschil` is described
in published removal guides as a *heuristic/generic* Trojan detection with a
long public record of flagging legitimate release archives (WhyNotWin11,
OF-Scraper, fluux-messenger, tidal-dl-ng, PhotoMigrator). Three facts point the
same way: the *extracted* harfbuzz 14.5.1 binaries had been on disk for weeks
under RTP and were walked by this same scan without a hit — only the archive
was flagged; the Scoop main bucket pinned `cdd2f68…` for that version, so the
Scoop install-time hash check would have had to pass; and the archive is now
quarantined, so it could not be re-verified after the fact.

Correction to an intermediate reading of mine, recorded because it was wrong:
the `#ae19982` suffix in the Scoop cache filename is **not** a SHA-256 prefix.
Checked against other cached packages, the convention does not encode the file
digest, so that suffix carries no implication either way. My earlier suspicion
that it mismatched the pinned hash rested on a false assumption about Scoop
caching, not on evidence.

**On the keygen**: `HackTool:Win32/Keygen` is a taxonomy statement, not a
heuristic guess, and a keygen distributed inside a repack is a recognised
delivery vector for real malware. That is an owner risk decision rather than a
finding of this review; it is recorded because it belongs to the host security
picture, alongside the June/July `PUABundler` record.

**Cleanup — 2026-10-29T22:40Z, on owner instruction.** The downloaded repack
folder was removed in full: 2,217 files, 8.01 GB, permanent deletion rather
than recycle bin, verified absent afterwards with free space on `E:` rising by
8.02 GB. Confirmed beforehand that nothing depended on it — no installed
plugin, no SAGE library, no VST binary and no registry entry existed anywhere
on the host — so the deletion destroyed no working installation. The two
flagged files (`keygen.exe`, `keygen.rar`) had already been quarantined at
22:31:53Z, and the June/July `PUABundler` keygen was already absent, so this
removed the surrounding unused repack rather than any file this review treated
as evidence. Both threats remain `IsActive: False`.

The `harfbuzz` package itself was also uninstalled on owner instruction
(`scoop uninstall harfbuzz`, exit 0). No installed package depended on it, its
six shims were removed, the app directory and every cache entry are gone, and
`scoop list` no longer shows it. The `libharfbuzz-0` libraries and headers that
remain on this host are unrelated copies bundled inside other official
packages (`fontforge`, `gimp`) and were deliberately left alone.
## 16. Reproducibility test — the detection reproduces (2026-10-29T22:47Z)

Raising this because analysis of the lane showed the skip at
`tests/test_textbuf_native.py:617-624`: the test does **not** build the
empty-literal runner, on the belief that Defender "persistently blocks that
exact binary". That skip was the last unverified vector in the native lane, so
it was executed once, deliberately, in an isolated worktree.

Setup: RTP and tamper protection on, no exclusions, signatures 1.463.30.0. The
source was regenerated from the committed template with the `""` literal and
verified **byte-identical** to the quarantined source before building
(`725A933BC6D79AFD016D0D6787BFD8B5CAC37F4C3870D638D7D9DD8D330323A2`, 303
bytes). Committed flags, clang 23.1.4 (MSVC target) and MinGW GCC 16.2.0.

| build | binary | outcome |
| --- | --- | --- |
| clang | 128,000 B `0C383A7472E3DCC28EDB705C5E17BF2D7CE999B7868890858ED0646C08727E56` | **blocked at launch** ("the file contains a virus", the same class as the original WinError 225), `1116 Trojan:Win64/LummaC.NFD!MTB` at 22:47:37Z, re-detected on read at 22:47:53Z and **quarantined** |
| gcc | 55,101 B `1428556B57CF4C70A618BE7EDC4658C83889E9511A1C1F21B3DA8F7D3D715D98` | **ran clean**, exit 0, wrote the expected zero-byte file, not flagged |

### What this changes

1. **The detection is reproducible.** Same source, same documented compiler,
   fresh binary, current definitions, on demand. That is the opposite of
   compromise evidence: a trojaned toolchain would not faithfully rebuild a
   benign program into a flagging artefact, whereas a heuristic keyed to that
   artefact shape does exactly this. §7s paired non-detections are explained by
   the same mechanism — the trigger is the artefact, not the toolchain.
2. **§15 must be narrowed.** It recorded "no detection of any file under
   `D:\Projects`", which was true because the empty-literal runner was never
   built in that scan. The accurate statement is: hello/tricky/all256 runners
   under both compilers, and all 435 other build artefacts, are unflagged; the
   **clang** empty-literal runner is still detected and quarantined. The gcc
   build of the same program is not. The original asymmetry, therefore,
   reproduces exactly.
3. **The lane skip stays**, but its justification can be sharpened from
   folklore to measurement: this shape is detected reproducibly under
   1.463.30.0, and an exclusion would hide it rather than fix it.
4. **A false-positive submission is now genuinely worth making.** For the first
   time the package is complete: reproducible source, exact compiler and flags,
   and the binary SHA-256 above. The binary itself now sits in the Defender
   quarantine store, so submission would be Matthew action via Windows
   Security. Nothing was uploaded by this review.
5. **§1 confidence rises to ~90%** that the binary is benign and this is a
   persistent Defender heuristic problem, demonstrated from two independent
   builds seven hours apart. The heuristic trigger remains unidentified and is
   the one thing worth reporting upstream.

## 17. Native-lane clearance (recommendation, 2026-10-29T22:50Z)

Evidence base: §15 full scan clean with no detections in the repository;
`tests/test_a14_c23.py` 11/11 pass; `tests/test_textbuf_native.py` 21/22 pass;
the one failure is a CRLF expectation bug (§17 note); no exclusion in force;
toolchain hash-pinned to official upstream assets.

**Recommendation: clear the native lane.** Clang and GCC build-and-execute work
in `runtime/pep_text`, `runtime/pep_arena` and the A14 C23 emission path. Two
small items remain, and neither is security:

- `test_arena_demo_builds_and_runs` compares `b"42\r\n6\r\n"` against
  `b"42\n6\n"`. This is Windows CRT stdout text-mode translation, not a compiler
  or runtime fault, and it is a property of that one test — the other native
  tests compare bytes written through `fopen(..., "wb")` and are unaffected. It
  should be fixed by the lane owner. Do **not** fix it by normalising the
  comparison if byte-exactness is the invariant being protected; fix the
  expectation or write through a binary handle.
- The comment at `tests/test_textbuf_native.py:617-624` says a workspace
  exclusion "would re-enable" the skipped vector. Measurement now says that is
  the wrong trade: the exclusion hides a reproducible detection, and every other
  vector runs fine without one. The comment should carry the measured facts and
  the binary hash instead.

Status lines asserting an active hold (`runtime/pep_text/README.md:48`,
`runtime/pep_arena/README.md:39-40`) are now false and should be updated by the
lane owner. This review did not edit another lane files.
