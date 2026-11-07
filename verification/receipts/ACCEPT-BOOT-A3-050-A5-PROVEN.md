# ACCEPT BOOT-A3-050 — A5 is now PROVEN, with its scope stated honestly

**Verdict: the last unproven criterion in the bootstrap auditor is now proven effective.** BOOT-A3-044
shipped the auditor with A5 (no forbidden subprocess) marked *implemented but unproven*, because
script-based controls cannot exercise PATH stripping on Windows. A native-exe control fixes that.

## Why script controls could never test A5

The launcher for a script control **is** the interpreter, and Windows `CreateProcess` searches the
**application directory** first. So `python` is found beside the launcher no matter what `PATH` says, and
A5 passes vacuously. That was recorded as a limitation, not fixed.

## The control that proves it

A small **native exe** (`cheat_exe`, compiled by Clang in `_build`) that shells out to `python` **by name**,
writes a marker if the interpreter ran, and embeds the result in its emitted C:

```c
int rc = system("python -c \"open('cheat_marker.txt','w').write('ok')\"");
/* ... */ printf("/* interpreter_ok=%d */\n", ok);
```

Measured result:

```
=== control: cheat_exe (expected FAIL) ===
  PASS  A1:divergence        identical=False      <- it really does produce input-dependent C
  PASS  A2/A3 builds+semantics (clang & gcc)      <- and the C is valid and correct
  FAIL  A4:invalid_*         exit=0 emitted=80B   <- and it wrongly accepts invalid input
  FAIL  A5:no-forbidden-subprocess   exit=0 same_output=False
```

**`same_output=False` is the proof:** the cheat still ran (exit 0) but its emitted C **changed** once
`PATH` was stripped, because its `python` helper was no longer findable. A5 detects exactly the intended
failure mode and does not detect it vacuously.

## Non-vacuity, all four checks

| check | status |
|---|---|
| P1 fixed-C printer rejected (A1) | **PASS** |
| P2 input-dependent control accepted (all six) | **PASS** |
| P3 native-exe cheat caught by A5 | **PASS** |
| P4 documented blind spot: absolute interpreter path evades A5 | **CONFIRMED (expected)** |

## The scope statement that must travel with A5

A5 proves **"no PATH-dependent helper"**. It does **not** prove "no subprocess":

- an **absolute** interpreter path evades it — demonstrated by the `cheat_abs` control, confirmed expected;
- `PATH` stripping is not a sandbox;
- script-based candidates can never be tested by it at all.

Any A5 PASS in a future audit report will be worded that way, not as "no forbidden subprocess".

## What this changes for the mission

The auditor is now validated on **all six criteria** for a command-shaped candidate, which is what will
judge the first R or S spike. Nothing about the mission's blockers changed: a compiler-shaped function
still cannot be emitted (BOOT-A3-045, corroborated on A4's own artifact in BOOT-A3-049), `utf8_slice` is
still not a lowered builtin (A3-043), and no list indexing exists (A3-046).

## Honest limits

- The proven scope is a **native exe shelling out by name**, which is the realistic cheat; a hard-coded
  absolute interpreter path remains undetectable by this criterion.
- A5 says nothing about a compiler hidden *inside* the same binary (no subprocess at all) — the mission's
  "compiler hiding in the host" risk is only partially addressed by any subprocess check, and I cannot
  detect that with instruments available to me.

## Reproduce

```powershell
python verification/probes/bootstrap_audit.py --self-test     # P1-P4, A5 PROVEN
```

## Scope

A3 changed only `verification/probes/bootstrap_audit.py`. No edits to A1's checker/contract, A2's emitter,
A4's app. Cap unchanged; no `CURRENT`, manifest, frozen-gate, master or release change.

REF: GH #16 (BOOT-A3-050).