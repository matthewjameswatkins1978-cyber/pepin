# PRE-REGISTRATION A3-041: does the documented user-facing command actually exist and run the app?

**Seat:** A3. **Written and committed before measurement.**

## Why this is the right check now

The packet's first objective says, of the source inspector:

> Ideally expose the result through a normal CLI; if the current output contract only returns `Int`,
> demonstrate the real native result honestly and **name the precise missing user-facing I/O
> capability** rather than adding an unapproved new ABI.

A4's `SPEC.md` documents the contract a user is meant to run:

```powershell
.\pep.ps1 run-c23 examples/dogfood/pepin-source-scan.pep --grant-file examples/dogfood/input_ascii.pep
# expected: 23
```

and states plainly: *"Current slice does NOT claim this command works; it defines the contract A1/A2
implement against."* **Nobody has checked whether it works.** Every gate I have run (including the
PROVEN 49/49 line-scan gate) drives the app through an **A3 probe harness** — a Python driver that
speaks the session protocol directly. That is not a user-facing path.

So there is a real possibility that the application runs natively **and yet no user-reachable command
can run it**, which is exactly the gap the packet asks to be named precisely.

## Checks

All read-only, on a clean worktree at A1 `86ff953` (carries the apps and the chunk tooling), seed built
there. Nothing is edited.

| # | check | predicted |
|---|---|---|
| U1 | `pep.ps1 --help` advertises a `--grant-file`-style option for `run-c23`/`build-c23` | **no** — I saw the option list earlier and it had only `--compiler` and `--emit-c` |
| U2 | the exact documented command runs and prints `23` | **fails** — unknown/unsupported option, or the app is refused |
| U3 | `run-c23` on the app **without** any grant option at least reports an honest refusal rather than a wrong number or a crash | reports something, exact behaviour recorded |
| U4 | the same for `pepin-line-scan.pep`, a program my probes proved runs natively | **also unrunnable via the CLI**, because it needs the same `SourceBytes` grant |

**Prediction: U1 and U2 both "no", and the precise missing capability is a way to grant a file's bytes
to `main(source: SourceBytes)` from the CLI.** If instead U2 works, my prediction is wrong and the
user-facing path is fine — which would be a materially better result and would be reported as such.

## What is and is not being questioned

- **Not** questioning A1's or A2's work: no receipt of theirs claims the CLI grant path exists.
- **Not** proposing an ABI change. A2's receipt 46 already raised a "chunk-window ask"; this is a
  different, user-facing question and A3 implements nothing.
- **Only** establishing what a user can actually do today, with exact commands and exact output, so the
  gap can be stated precisely instead of being rediscovered later.

## Method and honesty

Exact commands and exact outputs are recorded verbatim, including stderr and exit codes. If an option
is silently ignored rather than rejected — the worst case, because it would look like it worked — that
will be reported prominently.

## Scope guard

A3 owns only `verification/**`. No edits to `pep.ps1`, `pep_c23.py`, A1's checker/contract, A2's
emitter, or A4's app and SPEC. Cap unchanged; no `CURRENT`, manifest, frozen-gate, master or release
change.
