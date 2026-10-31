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

`active.json` in the root remembers the last opened project across
process restarts. Names allow letters/digits/`_`/`-` (max 64); corrupt
metadata and unknown projects fail with clean JSON errors, never
tracebacks. Tests: `python -m unittest tests.test_workshop -v`.
