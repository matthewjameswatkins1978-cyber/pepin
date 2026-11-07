# ACCEPT BOOT-A3-040 — line-scan now meets the packet's full acceptance shape, guards included

**Verdict: PROVEN, 49/49.** `pepin-line-scan` now has every element the packet's first acceptance gate
lists: a documented Pep source under `examples/dogfood/`, a native build over **six** genuinely
different real files including a **NUL-sensitive** edge, an independent reference with byte provenance,
strict Clang **and** GCC in both assembly orders, and an independent A3 gate **including
intentionally malformed/incomplete fact cases**.

**Scope, unchanged:** this is A4's **second** program. The mission's named target
`pepin-source-scan.pep` (blob `4a44dd65…`) still has **no native result** — it is blocked on emitter
capacity (BOOT-A3-038/039). Nothing here promotes line-scan or changes the target.

## Pins

| Item | Value |
|---|---|
| A2 emitter | `4b70c61`, blob `3f5b9582` (identical at A1 `4e325e0`/`86ff953`) |
| App | `pepin-line-scan.pep` @ A4 `36934a6`, 998 B, sha256 `12d4b1ab…` |
| Tree gated | fresh detached worktree at A1 `86ff953`, seed built there |
| New fixture | `verification/fixtures/line-scan/nul_sensitive.bin`, 9 B, `61 00 62 0a 63 00 0a 64 0a` |

## The NUL-sensitive edge — predicted 3, measured 3 on every build

Pre-registered prediction: `a\0b\nc\0\nd\n` (9 bytes, **2 NULs**, **3 LFs**) must report **3**. A
scanner that stopped at NUL would say 1; one that counted NUL as LF would say 5.

| fixture | bytes | expected | oracle | Clang d/p | GCC d/p |
|---|---|---|---|---|---|
| `nul_sensitive.bin` | 9 | 3 | 3 | **3/3** | **3/3** |
| `input_ascii.pep` | 168 | 3 | 3 | 3/3 | 3/3 |
| `input_nonascii.pep` | 218 | 5 | 5 | 5/5 | 5/5 |
| `input_empty.pep` | 0 | 0 | 0 | 0/0 | 0/0 |
| `pepin-source-scan.pep` | 1159 | 39 | 39 | 39/39 | 39/39 |
| `pepin-line-scan.pep` | 998 | 32 | 32 | 32/32 | 32/32 |

Metamorphic: one binary, six files, six distinct answers `3, 5, 0, 39, 32, 3`. Missing path → exit 1,
empty stdout, `PEP_RUNTIME_SOURCE_OPEN`; no argv → `PEP_RUNTIME_SOURCE_CONTEXT`.

**The NUL case matters because it is the input class that would silently truncate a naive scanner**,
and it is the one the packet explicitly asks for.

## Malformed / incomplete fact cases — and one honest "not applicable"

| case | result |
|---|---|
| **M5 false-positive control**: the honest report on its own target | **emits**, 474 C bytes — without this the refusals below would be vacuous |
| **M4 stale revision**: honest report against a different valid target | **`PEP_STALE_REVISION`** |
| **M6 forged fingerprint**: `syntaxNodeCount` rewritten to 999999 | **refused** — *"Pep C23 emission inputs do not match the authorised source revision"* |
| M1 stripped call facts / M2 severed `calleeId` / M3 forged arity | **NOT APPLICABLE** |

**M1–M3 are structurally inapplicable to this program, and I am not going to dress that up as a pass
or a fail.** Line-scan's `main` calls only **builtins** (`byte_length`, `byte_at`), so it carries
**zero** cross-chunk `ResolvedCall` facts — measured: 0. A fact that does not exist cannot be stripped,
severed or forged. Those three cases are about *cross-chunk calls*, which the frozen app has
(`ascii_letter`, `ascii_continue`) and line-scan does not.

So the packet's "intentionally malformed/incomplete fact cases" is satisfied here by **two applicable
tamperings plus a control**, with the inapplicable three named and explained rather than faked.

## What this does and does not establish

**Does:** for the one program that runs natively, the packet's full acceptance shape is now evidenced —
source, native build, six file classes including NUL, independent reference, byte provenance, both
compilers, both assembly orders, fail-closed path negatives, and a fact-gate with real tamperings and a
control.

**Does not:** the mission's named target. `pepin-source-scan.pep` is still unproven natively and this
receipt does not move it. It also does not establish emitter capability in general — one program shape.

## Not tested

- The frozen app's M1–M3 equivalents: still blocked behind its emission refusal, so still `NOT TESTED`
  there (BOOT-A3-025/027 recorded the same).
- Cross-chunk-call tampering for a *third* program with mixed builtin and cross-chunk calls; line-scan
  cannot exercise it.
- Multi-byte or larger inputs beyond the six above; no fuzzing.
- One seed build, one machine; `-O2 -Werror -std=c23` / `-std=c2x` only.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
$env:PEPIN_GATE_ROOT = '<t>'
python verification/probes/line_scan_gate_034.py     # 49/49 PROVEN
```

## Scope

A3 changed only `verification/**`. A1's checker/contract, A2's emitter and A4's app were read, not
modified. Cap unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-040).
