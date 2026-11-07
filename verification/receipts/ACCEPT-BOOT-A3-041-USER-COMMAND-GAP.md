# ACCEPT BOOT-A3-041 — there is no user-facing command that can run these apps, for two reasons

**Verdict: my U1/U2 predictions held; U3/U4 revealed something more fundamental than I expected.**

Two independent gaps stand between "the application runs natively" and "a user can run it":

1. **No CLI path grants file bytes to `main(source: SourceBytes)`.** The documented option does not exist.
2. **The CLI's one-shot whole-program check exceeds the 100k budget on these programs** — including
   `pepin-line-scan`, which my probes proved runs natively through the chunked path.

So every PROVEN result so far (line-scan 49/49) was obtained through an **A3 probe harness** speaking
the session protocol directly. That is not a command a user can type.

## Evidence, verbatim

Tree: clean worktree at A1 `86ff953`, seed built there. Nothing edited.

**U1 — help advertises no grant option.** Grep of `pep.ps1 --help` for `grant` returns **nothing**.

```
.\pep.ps1 build-c23 FILE --output EXE [--compiler PATH] [--emit-c FILE]
.\pep.ps1 run-c23 FILE [--compiler PATH] [--emit-c FILE]
```

**U2 — the exact command from A4's `SPEC.md` fails:**

```powershell
.\pep.ps1 run-c23 examples/dogfood/pepin-source-scan.pep --grant-file examples/dogfood/input_ascii.pep
```
```
pep.ps1 build-c23/run-c23: error: unrecognized arguments: --grant-file examples/dogfood/input_ascii.pep
exit=2
```

**U5 — same for `build-c23 --grant-file`:** `unrecognized arguments: --grant-file …`, exit 2.

**U3 — `run-c23` on the frozen app, no grant option** → refuses during **check**, not emission:

```
Pep C23 error: check parsed source: PEP_RUNTIME_STEP_LIMIT
  Execution step budget exceeded at 2919:13   last_execute_steps=100001
```

**U4 — `run-c23` on `pepin-line-scan.pep`, the program my probes prove runs natively** →
**also refuses during check**:

```
Pep C23 error: check parsed source: PEP_RUNTIME_STEP_LIMIT
  Execution step budget exceeded at 3046:19   last_execute_steps=100001
```

## Why U4 is the more important row

Line-scan's four chunks **check valid** and its `main` **emits and runs correctly on six real files**
(BOOT-A3-034/040, 49/49). Yet the CLI cannot even *check* the same file. The difference is **which
checker runs**:

- the **chunked path** checks one function at a time against the host's analysis — and fits the budget;
- the **one-shot CLI path** typechecks the whole program in a single execute — and does not fit, on
  either app.

That is the same two-layer structure I recorded in BOOT-A3-031 (`open_bytes` performs whole-program
host analysis; the Pep-written checker is invoked per chunk), seen from the user's side. It means the
capability that works is currently reachable **only** through internal host/probe code.

## The precise missing capabilities, named as the packet asks

1. **A CLI way to grant a file's bytes** to `main(source: SourceBytes)` — the `--grant-file` shape the
   SPEC documents. It does not exist; unknown options are rejected, not silently ignored (that at least
   avoids the worst failure mode).
2. **A user-reachable checking path that fits the budget** — either the CLI using the chunked/staged
   path, or the one-shot checker becoming cheaper. Without this, gap 1 alone would not be enough: a
   grant would still hit `PEP_RUNTIME_STEP_LIMIT` before emission on both apps.

Both are A1/A2 territory; **A3 proposes neither and implements nothing.** I record them because the
packet explicitly asks for the missing user-facing capability to be named precisely rather than an
unapproved ABI invented.

## What this does not change

- It does **not** weaken any PROVEN result. Line-scan still provably runs natively over six file
  classes with both compilers; the probe harness is a legitimate, reproducible driver.
- It does **not** claim A1 or A2 misrepresented anything — neither has claimed the CLI grant path
  exists, and A4's SPEC states plainly *"Current slice does NOT claim this command works."*
- It does not touch the frozen target's status: `pepin-source-scan.pep` still has no native result.

## My predictions, scored

| # | Prediction | Result |
|---|---|---|
| U1 | no `--grant-file` in help | **CONFIRMED** |
| U2 | the documented command fails | **CONFIRMED** (unrecognized argument, exit 2) |
| U3 | app without grant reports an honest refusal | **CONFIRMED**, and precisely: a budget refusal during whole-program **check** |
| U4 | line-scan also unrunnable via the CLI | **CONFIRMED** — and for the *check-budget* reason, which I had not anticipated being the blocker |

I expected a grant-shaped failure; the deeper cause is that the CLI's checking path cannot fit these
programs at all.

## Not tested

- Whether a hypothetical CLI grant would use the chunked or one-shot path — not implemented, so not
  measurable.
- `--emit-c` with a grant program: same reason.
- Whether the one-shot check budget could be made to fit; A3 does not propose raising the cap.
- Other CLI subcommands (`inspect`, `check`, `query`, `run`) on these apps: `check` on the app is
  reported valid by A4 and by the host analysis, but I did not re-run the CLI `check` here.

## Reproduce

```powershell
git worktree add --detach <t> 86ff953
cd <t>; pwsh -NoProfile -File ./pep.ps1 run examples/hello.pep
pwsh -NoProfile -File ./pep.ps1 run-c23 examples/dogfood/pepin-source-scan.pep --grant-file examples/dogfood/input_ascii.pep   # exit 2
pwsh -NoProfile -File ./pep.ps1 run-c23 examples/dogfood/pepin-source-scan.pep                                               # budget refusal
```

## Scope

A3 changed only `verification/**`. `pep.ps1`, `pep_c23.py`, A1's checker/contract, A2's emitter and
A4's app were read, not modified. Cap unchanged; no `CURRENT`, manifest, frozen-gate, master or release
change.

REF: GH #16 (BOOT-A3-041).
