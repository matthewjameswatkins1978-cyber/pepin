# Platform inventory (V0 set 20 — oracle surface pin)

`pep.ps1 describe --json` at base `805062b`, recorded so the corpus's
own oracle surface is pinned, not assumed. If the seed surface moves,
replay failures here explain downstream ones.

## Pinned surface (TESTED, exact match)

- `language`: `"Pep"`.
- `types`: exactly `["Int", "Bool", "Str", "SourceBytes", "Unit"]`
  (`List[T]` is parametric, listed separately — not a flat type).
- `builtins` (12, by name): `append`, `byte_at`, `byte_length`,
  `byte_slice`, `contains`, `int_text`, `length`, `prepend`,
  `reverse`, `say`, `source_bytes`, `utf8_slice`.
  **Notably absent at this base: `str_contains`** — the A1-branch
  builtin my STR_CONTAINS.md covers at the A1 tip. The corpus's two
  baselines (seed base vs A1 tip) are therefore explicit, and any
  future base that gains builtins will fail this pin loudly.
- `runtime`: `maxSteps: 1000000`, `maxCallDepth: 512` (the budgets
  behind S4/S5).
- `session.operations`: open, open_bytes, query, inspect, apply_edit,
  fill_hole, tool_register/validate/activate/list/invoke, metrics
  (every op the corpus exercises, present).
- `session.toolProtocolVersions`: `[1, 2]` (both lanes covered:
  T/H-sets on v1, V/G/SN-sets on v2).

## Status

No findings. This is a pinned inventory, not a behavior probe: it
locks the platform assumptions every other case file runs on.
