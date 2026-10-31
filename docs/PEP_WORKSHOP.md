# Pep Lab Persistent Workshop

Durable, source-first project environment over the existing Pep Lab store
and seed compiler. Ordinary `.pep` files stay authoritative; the compiler
stays the sole semantic authority. No database, no new language.

## Projects (W1)

A workshop *root* is a plain directory; each subdirectory with a
`project.json` is a project. A project directory **is** a Pep Lab store
directory (`definitions.pep`, `buffers/`), so all existing `--store DIR`
workflows keep working. Directories with store files but no `project.json`
are legacy stores and are adopted on first open with contents preserved.

- `python pep_workshop.py create --root DIR --name NAME`
- `python pep_workshop.py list --root DIR` (JSON: projects + active)
- `python pep_workshop.py open --root DIR --name NAME` (marks active)
- `python pep_workshop.py active --root DIR`
- `python pep_workshop.py dir --root DIR [--name NAME]` (for scripts)
- `python pep_workshop.py repl --root DIR [--project NAME]` (defaults active)

## Checkpoints (W2)

- `checkpoint save --root DIR --project NAME [--label L}` snapshots the
  current `definitions.pep` bytes immutably as `checkpoints/cp-NNN.pep`
  with a JSON sidecar (`digest`, byte count, UTC time, label).
- Identity is `sha256:` over exact source bytes (`revision_kind:
  workshop-file-sha256`), distinct from the compiler's session revisions.
- `checkpoint list` / `checkpoint show --id cp-NNN` inspect revisions;
  a corrupt `index.json` is rebuilt from the snapshot files on disk.
- Empty projects snapshot honestly (0 bytes); bad ids and unknown
  projects fail with clean errors. Restore/diff arrive in the next slice
  with preview-before-write protection and no automatic execution.
- `checkpoint diff --a cp-001 --b current` (either side may be a snapshot
  id or `current`) shows a unified line diff; `identical: true` when equal.
- `checkpoint restore --id cp-001` previews only and changes nothing;
  `--apply` performs the restore atomically; `--expect DIGEST` refuses on
  conflict. Restoring is a file operation and never executes code.

## Experiments (W3)

- `experiment record --root DIR --project NAME --kind check|inspect|holes
  [--label L] [--run]` runs one compiler flow against the current source
  and records it as `experiments/exp-NNN.json` with the source digest,
  byte count, compiler identity digest, check status (plus diagnostics or
  typed holes), and -- only with explicit `--run` -- one execution
  observation (stdout/stderr/return code). Recording never executes unless
  `--run` is passed; check/inspect/holes kinds are side-effect free.
- `experiment list` marks each record `stale` when the live source digest
  differs, and `compiler_changed` when the compiler identity differs.
- `experiment show` returns the full record; `experiment rerun --id`
  re-runs the flow against current source, compares statuses, and leaves
  the stored record untouched. Observations are historical evidence, not
  current compiler facts.

## Inspection (W4)

- `inspect --root DIR --project NAME [--revision current|cp-NNN]` runs
  the compiler on the exact bytes of the live source or a checkpoint
  snapshot and returns a compact view: status, diagnostic codes/messages/
  spans, typed holes with fill suggestions, and checked function
  signatures. No AST dumps, no caching: every call re-runs the compiler,
  and the reported digest pins each fact to its revision.
- Checkpoint snapshots are integrity-checked against their recorded digest
  before inspection; tampering fails loudly instead of yielding facts.

`active.json` in the root remembers the last opened project across
process restarts. Names allow letters/digits/`_`/`-` (max 64); corrupt
metadata and unknown projects fail with clean JSON errors, never
tracebacks. Tests: `python -m unittest tests.test_workshop -v`.
