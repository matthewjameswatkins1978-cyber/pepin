"""Pep Lab Persistent Workshop: project workspaces over ordinary files.

A workshop *root* is a plain directory. Each subdirectory holding a
``project.json`` is a project; a subdirectory with ``definitions.pep`` or
``buffers/`` but no ``project.json`` is a legacy Pep Lab store and is
adopted seamlessly on first open (contents preserved, ``project.json``
added). There is no database and no second source representation: a
project directory *is* a Pep Lab store directory, so every existing
``--store DIR`` workflow keeps working unchanged.

Layout::

    <root>/
      active.json            -- {"active": "<name>"}; absent means none
      <name>/
        project.json         -- {"schema": 1, "name": ..., ...}
        definitions.pep      -- persisted definitions (as before)
        buffers/             -- named experiment buffers (as before)
        checkpoints/         -- W2 source revisions
        experiments/         -- W3 repeatable experiment records

``active.json`` records the last opened project so a developer can leave
Pep Lab and resume where they were.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile

WORKSHOP_SCHEMA = 1
PROJECT_FILENAME = "project.json"
ACTIVE_FILENAME = "active.json"
STORE_FILENAME = "definitions.pep"
BUFFERS_DIRNAME = "buffers"

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
RESERVED_NAMES = {"active.json", PROJECT_FILENAME}


def check_name(kind: str, name: str | None) -> str:
    if not name or not NAME_RE.match(name) or name in RESERVED_NAMES:
        raise ValueError(
            f"bad {kind} name {name!r}: use 1-64 letters/digits/_/-, starting alphanumeric")
    return name


def _atomic_write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".tmp", delete=False, encoding="utf-8",
        newline="\n", dir=str(path.parent),
    ) as tmp:
        tmp.write(text)
        tmp_path = pathlib.Path(tmp.name)
    os.replace(tmp_path, path)


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def project_dir(root: pathlib.Path, name: str) -> pathlib.Path:
    return root / check_name("project", name)


def project_meta_file(proj: pathlib.Path) -> pathlib.Path:
    return proj / PROJECT_FILENAME


def read_project_meta(proj: pathlib.Path) -> dict:
    meta_file = project_meta_file(proj)
    try:
        payload = json.loads(meta_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"not a project: {proj}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"project metadata is corrupt: {meta_file} ({exc})") from exc
    if not isinstance(payload, dict) or payload.get("schema") != WORKSHOP_SCHEMA:
        raise ValueError(f"project metadata is corrupt or unsupported: {meta_file}")
    return payload


def is_legacy_store(proj: pathlib.Path) -> bool:
    return proj.is_dir() and not project_meta_file(proj).exists() and (
        (proj / STORE_FILENAME).exists() or (proj / BUFFERS_DIRNAME).is_dir())


def adopt_legacy_store(proj: pathlib.Path, name: str) -> dict:
    """Write project.json for a pre-existing store dir; contents untouched."""
    meta = {"name": name, "schema": WORKSHOP_SCHEMA, "created_utc": _utcnow(),
            "tool": "pep_workshop/1", "adopted": True}
    _atomic_write_text(project_meta_file(proj),
                       json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


def create_project(root: pathlib.Path, name: str) -> dict:
    name = check_name("project", name)
    proj = root / name
    if project_meta_file(proj).exists():
        raise ValueError(f"project already exists: {name!r}")
    if proj.is_file() or (proj.exists() and not proj.is_dir()):
        raise ValueError(f"cannot create project over a non-directory: {proj}")
    if is_legacy_store(proj):
        meta = adopt_legacy_store(proj, name)
        return {"project": name, "dir": str(proj), "adopted": True, "meta": meta}
    proj.mkdir(parents=True, exist_ok=True)
    meta = {"name": name, "schema": WORKSHOP_SCHEMA, "created_utc": _utcnow(),
            "tool": "pep_workshop/1"}
    _atomic_write_text(project_meta_file(proj),
                       json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return {"project": name, "dir": str(proj), "adopted": False, "meta": meta}


def list_projects(root: pathlib.Path) -> dict:
    entries = []
    if root.is_dir():
        for child in sorted(root.iterdir(), key=lambda p: p.name):
            if not child.is_dir() or child.is_symlink():
                continue
            name = child.name
            if not NAME_RE.match(name) or name in RESERVED_NAMES:
                continue
            if project_meta_file(child).exists():
                try:
                    meta = read_project_meta(child)
                    entries.append({"name": name, "status": "ok",
                                    "created_utc": meta.get("created_utc"),
                                    "adopted": bool(meta.get("adopted"))})
                except ValueError:
                    entries.append({"name": name, "status": "corrupt"})
            elif is_legacy_store(child):
                entries.append({"name": name, "status": "legacy"})
    return {"root": str(root), "active": read_active(root), "projects": entries}


def _active_file(root: pathlib.Path) -> pathlib.Path:
    return root / ACTIVE_FILENAME


def read_active(root: pathlib.Path) -> str | None:
    active_file = _active_file(root)
    if not active_file.exists():
        return None
    try:
        payload = json.loads(active_file.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"active pointer is corrupt: {active_file} ({exc})") from exc
    active = payload.get("active") if isinstance(payload, dict) else None
    if not isinstance(active, str) or not active:
        raise ValueError(f"active pointer is corrupt: {active_file}")
    return active


def write_active(root: pathlib.Path, name: str) -> None:
    _atomic_write_text(_active_file(root),
                       json.dumps({"active": name}, indent=2, sort_keys=True) + "\n")


def open_project(root: pathlib.Path, name: str) -> dict:
    """Open (and adopt if legacy) a project; records it as active."""
    name = check_name("project", name)
    proj = root / name
    if not proj.is_dir():
        raise FileNotFoundError(f"no such project: {name!r}")
    adopted = False
    if not project_meta_file(proj).exists():
        if not is_legacy_store(proj):
            raise FileNotFoundError(f"not a project: {name!r}")
        adopt_legacy_store(proj, name)
        adopted = True
    else:
        read_project_meta(proj)  # fail cleanly on corruption
    root.mkdir(parents=True, exist_ok=True)
    write_active(root, name)
    return {"project": name, "dir": str(proj), "adopted": adopted, "active": name}


def resolve_project_dir(root: pathlib.Path, name: str | None) -> pathlib.Path:
    """Resolve a project directory: named, else the active pointer."""
    if name is not None:
        check_name("project", name)
        proj = root / name
        if not proj.is_dir() or not project_meta_file(proj).exists():
            raise FileNotFoundError(f"no such project: {name!r}")
        return proj
    active = read_active(root)
    if active is None:
        raise FileNotFoundError(f"no active project in {root}; open one first")
    return resolve_project_dir(root, active)


def project_source_digest(proj: pathlib.Path) -> str:
    """SHA-256 of the project's current definitions source (may be empty)."""
    store = proj / STORE_FILENAME
    data = store.read_bytes() if store.exists() else b""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def run_project_repl(root: pathlib.Path, name: str | None) -> int:
    """Open the interactive prompt on a project's store directory."""
    try:
        from pep_lab import run_repl
    except ImportError as exc:
        raise RuntimeError(f"pep_lab.py is required next to pep_workshop.py: {exc}") from exc
    return run_repl(resolve_project_dir(root, name))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pep Lab Persistent Workshop")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="create (or adopt) a project")
    p_create.add_argument("--root", required=True)
    p_create.add_argument("--name", required=True)

    p_list = sub.add_parser("list", help="list projects in a root")
    p_list.add_argument("--root", required=True)

    p_open = sub.add_parser("open", help="open a project and mark it active")
    p_open.add_argument("--root", required=True)
    p_open.add_argument("--name", required=True)

    p_active = sub.add_parser("active", help="show the active project")
    p_active.add_argument("--root", required=True)

    p_dir = sub.add_parser("dir", help="print a project directory (default: active)")
    p_dir.add_argument("--root", required=True)
    p_dir.add_argument("--name", default=None)

    p_repl = sub.add_parser("repl", help="interactive prompt on a project")
    p_repl.add_argument("--root", required=True)
    p_repl.add_argument("--project", default=None)

    args = parser.parse_args(argv)
    try:
        root = pathlib.Path(args.root)
        if args.command == "create":
            print(json.dumps(create_project(root, args.name), indent=2))
        elif args.command == "list":
            print(json.dumps(list_projects(root), indent=2))
        elif args.command == "open":
            print(json.dumps(open_project(root, args.name), indent=2))
        elif args.command == "active":
            print(json.dumps({"root": str(root), "active": read_active(root)}, indent=2))
        elif args.command == "dir":
            print(json.dumps({"dir": str(resolve_project_dir(root, args.name))}, indent=2))
        elif args.command == "repl":
            return run_project_repl(root, args.project)
        return 0
    except (RuntimeError, ValueError, FileNotFoundError, OSError,
            UnicodeDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
