# `pep test` — first-party Pep test runner (Road 2 V8, slice 1)

Runs real Pep fixtures through Pep's actual compiler and interpreter.
The runner never interprets Pep itself: every verdict comes from
`pep.ps1 check --json` / `pep.ps1 run`.

## Usage

```powershell
.\pep.ps1 test                                   # whole manifest, human output
.\pep.ps1 test --json                            # machine-readable JSON document (contract: results-schema.json)
.\pep.ps1 test --filter reject                   # only fixtures whose id contains SUBSTR
.\pep.ps1 test --timeout 30                      # per-phase seconds override
.\pep.ps1 test --manifest path/to/manifest.json  # alternate manifest
.\pep.ps1 test --backend interpreter,clang,gcc   # native differential (NATIVE-DIFFERENTIAL.md)
.\pep.ps1 test --backend clang --compiler-clang C:\path\to\clang.exe
```

Exit code: `0` when every executed test passes, skips or is a declared
`unsupported`, `1` when any test fails, diverges, errors or times out,
`2` for infrastructure problems — missing or malformed manifest, empty
fixture selection, an unavailable native compiler, or any fixture that
could not be evaluated at all (`infra_error`). Exit 2 means the run
cannot vouch for a case, which is not the same as a test failing. A
`--filter` that matches nothing, or a manifest with no fixtures, fails
loudly instead of reporting a vacuous all-green run.

Each executed test writes per-test evidence artifacts (`check.json`,
`stdout.txt`, `stderr.txt` under `--evidence-dir`, default
`_build/pep-test-evidence/<UTC timestamp>/`); paths are recorded in the
JSON result alongside the inlined values.

`--list` prints the declared fixtures (id, kind, file, skip reason)
without executing them — the discovery query other tools can rely on.

Fixtures are LF-canonical: `test-runner/fixtures/.gitattributes` marks
`*.pep` as `-text` so `core.autocrlf` cannot rewrite them on checkout.
Manifest spans are byte offsets into those exact bytes, so a CRLF copy
would shift them; the runner refuses such a fixture as `infra_error`
instead of reporting a misleading span mismatch.

## Standard-library conformance

`stdlib-conformance/` drives this runner to check the standard library against a
public-behaviour contract, composing the real library source with one caller per
case. See [../stdlib-conformance/README.md](../stdlib-conformance/README.md).

## Fixture manifest

See [MANIFEST-SCHEMA.md](MANIFEST-SCHEMA.md). Fixtures are explicit:
no `test {}` grammar or `std.test` APIs until their contracts are accepted.

## Outcome taxonomy

`pass` · `fail` (assertion or expected-rejection mismatch) · `divergence`
(native backends disagreed with each other) · `unsupported` (declared C23
unsupported subset, confirmed on every native backend) · `compile_error`
· `runtime_error` · `timeout` · `infra_error` · `skip` · `policy_denied`
(reserved: no current `run` surface triggers a host-grant refusal, but the
Road 2 V8 gate requires the category distinct so a future enforcing backend
plugs in without a schema break).

A crash, timeout, transport failure, or malformed compiler output NEVER
counts as a pass — not even for negative fixtures. A `reject` fixture
passes only when `check --json` parses AND reports `status: invalid`
with exactly the expected diagnostic `code` (and `span`, when given).

## Evidence recorded

Per test: source SHA-256, executed command, elapsed seconds, exit code,
captured stdout/stderr, parsed diagnostics. Per run: repo revision,
selected `backends`, toolchain (compiler source SHA-256), manifest
path, and pass/fail/error/skip counts. JSON output carries the full
document; it is the integration surface for the external Terror Bats
adapter (see PEP-DEC-008T: execution status and verdict stay separate;
a passed test is evidence for that case, never universal proof).

## Current limitations (slice 1)

- Native differential covers the C23 subset documented in
  [NATIVE-DIFFERENTIAL.md](NATIVE-DIFFERENTIAL.md): `fn main() -> Int`
  arithmetic, calls and `if`/`else`, plus runtime guards. Records,
  variants, `for`-in, `var`/`while` and `Unit` main are declared
  unsupported and asserted as such — never silently skipped.
- No property testing, shrinking, or concurrency adversaries.
- Manifest lists files explicitly; no compiler-discovered test blocks.
- Timeouts bound each CLI phase; runaway compiler builds are bounded
  but not incrementally cancellable.
- Fixture spans are byte-exact for the current compiler; a diagnostic
  wording/span change fails the fixture loudly rather than silently.
