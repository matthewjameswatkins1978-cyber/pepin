"""Pep Lab: Living Prompt (step 1) over the existing OCaml seed.

Thin file-backed wrapper. It does NOT change pep_ocaml.ml, the session
protocol, or any accepted language semantics. All evaluation and
inspection delegate to the existing ``pep.ps1`` CLI:

- evaluation: ``pep.ps1 run FILE``
- compiler inspection: ``describe`` / ``check`` / ``inspect`` / ``query --holes``
- persistent definitions: an append-only ``definitions.pep`` store file
  validated with ``check`` before each append
- source export: a plain ``.pep`` file with an explicit dependency header

The in-process ``session --jsonl`` keeps revisions only for its own
lifetime; this wrapper provides persistence by keeping ordinary source
bytes in files, which remain the durable program (Founding Design v0.3).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
PEP = ROOT / "pep.ps1"
STORE_FILENAME = "definitions.pep"

FN_RE = re.compile(r"^\s*fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)


def _run_pep(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(PEP), *args],
        cwd=ROOT, text=True, capture_output=True, check=False, input=input_text,
    )


def cmd_describe() -> dict:
    proc = _run_pep("describe", "--json")
    if proc.returncode != 0:
        raise RuntimeError(f"describe failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def cmd_check(path: pathlib.Path) -> dict:
    proc = _run_pep("check", str(path), "--json")
    if proc.returncode != 0:
        raise RuntimeError(f"check failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def cmd_inspect(path: pathlib.Path) -> dict:
    proc = _run_pep("inspect", str(path), "--json")
    if proc.returncode != 0:
        raise RuntimeError(f"inspect failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def cmd_holes(path: pathlib.Path, offset: int | None = None) -> dict:
    args = ["query", str(path), "--holes", "--json"]
    if offset is not None:
        args += ["--offset", str(offset)]
    proc = _run_pep(*args)
    if proc.returncode != 0:
        raise RuntimeError(f"query failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def cmd_eval(path: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return _run_pep("run", str(path))


def store_path(store_dir: pathlib.Path) -> pathlib.Path:
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir / STORE_FILENAME


def list_definitions(store_dir: pathlib.Path) -> list[str]:
    path = store_dir / STORE_FILENAME
    if not path.exists():
        return []
    return FN_RE.findall(path.read_text(encoding="utf-8"))


def define_source(store_dir: pathlib.Path, snippet: str) -> dict:
    """Validate ``existing defs + snippet`` with ``check``, then append.

    Accepts ``valid`` or ``incomplete`` combined status (holes allowed);
    rejects ``invalid`` so one bad definition cannot poison the store.
    Returns the combined check payload plus the stored function names.
    """
    path = store_path(store_dir)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    combined = existing + ("" if not existing.endswith("\n") and existing else "") + snippet
    if not combined.endswith("\n"):
        combined += "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pep", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(combined)
        tmp_path = pathlib.Path(tmp.name)
    try:
        payload = cmd_check(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    if payload.get("status") == "invalid":
        raise ValueError(f"definition rejected: {payload.get('diagnostics')!r}")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(snippet if snippet.endswith("\n") else snippet + "\n")
    return {"status": payload.get("status"), "functions": FN_RE.findall(snippet)}


def export_store(store_dir: pathlib.Path, output: pathlib.Path) -> dict:
    """Write the stored definitions to ``output`` with an explicit header."""
    src = store_dir / STORE_FILENAME
    if not src.exists():
        raise FileNotFoundError(f"no lab store at {src}")
    body = src.read_text(encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    names = FN_RE.findall(body)
    header = (
        "# Pep Lab export: ordinary source, explicit dependencies only.\n"
        f"# store_sha256: {digest}\n"
        f"# definitions: {', '.join(names) if names else '(none)'}\n"
        "# Common lab modules are NOT implicit; import by pasting this file.\n"
    )
    output.write_text(header + body, encoding="utf-8")
    return {"output": str(output), "sha256": digest, "definitions": names}


def eval_with_store(store_dir: pathlib.Path, main_source: str) -> subprocess.CompletedProcess[str]:
    """Evaluate ``stored defs + main_source`` via a temp file with ``run``."""
    src = store_dir / STORE_FILENAME
    defs = src.read_text(encoding="utf-8") if src.exists() else ""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pep", delete=False, encoding="utf-8", dir=ROOT
    ) as tmp:
        # dir=ROOT keeps Resolve-Path simple on Windows; removed afterwards.
        tmp.write(defs + main_source)
        tmp_path = pathlib.Path(tmp.name)
    try:
        return cmd_eval(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pep Lab Living Prompt (step 1)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_eval = sub.add_parser("eval", help="evaluate a .pep file with the seed interpreter")
    p_eval.add_argument("file")

    p_check = sub.add_parser("check", help="compiler check with JSON output")
    p_check.add_argument("file")

    p_inspect = sub.add_parser("inspect", help="compiler inspect with JSON output")
    p_inspect.add_argument("file")

    p_holes = sub.add_parser("holes", help="typed-hole query with JSON output")
    p_holes.add_argument("file")
    p_holes.add_argument("--offset", type=int, default=None)

    sub.add_parser("describe", help="compiler identity with JSON output")

    p_define = sub.add_parser("define", help="validate and persist a definition snippet")
    p_define.add_argument("--store", required=True)
    group = p_define.add_mutually_exclusive_group(required=True)
    group.add_argument("--source", default=None)
    group.add_argument("--file", default=None)

    p_show = sub.add_parser("show", help="list persisted definition names")
    p_show.add_argument("--store", required=True)

    p_export = sub.add_parser("export", help="export store to a plain .pep file")
    p_export.add_argument("--store", required=True)
    p_export.add_argument("--output", required=True)

    p_run = sub.add_parser("eval-store", help="evaluate snippet on top of stored defs")
    p_run.add_argument("--store", required=True)
    p_run.add_argument("--file", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "eval":
            proc = cmd_eval(pathlib.Path(args.file))
            sys.stdout.write(proc.stdout)
            sys.stderr.write(proc.stderr)
            return proc.returncode
        if args.command == "check":
            print(json.dumps(cmd_check(pathlib.Path(args.file)), indent=2))
            return 0
        if args.command == "inspect":
            print(json.dumps(cmd_inspect(pathlib.Path(args.file)), indent=2))
            return 0
        if args.command == "holes":
            print(json.dumps(cmd_holes(pathlib.Path(args.file), args.offset), indent=2))
            return 0
        if args.command == "describe":
            print(json.dumps(cmd_describe(), indent=2))
            return 0
        if args.command == "define":
            snippet = args.source if args.source is not None else pathlib.Path(args.file).read_text(encoding="utf-8")
            print(json.dumps(define_source(pathlib.Path(args.store), snippet), indent=2))
            return 0
        if args.command == "show":
            print(json.dumps({"store": args.store, "definitions": list_definitions(pathlib.Path(args.store))}, indent=2))
            return 0
        if args.command == "export":
            print(json.dumps(export_store(pathlib.Path(args.store), pathlib.Path(args.output)), indent=2))
            return 0
        if args.command == "eval-store":
            main_source = pathlib.Path(args.file).read_text(encoding="utf-8")
            proc = eval_with_store(pathlib.Path(args.store), main_source)
            sys.stdout.write(proc.stdout)
            sys.stderr.write(proc.stderr)
            return proc.returncode
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
