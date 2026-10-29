# Tool hot-replacement (V0 set 14 — registry lifecycle, part 2)

All observations via `pep.ps1 session --jsonl` (v1, OCaml
in-process session) from base `805062b`. Tool `dt` wraps
`fn f(n: Int) -> Int`; v1 body `n + 1`, v2 body `n + 100`
(via `apply_edit` on bytes 29–34), broken variant via `@@@` splice.

## H1 — successful replacement is atomic

Register v1 → validate (`21 → 22`) → activate → invoke `21` →
`TESTED`: `22`. Edit the tool source (`+1` to `+100`, revision
advances) → re-register same tool name on the new revision →
validate (`21 → 121`) → `Validated` → activate → `Active` →
invoke → `TESTED`: `121`. `tool_list` shows exactly two entries for
`dt`: `Active` (new revision) and `Superseded` (old revision).
The swap is atomic: no window serves a half-replaced tool, and the
superseded entry is retained for provenance rather than deleted.

## H2 — failed replacement leaves the active entry serving

Activate v1, then break the tool source (`@@@` splice → invalid new
revision): re-register on the broken revision → `TESTED`: `Rejected`;
validate → `TESTED`: `Rejected`. `tool_invoke` → `TESTED`: still
`22` — the last good active entry keeps serving. `tool_list` shows
the `Rejected` attempt alongside the untouched `Active` entry.
A bad replacement can neither displace nor corrupt the running tool.

## Status

No findings. Registration, validation, activation, invocation,
atomic replacement, and failed-replacement isolation all behave per
the protocol contract on the seed path. v2 `semanticTarget`-bound
replacements (compiler-owned tools) were not separately exercised.
