# V0 evidence ledger — independent baseline (Agent 3)

**Worktree/branch:** `D:/Projects/pepin/_build/bootstrap-agent3-verification`,
`codex/bootstrap-agent3-verification`, base = HEAD = `805062b`
(= `origin/campaign/pep-v01-sustained-build-20261027` at pin time).
**Reviewed pins (read-only):** Agent 1 `codex/bootstrap-agent1-b0@95ab6c6`,
Agent 2 `codex/bootstrap-agent2-b0@52f1b38`.
**Method:** source inspection + OCaml-interpreter probes only. No builder
file edited. B0 closure JSON reused read-only from Agent 1 branch as
`verification/receipts/B0-closure-agent1-95ab6c6-READONLY.json`
(sha256 `ec46300d...fd756c`, full file).

## Truth matrix (accepted spec vs actual code, 2026-10-29)

| # | feature | accepted (final draft) | seed/actual state | evidence status |
|---|---|---|---|---|
| 1 | value independence (DEC-001) | §4: copies are independent logical values | holds on OCaml for `List`/records via `append`/`var` (P1–P3) | `TESTED` (interpreter); C23 `BLOCKED_SECURITY` |
| 2 | `read/edit/take` (DEC-002) | §5: explicit modes | `edit` rejected at parse (`PEP_PARSE_EXPECTED`, N2) | `TESTED`; gap, not defect |
| 3 | types Int/Bool/Str/Unit, List[T] (DEC-005) | §4 | implemented; `contains` scalar-only, nested fail-closed (N3) | `TESTED` |
| 4 | records/unions/match (A4) | §4, §10 | implemented in seed + A13 differential suites (46–48/48 per A1 receipts) | builder-reported; Agent 3 `NOT_RUN` (A1-owned harness needs generated executable) |
| 5 | checked arithmetic faults | seed facts | `PEP_RUNTIME_DIVISION_BY_ZERO` with span, exit 1 (N4) | `TESTED` |
| 6 | holes block execution | seed facts | `incomplete` + run refusal (N1) | `TESTED` |
| 7 | C23 lowering (Agent 2) | TR002 C23 backend | scalars only; no records/unions/List/Str (B0 peerEvidence) | builder-reported, source-only; native `BLOCKED_SECURITY` |
| 8 | limits | 65536 source bytes, 100k tool steps, 128 depth, 1M interp steps | from B0 `resourceLimits` + `describe` | source-stated, `UNVERIFIED` (unmeasured) |
| 9 | Lean value model (V1) | mission workstream V1 | sources written, `leanprover/lean4:v4.35.0` pinned | `DRAFT` / `BLOCKED_SECURITY` (receipt) |
| 10 | Defender hold | `SECURITY_2026-10-29_DEFENDER.md` | Severe/Trojan quarantine, hold in force, no restores/exclusions by Agent 3 | acknowledged; no native execution |

## Independent reproductions this slice

- P1/P2/P3 value-copy probes: `TESTED` PASS on OCaml seed (exact commands in case file).
- N1–N4/E1 edge probes: `TESTED` (statuses/diagnostics recorded in case file).
- `py_compile` of nothing new (no Python harness added this slice); `git diff
  --check` to run pre-commit.

## Peer-review position (narrow, SHA-bound)

- A1@95ab6c6 (`str_contains` + single-pass `collect_functions`): no independent
  execution (differential harness needs the generated executable under hold).
  Source-level read found no contradiction with the stated contract (UTF-8
  byte substring, empty-needle match, NUL support); claim remains
  builder-reported until execution is cleared. No finding filed.
- A2@52f1b38 (scalar record C23 source lowering): independent re-run of the
  Python-only source-emission test at the pinned SHA is scheduled next slice
  (safe: `emit` + in-memory inspection, no C compiler). No finding filed.
- No blanket verification is claimed from this ledger.

## Unresolved coverage

Stale/forged revision identity, source-vs-fuel limits, B4/B5 lineage
scrutiny (V2/V3). Lean kernel check awaits an approved safe host
(BLOCKED_SECURITY receipt). UTF-8/CRLF spans and the A2 emitter re-run
landed this slice: see `adversarial/cases/UTF8_SPANS.md` (U1–U5 TESTED,
E2 byte-derived columns recorded) and
`receipts/A2-emitter-rerun-52f1b38.md` (3/3 TESTED at emit layer).
