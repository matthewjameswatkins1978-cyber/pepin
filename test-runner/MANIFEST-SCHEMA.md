# Test-runner manifest schema v1

JSON object:

```json
{
  "schemaVersion": 1,
  "runner": "human label, ignored",
  "fixtures": [ <fixture>, ... ],
  "limits": { "timeoutSeconds": 120 }
}
```

## Fixture

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable unique name, e.g. `pass/add`. `--filter` matches substrings of it. |
| `file` | yes | `.pep` path relative to the manifest directory. |
| `kind` | yes | `run` \| `reject` \| `check`. |
| `expect` | for run/reject | See below. |
| `timeoutSeconds` | no | Per-phase override. Falls back to `--timeout`, then `limits.timeoutSeconds` (default 120). |
| `skip` | no | String reason. The fixture is recorded `skip` and never executed. |

## `expect` by kind

- `run`: `{ "exit": 0, "stdout": "42\n" }`. Both must match. For a
  *deliberate* failure demo, `exit` may be nonzero with
  `"diagnosticCode": "PEP_RUNTIME_..."`; the test passes only when the
  exit, stdout, and code all occur exactly as specified.
  `"match"` selects stdout comparison: `"exact"` (default, byte equality),
  `"contains"` (substring), or `"regex"` (Python `re.search`). Use
  `contains`/`regex` for nondeterministic fragments (timings, paths);
  keep `exact` whenever output is deterministic. Unknown modes and bad
  regexes are `infra_error`, never passes.
- `reject`: `{ "code": "PEP_TYPE_MISMATCH", "span": {...} }`.
  Passes only when `check --json` parses, reports `invalid`, and the
  first diagnostic carries exactly this `code`. `span` is optional;
  when present, only the listed keys are compared
  (`start.offset/line/column`, `endOffset`).
- `check`: `{}`. Passes when `check --json` reports `valid`.

Anything else — valid program in a `reject` fixture, wrong code,
stdout mismatch, crash, timeout, missing file, non-JSON compiler
output — is `fail`, `compile_error`, `runtime_error`, `timeout`, or
`infra_error`, never `pass`.
