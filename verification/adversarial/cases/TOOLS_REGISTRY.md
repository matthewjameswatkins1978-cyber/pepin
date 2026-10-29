# Local tool registry trust boundary (V0 set 10 — A5 surface)

All observations via `pep.ps1 session --jsonl` (schema v3,
`toolProtocolVersion: 1`, OCaml in-process session) from base `805062b`.
Programs: `fn double(n: Int) -> Int { return n + n }` (+ trivial main)
and `fn loud(s: Str) -> Str { say(s) return s }`.

## T1 — happy path: register → validate → activate → invoke

| step | observed |
|---|---|
| `tool_register(double)` | `TESTED` — outcome `ok`, status `Registered`, `callable: false`, checker-derived signature `([Int] -> Int)` |
| `tool_validate` vector `21 → 42` (real interpreter run) | `TESTED` — outcome `ok`, status `Validated`, still `callable: false` |
| `tool_activate` | `TESTED` — outcome `ok`, status `Active`, `callable: true` |
| `tool_invoke(21)` | `TESTED` — outcome `ok`, typed result `{"type":"Int","value":"42"}`, bound to the immutable document revision |
| `tool_list` | `TESTED` — reports entry with protocol version, status, signature, `activeRevision`; callable flag follows state |

Callable is a state, not a property: only `Active` entries execute.

## T2–T5 — every boundary fail-closed with a dedicated code

| probe | observed |
|---|---|
| validate with failing vector (`21 → 43`) | `TESTED` — outcome `rejected` |
| invoke with wrong arg type (`Str` for `Int`) | `TESTED` — `error`, `PEP_TOOL_ARGUMENT_TYPE` |
| invoke with wrong arg count (2 for 1) | `TESTED` — `error`, `PEP_TOOL_ARGUMENT_COUNT` |
| invoke unknown tool name | `TESTED` — `error`, `PEP_TOOL_NOT_ACTIVE` |
| activate without validation | `TESTED` — `error`, `PEP_TOOL_NOT_VALIDATED` ("Only a successfully validated tool can be activated") |
| register `say`-reaching function | `TESTED` — registers (signature derived), but validation ends `Rejected`: "Exported function reaches say and is not permitted for tool execution" |

The host keeps its promise: no filesystem/network/process surface, no
`say` through tools (blocked at both reachable-call validation and the
interpreter runtime check per the protocol doc), typed scalar boundary
only, revision-bound invocation. Tool execution runs under the 100,000
step / 128 depth tool budget (not separately stressed here).

## Invoke requires Active — Registered and Rejected are not enough

- Registered-but-never-validated tool invoked → `TESTED`: `error`, `PEP_TOOL_NOT_ACTIVE`. The middle state is not callable either; only `Active` executes (completing the T-set's callable-only-when-Active ladder).
- Broken-source tool: register → `rejected` ("Source is invalid and has no checked function signature"); validate → `rejected` ("Source is invalid and cannot be validated"); invoke → `TESTED`: `error`, `PEP_TOOL_NOT_ACTIVE`. An invalid bundle yields no activatable tool at any step.

- Incomplete (holey) source tool: registers fine (signature is derivable), but validation is refused. No holey program can ever become callable. (The rejection message names activation while surfacing at validation — a cosmetic mismatch in an otherwise correct fail-closed path.)

## Status

No findings. This closes the A5 tool-registry surface at the v1 protocol layer on the seed path. v2 typed transport, host grants, semantic snapshots, and the Pep-written checker/driver use of these ops are covered in the V-set, G-set, SN-set and X-set case files; native execution stays `BLOCKED_SECURITY`. (Validation diagnostics observed: wrong *type* in expect → `PEP_TOOL_ARGUMENT_TYPE`; wrong *value* with correct types → `PEP_TOOL_TEST_FAILED` ("Interpreter result did not match the expected test vector").)
