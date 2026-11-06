# BOOT-A3-005: source-ingress + byte-cap boundary re-pinned on Candidate7 `6dce37d` (Agent 3)

**Seat:** Agent 3. Detached read-only scratch `D:/Projects/wt-a3-ingress` @ `6dce37d`
(removed afterwards). Unmodified probes from my tree @ `7ffa287`:
`verification/probes/open_bytes_limit.py`, `verification/probes/source_ingress_negative.py`.

## Results (exact)

- **open_bytes_limit: 2/2, falsified=0.** 65,536 bytes open `ok`; 65,537 refused
  with `PEP_SOURCE_BYTE_LIMIT` ("Source byte input exceeds 65536 bytes").
- **source_ingress_negative: 4/4, falsified=0.** G0 honest complete parse `valid`;
  G1 stale parse refused (provenance code); G2 unfinished continuation refused with
  `A13_PARSER_BUDGET` (stamps match, done=false — reaches Pep code as registered);
  G3 foreign-document parse refused (provenance code).

## Use

- Pins the current source-grant/ingress contract on the candidate for A2's upcoming
  SourceBytes/native-grant slices (`byte_at`/`byte_length`/`utf8_slice` lowering,
  `source_bytes()` target-grant): grants are document+revision bound, unfinished parses
  fail closed in-language, oversize ingress fails at the session boundary. No new
  builder SHA observed (A1 `1aaead7`, A2 `6f7d72d`, candidate impl `6dce37d` unchanged);
  prior verdicts stand. A3 remains on standby for re-gate triggers.

## Reproduce

```powershell
git worktree add --detach D:/Projects/wt-a3-ingress 6dce37da8930bdb4b0f5ba410c8042f23110545d
python verification/probes/open_bytes_limit.py D:/Projects/wt-a3-ingress        # 2/2
python verification/probes/source_ingress_negative.py D:/Projects/wt-a3-ingress # 4/4
```
