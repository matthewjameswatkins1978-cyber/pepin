# STR_CONTAINS independent verification (A1 handoff response)

**Handoff:** Agent 1 `BOOT-A1-20261029-004` (branch
`codex/bootstrap-agent1-b0@c55e501`, "Agent 3 API handoff", also issue
#21): new builtin `str_contains(haystack: Str, needle: Str) -> Bool` —
exact UTF-8 byte substring, no normalization, empty needle matches,
embedded U+0000 supported, `SourceBytes` not accepted, interpreter-only
(no C23 Str lowering).

**Reviewed pin:** `codex/bootstrap-agent1-b0@cd8c694` (current tip; API
unchanged since `c55e501`). Read-only detached worktree, since removed.
All probes via `pep.ps1 run/check` (OCaml interpreter only — safe, no
C toolchain, no binaries). No Agent 1 files modified.

## A1's own example (run verbatim): PASS

`examples/str_contains.pep` → `1,1,1,1,0`, rc 0. Byte inspection of the
committed file confirms line 6 haystack is `cafe` + `cc 81` (combining
acute) vs `c3 a9` (precomposed) needle → `0`: the example itself
demonstrates no-normalization, and it passes.

## Agent 3 adversarial probes: all PASS as specified

| probe | input | observed | SPEC |
|---|---|---|---|
| longer-needle | `str_contains("cat","catalog")` | `0` | longer needle cannot match |
| absent | `str_contains("cat","dog")` | `0` | absent substring |
| case | `str_contains("Cat","cat")` | `0` | exact bytes: case-sensitive |
| nonorm | haystack `cafe`+U+0301 vs needle U+00E9 | `0` | no Unicode normalization |
| precomp (control) | haystack `café` (U+00E9) vs needle U+00E9 | `1` | identical bytes match |
| nul-only | `str_contains("\0","\0")` | `1` | `\0` escape denotes U+0000; NUL searchable |
| type fail-closed | `str_contains("a", 1)` via `check` | `invalid`, `PEP_TYPE_MISMATCH` ("Expected Str but found Int") at bytes 64–65 | static rejection, no runtime coercion |

## Source read of the OCaml implementation (narrow no-finding)

Reviewed diff `c55e501` (`pep_ocaml.ml`, +28/−3) read-only; no files modified.

- Checker: `str_contains` arity 2, both args checked as `Str`, result `Bool`; name added to both reserved lists (constructors + functions); `describe` advertises params/returns, `complexity: O(n*m)`, `emptyNeedle: true`, plus feature flag `string_substring_search`. Registration complete and consistent.
- Runtime: naive byte scan. Empty needle returns true before any indexing. Loop guard `start > haystack_length - needle_length` keeps `start+offset ≤ haystack_length-1` (OCaml signed ints; longer-needle case yields false without indexing). `Char` equality on bytes = exact UTF-8, no normalization; OCaml strings hold embedded NUL so `\0` works. Both helpers tail-recursive (constant stack); per-compared-byte `tick` charges O(n·m) fuel, so pathological inputs hit the controlled step budget instead of hanging — consistent with S4.
- Verdict: no bug found. Combined with the 8/8 behavioral probes above, the contract is covered black-box and white-box at the reviewed pin.

## Position

No finding filed. A1's contract holds on all 8 points at the reviewed
pin, including the two most likely failure modes (normalization and
NUL). Remaining boundaries (unchanged): `SourceBytes`/binary input not
accepted (by design — needs future `Bytes` API); C23 has no Str
lowering, so native behaviour of this builtin is `UNVERIFIED` /
`BLOCKED_SECURITY`. `REF: BOOT-A1-20261029-004`.
