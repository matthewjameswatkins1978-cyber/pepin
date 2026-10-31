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

## Interactive REPL (Milestone 2)

`python pep_lab.py repl --store DIR` opens a text prompt over the same
compiler. Type Pep code (several lines if needed); a blank line checks
``stored definitions + buffer`` and reports `valid`,
`incomplete: holes [...]`, or `invalid: CODE message @ line:col`.

- `:run` evaluates the buffer once against the store and prints output.
- `:def` validates and persists the buffer, then clears it. Rejection
  keeps the buffer so it can be corrected (`:clear`/`:pop` discard).
- `:check`, `:holes`, `:show`, `:export FILE`, `:describe`, `:help`, `:quit`.
- Buffers are ad-hoc: quitting never writes, and nothing re-executes.
- Note: `query --holes` names holes `identity` where `check` uses `name`;
  the REPL accepts both.

## Compiler-aware output (Milestone 3)

- Invalid diagnostics render the offending source line with a caret under
  the reported column, in addition to `CODE message @ line:col`.
- `:holes` appends the compiler's fill candidates (`try: n`) when known.
- `:info` lists stored definitions with their compiler-checked signatures
  (`fn double(n: Int) -> Int`) plus the numbered buffer contents.
- No new semantics are claimed: file-backed sources only, no incremental
  compilation, no revision-aware session state beyond ordinary files.

## Dogfooding demos (Milestone 4)

- `examples/lab_shapes.pep`: records, tagged unions, `match`, lists and
  `for` loops -- shape areas and a gallery total (outputs 12/12/27).
- `examples/lab_text_table.pep`: text output via `say`/`int_text`
  composition over lists and function calls (outputs 42/54 tables).
- `examples/lab_session.txt`: scripted REPL workflow -- define, `:info`,
  use, `:run`, typed-error rejection, correction, `:show`, `:quit`.
  Pipe it into `repl --store` for a reproducible interactive demo.
- Known language boundary met while dogfooding: `Str` has no
  concatenation operator, so multi-value lines are separate `say` calls.
  No compiler change proposed; recorded here as observed behavior.

## Hardening and packaging (Milestone 5)

- `pep-lab.ps1` forwards to `pep_lab.py` with repo-style `--help`, matching
  `pep.ps1` conventions. Non-interactive commands emit JSON for machines;
  the REPL is deliberately human-readable text.
- Corrupt stores (non-UTF-8 bytes) report `store file is not valid UTF-8`
  with exit 2 instead of a codec traceback; the store is never modified.
- Platform boundary (verified, not assumed): PowerShell wrapper scripts
  using `ValueFromRemainingArguments` cannot take piped stdin -- `pep.ps1`
  `session --jsonl` behaves the same way. Interactive use runs the `repl`
  command directly; scripted sessions drive `python pep_lab.py` with stdin
  (as `tests/test_lab.py` does) or the in-process `ReplSession` API.
- Sartorial reuse investigated and declined: no Sartorial code exists in
  this repo, and Matthew's 28 Oct priorities explicitly defer a
  Sartorial/Rust-tool migration. No new presentation dependency added.
- `readline`-style history investigated and declined: unavailable in
  Windows stock Python; no third-party dependency for appearance's sake.

## Recommended next layer

Defer graphics/audio: the seed exposes no canvas, image, or sound
builtins, so a Living Canvas/ Pulse would need new compiler-approved host
capabilities first -- a product-scope decision, not a REPL tweak. The
nearest supported value is named experiment buffers (`:save`/`:load` as
ordinary `.pep` files beside the store), reusing only existing file and
check/run machinery.

## Limits

- No `pep_ocaml.ml` change, no new builtin, no protocol version change.
- No `CURRENT.md` / `manifest.json` advance; A10 remains the next design gate.
- Demo: `examples/lab_demo.pep`. Tests: `python -m unittest tests.test_lab -v`.
