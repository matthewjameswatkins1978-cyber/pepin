# ACCEPT BOOT-A3-026 — granted `byte_at` IS bounds-checked (my prediction was wrong)

**Verdict: SOUND. 21/21 checks, exit 0, both strict compilers.**

Pre-registration `ac5971a`, committed before the probe existed or ran, predicted **silent
out-of-range reads** for four cases. **That prediction was falsified, and in the good direction:**
every out-of-range `byte_at` traps with `PEP_RUNTIME_BYTE_RANGE`, exit 1, and prints no value.

I am recording this as a *falsified prediction*, not as a lucky pass. The value of the slice is the
correction: I believed the grant boundary was weaker than it is.

## Pins

| Item | Value |
|---|---|
| A3 | `codex/bootstrap-agent3-verification@ac5971a` (pre-registration) |
| Seam | A1 `a7d3ee1` + A2 `537967e`, merged cold, zero conflicts |
| Probe | `verification/probes/grant_byte_bounds_026.py` |
| Grant file | `examples/dogfood/input_ascii.pep` @ `12e143f` — 168 B, sha256 `7269de343494e4a1…` (committed LF bytes) |
| Compilers | Clang `-std=c23`, GCC `-std=c2x`, `-Wall -Wextra -Wpedantic -Werror -O2` |

## Mechanism, read from the emitted C (not inferred)

```c
static int64_t pep_byte_at(pep_source_bytes source, int64_t offset) {
  if (source.length != 0 && source.data == NULL) { fputs("PEP_RUNTIME_INVALID_SOURCE_BYTES\n", stderr); exit(1); }
  if (offset < 0 || (uintmax_t)offset >= (uintmax_t)source.length) { fputs("PEP_RUNTIME_BYTE_RANGE\n", stderr); exit(1); }
  return (int64_t)source.data[(size_t)offset];
}
```

Three things are right here and worth stating explicitly, because each is a place a bounds check
usually goes wrong:

1. **The negative case is tested before any promotion.** `offset < 0` is evaluated on the signed
   value, so `0 - 1` cannot become a huge `size_t` and slip through.
2. **The upper test promotes both sides to `uintmax_t`.** No sign-confusion bypass, and no
   truncation on a 64-bit `int64_t`.
3. **`pep_byte_length` has its own guard** (`PEP_RUNTIME_LENGTH_RANGE` above `INT64_MAX`), so the
   `length` used in the comparison is itself bounded.

## Cases

| # | Offset expression | In-bounds? | Clang | GCC | Result |
|---|---|---|---|---|---|
| B0 | `byte_at(source, 0)` on a real file | yes | stdout `102`, exit 0 | stdout `102`, exit 0 | matches independent Python read of the same bytes |
| B1 | `byte_at(source, 0 - 1)` | no | exit 1, stderr `PEP_RUNTIME_BYTE_RANGE` | same | **SOUND** (predicted silent read — **wrong**) |
| B2 | `byte_at(source, byte_length(source))` | no, one past end | exit 1, `PEP_RUNTIME_BYTE_RANGE` | same | **SOUND** (predicted uninitialised-byte read — **wrong**) |
| B3 | `byte_at(source, byte_length(source) + 1048576)` | no, far past end | exit 1, `PEP_RUNTIME_BYTE_RANGE` | same | **SOUND** (predicted heap over-read — **wrong**) |
| B4 | `byte_at(source, 0)` on an **empty** grant | no | exit 1, `PEP_RUNTIME_BYTE_RANGE` | same | **SOUND** (predicted read of the spare byte — **wrong**) |

B0 is the false-positive control: without it, four traps would be indistinguishable from a binary
that traps unconditionally. All four out-of-range programs **check `valid` with zero diagnostics**
and **emit normally** — the safety is a *runtime* guard, which is the correct layering for a
value the checker cannot know statically.

## Why this matters to the current mission

A4's application computes `byte_at(source, o - 1)`. It is correct because its own `o == 0` guard
holds — but it is *also* safe if that guard were ever wrong, because the runtime traps rather than
reading memory outside the granted buffer. The grant's trust boundary is therefore real at
`byte_at`, not merely conventional. That strengthens the acceptance story for the mission's
application rather than complicating it.

It also means an out-of-range scan bug in a future Pep-native capability will be **loud** (exit 1,
`PEP_RUNTIME_BYTE_RANGE` on stderr) rather than silently returning wrong numbers — which is the
distinction that makes agent-driven verification tractable at all.

## Not tested — stated, not implied

- The **interpreter** path (`pep.ps1 run`) for the same four cases: `run` refuses ungranted
  `source_bytes()`, so the comparison is not expressible the same way. **NOT TESTED.**
- Other source accessors (`utf8_slice`, and whatever a future capability adds): the guard above is
  specific to `pep_byte_at`. Whether every accessor carries an equivalent guard is **NOT TESTED**.
- Simultaneous multi-byte or slice-boundary arithmetic (`o - 1` inside `utf8_slice`): **NOT TESTED**.
- Adversarial offsets beyond `INT64_MAX` or a `length` near `INT64_MAX` on a real allocation:
  **NOT TESTED** (needs an allocation I cannot honestly construct here).
- Whether a *malicious* `pep_source_bytes` can be constructed through the normal host path is out of
  scope; the epilogue builds it from `fopen`/`ftell`/`fread`, which I did not attack here.

## Reproduce

```powershell
git worktree add --detach <tmp> a7d3ee1; git -C <tmp> merge --no-commit --no-ff 537967e
cd <tmp>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<tmp>'
python verification/probes/grant_byte_bounds_026.py     # 21/21, SOUND
```

## Scope

A3 changed only `verification/**`. Nothing raised, nothing frozen altered, no `CURRENT`/manifest/
master/release change, peer worktrees read-only. A3 does not propose a fix because none is needed
here — the finding is that the existing guard is correct.

REF: GH #16 (BOOT-A3-026).
