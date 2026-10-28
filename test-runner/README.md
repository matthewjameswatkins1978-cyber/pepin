# `pep test` — first-party Pep test runner (Road 2 V8, slice 1)

Runs real Pep fixtures through Pep's actual compiler and interpreter.
The runner never interprets Pep itself: every verdict comes from
`pep.ps1 check --json` / `pep.ps1 run`.

## Usage

```powershell
.\pep.ps1 test                                   # whole manifest, human output
.\pep.ps1 test --json                            # machine-readable JSON document
.\pep.ps1 test --filter reject                   # only fixtures whose id contains SUBSTR
.\pep.ps1 test --timeout 30                      # per-phase seconds override
.\pep.ps1 test --manifest path/to/manifest.json  # alternate manifest
```

Exit code: `0` when every executed test passes or skips, `1` when any
test fails/errors/times out, `2` for runner infrastructure problems
(missing or malformed manifest).

`--list` prints the declared fixtures (id, kind, file, skip reason)
without executing them — the discovery query other tools can rely on.

## Fixture manifest

See [MANIFEST-SCHEMA.md](MANIFEST-SCHEMA.md). Fixtures are explicit:
no `test {}` grammar or `std.test` APIs until their contracts are accepted.

## Outcome taxonomy

`pass` · `fail` (assertion or expected-rejection mismatch) · `compile_error`
· `runtime_error` · `timeout` · `infra_error` · `skip`.

A crash, timeout, transport failure, or malformed compiler output NEVER
counts as a pass — not even for negative fixtures. A `reject` fixture
passes only when `check --json` parses AND reports `status: invalid`
with exactly the expected diagnostic `code` (and `span`, when given).

## Evidence recorded

Per test: source SHA-256, executed command, elapsed seconds, exit code,
captured stdout/stderr, parsed diagnostics. Per run: repo revision,
backend (`interpreter`), toolchain (compiler source SHA-256), manifest
path, and pass/fail/error/skip counts. JSON output carries the full
document; it is the integration surface for the external Terror Bats
adapter (see PEP-DEC-008T: execution status and verdict stay separate;
a passed test is evidence for that case, never universal proof).

## Current limitations (slice 1)

- Single interpreter backend only; no native (C23) differential yet.
- No property testing, shrinking, or concurrency adversaries.
- Manifest lists files explicitly; no compiler-discovered test blocks.
- Timeouts bound each CLI phase; runaway compiler builds are bounded
  but not incrementally cancellable.
- Fixture spans are byte-exact for the current compiler; a diagnostic
  wording/span change fails the fixture loudly rather than silently.
