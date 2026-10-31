# Pep Lab — Living Prompt (step 1)

File-backed interactive wrapper over the existing OCaml seed. It changes
no compiler semantics and claims no new packet acceptance.

## What it does

- **Evaluation:** `python pep_lab.py eval FILE` runs `pep.ps1 run FILE`.
- **Persistent definitions:** `define --store DIR (--source SNIPPET | --file F)`
  validates `existing defs + snippet` with `check` and appends only when the
  combined source is `valid` or `incomplete`. `invalid` is rejected and the
  store is unchanged.
- **Source export:** `export --store DIR --output FILE` writes a plain `.pep`
  file with an explicit header (`store_sha256`, definition names). No lab
  module is implicit; the exported file is the durable program.
- **Compiler inspection:** `describe`, `check`, `inspect`, `holes` pass
  through to the existing CLI JSON (`schemaVersion` 2/3).

`eval-store --store DIR --file MAIN.pep` evaluates stored definitions plus
a main snippet in a temporary file. The in-process `session --jsonl`
remains ephemeral; persistence here means ordinary source bytes in files.

## Reliability (Milestone 1)

- `check` exits nonzero for incomplete/invalid programs but still emits its
  JSON payload; the wrapper reads the payload (not the exit code) to tell
  valid/incomplete/invalid apart from a genuine transport failure.
- Store updates and exports are atomic (same-directory temp file + replace).
- All temp writes use `newline="\n"` so Windows text mode never rewrites
  stored source bytes to CRLF.
- Every compiler subprocess has a 120s timeout; missing executables, hangs
  and malformed JSON surface as clean errors, never tracebacks.
- Rejected (invalid/duplicate) definitions leave the existing store
  byte-identical; diagnostics carry the compiler's exact error code.

## Limits

- No `pep_ocaml.ml` change, no new builtin, no protocol version change.
- No `CURRENT.md` / `manifest.json` advance; A10 remains the next design gate.
- Demo: `examples/lab_demo.pep`. Tests: `python -m unittest tests.test_lab -v`.
